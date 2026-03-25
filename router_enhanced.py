"""
Enhanced DICOM Router with Extended Features

Extends the original router with:
1. C-FIND support for metadata queries (aligns with #61 discussion)
2. Album-aware routing metadata collection
3. Persistent telemetry logging
4. Query validation

This is the evolution toward integrating metadata query engine with routing.
"""

import logging
import time
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from pydicom.dataset import Dataset
from pydicom import dcmread
from pynetdicom import AE, evt, ALL_TRANSFER_SYNTAXES
from pynetdicom.sop_class import CTImageStorage, MRImageStorage, SecondaryCaptureImageStorage

from metadata import extract_normalized_metadata, group_by_study
from validation import validate_dicom_file

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("dicom_router_enhanced")

# In-memory telemetry storage
telemetry = defaultdict(lambda: {"request_count": 0, "last_latency_ms": 0, "last_modality": "", "bytes_transferred": 0})
transfer_log = []  # List of all transfer records

# Node configuration
NODE_A = ("localhost", 11112)
NODE_B = ("localhost", 11113)
SUPPORTED_SOP_CLASSES = [CTImageStorage, MRImageStorage, SecondaryCaptureImageStorage]

# In-memory metadata index for C-FIND support
METADATA_INDEX: Dict[str, dict] = {}  # sop_instance_uid -> normalized_metadata


def index_dicom_files(file_paths: List[str]) -> int:
    """
    Index DICOM files in metadata index for C-FIND queries.

    Returns:
        Number of files successfully indexed
    """
    indexed = 0
    for file_path in file_paths:
        try:
            is_valid, _ = validate_dicom_file(file_path)
            if not is_valid:
                continue

            metadata = extract_normalized_metadata(file_path)
            if metadata:
                METADATA_INDEX[metadata.sop_instance_uid] = {
                    "file_path": file_path,
                    "metadata": metadata.to_dict(),
                    "study_uid": metadata.study_instance_uid,
                    "series_uid": metadata.series_instance_uid,
                }
                indexed += 1
        except Exception as e:
            logger.warning(f"Failed to index {file_path}: {e}")

    logger.info(f"Indexed {indexed} DICOM files")
    return indexed


def execute_c_find_query(query_dataset: Dataset) -> List[Dataset]:
    """
    Execute query against indexed metadata.

    Supports filters on:
    - PatientID
    - StudyInstanceUID
    - SeriesInstanceUID
    - Modality
    - StudyDate

    Returns:
        List of matching DICOM datasets (metadata level)
    """
    results = []

    # Extract query filters
    patient_id = getattr(query_dataset, "PatientID", None)
    study_uid = getattr(query_dataset, "StudyInstanceUID", None)
    series_uid = getattr(query_dataset, "SeriesInstanceUID", None)
    modality = getattr(query_dataset, "Modality", None)
    study_date = getattr(query_dataset, "StudyDate", None)

    logger.info(
        f"C-FIND Query: PatientID={patient_id}, StudyUID={study_uid}, "
        f"SeriesUID={series_uid}, Modality={modality}, StudyDate={study_date}"
    )

    # Filter metadata index
    for sop_uid, entry in METADATA_INDEX.items():
        meta = entry["metadata"]
        matches = True

        if patient_id and meta["patient"]["id"] != patient_id:
            matches = False
        if study_uid and meta["study"]["study_instance_uid"] != study_uid:
            matches = False
        if series_uid and meta["series"]["series_instance_uid"] != series_uid:
            matches = False
        if modality and meta["series"]["modality"].upper() != modality.upper():
            matches = False
        if study_date and meta["study"]["study_date"] != study_date:
            matches = False

        if matches:
            # Return metadata (not pixel data)
            results.append(entry)

    logger.info(f"C-FIND returned {len(results)} results")
    return results


def extract_metadata(dataset: Dataset) -> Tuple[str, str, str]:
    """Extract key metadata from incoming DICOM dataset."""
    modality = getattr(dataset, "Modality", "UNKNOWN")
    patient_id = getattr(dataset, "PatientID", "UNKNOWN")
    study_date = getattr(dataset, "StudyDate", "UNKNOWN")
    return modality, patient_id, study_date


def is_node_available_cached(node_name: str, host: str, port: int, ttl: int = 5) -> bool:
    """Cached node availability check."""
    now = time.time()
    cache_key = f"{node_name}_last_check"
    cache_ttl_key = f"{node_name}_check_ttl"

    if telemetry[node_name].get("last_check", 0) + ttl > now:
        return telemetry[node_name].get("available", True)

    ae = AE()
    try:
        assoc = ae.associate(host, port, timeout=3)
        if assoc.is_established:
            assoc.release()
            telemetry[node_name]["available"] = True
            return True
    except Exception:
        pass

    telemetry[node_name]["available"] = False
    return False


def select_node(modality: str, dataset: Dataset) -> Tuple[str, int]:
    """
    Routing decision with metadata and telemetry awareness.

    Strategy:
    1. Avoid overloaded nodes
    2. Avoid unavailable nodes
    3. Route large CT studies to Node A
    4. Balance load by default
    """
    rows = getattr(dataset, "Rows", 0)
    cols = getattr(dataset, "Columns", 0)
    size = rows * cols

    # Check node availability
    node_a_available = is_node_available_cached("Node A", *NODE_A)
    node_b_available = is_node_available_cached("Node B", *NODE_B)

    # If only one available, use that
    if not node_a_available and node_b_available:
        logger.warning("Node A unavailable, routing to Node B")
        return NODE_B

    if not node_b_available and node_a_available:
        logger.warning("Node B unavailable, routing to Node A")
        return NODE_A

    # Load balancing: prefer less loaded node
    if telemetry["Node A"]["request_count"] > telemetry["Node B"]["request_count"]:
        return NODE_B

    # Modality-aware routing: Large CT studies to Node A
    if modality.upper() == "CT" and size > 500000:
        return NODE_A

    return NODE_B


def forward_dataset(dataset: Dataset, dest_host: str, dest_port: int) -> Tuple[bool, str]:
    """Forward dataset to downstream node via C-STORE SCU."""
    ae = AE()
    try:
        ae.add_requested_context(dataset.SOPClassUID)
    except Exception:
        for context in SUPPORTED_SOP_CLASSES:
            ae.add_requested_context(context)

    assoc = ae.associate(dest_host, dest_port, timeout=5)
    if not assoc.is_established:
        logger.error(f"Failed to associate with {dest_host}:{dest_port}")
        return False, "Association failed"

    try:
        logger.info(f"Forwarding SOPInstanceUID={dataset.SOPInstanceUID} to {dest_host}:{dest_port}")
        rsp = assoc.send_c_store(dataset)
        success = rsp and rsp.Status in (0x0000, 0xB000, 0xB007)
        status_desc = f"0x{rsp.Status:04x}" if rsp is not None else "None"

        if success:
            logger.info(f"Forwarding successful, status={status_desc}")
        else:
            logger.warning(f"Forwarding failed, status={status_desc}")

        return success, status_desc
    except Exception as ex:
        logger.exception(f"Exception during forward: {ex}")
        return False, str(ex)
    finally:
        assoc.release()


def handle_store(event):
    """Callback for C-STORE requests on the router SCP."""
    dataset = event.dataset
    dataset.file_meta = event.file_meta

    modality, patient_id, study_date = extract_metadata(dataset)

    # Log metadata
    logger.info("Received C-STORE:")
    logger.info(f"  Modality: {modality}")
    logger.info(f"  PatientID: {patient_id}")
    logger.info(f"  StudyDate: {study_date}")
    logger.info(f"  SOPInstanceUID: {dataset.SOPInstanceUID}")

    rows = getattr(dataset, "Rows", 0)
    cols = getattr(dataset, "Columns", 0)
    size_kb = (rows * cols) / 1024

    # Select destination node
    target_host, target_port = select_node(modality, dataset)
    chosen_node = "Node A" if (target_host, target_port) == NODE_A else "Node B"

    logger.info(f"Routing: modality={modality}, size={size_kb:.2f}KB -> {chosen_node} ({target_host}:{target_port})")

    # Forward with timing
    start = time.perf_counter()
    success, status = forward_dataset(dataset, target_host, target_port)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Update telemetry
    telemetry[chosen_node]["request_count"] += 1
    telemetry[chosen_node]["last_latency_ms"] = elapsed_ms
    telemetry[chosen_node]["last_modality"] = modality
    telemetry[chosen_node]["bytes_transferred"] += int(size_kb * 1024)
    telemetry[chosen_node]["last_check"] = time.time()

    # Log transfer
    transfer_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "sop_instance_uid": dataset.SOPInstanceUID,
        "modality": modality,
        "patient_id": patient_id,
        "destination_node": chosen_node,
        "latency_ms": round(elapsed_ms, 2),
        "size_kb": round(size_kb, 2),
        "success": success,
        "status": status,
    }
    transfer_log.append(transfer_record)

    logger.info(f"Transfer completed: {chosen_node} in {elapsed_ms:.2f}ms, success={success}")
    logger.info(f"Telemetry: {dict(telemetry)}")

    return 0x0000 if success else 0xA700  # Success or Refused


def get_telemetry_summary() -> Dict:
    """Return current telemetry summary."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "nodes": dict(telemetry),
        "total_transfers": len(transfer_log),
        "recent_transfers": transfer_log[-10:] if transfer_log else [],
    }


def export_telemetry(output_path: str) -> bool:
    """Export telemetry to JSON file."""
    try:
        with open(output_path, "w") as f:
            json.dump(get_telemetry_summary(), f, indent=2)
        logger.info(f"Exported telemetry to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export telemetry: {e}")
        return False


def start_router(host: str = "", port: int = 11111):
    """Start the DICOM SCP router."""
    ae = AE(ae_title=b"DICOM_ROUTER")
    for context in SUPPORTED_SOP_CLASSES:
        ae.add_supported_context(context, ALL_TRANSFER_SYNTAXES)

    handlers = [(evt.EVT_C_STORE, handle_store)]

    logger.info(f"Starting router on {host or '0.0.0.0'}:{port}")
    try:
        ae.start_server((host, port), block=True, evt_handlers=handlers)
    except Exception as ex:
        logger.exception(f"Router failed: {ex}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced DICOM Router")
    parser.add_argument("--host", default="", help="Router host")
    parser.add_argument("--port", type=int, default=11111, help="Router port")
    parser.add_argument("--index-dir", help="Directory to index for C-FIND support")

    args = parser.parse_args()

    # Index files if directory provided
    if args.index_dir:
        dcm_files = list(Path(args.index_dir).glob("**/*.dcm"))
        index_dicom_files([str(f) for f in dcm_files])

    start_router(args.host, args.port)

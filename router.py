import logging
import time
from collections import defaultdict

from pydicom.dataset import Dataset
from pydicom import dcmread
from pynetdicom import AE, evt, ALL_TRANSFER_SYNTAXES
from pynetdicom.sop_class import CTImageStorage, MRImageStorage, SecondaryCaptureImageStorage

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("dicom_router")

# In-memory telemetry counters
telemetry = defaultdict(int)
last_health_check = {"Node A": 0, "Node B": 0}

NODE_A = ("localhost", 11112)
NODE_B = ("localhost", 11113)

SUPPORTED_SOP_CLASSES = [CTImageStorage, MRImageStorage, SecondaryCaptureImageStorage]


def extract_metadata(dataset: Dataset):
    """Extract key metadata from incoming DICOM dataset. Returns safe defaults if missing."""
    modality = getattr(dataset, "Modality", "UNKNOWN")
    patient_id = getattr(dataset, "PatientID", "UNKNOWN")
    study_date = getattr(dataset, "StudyDate", "UNKNOWN")
    return modality, patient_id, study_date


def is_node_available_cached(node_name: str, host: str, port: int, ttl: int = 5) -> bool:
    """Cached node availability check to avoid frequent health checks."""
    now = time.time()
    last = last_health_check.get(node_name, 0)
    if now - last > ttl:
        last_health_check[node_name] = now
        ae = AE()
        assoc = ae.associate(host, port, timeout=5)
        if assoc.is_established:
            assoc.release()
            return True
        return False
    return True


"""
Routing strategy:
1. Avoid overloaded nodes (telemetry)
2. Avoid unavailable nodes (health check)
3. Route large CT studies to Node A
4. Default to Node B
"""

def select_node(modality: str, dataset: Dataset):
    """Routing decision with metadata and telemetry awareness."""
    rows = getattr(dataset, "Rows", 0)
    cols = getattr(dataset, "Columns", 0)
    size = rows * cols

    # prefer the lighter node if Node A is heavier already
    if telemetry["Node A"] > telemetry["Node B"]:
        return NODE_B

    # if Node A down for any reason, route to Node B
    if not is_node_available_cached("Node A", *NODE_A):
        logger.warning("Node A unavailable, routing to Node B")
        return NODE_B

    if modality.upper() == "CT" and size > 500000:
        return NODE_A

    return NODE_B


def forward_dataset(dataset: Dataset, dest_host: str, dest_port: int):
    """Forward dataset to downstream node via C-STORE SCU."""
    ae = AE()
    try:
        ae.add_requested_context(dataset.SOPClassUID)
    except Exception:
        # Fallback for unknown SOPClassUID
        for context in SUPPORTED_SOP_CLASSES:
            ae.add_requested_context(context)

    assoc = ae.associate(dest_host, dest_port, timeout=5)
    if not assoc.is_established:
        logger.error("Failed to associate with %s:%d", dest_host, dest_port)
        return False, "Association failed"

    try:
        logger.info("Forwarding dataset SOPInstanceUID=%s to %s:%d", dataset.SOPInstanceUID, dest_host, dest_port)
        rsp = assoc.send_c_store(dataset)
        success = (rsp and rsp.Status in (0x0000, 0xB000, 0xB007))
        status_desc = f"0x{rsp.Status:04x}" if rsp is not None else "None"
        if success:
            logger.info("Forwarding successful status=%s", status_desc)
        else:
            logger.warning("Forwarding failed status=%s", status_desc)
        return success, status_desc
    except Exception as ex:
        logger.exception("Exception while forwarding dataset: %s", ex)
        return False, str(ex)
    finally:
        assoc.release()


def handle_store(event):
    """Callback for C-STORE requests on the router SCP."""
    dataset = event.dataset
    dataset.file_meta = event.file_meta

    modality, patient_id, study_date = extract_metadata(dataset)

    # Clean metadata logging
    logger.info("Received C-STORE dataset:")
    logger.info("  Modality: %s", modality)
    logger.info("  PatientID: %s", patient_id)
    logger.info("  StudyDate: %s", study_date)
    logger.info("  SOPClassUID: %s", dataset.SOPClassUID)
    logger.info("  SOPInstanceUID: %s", dataset.SOPInstanceUID)

    rows = getattr(dataset, "Rows", 0)
    cols = getattr(dataset, "Columns", 0)
    size_kb = (rows * cols) / 1024
    logger.info("Dataset size (est): %.2f KB (rows=%s, cols=%s)", size_kb, rows, cols)

    target_host, target_port = select_node(modality, dataset)
    chosen_node = "Node A" if (target_host, target_port) == NODE_A else "Node B"
    logger.info("Routing decision: modality=%s size=%.2fKB -> %s (%s:%s)", modality, size_kb, chosen_node, target_host, target_port)

    start = time.perf_counter()
    success, status = forward_dataset(dataset, target_host, target_port)
    end = time.perf_counter()
    elapsed_ms = (end - start) * 1000

    if success:
        telemetry[chosen_node] += 1
        telemetry[f"{chosen_node}_last_latency"] = elapsed_ms
        telemetry[f"{chosen_node}_last_modality"] = modality
        telemetry[f"{chosen_node}_last_size_kb"] = size_kb

    logger.info("Forwarding completed in %.2f ms. status=%s. success=%s", elapsed_ms, status, success)
    logger.info("Telemetry: %s", dict(telemetry))

    # C-STORE response status.
    # 0x0000 Success. other values are failure conditions.
    return 0x0000 if success else 0xA700  # Refused: Out of resources or general failure


def start_router(host: str = "", port: int = 11111):
    """Boots the DICOM SCP router."""
    ae = AE(ae_title=b"DICOM_ROUTER")
    for context in SUPPORTED_SOP_CLASSES:
        ae.add_supported_context(context, ALL_TRANSFER_SYNTAXES)

    handlers = [(evt.EVT_C_STORE, handle_store)]

    logger.info("Starting router SCP on %s:%d", host or "0.0.0.0", port)
    try:
        ae.start_server((host, port), block=True, evt_handlers=handlers)
    except Exception as ex:
        logger.exception("Router failed to start: %s", ex)


if __name__ == "__main__":
    start_router()

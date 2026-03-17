import logging
from pynetdicom import AE, evt
from pynetdicom.sop_class import CTImageStorage, MRImageStorage, SecondaryCaptureImageStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("destination_node")

SUPPORTED_SOP_CLASSES = [CTImageStorage, MRImageStorage, SecondaryCaptureImageStorage]


def handle_store(event):
    """Simple handler for Node A/B to accept and ack C-STORE requests."""
    ds = event.dataset
    ds.file_meta = event.file_meta

    logger.info("Node received C-STORE: SOPClassUID=%s SOPInstanceUID=%s", ds.SOPClassUID, ds.SOPInstanceUID)
    logger.info("  PatientID=%s Modality=%s StudyDate=%s", getattr(ds, "PatientID", "UNKNOWN"), getattr(ds, "Modality", "UNKNOWN"), getattr(ds, "StudyDate", "UNKNOWN"))

    # Return Success
    return 0x0000


def start_node(node_name: str, port: int, host: str = ""):
    ae = AE(ae_title=node_name.encode("utf-8"))
    for context in SUPPORTED_SOP_CLASSES:
        ae.add_supported_context(context)

    handlers = [(evt.EVT_C_STORE, handle_store)]

    logger.info("Starting %s SCP on %s:%d", node_name, host or "0.0.0.0", port)
    ae.start_server((host, port), block=True, evt_handlers=handlers)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mock DICOM destination node")
    parser.add_argument("--name", default="NodeA", help="Node name for logging")
    parser.add_argument("--port", type=int, default=11112, help="Port to listen on")
    parser.add_argument("--host", default="", help="Host to bind")
    args = parser.parse_args()

    start_node(args.name, args.port, args.host)

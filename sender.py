import argparse
import logging

from pydicom import dcmread
from pynetdicom import AE
from pynetdicom.sop_class import CTImageStorage, MRImageStorage, SecondaryCaptureImageStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("dicom_sender")

SUPPORTED_SOP_CLASSES = [CTImageStorage, MRImageStorage, SecondaryCaptureImageStorage]


def send_dicom(file_path: str, host: str = "localhost", port: int = 11111):
    """Send a DICOM file as C-STORE to the router."""
    ds = dcmread(file_path)

    ae = AE(ae_title=b"DICOM_SENDER")
    try:
        ae.add_requested_context(ds.SOPClassUID)
    except Exception:
        for context in SUPPORTED_SOP_CLASSES:
            ae.add_requested_context(context)

    logger.info("Connecting to router %s:%d", host, port)
    assoc = ae.associate(host, port)
    if not assoc.is_established:
        logger.error("Unable to associate with router")
        return

    try:
        logger.info("Sending %s (SOPClass=%s, SOPInstance=%s)", file_path, ds.SOPClassUID, ds.SOPInstanceUID)
        status = assoc.send_c_store(ds)
        if status:
            logger.info("C-STORE response status: 0x%04x", status.Status)
        else:
            logger.error("No response from router")
    except Exception as exc:
        logger.exception("Error during C-STORE: %s", exc)
    finally:
        assoc.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a DICOM file to routing prototype")
    parser.add_argument("file", help="Path to DICOM file")
    parser.add_argument("--host", default="localhost", help="Router host")
    parser.add_argument("--port", type=int, default=11111, help="Router port")

    args = parser.parse_args()
    send_dicom(args.file, args.host, args.port)

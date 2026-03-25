"""
DICOM File Validation Module

Ensures only valid DICOM files enter the system, addressing requirements from
GSoC discussion #62, #13 (Album creation).
"""

import logging
from pathlib import Path
from pydicom import dcmread
from pydicom.errors import InvalidDicomError

logger = logging.getLogger("dicom_validation")


def validate_dicom_file(file_path: str) -> tuple[bool, str]:
    """
    Validate a DICOM file for correctness and required attributes.

    Returns:
        Tuple of (is_valid, error_message)
        is_valid: True if file is valid DICOM
        error_message: Descriptive error if invalid, empty string if valid
    """
    try:
        # Check file exists
        if not Path(file_path).exists():
            return False, f"File does not exist: {file_path}"

        # Attempt to read DICOM
        ds = dcmread(file_path)

        # Check for critical DICOM attributes required for album grouping
        required_attrs = ["PatientID", "StudyInstanceUID", "SeriesInstanceUID", "SOPClassUID", "SOPInstanceUID"]
        missing = [attr for attr in required_attrs if not hasattr(ds, attr)]

        if missing:
            return False, f"Missing required DICOM attributes: {', '.join(missing)}"

        return True, ""

    except InvalidDicomError as e:
        return False, f"Invalid DICOM file: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def validate_dicom_directory(dir_path: str, recursive: bool = True) -> dict:
    """
    Validate all DICOM files in a directory.

    Returns:
        dict with:
        - "valid_files": list of valid DICOM paths
        - "invalid_files": dict of {path: error_reason}
        - "summary": {"total": int, "valid": int, "invalid": int}
    """
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        return {"valid_files": [], "invalid_files": {}, "summary": {"total": 0, "valid": 0, "invalid": 0}}

    pattern = "**/*.dcm" if recursive else "*.dcm"
    dcm_files = list(dir_path.glob(pattern))

    valid_files = []
    invalid_files = {}

    for dcm_file in dcm_files:
        is_valid, error_msg = validate_dicom_file(str(dcm_file))
        if is_valid:
            valid_files.append(str(dcm_file))
        else:
            invalid_files[str(dcm_file)] = error_msg
            logger.warning(f"Invalid DICOM: {dcm_file} - {error_msg}")

    return {
        "valid_files": valid_files,
        "invalid_files": invalid_files,
        "summary": {
            "total": len(dcm_files),
            "valid": len(valid_files),
            "invalid": len(invalid_files),
        },
    }

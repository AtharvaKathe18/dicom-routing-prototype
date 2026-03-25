"""
DICOM Metadata Extraction and Normalization Module

Implements consistent metadata schema extraction from DICOM files.
Aligns with Pragya-rathal's metadata normalization discussion (#72)
and Niffler's meta-extraction module approach.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pydicom import dcmread
from pydicom.dataset import Dataset

logger = logging.getLogger("metadata_extraction")


class NormalizedMetadata:
    """Standardized metadata schema for DICOM instances."""

    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self._extract()

    def _extract(self):
        """Extract and normalize metadata fields."""
        # Patient Information
        self.patient_id: str = self._get_attr("PatientID", "ANONYMOUS")
        self.patient_name: str = self._get_attr("PatientName", "UNKNOWN")
        self.patient_birth_date: Optional[str] = self._normalize_date(self._get_attr("PatientBirthDate"))
        self.patient_sex: str = self._get_attr("PatientSex", "U")  # M, F, or U (unknown)

        # Study Information (hierarchical grouping key #1)
        self.study_instance_uid: str = self._get_attr("StudyInstanceUID", "UNKNOWN")
        self.study_date: Optional[str] = self._normalize_date(self._get_attr("StudyDate"))
        self.study_time: Optional[str] = self._normalize_time(self._get_attr("StudyTime"))
        self.study_description: str = self._get_attr("StudyDescription", "")
        self.referring_physician: str = self._get_attr("ReferringPhysicianName", "")

        # Series Information (hierarchical grouping key #2)
        self.series_instance_uid: str = self._get_attr("SeriesInstanceUID", "UNKNOWN")
        self.series_number: int = self._get_int_attr("SeriesNumber", 0)
        self.series_description: str = self._get_attr("SeriesDescription", "")
        self.modality: str = self._get_attr("Modality", "UNKNOWN")  # CT, MR, US, XC, etc.
        self.body_part_examined: str = self._get_attr("BodyPartExamined", "")

        # SOP Information (instance-level)
        self.sop_class_uid: str = self._get_attr("SOPClassUID", "UNKNOWN")
        self.sop_instance_uid: str = self._get_attr("SOPInstanceUID", "UNKNOWN")
        self.instance_number: int = self._get_int_attr("InstanceNumber", 0)

        # Image Information (for size estimation)
        self.rows: int = self._get_int_attr("Rows", 0)
        self.columns: int = self._get_int_attr("Columns", 0)
        self.bits_allocated: int = self._get_int_attr("BitsAllocated", 16)

        # Acquisition Information
        self.acquisition_date: Optional[str] = self._normalize_date(self._get_attr("AcquisitionDate"))
        self.acquisition_time: Optional[str] = self._normalize_time(self._get_attr("AcquisitionTime"))

        # Institution
        self.institution_name: str = self._get_attr("InstitutionName", "")

        # Calculated fields
        self.estimated_size_kb = (self.rows * self.columns * self.bits_allocated) / (8 * 1024)

    def _get_attr(self, attr_name: str, default: str = "") -> str:
        """Safely retrieve string attribute."""
        try:
            value = getattr(self.dataset, attr_name, default)
            return str(value).strip() if value else default
        except Exception:
            return default

    def _get_int_attr(self, attr_name: str, default: int = 0) -> int:
        """Safely retrieve integer attribute."""
        try:
            value = getattr(self.dataset, attr_name, default)
            return int(value) if value else default
        except (ValueError, TypeError):
            return default

    def _normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        """Normalize date format to ISO 8601 (YYYY-MM-DD)."""
        if not date_str:
            return None
        try:
            # Handle DICOM format (YYYYMMDD)
            if isinstance(date_str, str) and len(date_str) == 8:
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            return str(date_str)
        except Exception:
            return None

    def _normalize_time(self, time_str: Optional[str]) -> Optional[str]:
        """Normalize time format to ISO 8601 (HH:MM:SS or HH:MM:SS.fff)."""
        if not time_str:
            return None
        try:
            # Handle DICOM format (HHMMSS.ffffff)
            if isinstance(time_str, str):
                time_str = time_str.strip()
                if len(time_str) >= 6:
                    return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
            return str(time_str)
        except Exception:
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "patient": {
                "id": self.patient_id,
                "name": self.patient_name,
                "birth_date": self.patient_birth_date,
                "sex": self.patient_sex,
            },
            "study": {
                "study_instance_uid": self.study_instance_uid,
                "study_date": self.study_date,
                "study_time": self.study_time,
                "study_description": self.study_description,
                "referring_physician": self.referring_physician,
            },
            "series": {
                "series_instance_uid": self.series_instance_uid,
                "series_number": self.series_number,
                "series_description": self.series_description,
                "modality": self.modality,
                "body_part_examined": self.body_part_examined,
            },
            "sop": {
                "sop_class_uid": self.sop_class_uid,
                "sop_instance_uid": self.sop_instance_uid,
                "instance_number": self.instance_number,
            },
            "image": {
                "rows": self.rows,
                "columns": self.columns,
                "bits_allocated": self.bits_allocated,
                "estimated_size_kb": round(self.estimated_size_kb, 2),
            },
            "acquisition": {
                "acquisition_date": self.acquisition_date,
                "acquisition_time": self.acquisition_time,
            },
            "institution": self.institution_name,
        }


def extract_normalized_metadata(file_path: str) -> Optional[NormalizedMetadata]:
    """Extract and normalize metadata from DICOM file."""
    try:
        ds = dcmread(file_path, stop_before_pixels=True)  # Don't load pixel data
        return NormalizedMetadata(ds)
    except Exception as e:
        logger.error(f"Failed to extract metadata from {file_path}: {e}")
        return None


def group_by_study(file_paths: list[str]) -> Dict[str, Dict[str, list[str]]]:
    """
    Group DICOM files by StudyInstanceUID and SeriesInstanceUID.
    Used for album creation.

    Returns:
        {
            study_uid: {
                series_uid: [file_path1, file_path2, ...],
                ...
            },
            ...
        }
    """
    groups = {}

    for file_path in file_paths:
        metadata = extract_normalized_metadata(file_path)
        if not metadata:
            continue

        study_uid = metadata.study_instance_uid
        series_uid = metadata.series_instance_uid

        if study_uid not in groups:
            groups[study_uid] = {}
        if series_uid not in groups[study_uid]:
            groups[study_uid][series_uid] = []

        groups[study_uid][series_uid].append(file_path)

    return groups

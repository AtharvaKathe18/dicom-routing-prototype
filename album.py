"""
DICOM Album Management Module

Creates and manages shareable albums from locally stored DICOM images.
Aligns with GSoC project #13 and discussions by @lizatinku, @Pragya-rathal, @aasthathakkar.

Albums can be:
- Static snapshots (fixed set of files at creation time)
- Query-driven (dynamically fetches files matching criteria)

Initially focusing on static albums as recommended.
"""

import logging
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from metadata import extract_normalized_metadata, NormalizedMetadata
from validation import validate_dicom_file

logger = logging.getLogger("album_manager")


class AlbumType(Enum):
    """Album type classification."""

    STATIC = "static"  # Fixed snapshot at creation time
    DYNAMIC = "dynamic"  # Query-driven, reproducible collection


@dataclass
class AlbumMetadata:
    """Album metadata structure."""

    album_id: str
    name: str
    description: str
    album_type: str  # "static" or "dynamic"
    created_at: str
    modified_at: str
    creator: str
    studies: List[str]  # List of StudyInstanceUIDs included
    series: List[str]  # List of SeriesInstanceUIDs included
    file_count: int
    total_size_kb: float
    tags: List[str] = None
    sharable_url: Optional[str] = None  # For external sharing
    query_criteria: Optional[Dict[str, Any]] = None  # For dynamic albums

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class Album:
    """Represents a DICOM Album (collection of related studies/series)."""

    def __init__(
        self,
        name: str,
        description: str = "",
        creator: str = "system",
        album_type: AlbumType = AlbumType.STATIC,
    ):
        self.album_id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.creator = creator
        self.album_type = album_type
        self.created_at = datetime.utcnow().isoformat()
        self.modified_at = self.created_at

        self.files: Dict[str, str] = {}  # {sop_instance_uid: file_path}
        self.metadata_cache: Dict[str, NormalizedMetadata] = {}
        self.studies: set = set()
        self.series: set = set()
        self.total_size_kb = 0.0
        self.query_criteria: Optional[Dict[str, Any]] = None

    def add_file(self, file_path: str) -> bool:
        """Add a DICOM file to the album."""
        # Validate file
        is_valid, error = validate_dicom_file(file_path)
        if not is_valid:
            logger.warning(f"Cannot add invalid DICOM file {file_path}: {error}")
            return False

        # Extract metadata
        metadata = extract_normalized_metadata(file_path)
        if not metadata:
            logger.warning(f"Failed to extract metadata from {file_path}")
            return False

        # Add to album
        sop_uid = metadata.sop_instance_uid
        self.files[sop_uid] = file_path
        self.metadata_cache[sop_uid] = metadata
        self.studies.add(metadata.study_instance_uid)
        self.series.add(metadata.series_instance_uid)
        self.total_size_kb += metadata.estimated_size_kb
        self.modified_at = datetime.utcnow().isoformat()

        logger.info(
            f"Added {file_path} to album {self.album_id}. "
            f"Study: {metadata.study_instance_uid[:8]}... Series: {metadata.series_instance_uid[:8]}..."
        )
        return True

    def add_files_from_directory(self, dir_path: str, recursive: bool = True) -> int:
        """
        Scan directory for DICOM files and add them to album.

        Returns:
            Number of files successfully added
        """
        dir_path = Path(dir_path)
        pattern = "**/*.dcm" if recursive else "*.dcm"
        dcm_files = list(dir_path.glob(pattern))

        added = 0
        for dcm_file in dcm_files:
            if self.add_file(str(dcm_file)):
                added += 1

        return added

    def get_studies(self) -> List[str]:
        """Return list of StudyInstanceUIDs in album."""
        return sorted(list(self.studies))

    def get_series(self) -> List[str]:
        """Return list of SeriesInstanceUIDs in album."""
        return sorted(list(self.series))

    def get_file_count(self) -> int:
        """Return number of files in album."""
        return len(self.files)

    def get_metadata(self) -> Dict[str, Dict]:
        """Return normalized metadata for all files."""
        return {sop_uid: asdict(meta) for sop_uid, meta in self.metadata_cache.items()}

    def to_metadata_dict(self) -> AlbumMetadata:
        """Convert album to metadata object."""
        return AlbumMetadata(
            album_id=self.album_id,
            name=self.name,
            description=self.description,
            album_type=self.album_type.value,
            created_at=self.created_at,
            modified_at=self.modified_at,
            creator=self.creator,
            studies=self.get_studies(),
            series=self.get_series(),
            file_count=self.get_file_count(),
            total_size_kb=round(self.total_size_kb, 2),
            query_criteria=self.query_criteria,
        )

    def create_manifest(self) -> Dict[str, Any]:
        """
        Create JSON manifest for album (for external sharing, Kheops integration).

        Returns:
            Manifest structure suitable for JSON export or REST API
        """
        manifest = {
            "album": asdict(self.to_metadata_dict()) if isinstance(self.to_metadata_dict(), AlbumMetadata) else self.to_metadata_dict(),
            "studies": {study_uid: {"series": sorted(list(self.series))} for study_uid in self.get_studies()},
            "files": list(self.files.values()),
            "metadata_summary": {
                "modalities": list(set(m.modality for m in self.metadata_cache.values())),
                "date_range": {
                    "earliest": min(
                        (m.study_date for m in self.metadata_cache.values() if m.study_date),
                        default=None,
                    ),
                    "latest": max(
                        (m.study_date for m in self.metadata_cache.values() if m.study_date),
                        default=None,
                    ),
                },
                "total_size_kb": round(self.total_size_kb, 2),
            },
        }
        return manifest


class AlbumManager:
    """Manages multiple albums and persistence."""

    def __init__(self, storage_dir: str = "./albums"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.albums: Dict[str, Album] = {}

    def create_album(
        self,
        name: str,
        description: str = "",
        creator: str = "system",
        album_type: AlbumType = AlbumType.STATIC,
    ) -> Album:
        """Create a new album."""
        album = Album(name, description, creator, album_type)
        self.albums[album.album_id] = album
        logger.info(f"Created album {album.album_id}: {name}")
        return album

    def get_album(self, album_id: str) -> Optional[Album]:
        """Retrieve album by ID."""
        return self.albums.get(album_id)

    def list_albums(self) -> List[Dict[str, Any]]:
        """List all albums as dictionaries."""
        return [asdict(a.to_metadata_dict()) if isinstance(a.to_metadata_dict(), AlbumMetadata) else a.to_metadata_dict() for a in self.albums.values()]

    def export_album_manifest(self, album_id: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Export album manifest to JSON file.

        Returns:
            Path to exported manifest file, or None if failed
        """
        album = self.get_album(album_id)
        if not album:
            logger.error(f"Album {album_id} not found")
            return None

        manifest = album.create_manifest()

        if not output_path:
            output_path = self.storage_dir / f"{album.name.replace(' ', '_')}_{album_id[:8]}.json"

        try:
            with open(output_path, "w") as f:
                json.dump(manifest, f, indent=2)
            logger.info(f"Exported album manifest to {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to export manifest: {e}")
            return None

    def delete_album(self, album_id: str) -> bool:
        """Delete album (metadata only, not actual files)."""
        if album_id in self.albums:
            del self.albums[album_id]
            logger.info(f"Deleted album {album_id}")
            return True
        return False

"""
Comprehensive Demo Script

Shows how to use all modules together:
1. Validate DICOM files
2. Extract and normalize metadata
3. Create albums from validated files
4. Export manifest for sharing
5. Understand routing decisions
"""

import logging
from pathlib import Path
from validation import validate_dicom_directory, validate_dicom_file
from metadata import extract_normalized_metadata, group_by_study
from album import AlbumManager, AlbumType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo")


def demo_validation():
    """Demo 1: Validate DICOM files."""
    logger.info("=" * 60)
    logger.info("DEMO 1: DICOM File Validation")
    logger.info("=" * 60)

    # Validate the sample DICOM file
    demo_dir = Path("./demo")
    if not demo_dir.exists():
        logger.warning(f"Demo directory {demo_dir} not found. Skipping validation demo.")
        return None

    dcm_file = demo_dir / "sample.dcm"
    if dcm_file.exists():
        is_valid, error = validate_dicom_file(str(dcm_file))
        logger.info(f"File: {dcm_file}")
        logger.info(f"Valid: {is_valid}")
        if error:
            logger.info(f"Error: {error}")
        return dcm_file if is_valid else None
    else:
        logger.warning(f"Sample DICOM file not found at {dcm_file}")
        return None


def demo_metadata(dcm_file: Path):
    """Demo 2: Extract and normalize metadata."""
    logger.info("=" * 60)
    logger.info("DEMO 2: Metadata Extraction and Normalization")
    logger.info("=" * 60)

    if not dcm_file:
        logger.warning("No valid DICOM file provided. Skipping metadata demo.")
        return None

    metadata = extract_normalized_metadata(str(dcm_file))
    if not metadata:
        logger.error(f"Failed to extract metadata from {dcm_file}")
        return None

    logger.info(f"File: {dcm_file}")
    logger.info("\nPatient Information:")
    logger.info(f"  ID: {metadata.patient_id}")
    logger.info(f"  Name: {metadata.patient_name}")
    logger.info(f"  Birth Date: {metadata.patient_birth_date or 'N/A'}")

    logger.info("\nStudy Information:")
    logger.info(f"  Study UID: {metadata.study_instance_uid}")
    logger.info(f"  Study Date: {metadata.study_date or 'N/A'}")
    logger.info(f"  Description: {metadata.study_description or 'N/A'}")

    logger.info("\nSeries Information:")
    logger.info(f"  Series UID: {metadata.series_instance_uid}")
    logger.info(f"  Modality: {metadata.modality}")
    logger.info(f"  Description: {metadata.series_description or 'N/A'}")

    logger.info("\nImage Information:")
    logger.info(f"  Rows: {metadata.rows}")
    logger.info(f"  Columns: {metadata.columns}")
    logger.info(f"  Estimated Size: {metadata.estimated_size_kb:.2f} KB")

    return metadata


def demo_album_creation(dcm_file: Path):
    """Demo 3: Create and manage albums."""
    logger.info("=" * 60)
    logger.info("DEMO 3: Album Creation and Management")
    logger.info("=" * 60)

    # Create album manager
    mgr = AlbumManager(storage_dir="./albums")
    logger.info(f"Album Manager initialized (storage: ./albums)")

    # Create new album
    album = mgr.create_album(
        name="Sample DICOM Album",
        description="Demo album created from sample DICOM file",
        creator="demo_script",
        album_type=AlbumType.STATIC,
    )
    logger.info(f"Created album: {album.album_id}")
    logger.info(f"Name: {album.name}")
    logger.info(f"Type: {album.album_type.value}")

    # Add the sample DICOM file
    if dcm_file:
        success = album.add_file(str(dcm_file))
        if success:
            logger.info(f"\nAdded file to album: {dcm_file}")
            logger.info(f"Total files in album: {album.get_file_count()}")
            logger.info(f"Album studies: {album.get_studies()}")
            logger.info(f"Album series: {album.get_series()}")
            logger.info(f"Total size: {album.total_size_kb:.2f} KB")
        else:
            logger.warning(f"Failed to add file: {dcm_file}")
    else:
        logger.warning("No DICOM file to add to album")

    # Try to add files from demo directory
    demo_dir = Path("./demo")
    if demo_dir.exists():
        added = album.add_files_from_directory(str(demo_dir), recursive=False)
        logger.info(f"\nScanned demo directory: added {added} additional files")

    return mgr, album


def demo_manifest_export(mgr: AlbumManager, album):
    """Demo 4: Export album manifest."""
    logger.info("=" * 60)
    logger.info("DEMO 4: Album Manifest Export (for Kheops)")
    logger.info("=" * 60)

    # Create manifest
    manifest = album.create_manifest()

    logger.info(f"\nManifest for album: {album.name}")
    logger.info(f"Album ID: {manifest['album']['album_id']}")
    logger.info(f"Files in album: {manifest['album']['file_count']}")
    logger.info(f"Total size: {manifest['album']['total_size_kb']} KB")
    logger.info(f"Studies: {manifest['album']['studies']}")

    logger.info(f"\nMetadata Summary:")
    logger.info(f"  Modalities: {manifest['metadata_summary']['modalities']}")
    logger.info(f"  Date Range: {manifest['metadata_summary']['date_range']}")

    # Export to JSON file
    export_path = mgr.export_album_manifest(album.album_id)
    if export_path:
        logger.info(f"\n✓ Manifest exported to: {export_path}")
        logger.info("This manifest can be used for:")
        logger.info("  - Sharing with Kheops viewer")
        logger.info("  - REST API integration")
        logger.info("  - External research collaboration")
    else:
        logger.error("Failed to export manifest")


def demo_routing_insights(metadata):
    """Demo 5: Routing insights based on metadata."""
    logger.info("=" * 60)
    logger.info("DEMO 5: Routing Insights")
    logger.info("=" * 60)

    if not metadata:
        logger.warning("No metadata provided. Skipping routing demo.")
        return

    logger.info("Routing Decision for this dataset:")
    logger.info(f"  Modality: {metadata.modality}")
    logger.info(f"  Estimated Size: {metadata.estimated_size_kb:.2f} KB")

    # Simple routing logic
    if metadata.modality.upper() == "CT" and metadata.estimated_size_kb > 500:
        logger.info("\nRouting Decision: Node A (High-capacity node)")
        logger.info("  Reason: Large CT study")
    else:
        logger.info("\nRouting Decision: Node B (Default node)")
        logger.info("  Reason: Load balancing")

    logger.info("\nMetadata fields available for advanced routing:")
    fields = [
        "patient_id",
        "modality",
        "study_instance_uid",
        "series_instance_uid",
        "acquisition_date",
        "body_part_examined",
    ]
    for field in fields:
        value = getattr(metadata, field, "N/A")
        logger.info(f"  - {field}: {value}")


def main():
    """Run all demos."""
    logger.info("\nDIOMEDE PROTOTYPE COMPREHENSIVE DEMO")
    logger.info("=" * 60)

    # Demo 1: Validation
    dcm_file = demo_validation()

    # Demo 2: Metadata extraction
    if dcm_file:
        metadata = demo_metadata(dcm_file)

        # Demo 5: Routing insights
        if metadata:
            demo_routing_insights(metadata)
    else:
        metadata = None
        logger.warning("Skipping metadata and routing demos.")

    # Demo 3: Album creation
    mgr, album = demo_album_creation(dcm_file)

    # Demo 4: Manifest export
    if album.get_file_count() > 0:
        demo_manifest_export(mgr, album)
    else:
        logger.warning("Album is empty, skipping manifest export.")

    logger.info("\n" + "=" * 60)
    logger.info("DEMO COMPLETE")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Start destination nodes: python node.py --port 11112 & python node.py --port 11113")
    logger.info("2. Start router: python router.py")
    logger.info("3. Send DICOM files: python sender.py /path/to/file.dcm")
    logger.info("\nSee README.md for more information.")


if __name__ == "__main__":
    main()

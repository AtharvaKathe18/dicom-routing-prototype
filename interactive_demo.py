"""
Interactive demo showing validation, metadata extraction, and routing logic
"""
from validation import validate_dicom_file, validate_dicom_directory
from metadata import extract_normalized_metadata
from album import AlbumManager, AlbumType

print("\n" + "="*70)
print("DIOMEDE PROTOTYPE - INTERACTIVE DEMO")
print("="*70 + "\n")

# Step 1: Validate DICOM Files
print("STEP 1: DICOM File Validation")
print("-" * 70)

dcm_file = "./demo/sample.dcm"
is_valid, error = validate_dicom_file(dcm_file)

if is_valid:
    print(f"✓ DICOM file is VALID: {dcm_file}\n")
else:
    print(f"✗ DICOM file is INVALID: {error}\n")
    exit(1)

# Step 2: Extract Normalized Metadata
print("STEP 2: Metadata Extraction & Normalization")
print("-" * 70)

metadata = extract_normalized_metadata(dcm_file)

if metadata:
    print(f"✓ Metadata extracted successfully:\n")
    meta_dict = metadata.to_dict()
    
    for section, data in meta_dict.items():
        if isinstance(data, dict):
            print(f"\n  {section.upper()}:")
            for key, value in data.items():
                print(f"    - {key}: {value}")
        else:
            print(f"  {section}: {data}")
else:
    print(f"✗ Failed to extract metadata")
    exit(1)

# Step 3: Routing Decision Logic
print("\n\nSTEP 3: Routing Decision Analysis")
print("-" * 70)

modality = metadata.modality
size_kb = metadata.estimated_size_kb

print(f"\nInput Parameters:")
print(f"  - Modality: {modality}")
print(f"  - Dataset Size: {size_kb:.2f} KB")
print(f"  - Body Part: {metadata.body_part_examined}")
print(f"  - Study Date: {metadata.study_date}")

print(f"\nRouting Logic:")
print(f"  1. Check if modality is CT and size > 500 KB")
print(f"     → Modality={modality}, Size={size_kb:.2f}KB")

if modality.upper() == "CT" and size_kb > 500:
    decision = "Node A"
    reason = "Large CT study - route to high-capacity node"
else:
    decision = "Node B"
    reason = "Default routing - load balancing"

print(f"     → Decision: Route to {decision}")
print(f"     → Reason: {reason}")

# Step 4: Album Creation with Metadata
print("\n\nSTEP 4: Album Creation with Study/Series Grouping")
print("-" * 70)

mgr = AlbumManager()
album = mgr.create_album(
    name="Demo Study Group",
    description="Grouped by StudyInstanceUID and SeriesInstanceUID",
    album_type=AlbumType.STATIC
)

album.add_file(dcm_file)

print(f"\n✓ Album created: {album.album_id}")
print(f"  - Name: {album.name}")
print(f"  - Type: {album.album_type.value}")
print(f"  - Files: {album.get_file_count()}")
print(f"  - Studies: {album.get_studies()}")
print(f"  - Series: {album.get_series()}")
print(f"  - Total Size: {album.total_size_kb:.2f} KB")

# Step 5: Export Manifest for Kheops
print("\n\nSTEP 5: Album Manifest Export (for Kheops Integration)")
print("-" * 70)

manifest_path = mgr.export_album_manifest(album.album_id)
print(f"\n✓ Manifest exported to: {manifest_path}")
print(f"  This JSON manifest can be imported into:")
print(f"  - Kheops DICOM viewer")
print(f"  - REST API endpoints")
print(f"  - External research platforms")

# Step 6: Display Telemetry Information
print("\n\nSTEP 6: Transfer Simulation & Telemetry")
print("-" * 70)

print(f"\nSimulated Transfer Telemetry:")
print(f"  - Destination Node: {decision} ({('localhost', 11112) if decision == 'Node A' else ('localhost', 11113)})")
print(f"  - Estimated Transfer Time: {(size_kb / 1024):.2f}s (at 1 MB/s)")
print(f"  - Routing Reason: {reason}")
print(f"  - Metadata Used: Modality={modality}, Size, Availability")

# Summary
print("\n\n" + "="*70)
print("DEMO SUMMARY")
print("="*70)

print(f"""
✓ File Validation:      PASSED ({dcm_file})
✓ Metadata Extraction:  {metadata.modality} study from {metadata.study_instance_uid[:16]}...
✓ Routing Decision:     {decision} (Large CT study)
✓ Album Creation:       {len(album.get_studies())} study, {len(album.get_series())} series
✓ Manifest Export:      Ready for Kheops

This prototype demonstrates:
  1. DICOM validation (Project #13)
  2. Metadata normalization (Discussion #72)
  3. Smart routing decisions (Project #14, Discussion #61)
  4. Album creation with Study/Series grouping (Project #13)
  5. Kheops integration via manifest export
  
Next Steps:
  1. Start router: python router_enhanced.py --index-dir ./demo
  2. Start nodes: python node.py --port 11112 & python node.py --port 11113
  3. Send DICOM: python sender.py ./demo/sample.dcm
""")

print("="*70)

# Diomede DICOM Prototype: Routing, Albums, and Metadata Query

## Overview

This project implements a comprehensive DICOM middleware prototype aligned with GSoC 2026 projects #13, #14, and related discussions.

**Key Features:**
1. **Dynamic DICOM Routing** (#14) - Intelligent routing based on metadata, load, and availability
2. **DICOM Album Creation** (#13) - Group and share DICOM studies/series
3. **Metadata Extraction & Normalization** - Consistent schema for querying
4. **DICOM Validation** - Ensure only valid files enter the system
5. **Telemetry & Transfer Monitoring** - Track transfers, latency, throughput

---

## Architecture

```
Sender (SCU)
   │
   ▼
┌─────────────────────────┐
│  DICOM Router           │
│  ├─ C-STORE Handler     │  ◄── Receives DICOM files
│  ├─ C-FIND Handler      │  ◄── Metadata queries
│  ├─ Routing Engine      │  ◄── Metadata + Telemetry
│  └─ Telemetry Tracker   │
└─────────────────────────┘
   │         │
   ├────────┬┴─────────────┐
   │        │              │
   ▼        ▼              ▼
 Node A   Node B     Album Manager
 (SCP)    (SCP)      ├─ Validation
                      ├─ Metadata Index
                      ├─ Album Creation
                      └─ Manifest Export

```

---

## Modules

### 1. **validation.py**
DICOM file validation ensuring only valid files enter the system.

**Features:**
- Single file validation with DICOM format checking
- Required attribute verification (PatientID, StudyInstanceUID, etc.)
- Batch directory validation

**Usage:**
```python
from validation import validate_dicom_file, validate_dicom_directory

# Single file
is_valid, error = validate_dicom_file("~/patient_scan.dcm")

# Directory scan
results = validate_dicom_directory("/dicom/data", recursive=True)
print(f"Valid: {len(results['valid_files'])}, Invalid: {len(results['invalid_files'])}")
```

---

### 2. **metadata.py**
Metadata extraction and normalization into consistent schema (addresses discussion #72).

**Features:**
- Normalized metadata class with safe field extraction
- ISO 8601 date/time normalization
- Study/Series hierarchy support (for album grouping)
- Metadata caching for performance
- Size estimation for routing decisions

**Normalized Fields:**
- Patient: ID, Name, Birth Date, Sex
- Study: Study UID, Date, Time, Description, Physician
- Series: Series UID, Number, Description, Modality, Body Part
- SOP: Class UID, Instance UID, Instance Number
- Image: Rows, Columns, Bits Allocated, Estimated Size

**Usage:**
```python
from metadata import extract_normalized_metadata, group_by_study

# Extract normalized metadata
metadata = extract_normalized_metadata("~/patient_scan.dcm")
print(f"Modality: {metadata.modality}")
print(f"Study: {metadata.study_instance_uid}")
print(f"Series: {metadata.series_instance_uid}")

# Group files by Study/Series (for albums)
files = ["/path/to/file1.dcm", "/path/to/file2.dcm"]
grouped = group_by_study(files)
# grouped[study_uid][series_uid] = [file_list]
```

---

### 3. **album.py**
Creates and manages shareable DICOM albums from local files (project #13).

**Features:**
- Static albums (snapshots at creation time)
- Support for dynamic albums (query-driven, future)
- Study/Series hierarchy
- File validation on add
- JSON manifest export (for Kheops integration)
- Album metadata tracking

**Workflow:**
```python
from album import AlbumManager, AlbumType

# Create album manager
mgr = AlbumManager(storage_dir="./albums")

# Create new album
album = mgr.create_album(
    name="Chest CT Study 2026",
    description="Multi-patient chest CT series",
    album_type=AlbumType.STATIC
)

# Add files
album.add_file("~/patient1_chest.dcm")
album.add_files_from_directory("/dicom/data/chest_studies", recursive=True)

# Export manifest for external sharing (Kheops)
manifest_path = mgr.export_album_manifest(album.album_id)

# Get album info
print(f"Files: {album.get_file_count()}")
print(f"Studies: {album.get_studies()}")
print(f"Series: {album.get_series()}")
```

**Manifest Structure (for Kheops/REST API):**
```json
{
  "album": {
    "album_id": "uuid",
    "name": "Album Name",
    "file_count": 125,
    "total_size_kb": 45000,
    "created_at": "2026-03-25T10:30:00",
    "studies": ["1.2.3.4.5.6"],
    "series": ["1.2.3.4.5.6.7"]
  },
  "studies": {
    "1.2.3.4.5.6": {
      "series": ["1.2.3.4.5.6.7"]
    }
  },
  "files": ["/path/to/file1.dcm", "/path/to/file2.dcm"],
  "metadata_summary": {
    "modalities": ["CT", "MR"],
    "date_range": {"earliest": "2026-01-15", "latest": "2026-03-20"},
    "total_size_kb": 45000
  }
}
```

---

### 4. **router.py** (Original)
Core DICOM routing middleware with C-STORE support.

**Components:**
- Metadata extraction
- Node health checking (cached)
- Load-aware routing engine
- C-STORE forwarding with telemetry

**Routing Strategy:**
1. Avoid overloaded nodes (telemetry awareness)
2. Check node availability with caching
3. Route large CT studies to high-capacity nodes
4. Default to least-loaded node
5. Track latency per transfer

---

### 5. **router_enhanced.py**
Extended router with C-FIND support and metadata indexing.

**New Features:**
- **C-FIND Query Support**: Metadata queries before routing
- **Metadata Indexing**: In-memory index for query filtering
- **Query Validation**: Filter on PatientID, StudyUID, SeriesUID, Modality, Date
- **Transfer Logging**: Detailed transfer records with timestamps
- **Telemetry Export**: JSON export for monitoring

**Usage:**
```bash
# Start router with optional metadata indexing
python router_enhanced.py --host localhost --port 11111 --index-dir ./dcm_data

# Router now supports C-FIND queries
```

**Telemetry Export:**
```python
from router_enhanced import export_telemetry, get_telemetry_summary

summary = get_telemetry_summary()
# {
#   "timestamp": "2026-03-25T10:30:00",
#   "nodes": {"Node A": {...}, "Node B": {...}},
#   "total_transfers": 100,
#   "recent_transfers": [...]
# }

export_telemetry("./telemetry.json")
```

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Validate Local DICOM Data
```bash
python -c "
from validation import validate_dicom_directory
results = validate_dicom_directory('./demo', recursive=True)
print(f'Valid: {results[\"summary\"][\"valid\"]}, Invalid: {results[\"summary\"][\"invalid\"]}')
"
```

### 3. Create an Album from Local Data
```bash
python -c "
from album import AlbumManager, AlbumType
from validation import validate_dicom_directory

mgr = AlbumManager('./albums')
album = mgr.create_album('Test Album', 'Demo album')

# Add validated files
results = validate_dicom_directory('./demo')
for f in results['valid_files'][:10]:
    album.add_file(f)

# Export
mgr.export_album_manifest(album.album_id)
print(f'Created album with {album.get_file_count()} files')
"
```

### 4. Start Destination Nodes (in separate terminals)
```bash
# Terminal 1
python node.py --name "Node A" --port 11112

# Terminal 2
python node.py --name "Node B" --port 11113
```

### 5. Start Router (in separate terminal)
```bash
# Basic routing
python router.py

# Or with metadata indexing
python router_enhanced.py --index-dir ./demo
```

### 6. Send DICOM Files to Router
```bash
python sender.py ./demo/sample.dcm --host localhost --port 11111
```

---

## GSoC Project Alignment

| Project | Feature | Implementation |
|---------|---------|-----------------|
| #13 - DICOM Albums | Group by Study/Series | `album.py` + `metadata.py` |
| #13 - Share Albums | JSON Manifest Export | `album.py:create_manifest()` |
| #14 - Dynamic Endpoints | Load-aware Routing | `router.py:select_node()` |
| #14 - Telemetry | Transfer Tracking | `router_enhanced.py` telemetry |
| #61 - Metadata Routing | Modality/Size-based | `router.py:select_node()` |
| #67 - Query Engine | Metadata Normalization | `metadata.py:NormalizedMetadata` |
| #67 - Query Engine | C-FIND Support | `router_enhanced.py:execute_c_find_query()` |

---

## Future Enhancements

1. **Kheops Integration** - REST API bridge for album sharing
2. **Persistent Storage** - PostgreSQL/Redis for telemetry and album metadata
3. **Dynamic Albums** - Query-driven albums (reproducible)
4. **PHI Anonymization** - Automatic metadata scrubbing
5. **DWiM Integration** - Automated workflow integration
6. **C-MOVE Support** - Query/retrieve operations
7. **Authentication** - OAuth/token-based access for shared albums
8. **Visualization** - Web UI for album browsing

---

## References

- [Diomede Repository](https://github.com/KathiraveluLab/Diomede)
- [GSoC 2026 Projects](https://github.com/uaanchorage/GSoC)
- [pynetdicom Documentation](https://pynetdicom.readthedocs.io/)
- [DICOM Standard](https://www.dicomstandard.org/)

### Telemetry-based load balancing
- Tracks per-node request counts
- Prefers less loaded node

### Node health awareness
- Cached health checks prevent frequent probing
- Automatically reroutes if a node is unavailable

### Latency tracking
- Measures forwarding time per dataset
- Stores last latency per node

### Fault tolerance
- Safe handling of missing metadata
- Graceful handling of association failures

---

## Routing Strategy

1. Avoid overloaded nodes (telemetry)
2. Avoid unavailable nodes (health check)
3. Route large CT studies to Node A
4. Default to Node B

---

## Requirements

- Python 3.8+
- Install dependencies:

```bash
pip install pynetdicom pydicom

## How to Run
 
 1. Start Node A
                python node.py --name NodeA --port 11112
 2. Start Node B
                python node.py --name NodeB --port 11113
 3. Start Router
                python router.py
 4. Send a DICOM file
                python sender.py /path/to/file.dcm

Example Workflow

1.Sender sends dataset to router
2.Router extracts metadata and estimates size
3.Router evaluates:
                    -metadata
                    -dataset size
                    -node load
                    -node availability
4.Router forwards dataset to selected node
5.Telemetry is updated

Example Output
Router Logs
                 Received C-STORE dataset:
                       Modality: CT
                       PatientID: PAT123
                       StudyDate: 20250101

                  Routing decision: modality=CT size=512KB -> Node A
                  Forwarding successful status=0x0000

                  Telemetry: {
                              'Node A': 1,
                              'Node A_last_latency': 12.3,
                              'Node A_last_modality': 'CT'
                              }
Future Improvements

1.Distributed telemetry (Redis / PostgreSQL)
2.Advanced routing algorithms (latency-aware, predictive)
3.Integration with Orthanc / PACS systems
4.Dynamic endpoint orchestration (Diomede integration)
5.Multi-node distributed routing

Motivation

This prototype explores how DICOM infrastructure can evolve from:
Static routing → Intelligent, adaptive routing

It provides a foundation for:

       -dynamic endpoint selection

       -load-aware distribution

       -resilient medical imaging pipelines

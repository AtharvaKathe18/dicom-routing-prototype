# Diomede DICOM Prototype: Central Router Architecture

## Overview

This project implements a **Central Router** DICOM middleware prototype for intelligent, metadata-aware DICOM distribution.

**Mentor-Endorsed Approach:** Central Router (addresses static endpoint constraints of DICOM)

**Core Features:**
1. ✅ **Central Router Middleware** - Fixed endpoint for DICOM senders, intelligent backend routing
2. ✅ **Metadata-Aware Routing** - Route decisions based on modality, size, node load
3. ✅ **DICOM Album Creation** - Group and share DICOM studies/series
4. ✅ **Validation & Normalization** - Quality gates and consistent metadata schema
5. ✅ **Telemetry Tracking** - Monitor transfers, latency, throughput

---

## Architecture: Central Router Approach

```
DICOM Sender/PACS
   (fixed config: Router IP:Port:AE)
        │
        │ C-STORE
        ▼
    ┌─────────────────┐
    │ DIOMEDE ROUTER  │  ◄── Fixed Static Endpoint
    │                 │      (from sender perspective)
    │ • Receive DICOM │
    │ • Extract Meta  │
    │ • Decide Route  │
    │ • Forward C-STORE
    │ • Track Latency │
    └─────────────────┘
        │
    ┌─────────────────┬─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
  Node A            Node B           Node C
(Orthanc)        (Orthanc)        (Orthanc)
Port 11112       Port 11113       Port 11114

Router Decision Logic:
  1. Check node availability
  2. Balance load (request counts)
  3. Route by metadata (CT → Node A by default)
  4. Default to least-loaded node
```

**Why This Approach?** 
- ✅ DICOM systems expect static endpoints (cannot change scanner config)
- ✅ Backward compatible with existing infrastructure
- ✅ Practical, implementable, production-ready
- ✅ Endorsed by mentors as most viable solution

---

## Core Modules

### 1. **router.py** - Central DICOM Router
The heart of the system. Acts as intelligent middleware between senders and backends.

**Features:**
- Listens on fixed DICOM endpoint (SCP)
- Extracts metadata from incoming DICOM files
- Makes routing decisions based on:
  - Node availability (health checks)
  - Node load (request counts)
  - DICOM metadata (modality, size)
- Forwards via C-STORE to selected backend (SCU)
- Tracks latency and throughput

**Routing Logic:**
```python
def select_node(modality, dataset_size, telemetry):
    # 1. Check availability
    if not node_a.is_available: return node_b
    if not node_b.is_available: return node_a
    
    # 2. Load balance
    if node_a.load > node_b.load: return node_b
    
    # 3. Modality-aware
    if modality == "CT" and size > 500_kb: return node_a
    
    # 4. Default
    return node_b
```

---

### 2. **metadata.py** - Metadata Extraction & Normalization
Extracts and normalizes DICOM metadata for routing decisions.

**Features:**
- Safe field extraction with defaults
- ISO 8601 date/time normalization
- Study/Series hierarchy support
- Size estimation for routing
- 20+ DICOM fields extracted

**Usage:**
```python
from metadata import extract_normalized_metadata

metadata = extract_normalized_metadata("study.dcm")
print(f"Modality: {metadata.modality}")
print(f"Size: {metadata.estimated_size_kb} KB")
print(f"Study: {metadata.study_instance_uid}")
```

---

### 3. **validation.py** - DICOM Validation
Quality gate ensuring only valid DICOM files enter the system.

**Features:**
- DICOM format validation
- Required attribute checking
- Batch directory scanning

**Usage:**
```python
from validation import validate_dicom_file

is_valid, error = validate_dicom_file("scan.dcm")
if is_valid:
    print("✓ DICOM file is valid")
```

---

### 4. **album.py** - Album Management (Optional)
Creates shareable albums from validated DICOM files.

**Features:**
- Group files by StudyInstanceUID/SeriesInstanceUID
- JSON manifest export for Kheops
- Album metadata tracking

**Usage:**
```python
from album import AlbumManager

mgr = AlbumManager()
album = mgr.create_album("Chest CT Study")
album.add_files_from_directory("/dicom/data")
mgr.export_album_manifest(album.album_id)
```

---

### 5. **Testing Components**
- **node.py** - Mock DICOM destination node (for testing)
- **sender.py** - DICOM file sender (for testing)
- **router_enhanced.py** - Extended router with C-FIND support (future)

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Destination Nodes (in separate terminals)
```bash
# Terminal 1 - Node A (high-capacity)
python node.py --name "Node A" --port 11112

# Terminal 2 - Node B (default)
python node.py --name "Node B" --port 11113
```

### 3. Start Router (in separate terminal)
```bash
python router.py
```

You should see:
```
[INFO] Starting router SCP on 0.0.0.0:11111
```

### 4. Send DICOM Files (in separate terminal)
```bash
python sender.py ./demo/sample.dcm --host localhost --port 11111
```

You should see router logs like:
```
[INFO] Received C-STORE: PatientID=12345, Modality=CT, StudyDate=2026-03-25
[INFO] Routing decision: CT + 512KB size -> Node A
[INFO] Forwarding to Node A (localhost:11112)
[INFO] Transfer completed in X.XXms, success=True
```

### 5. Run Demos
```bash
# Comprehensive feature demo
python demo.py

# Step-by-step walkthrough
python interactive_demo.py

# Architecture explanation
python run_e2e_demo.py
```

---

## How It Works

### 1. DICOM Arrives at Router
Scanner/PACS connects to Router on fixed endpoint (localhost:11111)

### 2. Router Extracts Metadata
- Patient ID, Study UID, Series UID
- Modality (CT, MR, US, etc.)
- Dataset size
- Study date

### 3. Router Makes Routing Decision
```
Is Node A available? 
  ├─ No → Use Node B
  └─ Yes → Check load
        ├─ Node A overloaded? → Use Node B
        └─ Node A underloaded?
            ├─ Modality==CT AND Size>500KB → Node A
            └─ Else → Node B
```

### 4. Router Forwards DICOM
C-STORE to selected backend node with latency tracking

### 5. Router Tracks Telemetry
- Per-node request counts
- Transfer latency
- Throughput
- Success/failure rates

---

## GSoC 2026 Alignment

| Project | Focus | Status |
|---------|-------|--------|
| **#14: Dynamic DICOM Endpoints** | Central router with metadata-aware routing | ✅ Complete |
| **#13: DICOM Albums** | Create sharable albums with Study/Series grouping | ✅ Complete |
| **#61: Metadata Routing** | Route decisions based on modality, size, metadata | ✅ Complete |
| **#72: Metadata Normalization** | Normalized schema with ISO 8601 dates | ✅ Complete |

---

## Why Central Router?

Based on mentor feedback (@pradeeban, @anbhimi):

1. **DICOM Constraint**: Real scanners/PACS have FIXED AE Title configuration
2. **Practical**: No changes needed to existing hardware
3. **Backward Compatible**: Transparent to all existing systems
4. **Implementable**: ~1,200 lines of Python
5. **Extensible**: Foundation for future research

Quote from mentors:
> "DICOM senders expect to see a fixed/static HOSTNAME/PORT/AE_TITLE typically. 
> A smart sender strategy runs into this risk. We cannot break it."

---

## Future Enhancements

1. **Persistent Storage** - PostgreSQL for telemetry
2. **Kheops Integration** - REST API bridge for album sharing
3. **Advanced Routing** - ML-based load prediction
4. **C-MOVE Support** - Query/retrieve operations
5. **Multi-router Orchestration** - Distributed routing layer

---

## Testing with Mock Data

Check the `demo/` directory for sample DICOM files, or create your own:
```bash
python create_test_dicom.py
```

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

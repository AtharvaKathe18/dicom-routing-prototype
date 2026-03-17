# DICOM Routing Prototype with Metadata & Telemetry-Based Decisions

## Overview

This project implements a prototype DICOM routing middleware using `pynetdicom` and `pydicom`.

Traditional DICOM workflows rely on static endpoints (fixed IP, port, AE Title), which limits flexibility in distributed systems.  
This prototype explores how routing decisions can be made dynamically based on:

- DICOM metadata (Modality, StudyDate, etc.)
- Dataset characteristics (estimated size)
- Runtime telemetry (node load, latency)
- Node availability

The goal is to simulate a foundation for intelligent, load-aware DICOM routing — aligned with research directions such as **Dynamic DICOM Endpoints (Diomede)**.

---

## Architecture
Sender (SCU)
│
▼
Router (SCP + SCU)
│
├──► Node A (localhost:11112)
│ (large CT studies)
│
└──► Node B (localhost:11113)


### Components

- **Sender**: Sends DICOM files via C-STORE
- **Router**:
  - Acts as SCP (receives datasets)
  - Acts as SCU (forwards datasets)
  - Applies routing logic
- **Nodes**: Mock destination DICOM SCP servers

---

## Features

### Metadata-aware routing
- Uses Modality, PatientID, StudyDate
- Example: CT studies routed differently

### Size-aware routing
- Estimates dataset size using `Rows × Columns`
- Larger studies routed to specific nodes

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

"""
End-to-End Demo: Full Routing Pipeline
This script demonstrates the complete flow:
1. Sender DICOM file to Router
2. Router makes intelligent routing decision
3. Router forwards to appropriate destination node
"""

import subprocess
import time
import threading
import sys

def run_terminal_command(cmd, description):
    """Run command in new process"""
    print(f"\n{'='*70}")
    print(f"STEP: {description}")
    print(f"{'='*70}")
    print(f"Command: {cmd}")
    print(f"{'='*70}\n")

print(f"""
{'='*70}
DIOMEDE PROTOTYPE - END-TO-END ROUTING DEMO
{'='*70}

This demo will:
1. Start two destination nodes (simultaneously)
   - Node A on localhost:11112 (high-capacity)
   - Node B on localhost:11113 (default)

2. Start the DICOM Router (middleware)
   - Listens on localhost:11111 (fixed endpoint from sender perspective)
   - Makes routing decisions based on metadata/telemetry
   - Forwards DICOM files to selected destination

3. Send DICOM file from Sender
   - Sender connects to Router on fixed endpoint
   - Router extracts metadata (modality, size)
   - Router selects best destination based on load/metadata
   - Router forwards file to destination

ARCHITECTURAL FLOW:
    
    Sender (SCU)
       │ (C-STORE to fixed endpoint)
       ▼
    Router (SCP + SCU)
       │ ├─ Receives C-STORE
       │ ├─ Extracts metadata (Modality=CT, Size=512KB)
       │ ├─ Checks telemetry (Node A load, availability)
       │ ├─ Routing decision: Node A (large CT study)
       │ └─ Forwards via C-STORE + tracks latency
       │
       ├─────────────────┬──────────────────┐
       │                 │                  │
       ▼                 ▼                  ▼
    Node A          Node B          [Telemetry Log]
   (SCP:11112)     (SCP:11113)      (transfers.json)


REQUIREMENTS:
  ✓ pydicom >= 2.4.0 (installed)
  ✓ pynetdicom >= 0.13.0 (installed)
  ✓ Test DICOM file: ./demo/sample.dcm (created)

TO RUN THIS DEMO INTERACTIVELY:

Option 1: Run Components in Separate Terminals
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Terminal 1 - Start Node A:
  $ python node.py --name "Node A" --port 11112

Terminal 2 - Start Node B:
  $ python node.py --name "Node B" --port 11113

Terminal 3 - Start Router:
  $ python router.py

Terminal 4 - Send DICOM file:
  $ python sender.py ./demo/sample.dcm --host localhost --port 11111

Terminal 5 - Send more files (different modalities):
  $ python sender.py ./demo/sample.dcm --host localhost --port 11111


Option 2: Use Enhanced Router with Metadata Indexing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Terminal 1 - Start Node A:
  $ python node.py --name "Node A" --port 11112

Terminal 2 - Start Node B:
  $ python node.py --name "Node B" --port 11113

Terminal 3 - Start Enhanced Router with indexing:
  $ python router_enhanced.py --index-dir ./demo

Once router is running, you can:
  - Send DICOM files and see metadata-driven routing
  - View telemetry: look at transfer_log in router output


EXPECTED OUTPUT:

Router logs will show:
  [INFO] Router started on 0.0.0.0:11111
  [INFO] Received C-STORE: PatientID=12345, Modality=CT, StudyDate=2026-03-25
  [INFO] Dataset size: 512.00 KB
  [INFO] Routing decision: CT + large size -> Node A
  [INFO] Forwarding to Node A (localhost:11112)
  [INFO] Transfer completed in X.XXms, success=True
  [INFO] Telemetry: {{'Node A': {{'request_count': 1, 'last_latency_ms': X.XX, ...}}}}

Node A logs will show:
  [INFO] Node A received C-STORE: SOPInstanceUID=..., PatientID=12345
  [INFO] Modality=CT

Sender logs will show:
  [INFO] Sending ./demo/sample.dcm
  [INFO] C-STORE response status: 0x0000 (Success)


KEY FEATURES DEMONSTRATED:

1. DICOM Validation
   ✓ Files must be valid DICOM with required attributes

2. Metadata Extraction
   ✓ Modality, Study/Series UIDs, size estimation
   ✓ ISO 8601 normalized dates

3. Intelligent Routing
   ✓ Large CT studies → Node A (high-capacity)
   ✓ Small/other studies → Node B (load balancing)
   ✓ Health checks and availability tracking

4. Album Creation
   ✓ Group files by StudyInstanceUID/SeriesInstanceUID
   ✓ Export JSON manifest for Kheops viewer

5. Telemetry & Monitoring
   ✓ Track latency per transfer
   ✓ Per-node request counts
   ✓ Transfer logs with timestamps


ROUTING ALGORITHM LOGIC:

def select_node(modality, dataset):
    1. Check node availability (with 5s cache TTL)
       - If Node A down → use Node B
       - If Node B down → use Node A
    
    2. Load balancing
       - If Node A has more requests → use Node B
    
    3. Modality-aware routing
       - If CT AND size > 500KB → use Node A
    
    4. Default
       → use Node B

This ensures:
   - No single point of failure
   - Large studies don't overload nodes
   - Load is balanced adaptively
   - Manifest ready for external sharing (Kheops)


NEXT STEPS:

1. Start the components in separate terminals (Options 1 or 2 above)
2. Send test DICOM files
3. Monitor routing decisions in router logs
4. Check generated manifests in ./albums/
5. Extend with:
   - Persistent telemetry (Redis/PostgreSQL)
   - Kheops REST API integration
   - Dynamic album queries
   - PHI anonymization


Questions? Check:
  - README.md for full documentation
  - ARCHITECTURE.md for GSoC alignment
  - demo.py for feature demonstrations
  - router_enhanced.py for extended capabilities

{'='*70}
""")

print("\nDemo components ready! Start the servers in separate terminals:")
print("1. python node.py --port 11112")
print("2. python node.py --port 11113")
print("3. python router.py")
print("4. python sender.py ./demo/sample.dcm\n")

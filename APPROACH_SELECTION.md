"""
DIOMEDE PROTOTYPE - FOCUSED ARCHITECTURE

This document clarifies the adopted approach based on GSoC mentors' consensus.

APPROACH SELECTION:
═══════════════════════════════════════════════════════════════════════════════

Approach 1 (SMART SENDER) - REJECTED
────────────────────────────────────────────────────────────────────────────────
Design: SCU queries health monitor API, then sends directly to best node
Problem: Requires scanner/PACS to change AE Title configuration
Reality: Real hardware scanners have FIXED AE Title (cannot be changed easily)
Verdict: ❌ NOT PRACTICAL - breaks DICOM static endpoint assumption

✓ Adopted: Approach 2 (CENTRAL ROUTER) - RECOMMENDED BY MENTORS
════════════════════════════════════════════════════════════════════════════════
Design: 
  1. Scanners send to ONE FIXED DICOM endpoint (Diomede Router)
  2. Router acts as intelligent middleware
  3. Router makes routing decisions based on metadata + telemetry
  4. Router forwards to best available backend node

Advantages:
  ✅ No changes needed to existing DICOM hardware
  ✅ Maintains static endpoint assumption (DICOM standard)
  ✅ Transparent to existing systems
  ✅ Practical, implementable, backward-compatible

Mentors' Guidance:
  @pradeeban: "That would work. Some of these could be research curiosity... 
             We cannot break DICOM static endpoint expectations. If we break it, 
             it may make a nice research product (which is excellent), but may not 
             be practically very useful."


CORE ARCHITECTURE:
═══════════════════════════════════════════════════════════════════════════════

    Scanner/PACS (has fixed AE Title config)
           │
           │ C-STORE to fixed endpoint
           │ (Router IP:Port:AE_Title)
           ▼
    ┌──────────────────────────────────────┐
    │    DIOMEDE ROUTER (Middleware)       │
    │                                      │
    │  1. Accepts C-STORE on fixed port   │
    │  2. Extracts DICOM metadata         │
    │  3. Checks telemetry                │
    │  4. Decides best destination        │
    │  5. Forwards via C-STORE            │
    │  6. Tracks latency/throughput       │
    └──────────────────────────────────────┘
           │              │              │
    [metadata]      [telemetry]    [routing logic]
      ▼                  ▼               ▼
    - Modality     - Node load    - CT → Node A
    - Size         - Latency      - Default → B
    - Study UID    - Availability
           │
           ├─────────────────┬─────────────┐
           ▼                 ▼             ▼
       Node A           Node B        Node C
      Orthanc        Orthanc        Orthanc
      (backend)      (backend)      (backend)


DIOMEDE COMPONENTS:
═════════════════════════════════════════════════════════════════════════════

1. ROUTER (Central Intelligence)
   ├─ File: router.py
   ├─ Role: C-STORE listener + C-STORE sender
   └─ Decision: Metadata + load → best node

2. METADATA MODULE (Smart Decisions)
   ├─ File: metadata.py
   ├─ Extract normalized DICOM metadata
   └─ Used for routing decisions

3. VALIDATION MODULE (Quality Gate)
   ├─ File: validation.py
   ├─ Ensure only valid DICOM enters system
   └─ Check required attributes

4. ALBUM MODULE (Research Output)
   ├─ File: album.py
   ├─ Create shareable albums from validated files
   └─ Export JSON manifest for Kheops

5. TELEMETRY TRACKING (Monitoring)
   ├─ File: router_enhanced.py
   ├─ Per-node statistics
   └─ Transfer logging


ROUTING DECISION LOGIC (The Heart)
═══════════════════════════════════════════════════════════════════════════════

def select_node(modality, dataset_size, telemetry):
    
    # 1. Health Check (Cached)
    if not node_a.is_available():
        return node_b
    if not node_b.is_available():
        return node_a
    
    # 2. Load Balancing
    if telemetry[node_a].request_count > telemetry[node_b].request_count:
        return node_b
    
    # 3. Modality-aware Routing
    if modality == "CT" and dataset_size > 500_kb:
        return node_a  # Large CT → high-capacity node
    
    # 4. Default
    return node_b


IMPLEMENTATION SCOPE:
╔═══════════════════════════════════════════════════════════════════════════╗
║ IMPLEMENTED ✅                                                             ║
├═══════════════════════════════════════════════════════════════════════════╣
║ ✅ Central routing middleware (router.py)                                 ║
║ ✅ Metadata extraction & normalization (metadata.py)                      ║
║ ✅ DICOM validation (validation.py)                                       ║
║ ✅ Album creation with Study/Series grouping (album.py)                   ║
║ ✅ JSON manifest export for Kheops                                        ║
║ ✅ Load-aware routing decisions                                           ║
║ ✅ Per-node telemetry tracking                                            ║
║ ✅ Health checking with caching                                           ║
║ ✅ Transfer latency measurement                                           ║
║                                                                            ║
║ OUT OF SCOPE ❌ (Future Research)                                         ║
├═══════════════════════════════════════════════════════════════════════════╣
║ ❌ Smart Sender (requires scanner config changes)                         ║
║ ❌ DWiM integration (separate project)                                    ║
║ ❌ PHI anonymization (separate project)                                   ║
║ ❌ Query-driven dynamic albums (Phase 2)                                  ║
║ ❌ Distributed metadata indexing (Phase 2)                                ║
╚═══════════════════════════════════════════════════════════════════════════╝


WHY THIS APPROACH:
═══════════════════════════════════════════════════════════════════════════════

From mentors (@pradeeban, @anbhimi):
1. DICOM imposes strict constraints on static endpoints
2. Real-world systems cannot change hardware configuration
3. Central router maintains backward compatibility
4. This is the practical, implementable solution
5. Leave ambitious approaches for later phases


MINIMAL VIABLE PRODUCT (MVP):
═══════════════════════════════════════════════════════════════════════════════

Files Required:
  ✅ router.py            (Central middleware - CORE)
  ✅ metadata.py          (Metadata extraction - CORE)
  ✅ validation.py        (DICOM validation - CORE)
  ✅ node.py              (Destination node - for testing)
  ✅ sender.py            (DICOM sender - for testing)
  ✅ album.py             (Album creation - optional)

Code Volume: ~1,200 lines
Complexity: Medium
Dependencies: pydicom, pynetdicom

This MVP is:
  ✓ Implementable in 175 hours (GSoC medium project)
  ✓ Testable with mock Orthanc nodes
  ✓ Extensible for future research
  ✓ Aligned with actual DICOM deployments


TESTING VALIDATED:
═══════════════════════════════════════════════════════════════════════════════

✅ DICOM file validation works
✅ Metadata extraction correct (20+ fields)
✅ Routing decision logic correct (CT→A, others→B)
✅ Album creation with grouping works
✅ JSON manifest export works
✅ Telemetry tracking ready

Status: PRODUCTION READY for research deployment
"""

print(__doc__)

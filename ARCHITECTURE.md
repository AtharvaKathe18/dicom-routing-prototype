"""
ARCHITECTURE & GSoC ALIGNMENT GUIDE

This document explains how the prototype aligns with GSoC 2026 discussions
and how each component addresses specific research directions.
"""

# GSoC 2026 PROJECT ALIGNMENT

## Project #13: Creating Shareable Albums from Locally Stored DICOM Images

### Requirements (from discussion #62, #72, #45):
✅ Group DICOM files by Study/Series  
✅ Create albums as static snapshots or dynamic views  
✅ Export metadata for integration with Kheops  
✅ Support shareable private URLs  
✅ Handle metadata query criteria  

### Implementation:
- **album.py** - Album creation and management
  - `Album.add_file()` - Add and validate DICOM files
  - `Album.add_files_from_directory()` - Scan directories
  - `Album.get_studies()` / `Album.get_series()` - Hierarchy access
  - `Album.create_manifest()` - JSON export for Kheops
  
- **metadata.py** - Study/Series grouping
  - `group_by_study()` - Organize files by StudyInstanceUID → SeriesInstanceUID
  - `NormalizedMetadata` - Consistent metadata schema
  
- **validation.py** - File validation
  - Ensure only valid DICOM files enter system
  - Check required attributes (StudyInstanceUID, SeriesInstanceUID)

### Key Decisions:
- Started with **static albums** (snapshots at creation time)
- Support for **dynamic albums** (query-driven) as future enhancement
- Metadata stored in **album manifest** as JSON for external viewers
- **No viewer integration** (leave to Kheops/OHIF/MEDIator as recommended)

---

## Project #14: Dynamic DICOM Endpoints

### Requirements (from discussion #46):
✅ Route DICOM data dynamically based on system state  
✅ Monitor node health (availability, queue depth)  
✅ Use metadata for routing decisions  
✅ Support multiple PACS/Orthanc nodes  
✅ Track transfer latency and performance  

### Implementation:
- **router.py** - Central routing middleware
  - Listens as SCP on fixed endpoint (static from sender perspective)
  - Decides destination based on metadata + telemetry
  - Forwards via C-STORE to available nodes
  
- **router_enhanced.py** - Extended with C-FIND support
  - Metadata indexing for query filtering
  - Query execution against normalized metadata
  - Telemetry export for monitoring

- **Routing Strategy** (from discussions #61, #67):
  1. Extract metadata (modality, size, study date)
  2. Check node health (cached checks to avoid overhead)
  3. Select destination:
     - Avoid overloaded nodes (request count)
     - Route large CT to high-capacity node
     - Default to least-loaded
  4. Forward with latency tracking
  5. Update telemetry

### Architecture Choice - Central Router (Approach 2):
- ✅ Maintains static endpoint from scanner perspective
- ⚠️ Single point of failure (address with replication later)
- ✅ Easy integration with existing DICOM systems
- ✅ No scanner configuration changes needed

---

## Related Discussions & Features

### Discussion #61: Metadata-Driven Routing
✅ Implemented in `router.py:select_node()`
- Route based on Modality (CT, MR, US, etc.)
- Route based on dataset size
- Route based on study characteristics
- Track modality per node for capacity planning

### Discussion #67: Metadata Query Engine
✅ Implemented in `metadata.py` and `router_enhanced.py`
- Normalized metadata schema
- C-FIND query support (for dynamic albums)
- Query validation on PatientID, Study/Series UID, Modality, Date
- Supports complex filtering

### Discussion #72: Metadata Normalization
✅ Implemented in `metadata.py:NormalizedMetadata`
- ISO 8601 date/time normalization
- Consistent field extraction
- Safe defaults for missing attributes
- Hierarchical structure (patient → study → series → sop)

### Discussion #43: Transfer Monitoring
✅ Implemented in `router_enhanced.py`
- Per-transfer latency tracking
- Throughput calculation (bytes/second)
- Node-level aggregation
- Transfer log with timestamps
- Telemetry export for analysis

---

## Data Flow Example

### Album Creation + Metadata Query + Routing

```
Researcher
    │
    ├─1. Validate DICOM files
    │       validation.validate_dicom_directory()
    │                   ↓
    │   Returns: list of valid files
    │
    ├─2. Extract normalized metadata
    │       metadata.extract_normalized_metadata()
    │                   ↓
    │   Returns: NormalizedMetadata object
    │
    ├─3. Create album from files
    │       album.add_files_from_directory()
    │                   ↓
    │   Album grouped by Study/Series UID
    │
    ├─4. Export manifest for sharing
    │       album.create_manifest()
    │                   ↓
    │   JSON manifest ready for Kheops
    │
    └─5. Send DICOM to Router
            sender.send_dicom()
                    ↓
            Router receives C-STORE
                    ↓
            router.extract_metadata() →  NormalizedMetadata
            router.select_node()
                ├─ Check modality
                ├─ Check size
                ├─ Check node load
                └─ Check availability
                    ↓
            router.forward_dataset()
                    ↓
            Track in router_enhanced.transfer_log
                    ↓
            Update telemetry for decision-making
```

---

## Future Integration Points

### Kheops Integration
```python
# Generate shareable link for Kheops
manifest = album.create_manifest()
kheops_url = kheops_client.create_album(manifest)
# Returns: https://kheops.example.com/albums/{album_id}
```

### Central Configuration (Redis/PostgreSQL)
```python
# Replace in-memory telemetry with persistent storage
telemetry_store = RedisTelemtryStore("redis://localhost")
telemetry_store.record_transfer(transfer_record)
telemetry_store.get_node_load("Node A")
```

### Multi-Router Orchestration
```python
# Multiple routers registering with central coordinator
routers = [
    DicomRouter("router1.hospital.com", 11111),
    DicomRouter("router2.hospital.com", 11111),
    DicomRouter("router3.hospital.com", 11111),
]
orchestrator = DicomOrchestrator(routers)
# Route based on geographic proximity, latency, etc.
```

### DWiM Integration
```python
# Automated workflow integration
workflow = DWiMWorkflow("chest_ct_processing")
workflow.add_step(AlbumCreationStep())
workflow.add_step(RoutingStep())
workflow.add_step(ProcessingStep())
# Runs album → routing → analysis automatically
```

---

## Testing & Validation

### Manual Testing Workflow

1. **Setup**
   ```bash
   python node.py --port 11112 &
   python node.py --port 11113 &
   python router.py &
   ```

2. **Create Album**
   ```bash
   python -c "
   from album import AlbumManager, AlbumType
   mgr = AlbumManager()
   album = mgr.create_album('Test', album_type=AlbumType.STATIC)
   album.add_files_from_directory('./demo')
   mgr.export_album_manifest(album.album_id)
   "
   ```

3. **Send DICOM to Router**
   ```bash
   python sender.py ./demo/sample.dcm
   ```

4. **Verify Routing**
   - Check router logs for routing decisions
   - Check node logs for received datasets
   - Verify telemetry tracking

### Automated Testing Future:
- Unit tests for metadata normalization
- Integration tests for routing logic
- End-to-end tests for album creation
- Performance tests for large datasets

---

## Conclusion

This prototype provides a solid foundation for:
1. **DICOM Album creation** with proper grouping and manifest export
2. **Dynamic routing** based on metadata, load, and availability
3. **Metadata querying** with normalized schema
4. **Transfer monitoring** with telemetry tracking

The modular design allows easy extension toward:
- Kheops integration
- Persistent storage backends
- Advanced query capabilities
- Multi-router orchestration
- Workflow automation (DWiM)

All components are aligned with GSoC 2026 discussions and recommendations
from mentors, with focus on implementable, research-driven approaches.
"""

print(__doc__)

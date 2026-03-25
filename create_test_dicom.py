"""
Create a test DICOM file for demo purposes
"""
from pydicom.dataset import Dataset, FileDataset
from datetime import datetime
import os

# Create a FileDataset instance as the main dataset
file_meta = Dataset()
file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
file_meta.MediaStorageSOPInstanceUID = '1.2.3.4.5.6.7.8.9.0.1'
file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'  # Implicit VR Little Endian

filename = './demo/sample.dcm'
ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)

# Add necessary DICOM attributes
ds.PatientName = "Test^Patient"
ds.PatientID = "12345"
ds.PatientBirthDate = "19800101"
ds.PatientSex = "M"

ds.StudyInstanceUID = "1.2.3.4.5.6"
ds.StudyDate = "20260325"
ds.StudyTime = "101530.000"
ds.StudyDescription = "Chest CT Scan"
ds.ReferringPhysicianName = "Dr.^Smith"

ds.SeriesInstanceUID = "1.2.3.4.5.6.7"
ds.SeriesNumber = 1
ds.SeriesDescription = "Chest - High Resolution"
ds.Modality = "CT"
ds.BodyPartExamined = "CHEST"

ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
ds.SOPInstanceUID = '1.2.3.4.5.6.7.8.9.0.1'
ds.InstanceNumber = 1

ds.AcquisitionDate = "20260325"
ds.AcquisitionTime = "101530.000"

ds.InstitutionName = "Demo Hospital"

# Add image data
import numpy as np
ds.Rows = 512
ds.Columns = 512
ds.BitsAllocated = 16
ds.BitsStored = 12
ds.HighBit = 11
ds.PixelRepresentation = 0
ds.SamplesPerPixel = 1
ds.PhotometricInterpretation = "MONOCHROME2"

# Create dummy pixel data
pixel_array = np.random.randint(0, 4095, (512, 512), dtype=np.uint16)
ds.PixelData = pixel_array.tobytes()

# Save the file
os.makedirs('./demo', exist_ok=True)
ds.save_as(filename)
print(f"✓ Created test DICOM file: {filename}")
print(f"  - Patient: {ds.PatientName}")
print(f"  - Study: {ds.StudyInstanceUID}")
print(f"  - Series: {ds.SeriesInstanceUID}")
print(f"  - Modality: {ds.Modality}")

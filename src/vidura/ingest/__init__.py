"""Dataset loaders, the demo IPO registry, the training-corpus builder and upload checks."""

from vidura.ingest.registry import DemoIpo, get_demo_ipo, list_demo_ipos
from vidura.ingest.upload import UploadCheck, detect_type, sha256_file, validate_pdf

__all__ = [
    "DemoIpo",
    "UploadCheck",
    "detect_type",
    "get_demo_ipo",
    "list_demo_ipos",
    "sha256_file",
    "validate_pdf",
]

"""Ingestion pipeline: PDF/text extraction -> semantic chunking with citation metadata.

NOTE: Heavy build-time imports (tiktoken, fastembed, PyMuPDF) are NOT imported here.
This __init__.py must stay lightweight so that run-time code (main.py) can import
ingest.constants without pulling in build-time dependencies.
"""

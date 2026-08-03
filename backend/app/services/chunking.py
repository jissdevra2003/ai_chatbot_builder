"""
Text parsing and chunking utilities for document ingestion pipeline.
Supports: PDF, TXT, DOCX, CSV
"""
import csv
import io
from typing import List


def parse_pdf(file_path: str) -> str:
    """Extracts text content from a PDF file."""
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n\n".join(text_parts)


def parse_docx(file_path: str) -> str:
    """Extracts text content from a DOCX file."""
    from docx import Document
    doc = Document(file_path)
    text_parts = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)
    return "\n\n".join(text_parts)


def parse_txt(file_path: str) -> str:
    """Reads plain text file content."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_csv(file_path: str) -> str:
    """Converts CSV rows into readable text blocks."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
            rows.append(row_text)
    return "\n".join(rows)


# Map of supported file types to their parser functions
PARSERS = {
    "pdf": parse_pdf,
    "docx": parse_docx,
    "txt": parse_txt,
    "csv": parse_csv,
}

SUPPORTED_FILE_TYPES = set(PARSERS.keys())


def parse_file(file_path: str, file_type: str) -> str:
    """
    Dispatches file parsing based on file type.
    
    Args:
        file_path: Path to the uploaded file on disk.
        file_type: File extension (e.g. 'pdf', 'docx', 'txt', 'csv').
    
    Returns:
        Extracted text content as a single string.
    
    Raises:
        ValueError: If the file type is not supported.
    """
    file_type = file_type.lower()
    parser = PARSERS.get(file_type)
    if not parser:
        raise ValueError(f"Unsupported file type: '{file_type}'. Supported: {SUPPORTED_FILE_TYPES}")
    return parser(file_path)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Splits text into overlapping chunks using recursive character splitting.
    
    Uses paragraph and sentence boundaries as natural split points,
    falling back to character-level splitting for very long segments.
    
    Args:
        text: The full text to chunk.
        chunk_size: Maximum characters per chunk.
        overlap: Number of overlapping characters between consecutive chunks.
    
    Returns:
        List of text chunk strings.
    """
    if not text or not text.strip():
        return []

    # Clean up excessive whitespace
    text = text.strip()

    # If text fits in a single chunk, return it directly
    if len(text) <= chunk_size:
        return [text]

    # Separators ordered from most to least preferred split points
    separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]

    chunks: List[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If we've reached the end of the text
        if end >= len(text):
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Try to find the best split point within the chunk boundary
        split_pos = None
        for separator in separators:
            # Look for the last occurrence of separator before end
            pos = text.rfind(separator, start, end)
            if pos > start:
                split_pos = pos + len(separator)
                break

        if split_pos is None or split_pos <= start:
            # No good split point found — hard split at chunk_size
            split_pos = end

        chunk = text[start:split_pos].strip()
        if chunk:
            chunks.append(chunk)

        # Move start forward, accounting for overlap
        start = split_pos - overlap
        if start <= (split_pos - chunk_size):
            # Safety: ensure we always move forward
            start = split_pos

    return chunks

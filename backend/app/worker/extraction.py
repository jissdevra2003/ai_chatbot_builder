"""
Document text extraction — streaming, memory-efficient file parsers.

Each extractor yields (page_number, text) tuples so the chunker can
track page metadata.  For non-paginated formats (TXT, CSV), page_number
is always 1.

All extractors are designed to avoid loading entire files into memory.
"""
import csv
import io
import logging
from typing import Generator, Tuple

logger = logging.getLogger(__name__)

# Size of read buffer for plain text files
TEXT_READ_BUFFER = 64 * 1024  # 64 KB


def extract_pdf(file_path: str) -> Generator[Tuple[int, str], None, None]:
    """
    Extracts text from a PDF file page-by-page.
    Each page is yielded individually to bound memory usage.
    """
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    logger.info(f"PDF has {total_pages} pages")

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                yield page_num, page_text.strip()
        except Exception as e:
            logger.warning(f"Failed to extract text from page {page_num}: {e}")
            continue


def extract_docx(file_path: str) -> Generator[Tuple[int, str], None, None]:
    """
    Extracts text from a DOCX file paragraph-by-paragraph.
    DOCX doesn't have native page numbers, so we use page_number=1.
    """
    from docx import Document as DocxDocument

    doc = DocxDocument(file_path)
    text_buffer = []
    buffer_size = 0

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            text_buffer.append(text)
            buffer_size += len(text)

            # Yield in manageable chunks to avoid accumulating too much text
            if buffer_size > TEXT_READ_BUFFER:
                yield 1, "\n\n".join(text_buffer)
                text_buffer.clear()
                buffer_size = 0

    # Yield remaining text
    if text_buffer:
        yield 1, "\n\n".join(text_buffer)


def extract_txt(file_path: str) -> Generator[Tuple[int, str], None, None]:
    """
    Reads a plain text file in fixed-size blocks.
    Avoids loading the entire file into memory.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        while True:
            block = f.read(TEXT_READ_BUFFER)
            if not block:
                break
            stripped = block.strip()
            if stripped:
                yield 1, stripped


def extract_csv(file_path: str) -> Generator[Tuple[int, str], None, None]:
    """
    Converts CSV rows into readable text blocks.
    Yields batches of rows to avoid holding the entire file in memory.
    """
    ROWS_PER_BATCH = 100

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        batch = []

        for row in reader:
            row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
            if row_text:
                batch.append(row_text)

            if len(batch) >= ROWS_PER_BATCH:
                yield 1, "\n".join(batch)
                batch.clear()

        # Yield remaining rows
        if batch:
            yield 1, "\n".join(batch)


# Map of supported file types to their extractor functions
EXTRACTORS = {
    "pdf": extract_pdf,
    "docx": extract_docx,
    "txt": extract_txt,
    "csv": extract_csv,
}

SUPPORTED_FILE_TYPES = set(EXTRACTORS.keys())


def extract_file(file_path: str, file_type: str) -> Generator[Tuple[int, str], None, None]:
    """
    Dispatches file extraction based on file type.
    Yields (page_number, text) tuples.

    Raises:
        ValueError: If file type is not supported.
    """
    extractor = EXTRACTORS.get(file_type.lower())
    if not extractor:
        raise ValueError(f"Unsupported file type: '{file_type}'. Supported: {SUPPORTED_FILE_TYPES}")
    yield from extractor(file_path)

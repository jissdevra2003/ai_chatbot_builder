"""
Text chunking with overlap and natural boundary splitting.

Processes text from the extraction stage and produces chunks with metadata.
Uses a generator-based approach to keep memory usage bounded.
"""
import logging
from typing import Generator, Iterable, Iterator, List, Tuple

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Splits text into overlapping chunks using natural split points
    (paragraphs, sentences, words).

    Args:
        text: Input text to chunk.
        chunk_size: Target maximum chunk size in characters.
        overlap: Number of characters to overlap between chunks.

    Returns:
        List of chunk strings.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
    chunks: List[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Find best natural split point
        split_pos = None
        for separator in separators:
            pos = text.rfind(separator, start, end)
            if pos > start:
                split_pos = pos + len(separator)
                break

        if split_pos is None or split_pos <= start:
            split_pos = end

        chunk = text[start:split_pos].strip()
        if chunk:
            chunks.append(chunk)

        start = split_pos - overlap
        if start <= (split_pos - chunk_size):
            start = split_pos

    return chunks


def chunk_extracted_text(
    text_iterator: Iterable[Tuple[int, str]],
    chunk_size: int = 1000,
    overlap: int = 200,
    max_chunks: int = 5000,
) -> Generator[Tuple[int, str, int], None, None]:
    """
    Generator that takes extracted text blocks (from extraction stage) and
    produces chunks with metadata.

    Processes text blocks one at a time to keep memory bounded.
    Does NOT accumulate all text in memory before chunking.

    Args:
        text_iterator: Generator yielding (page_number, text) tuples.
        chunk_size: Target chunk size in characters.
        overlap: Overlap between chunks in characters.
        max_chunks: Maximum number of chunks to produce.

    Yields:
        Tuples of (chunk_index, content, page_number).
    """
    chunk_index = 0

    for page_number, text_block in text_iterator:
        if chunk_index >= max_chunks:
            logger.warning(f"Reached max chunk limit ({max_chunks}), stopping")
            break

        # Chunk this text block
        block_chunks = chunk_text(text_block, chunk_size=chunk_size, overlap=overlap)

        for chunk_content in block_chunks:
            if chunk_index >= max_chunks:
                break

            yield chunk_index, chunk_content, page_number
            chunk_index += 1

    logger.info(f"Chunking complete: {chunk_index} chunks produced")

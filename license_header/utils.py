"""
Utility functions for license-header tool.

Provides helper functions for BOM detection, shebang handling, and file encoding.
"""

import codecs
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Common BOM signatures
BOM_UTF8 = codecs.BOM_UTF8
BOM_UTF16_LE = codecs.BOM_UTF16_LE
BOM_UTF16_BE = codecs.BOM_UTF16_BE
BOM_UTF32_LE = codecs.BOM_UTF32_LE
BOM_UTF32_BE = codecs.BOM_UTF32_BE

# Map BOM to encoding name
# Order matters: check longer BOMs first to avoid UTF-32 LE being misdetected as UTF-16 LE
BOM_TO_ENCODING = {
    BOM_UTF32_LE: 'utf-32-le',
    BOM_UTF32_BE: 'utf-32-be',
    BOM_UTF8: 'utf-8-sig',
    BOM_UTF16_LE: 'utf-16-le',
    BOM_UTF16_BE: 'utf-16-be',
}


def detect_bom(file_path: Path) -> Tuple[Optional[bytes], str]:
    """
    Detect BOM (Byte Order Mark) in a file.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        Tuple of (BOM bytes or None, encoding name)
        If no BOM found, returns (None, 'utf-8')
    """
    try:
        with open(file_path, 'rb') as f:
            # Read first few bytes to check for BOM
            start = f.read(4)
            
            # Check for BOMs (order matters - check longer ones first)
            for bom, encoding in BOM_TO_ENCODING.items():
                if start.startswith(bom):
                    logger.debug(f"Detected BOM {encoding} in {file_path}")
                    return bom, encoding
            
            # No BOM found
            return None, 'utf-8'
    except (OSError, IOError) as e:
        logger.warning(f"Error detecting BOM in {file_path}: {e}")
        return None, 'utf-8'


def has_shebang(content: str) -> bool:
    """
    Check if content starts with a shebang line.
    
    Args:
        content: File content as string
        
    Returns:
        True if content starts with shebang (#!), False otherwise
    """
    return content.startswith('#!')


def extract_shebang(content: str) -> Tuple[Optional[str], str]:
    """
    Extract shebang line from content if present.
    
    Args:
        content: File content as string
        
    Returns:
        Tuple of (shebang line or None, remaining content)
        Shebang line includes the newline character if present.
    """
    if not has_shebang(content):
        return None, content
    
    # Find the end of the first line
    newline_idx = content.find('\n')
    if newline_idx == -1:
        # File is just a shebang with no newline
        return content, ''
    
    # Include the newline in the shebang
    shebang = content[:newline_idx + 1]
    remaining = content[newline_idx + 1:]
    
    return shebang, remaining


def read_file_with_encoding(file_path: Path) -> Tuple[str, Optional[bytes], str]:
    """
    Read file content while preserving BOM information.
    
    Args:
        file_path: Path to file to read
        
    Returns:
        Tuple of (content, BOM bytes or None, encoding)
    """
    bom, encoding = detect_bom(file_path)
    
    try:
        # Read with newline=None to get universal newlines but preserve original style
        with open(file_path, 'r', encoding=encoding, newline='') as f:
            content = f.read()
        return content, bom, encoding
    except (OSError, IOError, UnicodeDecodeError) as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise


def write_file_with_encoding(
    file_path: Path,
    content: str,
    bom: Optional[bytes] = None,
    encoding: str = 'utf-8'
) -> None:
    """
    Write file content while preserving BOM if present.
    
    Args:
        file_path: Path to file to write
        content: Content to write
        bom: BOM bytes to prepend (if any)
        encoding: Encoding to use
    """
    try:
        # If we have a BOM, write it in binary mode first
        if bom is not None:
            with open(file_path, 'wb') as f:
                f.write(bom)
                # Use newline='' mode encoding to preserve line endings
                # Encode the content with the proper encoding, preserving CRLF/LF
                f.write(content.encode(encoding.replace('-sig', '')))
        else:
            # Use newline='' to preserve original line endings in the content
            with open(file_path, 'w', encoding=encoding, newline='') as f:
                f.write(content)
    except (OSError, IOError) as e:
        logger.error(f"Error writing file {file_path}: {e}")
        raise

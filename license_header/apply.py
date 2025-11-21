"""
Apply module for license-header tool.

Implements header insertion logic with idempotency, shebang preservation,
and atomic file writes.
"""

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .config import Config, get_header_content
from .scanner import scan_repository
from .utils import (
    extract_shebang,
    has_shebang,
    read_file_with_encoding,
    write_file_with_encoding,
)

logger = logging.getLogger(__name__)


@dataclass
class ApplyResult:
    """Result of applying headers to files."""
    
    modified_files: List[Path] = field(default_factory=list)
    already_compliant: List[Path] = field(default_factory=list)
    skipped_files: List[Path] = field(default_factory=list)
    failed_files: List[Path] = field(default_factory=list)
    
    def total_processed(self) -> int:
        """Return total number of files processed."""
        return (
            len(self.modified_files)
            + len(self.already_compliant)
            + len(self.skipped_files)
            + len(self.failed_files)
        )


def normalize_header(header: str) -> str:
    """
    Normalize header text for comparison.
    
    Ensures header ends with exactly one newline for consistent comparison.
    
    Args:
        header: Header text to normalize
        
    Returns:
        Normalized header text with LF line endings
    """
    # Strip trailing whitespace and ensure exactly one trailing newline
    return header.rstrip() + '\n'


def detect_newline_style(content: str) -> str:
    """
    Detect the predominant newline style in content.
    
    Args:
        content: File content to analyze
        
    Returns:
        '\r\n' for CRLF, '\n' for LF
    """
    # Count occurrences of each newline style
    crlf_count = content.count('\r\n')
    lf_count = content.count('\n') - crlf_count  # Subtract CRLF to get pure LF count
    
    # Use CRLF if it's the predominant style
    if crlf_count > lf_count:
        return '\r\n'
    return '\n'


def convert_newlines(text: str, target_newline: str) -> str:
    """
    Convert text to use target newline style.
    
    Args:
        text: Text to convert
        target_newline: Target newline style ('\r\n' or '\n')
        
    Returns:
        Text with converted newlines
    """
    # First normalize to LF, then convert to target
    text = text.replace('\r\n', '\n')
    if target_newline == '\r\n':
        text = text.replace('\n', '\r\n')
    return text


def has_header(content: str, header: str) -> bool:
    """
    Check if content already has the header.
    
    This performs an exact match check. The header must appear at the start
    of the file (after any shebang line).
    
    Args:
        content: File content to check
        header: Header text to look for
        
    Returns:
        True if content has the header, False otherwise
    """
    # Normalize header for comparison (convert to LF-only)
    normalized_header = normalize_header(header)
    
    # Extract shebang if present
    shebang, remaining = extract_shebang(content)
    
    # Normalize content to LF-only for comparison
    # This allows matching headers regardless of CRLF vs LF style
    normalized_remaining = remaining.replace('\r\n', '\n')
    
    # Check if remaining content starts with the header
    if normalized_remaining.startswith(normalized_header):
        return True
    
    # Also check with various whitespace variations around the header
    # to handle cases where there might be extra blank lines
    lines = normalized_remaining.split('\n')
    
    # Skip leading empty lines
    start_idx = 0
    while start_idx < len(lines) and lines[start_idx].strip() == '':
        start_idx += 1
    
    # Reconstruct content without leading whitespace
    if start_idx < len(lines):
        content_without_leading_ws = '\n'.join(lines[start_idx:])
        # Use exact match with the full normalized header (including trailing newline)
        if content_without_leading_ws.startswith(normalized_header):
            return True
    
    return False


def insert_header(content: str, header: str) -> str:
    """
    Insert header into file content.
    
    Preserves shebang lines if present. Inserts header immediately after
    shebang, or at the start of the file if no shebang.
    Preserves the newline style of the original content.
    
    Args:
        content: Original file content
        header: Header text to insert
        
    Returns:
        New file content with header inserted
    """
    # Detect the newline style of the content
    newline_style = detect_newline_style(content)
    
    # Normalize header to LF first, then convert to match content's newline style
    normalized_header = normalize_header(header)
    normalized_header = convert_newlines(normalized_header, newline_style)
    
    # Extract shebang if present
    shebang, remaining = extract_shebang(content)
    
    # Build new content
    if shebang:
        # Insert header after shebang
        # Ensure shebang ends with newline before adding header
        if not shebang.endswith('\n') and not shebang.endswith('\r\n'):
            shebang = shebang + newline_style
        new_content = shebang + normalized_header + remaining
    else:
        # Insert header at start
        new_content = normalized_header + remaining
    
    return new_content


def apply_header_to_file(
    file_path: Path,
    header: str,
    dry_run: bool = False,
    output_dir: Optional[Path] = None,
    scan_root: Optional[Path] = None
) -> bool:
    """
    Apply header to a single file.
    
    Writes changes atomically using a temporary file and rename.
    
    Args:
        file_path: Path to file to modify
        header: Header text to insert
        dry_run: If True, don't actually modify files
        output_dir: If provided, write to this directory instead of in-place
        scan_root: Root path used for scanning (needed to preserve relative paths in output_dir)
        
    Returns:
        True if file was modified, False if already compliant or skipped
        
    Raises:
        OSError: If file cannot be read or written
        PermissionError: If file cannot be accessed
    """
    try:
        # Read file with encoding detection
        content, bom, encoding = read_file_with_encoding(file_path)
        
        # Check if header already present
        if has_header(content, header):
            logger.debug(f"File already has header: {file_path}")
            return False
        
        # Insert header
        new_content = insert_header(content, header)
        
        if dry_run:
            logger.info(f"[DRY RUN] Would add header to: {file_path}")
            return True
        
        # Determine output path
        if output_dir:
            # Write to output directory, preserving relative directory structure
            if scan_root:
                try:
                    # Preserve relative path from scan root
                    rel_path = file_path.resolve().relative_to(scan_root.resolve())
                    output_path = output_dir / rel_path
                except ValueError:
                    # File is not relative to scan root, use basename as fallback
                    output_path = output_dir / file_path.name
            else:
                # No scan root provided, use basename
                output_path = output_dir / file_path.name
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_path = file_path
        
        # Write atomically using temporary file
        # Create temp file in same directory as target to ensure same filesystem
        temp_fd, temp_path = tempfile.mkstemp(
            dir=output_path.parent,
            prefix=f'.{output_path.name}.',
            suffix='.tmp'
        )
        
        try:
            # Close the fd, we'll use our own write function
            os.close(temp_fd)
            
            # Write new content to temp file
            write_file_with_encoding(Path(temp_path), new_content, bom, encoding)
            
            # Preserve file permissions if modifying in-place
            if not output_dir:
                try:
                    stat_info = os.stat(file_path)
                    os.chmod(temp_path, stat_info.st_mode)
                except (OSError, AttributeError):
                    # If we can't preserve permissions, continue anyway
                    pass
            
            # Atomic rename
            os.replace(temp_path, output_path)
            
            logger.info(f"Added header to: {file_path}")
            return True
            
        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    
    except PermissionError as e:
        logger.error(f"Permission denied accessing {file_path}: {e}")
        raise
    except (OSError, IOError) as e:
        logger.error(f"Error processing {file_path}: {e}")
        raise


def apply_headers(config: Config) -> ApplyResult:
    """
    Apply headers to all eligible files in the repository.
    
    Args:
        config: Configuration object with header and scanning settings
        
    Returns:
        ApplyResult with statistics about modified files
    """
    result = ApplyResult()
    
    # Get header content
    header = get_header_content(config)
    
    # Determine paths
    repo_root = config._repo_root
    scan_path = Path(config.path)
    if not scan_path.is_absolute():
        scan_path = repo_root / scan_path
    
    # Scan repository for eligible files
    logger.info(f"Scanning {scan_path} for eligible files...")
    scan_result = scan_repository(
        root_path=scan_path,
        include_extensions=config.include_extensions,
        exclude_patterns=config.exclude_paths,
        repo_root=repo_root,
    )
    
    logger.info(f"Found {len(scan_result.eligible_files)} eligible files")
    
    # Apply header to each eligible file (always in-place, never copying to output dir)
    for file_path in scan_result.eligible_files:
        try:
            was_modified = apply_header_to_file(
                file_path=file_path,
                header=header,
                dry_run=config.dry_run,
                output_dir=None,  # Always modify in-place
                scan_root=scan_path
            )
            
            if was_modified:
                result.modified_files.append(file_path)
            else:
                result.already_compliant.append(file_path)
                
        except (PermissionError, OSError, IOError, UnicodeDecodeError) as e:
            logger.error(f"Failed to process {file_path}: {e}")
            result.failed_files.append(file_path)
    
    # Track skipped files from scan
    result.skipped_files.extend(scan_result.skipped_binary)
    result.skipped_files.extend(scan_result.skipped_excluded)
    result.skipped_files.extend(scan_result.skipped_symlink)
    result.skipped_files.extend(scan_result.skipped_permission)
    result.skipped_files.extend(scan_result.skipped_extension)
    
    return result

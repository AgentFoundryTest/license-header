"""
Scanner module for license-header tool.

Provides deterministic repository traversal to identify eligible source files
based on configured extensions, excludes, and binary detection.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Default directories to exclude from scanning
# These match the defaults in config.py
DEFAULT_EXCLUDE_DIRS = [
    '.git',
    '.venv',
    'venv',
    'env',
    '__pycache__',
    'node_modules',
    'dist',
    'build',
]


@dataclass
class ScanResult:
    """Result of a repository scan."""
    
    eligible_files: List[Path] = field(default_factory=list)
    skipped_binary: List[Path] = field(default_factory=list)
    skipped_excluded: List[Path] = field(default_factory=list)
    skipped_symlink: List[Path] = field(default_factory=list)
    skipped_permission: List[Path] = field(default_factory=list)
    skipped_extension: List[Path] = field(default_factory=list)
    
    def total_files(self) -> int:
        """Return total number of files scanned."""
        return (
            len(self.eligible_files)
            + len(self.skipped_binary)
            + len(self.skipped_excluded)
            + len(self.skipped_symlink)
            + len(self.skipped_permission)
            + len(self.skipped_extension)
        )


def is_binary_file(file_path: Path) -> bool:
    """
    Detect if a file is binary by checking for null bytes in the first chunk.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file appears to be binary, False otherwise
    """
    try:
        # Read first 8KB to check for binary content
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
            # Check for null bytes which indicate binary content
            return b'\x00' in chunk
    except (OSError, IOError) as e:
        logger.warning(f"Could not read file for binary detection {file_path}: {e}")
        # If we can't read it, treat it as binary to be safe
        return True


# Recursive wildcard prefix used in glob patterns
_RECURSIVE_PREFIX = '**/'


def _try_directory_patterns(rel_path: Path, pattern: str) -> bool:
    """
    Try matching a pattern as a directory by adding directory wildcards.
    
    Args:
        rel_path: Path relative to repository root
        pattern: Pattern to try
        
    Returns:
        True if any directory variant matches, False otherwise
    """
    # Try both recursive and single-level directory patterns
    for suffix in ('/**', '/*'):
        if rel_path.match(pattern + suffix):
            return True
    return False


def _matches_glob_pattern(rel_path: Path, pattern: str) -> bool:
    """
    Check if a relative path matches a glob pattern.
    
    Handles both explicit glob patterns and directory-based patterns by trying
    multiple variations.
    
    Args:
        rel_path: Path relative to repository root
        pattern: Glob pattern to match against
        
    Returns:
        True if the path matches the pattern, False otherwise
    """
    # Direct match
    if rel_path.match(pattern):
        return True
    
    # For patterns that don't end with wildcards, also try matching as directory patterns
    # This allows patterns like 'vendor' or '**/vendor' to match 'vendor/file.js'
    if not pattern.endswith('*'):
        # Try the pattern as a directory
        if _try_directory_patterns(rel_path, pattern):
            return True
        
        # For patterns starting with **, also try without the ** prefix
        # This handles cases like '**/vendor' matching 'vendor/file.js' at root
        if pattern.startswith(_RECURSIVE_PREFIX):
            stripped_pattern = pattern[len(_RECURSIVE_PREFIX):]
            if _try_directory_patterns(rel_path, stripped_pattern):
                return True
    
    return False


def matches_exclude_pattern(path: Path, repo_root: Path, exclude_patterns: List[str]) -> bool:
    """
    Check if a path matches any exclude pattern.
    
    Patterns can be:
    - Simple directory names (e.g., 'node_modules') - matches if directory appears anywhere in path
    - Glob patterns (e.g., '*.pyc', 'generated/*.py', '**/vendor') - uses glob semantics
    
    Both glob and simple directory matching are attempted for each pattern. A path is excluded
    if it matches either check, so patterns like 'vendor' will match both as a glob and as a
    simple directory name.
    
    Args:
        path: Path to check (can be relative or absolute)
        repo_root: Repository root path (can be relative or absolute)
        exclude_patterns: List of exclude patterns/globs
        
    Returns:
        True if path matches any exclude pattern, False otherwise
    """
    try:
        # Resolve both paths to absolute to ensure relative_to works correctly
        abs_path = path.resolve()
        abs_repo_root = repo_root.resolve()
        
        # Get path relative to repo root for matching
        rel_path = abs_path.relative_to(abs_repo_root)
        
        # Check each pattern
        for pattern in exclude_patterns:
            # Try glob pattern matching
            if _matches_glob_pattern(rel_path, pattern):
                return True
            
            # Also check if pattern is a simple directory name that appears in the path
            # This ensures backward compatibility with simple patterns like 'node_modules'
            # which should match any occurrence of that directory in the path
            if pattern in rel_path.parts:
                return True
                
    except ValueError:
        # Path is not relative to repo_root, exclude it
        logger.warning(f"Path {path} is not within repo root {repo_root}")
        return True
    
    return False


def scan_repository(
    root_path: Path,
    include_extensions: List[str],
    exclude_patterns: List[str],
    repo_root: Path,
) -> ScanResult:
    """
    Scan repository directory tree for eligible source files.
    
    Performs an iterative (non-recursive) walk of the directory tree,
    applying filters for extensions, exclude patterns, binary detection,
    and symlink handling.
    
    Args:
        root_path: Root path to start scanning from
        include_extensions: List of file extensions to include (e.g., ['.py', '.js'])
        exclude_patterns: List of path patterns to exclude (in addition to defaults)
        repo_root: Repository root path
        
    Returns:
        ScanResult object with categorized files
        
    Note:
        - Results are deterministically sorted
        - Symlinks are not followed
        - Binary files are detected and skipped
        - Permission errors are logged but don't abort the scan
    """
    result = ScanResult()
    
    # Combine default excludes with user patterns
    all_exclude_patterns = DEFAULT_EXCLUDE_DIRS + exclude_patterns
    
    logger.info(f"Scanning repository at {root_path}")
    logger.info(f"Include extensions: {include_extensions}")
    logger.info(f"Exclude patterns: {all_exclude_patterns}")
    
    # Use os.walk for iterative directory traversal
    # This handles deep directory trees without recursion limits
    try:
        for dirpath_str, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=False):
            dirpath = Path(dirpath_str)
            
            # Skip if this directory matches exclude patterns
            if matches_exclude_pattern(dirpath, repo_root, all_exclude_patterns):
                logger.debug(f"Skipping excluded directory: {dirpath}")
                # Clear dirnames to prevent os.walk from descending
                dirnames.clear()
                continue
            
            # Filter out excluded subdirectories from dirnames
            # Modifying dirnames in-place affects which directories os.walk descends into
            dirs_to_remove = []
            for dirname in dirnames:
                subdir = dirpath / dirname
                
                # Check if it's a symlink
                if subdir.is_symlink():
                    logger.debug(f"Skipping symlink directory: {subdir}")
                    dirs_to_remove.append(dirname)
                    continue
                
                # Check if it matches exclude patterns
                if matches_exclude_pattern(subdir, repo_root, all_exclude_patterns):
                    logger.debug(f"Skipping excluded directory: {subdir}")
                    dirs_to_remove.append(dirname)
                    continue
            
            # Remove excluded directories
            for dirname in dirs_to_remove:
                dirnames.remove(dirname)
            
            # Sort dirnames for deterministic traversal order
            dirnames.sort()
            
            # Process files in this directory
            for filename in sorted(filenames):  # Sort for deterministic order
                filepath = dirpath / filename
                
                try:
                    # Skip symlinks
                    if filepath.is_symlink():
                        logger.debug(f"Skipping symlink file: {filepath}")
                        result.skipped_symlink.append(filepath)
                        continue
                    
                    # Check if it's a regular file
                    if not filepath.is_file():
                        logger.debug(f"Skipping non-file: {filepath}")
                        continue
                    
                    # Check if file matches exclude patterns
                    if matches_exclude_pattern(filepath, repo_root, all_exclude_patterns):
                        logger.debug(f"Skipping excluded file: {filepath}")
                        result.skipped_excluded.append(filepath)
                        continue
                    
                    # Check file extension
                    file_ext = filepath.suffix.lower()  # Case-insensitive comparison
                    
                    # Normalize extensions in include_extensions for case-insensitive comparison
                    normalized_extensions = [ext.lower() for ext in include_extensions]
                    
                    if file_ext not in normalized_extensions:
                        logger.debug(f"Skipping file with non-matching extension: {filepath}")
                        result.skipped_extension.append(filepath)
                        continue
                    
                    # Check if file is binary
                    if is_binary_file(filepath):
                        logger.debug(f"Skipping binary file: {filepath}")
                        result.skipped_binary.append(filepath)
                        continue
                    
                    # File passed all filters - it's eligible
                    logger.debug(f"Eligible file: {filepath}")
                    result.eligible_files.append(filepath)
                    
                except PermissionError as e:
                    logger.warning(f"Permission denied reading {filepath}: {e}")
                    result.skipped_permission.append(filepath)
                except (OSError, IOError) as e:
                    logger.warning(f"Error accessing {filepath}: {e}")
                    result.skipped_permission.append(filepath)
    
    except PermissionError as e:
        logger.error(f"Permission denied accessing directory {root_path}: {e}")
    except Exception as e:
        logger.error(f"Error scanning directory {root_path}: {e}", exc_info=True)
    
    # Sort all results for deterministic output
    result.eligible_files.sort()
    result.skipped_binary.sort()
    result.skipped_excluded.sort()
    result.skipped_symlink.sort()
    result.skipped_permission.sort()
    result.skipped_extension.sort()
    
    logger.info(f"Scan complete: {len(result.eligible_files)} eligible files, "
                f"{len(result.skipped_binary)} binary, "
                f"{len(result.skipped_excluded)} excluded, "
                f"{len(result.skipped_symlink)} symlinks, "
                f"{len(result.skipped_permission)} permission errors, "
                f"{len(result.skipped_extension)} wrong extension")
    
    return result

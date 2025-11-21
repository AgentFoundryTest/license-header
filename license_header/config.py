"""
Configuration module for license-header tool.

Handles loading and merging configuration from CLI arguments and config files.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import click

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration schema for license-header tool."""
    
    # Required configuration
    header_file: str
    
    # Optional configuration with defaults
    include_extensions: List[str] = field(default_factory=lambda: ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h'])
    exclude_paths: List[str] = field(default_factory=lambda: ['node_modules', '.git', '__pycache__', 'venv', 'env', '.venv'])
    output_dir: Optional[str] = None
    dry_run: bool = False
    mode: str = 'apply'  # 'apply' or 'check'
    path: str = '.'
    strict: bool = False
    
    # Resolved paths (computed after loading)
    _header_content: Optional[str] = field(default=None, init=False, repr=False)
    _repo_root: Optional[Path] = field(default=None, init=False, repr=False)


def find_repo_root(start_path: Path) -> Path:
    """
    Find the repository root by looking for .git directory.
    
    Args:
        start_path: Starting path to search from
        
    Returns:
        Path to repository root
        
    Raises:
        ValueError: If no repository root is found
    """
    current = start_path.resolve()
    
    # Check if we're already in a git repo
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent
    
    # If no .git found, use the current working directory
    return start_path.resolve()


def load_config_file(config_path: Path) -> dict:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing configuration values
        
    Raises:
        click.ClickException: If the file cannot be read or parsed
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config_data
    except FileNotFoundError:
        raise click.ClickException(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in configuration file {config_path}: {e}")
    except Exception as e:
        raise click.ClickException(f"Error reading configuration file {config_path}: {e}")


def validate_path_in_repo(path: Path, repo_root: Path, path_description: str) -> None:
    """
    Validate that a path does not traverse above the repository root.
    
    Args:
        path: Path to validate
        repo_root: Repository root path
        path_description: Description of the path for error messages
        
    Raises:
        click.ClickException: If path traverses above repo root
    """
    try:
        resolved_path = path.resolve()
        # Check if the resolved path is within the repo root
        resolved_path.relative_to(repo_root)
    except (ValueError, RuntimeError):
        raise click.ClickException(
            f"{path_description} '{path}' traverses above repository root '{repo_root}'. "
            "This is not allowed for security reasons."
        )


def load_header_content(header_file: str, repo_root: Path) -> str:
    """
    Load and validate the header file content.
    
    Args:
        header_file: Path to the header file (relative to repo root or absolute)
        repo_root: Repository root path
        
    Returns:
        Content of the header file
        
    Raises:
        click.ClickException: If header file is invalid or cannot be read
    """
    # Convert to Path and make absolute if relative
    header_path = Path(header_file)
    if not header_path.is_absolute():
        header_path = repo_root / header_path
    
    # Validate path is within repo
    validate_path_in_repo(header_path, repo_root, "Header file path")
    
    # Check file exists
    if not header_path.exists():
        raise click.ClickException(
            f"Header file not found: {header_file}\n"
            f"Resolved to: {header_path}\n"
            f"Please ensure the header file exists and the path is correct."
        )
    
    if not header_path.is_file():
        raise click.ClickException(f"Header path is not a file: {header_path}")
    
    # Read header content
    try:
        with open(header_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Loaded header content from {header_path}")
        return content
    except Exception as e:
        raise click.ClickException(f"Error reading header file {header_path}: {e}")


def validate_extensions(extensions: List[str]) -> None:
    """
    Validate file extensions format.
    
    Args:
        extensions: List of file extensions
        
    Note:
        Logs warnings for unusual extensions but does not fail
    """
    for ext in extensions:
        if not ext.startswith('.'):
            logger.warning(f"Extension '{ext}' does not start with '.'. This may not match files as expected.")


def validate_exclude_patterns(patterns: List[str]) -> None:
    """
    Validate exclude patterns.
    
    Args:
        patterns: List of exclude patterns/globs
        
    Note:
        Logs warnings for unusual patterns but does not fail
    """
    for pattern in patterns:
        if pattern.startswith('/') or pattern.startswith('\\'):
            logger.warning(
                f"Exclude pattern '{pattern}' starts with path separator. "
                "Patterns are matched against relative paths."
            )


def merge_config(
    cli_args: dict,
    config_file_path: Optional[str] = None,
    repo_root: Optional[Path] = None
) -> Config:
    """
    Merge CLI arguments with config file settings.
    
    CLI arguments take precedence over config file settings.
    
    Args:
        cli_args: Dictionary of CLI arguments
        config_file_path: Optional path to config file
        repo_root: Repository root path
        
    Returns:
        Merged Config object
        
    Raises:
        click.ClickException: If configuration is invalid
    """
    # Determine repo root
    if repo_root is None:
        repo_root = find_repo_root(Path.cwd())
    
    # Start with defaults from Config dataclass
    config_data = {
        'include_extensions': ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h'],
        'exclude_paths': ['node_modules', '.git', '__pycache__', 'venv', 'env', '.venv'],
        'output_dir': None,
        'dry_run': False,
        'mode': 'apply',
        'path': '.',
        'strict': False,
    }
    
    # Load config file if specified or if default exists
    config_file_data = {}
    if config_file_path:
        config_path = Path(config_file_path)
        if not config_path.is_absolute():
            config_path = repo_root / config_path
        config_file_data = load_config_file(config_path)
    else:
        # Check for default config file
        default_config = repo_root / 'license-header.config.json'
        if default_config.exists():
            config_file_data = load_config_file(default_config)
            logger.info(f"Using default configuration file: {default_config}")
    
    # Merge: config file overrides defaults
    if config_file_data:
        # Map config file keys to internal keys
        for key in ['include_extensions', 'exclude_paths', 'output_dir', 'header_file']:
            if key in config_file_data and config_file_data[key] is not None:
                config_data[key] = config_file_data[key]
    
    # Merge: CLI args override everything
    for key, value in cli_args.items():
        if value is not None:
            # Handle special CLI argument names
            if key == 'include_extension':
                # CLI can pass multiple --include-extension flags
                if value:
                    config_data['include_extensions'] = value
            elif key == 'exclude_path':
                # CLI can pass multiple --exclude-path flags
                if value:
                    config_data['exclude_paths'] = value
            elif key == 'header':
                config_data['header_file'] = value
            else:
                config_data[key] = value
    
    # Validate required fields
    if 'header_file' not in config_data:
        raise click.ClickException(
            "Header file is required. Specify it via:\n"
            "  - CLI flag: --header <path>\n"
            "  - Config file: 'header_file' key\n"
            "  - Default: 'LICENSE_HEADER' file in repository root"
        )
    
    # Validate and warn about extensions and patterns
    validate_extensions(config_data['include_extensions'])
    validate_exclude_patterns(config_data['exclude_paths'])
    
    # Create Config object
    config = Config(
        header_file=config_data['header_file'],
        include_extensions=config_data['include_extensions'],
        exclude_paths=config_data['exclude_paths'],
        output_dir=config_data.get('output_dir'),
        dry_run=config_data.get('dry_run', False),
        mode=config_data.get('mode', 'apply'),
        path=config_data.get('path', '.'),
        strict=config_data.get('strict', False),
    )
    
    # Store repo root
    config._repo_root = repo_root
    
    # Load and validate header content
    config._header_content = load_header_content(config.header_file, repo_root)
    
    # Validate output directory if specified
    if config.output_dir:
        output_path = Path(config.output_dir)
        if not output_path.is_absolute():
            output_path = repo_root / output_path
        validate_path_in_repo(output_path, repo_root, "Output directory")
    
    logger.info(f"Configuration loaded successfully: {config}")
    return config


def get_header_content(config: Config) -> str:
    """
    Get the header content from the configuration.
    
    Header content is loaded exactly once and cached.
    
    Args:
        config: Configuration object
        
    Returns:
        Header content string
    """
    if config._header_content is None:
        raise RuntimeError("Header content not loaded. This is a bug.")
    return config._header_content

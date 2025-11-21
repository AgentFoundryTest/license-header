"""
Reports module for license-header tool.

Provides JSON and Markdown report generation for apply and check operations.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Union, Optional

from .apply import ApplyResult
from .check import CheckResult

logger = logging.getLogger(__name__)


def _format_file_list(files: List[Path], repo_root: Optional[Path] = None, limit: Optional[int] = None) -> List[str]:
    """
    Format list of file paths as relative strings.
    
    Args:
        files: List of file paths
        repo_root: Repository root for relative path calculation
        limit: Optional limit on number of files to include
        
    Returns:
        List of formatted file path strings
    """
    formatted = []
    files_to_format = files[:limit] if limit else files
    
    for file_path in files_to_format:
        if repo_root:
            try:
                rel_path = file_path.relative_to(repo_root)
                formatted.append(str(rel_path))
            except ValueError:
                # File is not relative to repo root
                formatted.append(str(file_path))
        else:
            formatted.append(str(file_path))
    
    return formatted


def generate_json_report(
    result: Union[ApplyResult, CheckResult],
    output_path: Path,
    mode: str,
    repo_root: Optional[Path] = None
) -> None:
    """
    Generate JSON report for apply or check operation.
    
    Args:
        result: ApplyResult or CheckResult object
        output_path: Path to write JSON report
        mode: Operation mode ('apply' or 'check')
        repo_root: Repository root for relative path calculation
        
    Raises:
        OSError: If report cannot be written
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    if mode == 'apply':
        report_data = {
            'timestamp': timestamp,
            'mode': 'apply',
            'summary': {
                'scanned': result.total_processed(),
                'eligible': len(result.modified_files) + len(result.already_compliant) + len(result.failed_files),
                'modified': len(result.modified_files),
                'compliant': len(result.already_compliant),
                'skipped': len(result.skipped_files),
                'failed': len(result.failed_files),
            },
            'files': {
                'modified': _format_file_list(result.modified_files, repo_root),
                'compliant': _format_file_list(result.already_compliant, repo_root),
                'skipped': _format_file_list(result.skipped_files, repo_root),
                'failed': _format_file_list(result.failed_files, repo_root),
            }
        }
    else:  # mode == 'check'
        report_data = {
            'timestamp': timestamp,
            'mode': 'check',
            'summary': {
                'scanned': result.total_scanned(),
                'eligible': result.total_eligible(),
                'compliant': len(result.compliant_files),
                'non_compliant': len(result.non_compliant_files),
                'skipped': len(result.skipped_files),
                'failed': len(result.failed_files),
            },
            'files': {
                'compliant': _format_file_list(result.compliant_files, repo_root),
                'non_compliant': _format_file_list(result.non_compliant_files, repo_root),
                'skipped': _format_file_list(result.skipped_files, repo_root),
                'failed': _format_file_list(result.failed_files, repo_root),
            }
        }
    
    try:
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSON report
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON report written to {output_path}")
    
    except (OSError, IOError) as e:
        logger.error(f"Failed to write JSON report to {output_path}: {e}")
        raise


def generate_markdown_report(
    result: Union[ApplyResult, CheckResult],
    output_path: Path,
    mode: str,
    repo_root: Optional[Path] = None
) -> None:
    """
    Generate Markdown report for apply or check operation.
    
    Args:
        result: ApplyResult or CheckResult object
        output_path: Path to write Markdown report
        mode: Operation mode ('apply' or 'check')
        repo_root: Repository root for relative path calculation
        
    Raises:
        OSError: If report cannot be written
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    lines = []
    lines.append(f"# License Header {mode.capitalize()} Report")
    lines.append("")
    lines.append(f"**Generated:** {timestamp}")
    lines.append("")
    
    if mode == 'apply':
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Scanned:** {result.total_processed()}")
        lines.append(f"- **Eligible:** {len(result.modified_files) + len(result.already_compliant) + len(result.failed_files)}")
        lines.append(f"- **Modified:** {len(result.modified_files)}")
        lines.append(f"- **Already Compliant:** {len(result.already_compliant)}")
        lines.append(f"- **Skipped:** {len(result.skipped_files)}")
        lines.append(f"- **Failed:** {len(result.failed_files)}")
        lines.append("")
        
        if result.modified_files:
            lines.append("## Modified Files")
            lines.append("")
            for file_str in _format_file_list(result.modified_files, repo_root):
                lines.append(f"- `{file_str}`")
            lines.append("")
        
        if result.already_compliant:
            lines.append("## Already Compliant Files")
            lines.append("")
            # Limit to first 100 for readability
            file_list = _format_file_list(result.already_compliant, repo_root, limit=100)
            for file_str in file_list:
                lines.append(f"- `{file_str}`")
            if len(result.already_compliant) > 100:
                lines.append(f"- ... and {len(result.already_compliant) - 100} more")
            lines.append("")
        
        if result.failed_files:
            lines.append("## Failed Files")
            lines.append("")
            for file_str in _format_file_list(result.failed_files, repo_root):
                lines.append(f"- `{file_str}`")
            lines.append("")
    
    else:  # mode == 'check'
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Scanned:** {result.total_scanned()}")
        lines.append(f"- **Eligible:** {result.total_eligible()}")
        lines.append(f"- **Compliant:** {len(result.compliant_files)}")
        lines.append(f"- **Non-Compliant:** {len(result.non_compliant_files)}")
        lines.append(f"- **Skipped:** {len(result.skipped_files)}")
        lines.append(f"- **Failed:** {len(result.failed_files)}")
        lines.append("")
        
        if result.non_compliant_files:
            lines.append("## Non-Compliant Files")
            lines.append("")
            for file_str in _format_file_list(result.non_compliant_files, repo_root):
                lines.append(f"- `{file_str}`")
            lines.append("")
        
        if result.compliant_files:
            lines.append("## Compliant Files")
            lines.append("")
            # Limit to first 100 for readability
            file_list = _format_file_list(result.compliant_files, repo_root, limit=100)
            for file_str in file_list:
                lines.append(f"- `{file_str}`")
            if len(result.compliant_files) > 100:
                lines.append(f"- ... and {len(result.compliant_files) - 100} more")
            lines.append("")
        
        if result.failed_files:
            lines.append("## Failed Files")
            lines.append("")
            for file_str in _format_file_list(result.failed_files, repo_root):
                lines.append(f"- `{file_str}`")
            lines.append("")
    
    content = "\n".join(lines)
    
    try:
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write Markdown report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Markdown report written to {output_path}")
    
    except (OSError, IOError) as e:
        logger.error(f"Failed to write Markdown report to {output_path}: {e}")
        raise


def generate_reports(
    result: Union[ApplyResult, CheckResult],
    output_dir: Path,
    mode: str,
    repo_root: Optional[Path] = None
) -> None:
    """
    Generate both JSON and Markdown reports in the output directory.
    
    Args:
        result: ApplyResult or CheckResult object
        output_dir: Directory to write reports
        mode: Operation mode ('apply' or 'check')
        repo_root: Repository root for relative path calculation
        
    Raises:
        OSError: If output directory cannot be created or reports cannot be written
    """
    # Validate output directory
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")
        except (OSError, IOError) as e:
            logger.error(f"Failed to create output directory {output_dir}: {e}")
            raise OSError(f"Cannot create output directory {output_dir}: {e}")
    
    if not output_dir.is_dir():
        raise OSError(f"Output path is not a directory: {output_dir}")
    
    # Check if directory is writable
    if not os.access(output_dir, os.W_OK):
        raise OSError(f"Output directory is not writable: {output_dir}")
    
    # Generate reports
    json_path = output_dir / f"license-header-{mode}-report.json"
    markdown_path = output_dir / f"license-header-{mode}-report.md"
    
    generate_json_report(result, json_path, mode, repo_root)
    generate_markdown_report(result, markdown_path, mode, repo_root)
    
    logger.info(f"Reports generated in {output_dir}")

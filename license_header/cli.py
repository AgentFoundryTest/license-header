"""
CLI module for license-header tool.
"""

import logging
import sys
import click

from .config import merge_config, get_header_content
from .apply import apply_headers
from .check import check_headers
from .reports import generate_reports


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def check_python_version():
    """Check if Python version meets minimum requirement."""
    if sys.version_info < (3, 11):
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        logger.error(f"Python 3.11 or higher is required. Current version: {current_version}")
        click.echo(
            f"Error: Python 3.11 or higher is required.\n"
            f"Current version: {current_version}\n"
            f"Please upgrade your Python installation.",
            err=True
        )
        sys.exit(1)


@click.group()
@click.version_option(message='%(version)s')
def main():
    """
    License Header CLI - Deterministic license header enforcement.
    
    Use 'license-header <command> --help' for more information on a specific command.
    """
    check_python_version()


@main.command()
@click.option('--config', type=str, help='Path to configuration file (default: license-header.config.json if present)')
@click.option('--header', type=str, help='Path to license header file')
@click.option('--path', default='.', help='Path to apply license headers (default: current directory)')
@click.option('--output', type=str, help='Output directory for modified files (default: modify in place)')
@click.option('--include-extension', multiple=True, help='File extensions to include (e.g., .py, .js). Can be specified multiple times.')
@click.option('--exclude-path', multiple=True, help='Paths/patterns to exclude (e.g., node_modules). Can be specified multiple times.')
@click.option('--dry-run', is_flag=True, help='Preview changes without modifying files')
def apply(config, header, path, output, include_extension, exclude_path, dry_run):
    """Apply license headers to source files."""
    logger.info(f"Apply command called with path='{path}', dry_run={dry_run}")
    
    try:
        # Build CLI args dictionary
        cli_args = {
            'header': header,
            'path': path,
            'output_dir': output,
            'include_extension': list(include_extension) if include_extension else None,
            'exclude_path': list(exclude_path) if exclude_path else None,
            'dry_run': dry_run,
            'mode': 'apply',
        }
        
        # Merge configuration
        cfg = merge_config(cli_args, config_file_path=config)
        
        # Get header content to verify it's loaded
        header_content = get_header_content(cfg)
        
        # Display configuration
        click.echo(f"Configuration loaded successfully:")
        click.echo(f"  Header file: {cfg.header_file}")
        click.echo(f"  Target path: {cfg.path}")
        click.echo(f"  Include extensions: {', '.join(cfg.include_extensions)}")
        click.echo(f"  Exclude paths: {', '.join(cfg.exclude_paths)}")
        if cfg.output_dir:
            click.echo(f"  Output directory: {cfg.output_dir}")
        click.echo(f"  Dry run: {cfg.dry_run}")
        click.echo(f"  Header content loaded: {len(header_content)} characters")
        click.echo()
        
        # Apply headers
        logger.info("Applying license headers...")
        result = apply_headers(cfg)
        
        # Display summary
        click.echo(f"Summary:")
        click.echo(f"  Scanned: {result.total_processed()}")
        click.echo(f"  Eligible: {len(result.modified_files) + len(result.already_compliant)}")
        click.echo(f"  Added: {len(result.modified_files)}")
        click.echo(f"  Compliant: {len(result.already_compliant)}")
        click.echo(f"  Skipped-binary: {len(result.skipped_files)}")
        click.echo(f"  Failed: {len(result.failed_files)}")
        click.echo()
        
        if dry_run:
            click.echo("[DRY RUN] Files that would be modified:")
            for file_path in result.modified_files:
                click.echo(f"  - {file_path}")
            click.echo()
            click.echo("[DRY RUN] No files were actually modified.")
        elif result.modified_files:
            click.echo(f"Modified {len(result.modified_files)} file(s):")
            for file_path in result.modified_files[:10]:  # Show first 10
                click.echo(f"  - {file_path}")
            if len(result.modified_files) > 10:
                click.echo(f"  ... and {len(result.modified_files) - 10} more")
        
        if result.failed_files:
            click.echo(f"\nFailed to process {len(result.failed_files)} file(s):")
            for file_path in result.failed_files:
                click.echo(f"  - {file_path}")
        
        # Generate reports if output directory specified
        if cfg.output_dir and not dry_run:
            try:
                from pathlib import Path
                output_path = Path(cfg.output_dir)
                if not output_path.is_absolute():
                    output_path = cfg._repo_root / output_path
                
                click.echo(f"\nGenerating reports in {output_path}...")
                generate_reports(result, output_path, 'apply', cfg._repo_root)
                click.echo(f"Reports written to {output_path}")
            except Exception as e:
                logger.error(f"Failed to generate reports: {e}")
                raise click.ClickException(f"Failed to generate reports: {e}")
        
        logger.info("Apply command completed successfully")
        
    except click.ClickException:
        raise
    except Exception as e:
        logger.error(f"Error in apply command: {e}", exc_info=True)
        raise click.ClickException(f"Failed to apply license headers: {e}")


@main.command()
@click.option('--config', type=str, help='Path to configuration file (default: license-header.config.json if present)')
@click.option('--header', type=str, help='Path to license header file')
@click.option('--path', default='.', help='Path to check for license headers (default: current directory)')
@click.option('--output', type=str, help='Output directory for report files (default: none)')
@click.option('--include-extension', multiple=True, help='File extensions to include (e.g., .py, .js). Can be specified multiple times.')
@click.option('--exclude-path', multiple=True, help='Paths/patterns to exclude (e.g., node_modules). Can be specified multiple times.')
@click.option('--dry-run', is_flag=True, help='Preview results without generating reports')
def check(config, header, path, output, include_extension, exclude_path, dry_run):
    """Check source files for correct license headers."""
    logger.info(f"Check command called with path='{path}', dry_run={dry_run}")
    
    try:
        # Build CLI args dictionary
        cli_args = {
            'header': header,
            'path': path,
            'output_dir': output,
            'include_extension': list(include_extension) if include_extension else None,
            'exclude_path': list(exclude_path) if exclude_path else None,
            'dry_run': dry_run,
            'mode': 'check',
        }
        
        # Merge configuration
        cfg = merge_config(cli_args, config_file_path=config)
        
        # Get header content to verify it's loaded
        header_content = get_header_content(cfg)
        
        # Display configuration
        click.echo(f"Configuration loaded successfully:")
        click.echo(f"  Header file: {cfg.header_file}")
        click.echo(f"  Target path: {cfg.path}")
        click.echo(f"  Include extensions: {', '.join(cfg.include_extensions)}")
        click.echo(f"  Exclude paths: {', '.join(cfg.exclude_paths)}")
        if cfg.output_dir:
            click.echo(f"  Output directory: {cfg.output_dir}")
        click.echo(f"  Dry run: {cfg.dry_run}")
        click.echo(f"  Header content loaded: {len(header_content)} characters")
        click.echo()
        
        # Check headers
        logger.info("Checking license headers...")
        result = check_headers(cfg)
        
        # Display summary
        click.echo(f"Summary:")
        click.echo(f"  Scanned: {result.total_scanned()}")
        click.echo(f"  Eligible: {result.total_eligible()}")
        click.echo(f"  Compliant: {len(result.compliant_files)}")
        click.echo(f"  Non-compliant: {len(result.non_compliant_files)}")
        click.echo(f"  Skipped-binary: {len(result.skipped_files)}")
        click.echo(f"  Failed: {len(result.failed_files)}")
        click.echo()
        
        # Display non-compliant files
        if result.non_compliant_files:
            click.echo(f"Files missing license headers ({len(result.non_compliant_files)}):")
            for file_path in result.non_compliant_files:
                click.echo(f"  - {file_path}")
            click.echo()
        
        # Display failed files
        if result.failed_files:
            click.echo(f"Failed to check {len(result.failed_files)} file(s):")
            for file_path in result.failed_files:
                click.echo(f"  - {file_path}")
            click.echo()
        
        # Generate reports if output directory specified and not dry-run
        if cfg.output_dir and not dry_run:
            try:
                from pathlib import Path
                output_path = Path(cfg.output_dir)
                if not output_path.is_absolute():
                    output_path = cfg._repo_root / output_path
                
                click.echo(f"Generating reports in {output_path}...")
                generate_reports(result, output_path, 'check', cfg._repo_root)
                click.echo(f"Reports written to {output_path}")
                click.echo()
            except Exception as e:
                logger.error(f"Failed to generate reports: {e}")
                raise click.ClickException(f"Failed to generate reports: {e}")
        elif cfg.output_dir and dry_run:
            click.echo(f"[DRY RUN] Would generate reports in {cfg.output_dir}")
            click.echo()
        
        # Determine exit code
        # Check mode should fail by default when there are non-compliant files
        if result.non_compliant_files or result.failed_files:
            logger.error(f"Check failed: {len(result.non_compliant_files)} non-compliant, {len(result.failed_files)} failed")
            click.echo("Check FAILED: Files are missing license headers or could not be checked.", err=True)
            sys.exit(1)
        else:
            click.echo("Check PASSED: All files have correct license headers.")
        
        logger.info("Check command completed successfully")
        
    except click.ClickException:
        raise
    except Exception as e:
        logger.error(f"Error in check command: {e}", exc_info=True)
        raise click.ClickException(f"Failed to check license headers: {e}")


if __name__ == '__main__':
    main()

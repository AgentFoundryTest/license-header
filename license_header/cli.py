"""
CLI module for license-header tool.
"""

import logging
import sys
import click

from .config import merge_config, get_header_content


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
        
        if dry_run:
            click.echo(f"[DRY RUN] Would apply license headers to files in: {path}")
        else:
            click.echo(f"Would apply license headers to files in: {path}")
        
        click.echo("Note: Header application logic not yet implemented.")
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
@click.option('--strict', is_flag=True, help='Fail on any missing or incorrect headers')
def check(config, header, path, output, include_extension, exclude_path, strict):
    """Check source files for correct license headers."""
    logger.info(f"Check command called with path='{path}', strict={strict}")
    
    try:
        # Build CLI args dictionary
        cli_args = {
            'header': header,
            'path': path,
            'output_dir': output,
            'include_extension': list(include_extension) if include_extension else None,
            'exclude_path': list(exclude_path) if exclude_path else None,
            'strict': strict,
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
        click.echo(f"  Strict mode: {cfg.strict}")
        click.echo(f"  Header content loaded: {len(header_content)} characters")
        click.echo()
        
        click.echo(f"Checking license headers in: {path}")
        if strict:
            click.echo("Running in strict mode - will fail on any issues.")
        
        click.echo("Note: Header checking logic not yet implemented.")
        logger.info("Check command completed successfully")
        
    except click.ClickException:
        raise
    except Exception as e:
        logger.error(f"Error in check command: {e}", exc_info=True)
        raise click.ClickException(f"Failed to check license headers: {e}")


if __name__ == '__main__':
    main()

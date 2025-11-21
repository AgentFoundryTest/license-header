# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-21

### Added

#### Core CLI Commands
- `apply` command: Automatically add or update license headers in source files
- `check` command: Verify that all source files have correct license headers
- `--dry-run` flag for both commands to preview changes without modifying files
- `--version` flag to display current version

#### Configuration System
- JSON configuration file support (`license-header.config.json`)
- CLI options for all configuration parameters with precedence over config file
- Support for custom configuration file paths via `--config` flag
- Configuration validation and security checks for path traversal
- Default configuration with sensible exclude patterns and file extensions

#### Repository Traversal
- Deterministic file scanning with consistent ordering across platforms
- Iterative directory walking for deep directory trees (handles >1000 levels)
- Case-insensitive file extension matching
- Binary file detection and automatic skipping
- Symlink detection and circular reference prevention
- Permission error handling without aborting scans
- Default exclusion of common directories: `.git`, `node_modules`, `__pycache__`, `venv`, `dist`, `build`
- Support for custom exclude patterns (simple directory names and glob patterns)
- Configurable file extension filtering

#### Header Management
- Idempotent header detection and application
- Shebang-aware header insertion (preserves `#!/...` lines)
- Exact header matching for compliance verification
- Whitespace normalization (ensures one trailing newline)
- BOM (Byte Order Mark) preservation for UTF-8, UTF-16, UTF-32 files
- Atomic file writes using temporary files and rename operations
- File permission preservation during modifications

#### Reporting
- JSON report generation with complete file lists and statistics
- Markdown report generation with human-readable summaries
- Separate reports for `apply` and `check` modes
- Deterministic summary counters (scanned, eligible, compliant, skipped, failed)
- Optional report generation via `--output` flag
- Automatic output directory creation
- Report generation validation and error handling

#### GitHub Actions Integration
- Exit code 1 for check failures (CI/CD ready)
- Exit code 0 for successful checks
- Examples for basic check workflow, check with reports, and auto-fix workflow
- Designed for use in CI/CD pipelines

### Features by Category

**Configuration Options:**
- `--header`: Path to license header file (default: `LICENSE_HEADER`)
- `--path`: Target directory to scan (default: current directory)
- `--output`: Output directory for JSON and Markdown reports
- `--include-extension`: File extensions to process (can be specified multiple times)
- `--exclude-path`: Paths/patterns to exclude (can be specified multiple times)
- `--dry-run`: Preview mode without file modifications
- `--config`: Custom configuration file path

**Traversal Capabilities:**
- Deterministic ordering for reproducible results
- Deep directory tree support without recursion limits
- Binary file automatic detection
- Symlink and circular reference handling
- Permission error graceful handling
- Case-insensitive extension matching
- Glob pattern support for exclusions

**Apply Mode:**
- In-place file modification
- Dry-run preview mode
- Summary statistics (scanned, eligible, added, compliant, skipped, failed)
- Optional JSON and Markdown report generation
- Idempotent operations (safe to run multiple times)

**Check Mode:**
- Read-only verification
- Non-zero exit code on non-compliance (fails CI/CD builds)
- Detailed listing of non-compliant files
- Summary statistics (scanned, eligible, compliant, non-compliant, skipped, failed)
- Optional JSON and Markdown report generation
- Dry-run mode to preview without generating reports

**Reporting:**
- JSON reports with complete data and ISO 8601 timestamps
- Markdown reports with human-readable summaries
- Large file list truncation in Markdown (shows first 100 files)
- Automatic output directory creation
- Validation of output directory permissions

### Technical Details
- Requires Python 3.11 or higher
- Built with Click framework for CLI
- Setuptools-based packaging
- Comprehensive test suite with 164+ tests
- Structured logging for debugging

### Limitations
- Per-file or per-extension custom headers not yet supported (uses single header file for all files)
- Report file limits: Markdown reports truncate large file lists to first 100 entries (full data in JSON)

## [0.1.0] - Initial Development

### Added
- Initial project structure
- Basic CLI framework
- Python version validation (3.11+ requirement)

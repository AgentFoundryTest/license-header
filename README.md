# License Header CLI

A deterministic license header enforcement tool for source files. This CLI tool helps maintain consistent license headers across your codebase by applying and validating headers in source files.

## Features

- **Apply Mode**: Automatically add or update license headers in source files
- **Check Mode**: Verify that all source files have correct license headers
- **Deterministic**: Consistent, reproducible results across different environments
- **GitHub Actions Ready**: Designed for easy integration into CI/CD pipelines

## Requirements

- Python 3.11 or higher

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/AgentFoundryTest/license-header.git
cd license-header

# Install the package
pip install -e .
```

### For Development

```bash
# Install with development dependencies
pip install -e ".[dev]"
```

## Usage

The CLI provides two main commands: `apply` and `check`.

### Quick Start

1. Create a `LICENSE_HEADER` file in your repository root with your header content:

```
# Copyright (c) 2025 Your Organization
# Licensed under the MIT License
```

2. Optionally, create a `license-header.config.json` configuration file:

```json
{
  "header_file": "LICENSE_HEADER",
  "include_extensions": [".py", ".js", ".ts"],
  "exclude_paths": ["node_modules", ".git", "venv"]
}
```

3. Run the tool:

```bash
# Check headers (read-only)
license-header check

# Apply headers with preview
license-header apply --dry-run

# Apply headers
license-header apply
```

### Apply License Headers

Apply license headers to source files in your project:

```bash
# Apply headers to current directory
license-header apply

# Apply headers to specific path
license-header apply --path /path/to/project

# Preview changes without modifying files
license-header apply --dry-run

# Specify custom header file
license-header apply --header path/to/header.txt

# Include only specific file extensions
license-header apply --include-extension .py --include-extension .js

# Exclude specific paths
license-header apply --exclude-path dist --exclude-path build

# Save modified files to output directory
license-header apply --output ./output
```

### Check License Headers

Verify that source files have correct license headers:

```bash
# Check current directory
license-header check

# Check specific path
license-header check --path /path/to/project

# Preview check results without performing actions
license-header check --dry-run

# Fail on any missing or incorrect headers
license-header check --strict

# Use custom configuration
license-header check --config my-config.json
```

## Configuration

The tool supports configuration through both CLI options and a JSON configuration file. CLI options always take precedence over configuration file settings.

### Configuration File

Create a `license-header.config.json` file in your repository root:

```json
{
  "header_file": "LICENSE_HEADER",
  "include_extensions": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h"],
  "exclude_paths": ["node_modules", ".git", "__pycache__", "venv", "env", ".venv", "dist", "build"],
  "output_dir": null
}
```

### Configuration Options

| Option | CLI Flag | Config File Key | Default | Description |
|--------|----------|----------------|---------|-------------|
| **Header File** | `--header` | `header_file` | `LICENSE_HEADER` if present, else required | Path to the license header file (relative to repo root or absolute) |
| **Include Extensions** | `--include-extension` | `include_extensions` | `[".py", ".js", ".ts", ".java", ".cpp", ".c", ".h"]` | File extensions to process. CLI flag can be specified multiple times. |
| **Exclude Paths** | `--exclude-path` | `exclude_paths` | `["node_modules", ".git", "__pycache__", "venv", "env", ".venv", "dist", "build"]` | Paths/patterns to exclude from processing. CLI flag can be specified multiple times. |
| **Output Directory** | `--output` | `output_dir` | None (modify in-place) | Directory to save modified files (apply mode) or reports (check mode) |
| **Target Path** | `--path` | N/A | `.` (current directory) | Path to scan for source files |
| **Dry Run** | `--dry-run` | N/A | `false` | Preview results without modifying files (both apply and check modes) |
| **Strict Mode** | `--strict` | N/A | `false` | Fail with non-zero exit code on any issues (check mode only) |
| **Config File** | `--config` | N/A | `license-header.config.json` if present | Path to custom configuration file |

### Repository Traversal

The tool uses a deterministic repository scanner to identify eligible source files based on configured extensions and exclude patterns.

#### Traversal Behavior

- **Iterative scanning**: Uses non-recursive directory walking to handle deep directory trees without stack overflow
- **Deterministic ordering**: Results are consistently sorted for reproducible behavior across platforms
- **Default excludes**: Automatically skips common noise directories:
  - `.git` - Git repository metadata
  - `.venv`, `venv`, `env` - Python virtual environments
  - `node_modules` - Node.js dependencies
  - `__pycache__` - Python bytecode cache
  - `dist` - Distribution/build output
  - `build` - Build artifacts
- **Binary detection**: Automatically detects and skips binary files by checking for null bytes
- **Symlink handling**: Symbolic links are detected and skipped to avoid infinite loops and duplicate processing
- **Permission errors**: Files that cannot be read due to permission errors are logged and skipped without aborting the scan
- **Case-insensitive extensions**: File extensions are matched case-insensitively (e.g., `.py`, `.PY`, and `.Py` all match)

#### Customizing Exclusions

You can add custom exclude patterns to the default list:

```bash
# Exclude additional directories via CLI
license-header apply --exclude-path vendor --exclude-path generated

# Or via configuration file
{
  "exclude_paths": ["vendor", "generated", "third_party"]
}
```

Note: Custom exclude patterns are added to (not replacing) the default excludes. Patterns match directory and file names anywhere in the path.

#### Edge Cases

The scanner handles several edge cases robustly:

- **Deep directory trees**: Can handle directories nested >1000 levels deep without recursion limits
- **Circular symlinks**: Detected and skipped without causing infinite loops or crashes
- **Read permission errors**: Logged as warnings but do not abort the scan
- **Case-insensitive filesystems**: Extensions are matched consistently regardless of case
- **Binary files with text extensions**: Files are checked for binary content even if they have text file extensions
- **Paths outside repository**: Files outside the repository root are automatically excluded

### Configuration Precedence

Configuration is loaded and merged in the following order (later sources override earlier ones):

1. **Default values** - Built-in defaults for extensions and exclude paths
2. **Configuration file** - Settings from `license-header.config.json` (or custom config file)
3. **CLI arguments** - Command-line flags (highest precedence)

### Examples

#### Using only CLI flags

```bash
license-header apply \
  --header LICENSE_HEADER \
  --include-extension .py \
  --include-extension .js \
  --exclude-path node_modules \
  --exclude-path dist \
  --dry-run
```

#### Using configuration file with CLI overrides

```bash
# Config file provides defaults, CLI overrides specific options
license-header apply --include-extension .py --dry-run
```

#### Using custom configuration file

```bash
license-header check --config configs/strict-config.json --strict
```

### Path Validation

The tool enforces security restrictions on file paths:

- **Header file paths** must be within the repository root or absolute paths that don't traverse above the repo
- **Output directory paths** must be within the repository root
- Relative paths are resolved relative to the repository root (detected by finding `.git` directory)
- Paths that attempt to traverse above the repository root (e.g., `../../etc/passwd`) are rejected with an error

### Edge Cases

- **Missing header file**: Tool exits with descriptive error message and non-zero exit code
- **Header without trailing newline**: File content is read exactly as-is without modification
- **Invalid JSON config**: Tool exits with parse error details
- **Unknown file extensions**: Logged as warnings but don't prevent execution
- **Invalid exclude patterns**: Logged as warnings but don't prevent execution

## Getting Help

```bash
# Show version
license-header --version

# Show general help
license-header --help

# Show command-specific help
license-header apply --help
license-header check --help
```

## GitHub Actions Integration

Use the CLI in your GitHub Actions workflows:

```yaml
name: License Header Check

on: [push, pull_request]

jobs:
  check-headers:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install license-header
        run: |
          pip install -e .
      
      - name: Check license headers
        run: |
          license-header check --strict
```

## Development Status

This project is in early development. Configuration loading, CLI options, and repository scanning are fully implemented.

### Current Status

- ✅ CLI structure with `apply` and `check` commands
- ✅ Structured logging
- ✅ Python version validation (3.11+)
- ✅ Error handling for unknown commands
- ✅ Configuration file support with JSON format
- ✅ CLI options for all configuration parameters
- ✅ Configuration merging with proper precedence
- ✅ Path validation and security checks
- ✅ Header file loading and validation
- ✅ Repository traversal with deterministic file scanning
- ✅ File extension filtering and exclude pattern matching
- ✅ Binary file detection
- ✅ Symlink handling and circular reference detection
- ⏳ Header scanning logic (planned)
- ⏳ Header application logic (planned)



# Permanents (License, Contributing, Author)

Do not change any of the below sections

## License

All Agent Foundry work is licensed under the GPLv3 License - see the LICENSE file for details.

## Contributing

Feel free to submit issues and enhancement requests!

## Author

Created by Agent Foundry and John Brosnihan

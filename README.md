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

### Apply License Headers

Apply license headers to source files in your project:

```bash
# Apply headers to current directory
license-header apply

# Apply headers to specific path
license-header apply --path /path/to/project

# Preview changes without modifying files
license-header apply --dry-run
```

### Check License Headers

Verify that source files have correct license headers:

```bash
# Check current directory
license-header check

# Check specific path
license-header check --path /path/to/project

# Fail on any missing or incorrect headers
license-header check --strict
```

### Getting Help

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

This project is in early development. The CLI structure and commands are established, but header scanning and application logic is not yet implemented.

### Current Status

- ✅ CLI structure with `apply` and `check` commands
- ✅ Structured logging
- ✅ Python version validation (3.11+)
- ✅ Error handling for unknown commands
- ⏳ Configuration file support (planned)
- ⏳ Header scanning logic (planned)
- ⏳ Header application logic (planned)
- ⏳ File pattern matching (planned)



# Permanents (License, Contributing, Author)

Do not change any of the below sections

## License

All Agent Foundry work is licensed under the GPLv3 License - see the LICENSE file for details.

## Contributing

Feel free to submit issues and enhancement requests!

## Author

Created by Agent Foundry and John Brosnihan

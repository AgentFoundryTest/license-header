"""
Tests for CLI module.
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from click.testing import CliRunner

from license_header.cli import main


class TestCLI:
    """Test CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_version(self):
        """Test --version flag."""
        result = self.runner.invoke(main, ['--version'])
        assert result.exit_code == 0
        assert '0.1.0' in result.output
    
    def test_help(self):
        """Test --help flag."""
        result = self.runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'License Header CLI' in result.output
        assert 'apply' in result.output
        assert 'check' in result.output
    
    def test_apply_help(self):
        """Test apply --help."""
        result = self.runner.invoke(main, ['apply', '--help'])
        assert result.exit_code == 0
        assert '--config' in result.output
        assert '--header' in result.output
        assert '--include-extension' in result.output
        assert '--exclude-path' in result.output
        assert '--dry-run' in result.output
    
    def test_check_help(self):
        """Test check --help."""
        result = self.runner.invoke(main, ['check', '--help'])
        assert result.exit_code == 0
        assert '--config' in result.output
        assert '--header' in result.output
        assert '--strict' in result.output


class TestApplyCommand:
    """Test apply command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_apply_with_header_file(self):
        """Test apply command with header file."""
        with self.runner.isolated_filesystem():
            # Create header file
            Path('HEADER.txt').write_text('# Copyright\n')
            
            result = self.runner.invoke(main, ['apply', '--header', 'HEADER.txt', '--dry-run'])
            assert result.exit_code == 0
            assert 'Configuration loaded successfully' in result.output
            assert 'Header file: HEADER.txt' in result.output
    
    def test_apply_missing_header_file(self):
        """Test apply command with missing header file."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(main, ['apply', '--header', 'nonexistent.txt'])
            assert result.exit_code != 0
            assert 'Header file not found' in result.output
    
    def test_apply_with_config_file(self):
        """Test apply command with config file."""
        with self.runner.isolated_filesystem():
            # Create header file
            Path('HEADER.txt').write_text('# Copyright\n')
            
            # Create config file
            config_data = {
                'header_file': 'HEADER.txt',
                'include_extensions': ['.py'],
            }
            Path('config.json').write_text(json.dumps(config_data))
            
            result = self.runner.invoke(main, ['apply', '--config', 'config.json', '--dry-run'])
            assert result.exit_code == 0
            assert 'Configuration loaded successfully' in result.output
            assert 'Include extensions: .py' in result.output
    
    def test_apply_cli_overrides_config(self):
        """Test that CLI flags override config file."""
        with self.runner.isolated_filesystem():
            # Create header files
            Path('HEADER1.txt').write_text('# Header 1\n')
            Path('HEADER2.txt').write_text('# Header 2\n')
            
            # Create config file
            config_data = {
                'header_file': 'HEADER1.txt',
            }
            Path('config.json').write_text(json.dumps(config_data))
            
            result = self.runner.invoke(main, [
                'apply',
                '--config', 'config.json',
                '--header', 'HEADER2.txt',
                '--dry-run'
            ])
            assert result.exit_code == 0
            assert 'Header file: HEADER2.txt' in result.output
    
    def test_apply_with_default_config(self):
        """Test apply command with default config file."""
        with self.runner.isolated_filesystem():
            # Create header file
            Path('HEADER.txt').write_text('# Copyright\n')
            
            # Create default config file
            config_data = {
                'header_file': 'HEADER.txt',
            }
            Path('license-header.config.json').write_text(json.dumps(config_data))
            
            result = self.runner.invoke(main, ['apply', '--dry-run'])
            assert result.exit_code == 0
            assert 'Configuration loaded successfully' in result.output
    
    def test_apply_with_extensions(self):
        """Test apply command with custom extensions."""
        with self.runner.isolated_filesystem():
            Path('HEADER.txt').write_text('# Copyright\n')
            
            result = self.runner.invoke(main, [
                'apply',
                '--header', 'HEADER.txt',
                '--include-extension', '.py',
                '--include-extension', '.js',
                '--dry-run'
            ])
            assert result.exit_code == 0
            assert 'Include extensions: .py, .js' in result.output
    
    def test_apply_with_exclude_paths(self):
        """Test apply command with exclude paths."""
        with self.runner.isolated_filesystem():
            Path('HEADER.txt').write_text('# Copyright\n')
            
            result = self.runner.invoke(main, [
                'apply',
                '--header', 'HEADER.txt',
                '--exclude-path', 'dist',
                '--exclude-path', 'build',
                '--dry-run'
            ])
            assert result.exit_code == 0
            assert 'Exclude paths: dist, build' in result.output
    
    def test_apply_with_default_license_header(self):
        """Test apply command with default LICENSE_HEADER file."""
        with self.runner.isolated_filesystem():
            Path('LICENSE_HEADER').write_text('# Default Header\n')
            
            result = self.runner.invoke(main, ['apply', '--dry-run'])
            assert result.exit_code == 0
            assert 'Configuration loaded successfully' in result.output
            assert 'Header file: LICENSE_HEADER' in result.output
    
    def test_apply_cli_overrides_default_license_header(self):
        """Test that --header flag overrides default LICENSE_HEADER."""
        with self.runner.isolated_filesystem():
            Path('LICENSE_HEADER').write_text('# Default\n')
            Path('CUSTOM.txt').write_text('# Custom\n')
            
            result = self.runner.invoke(main, ['apply', '--header', 'CUSTOM.txt', '--dry-run'])
            assert result.exit_code == 0
            assert 'Header file: CUSTOM.txt' in result.output
    
    def test_apply_with_absolute_header_path(self):
        """Test apply command with absolute path to header file."""
        with self.runner.isolated_filesystem():
            # Create a header file with absolute path
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write('# Absolute Path Header\n')
                abs_header_path = f.name
            
            try:
                result = self.runner.invoke(main, ['apply', '--header', abs_header_path, '--dry-run'])
                assert result.exit_code == 0
                assert 'Configuration loaded successfully' in result.output
                assert abs_header_path in result.output
            finally:
                # Clean up
                os.unlink(abs_header_path)
    
    def test_apply_with_config_path_outside_repo_rejected(self):
        """Test that config paths escaping repo are rejected."""
        with self.runner.isolated_filesystem():
            # Create header file
            Path('HEADER.txt').write_text('# Copyright\n')
            
            # Try to use a config path that escapes the repo
            result = self.runner.invoke(main, ['apply', '--config', '../outside_config.json', '--dry-run'])
            assert result.exit_code != 0
            assert 'Configuration file path' in result.output
            assert 'traverses above repository root' in result.output


class TestCheckCommand:
    """Test check command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_check_with_header_file(self):
        """Test check command with header file."""
        with self.runner.isolated_filesystem():
            Path('HEADER.txt').write_text('# Copyright\n')
            
            result = self.runner.invoke(main, ['check', '--header', 'HEADER.txt'])
            assert result.exit_code == 0
            assert 'Configuration loaded successfully' in result.output
    
    def test_check_strict_mode(self):
        """Test check command with strict mode."""
        with self.runner.isolated_filesystem():
            Path('HEADER.txt').write_text('# Copyright\n')
            
            result = self.runner.invoke(main, ['check', '--header', 'HEADER.txt', '--strict'])
            assert result.exit_code == 0
            assert 'Strict mode: True' in result.output
            assert 'Running in strict mode' in result.output
    
    def test_check_dry_run_mode(self):
        """Test check command with dry-run mode."""
        with self.runner.isolated_filesystem():
            Path('HEADER.txt').write_text('# Copyright\n')
            
            result = self.runner.invoke(main, ['check', '--header', 'HEADER.txt', '--dry-run'])
            assert result.exit_code == 0
            assert 'Dry run: True' in result.output
            assert '[DRY RUN] Would check license headers' in result.output
    
    def test_check_dry_run_with_strict(self):
        """Test check command with both dry-run and strict modes."""
        with self.runner.isolated_filesystem():
            Path('HEADER.txt').write_text('# Copyright\n')
            
            result = self.runner.invoke(main, ['check', '--header', 'HEADER.txt', '--dry-run', '--strict'])
            assert result.exit_code == 0
            assert 'Dry run: True' in result.output
            assert 'Strict mode: True' in result.output
            assert '[DRY RUN] Would check license headers' in result.output
    
    def test_check_missing_header_file(self):
        """Test check command with missing header file."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(main, ['check', '--header', 'nonexistent.txt'])
            assert result.exit_code != 0
            assert 'Header file not found' in result.output

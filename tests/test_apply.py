"""
Tests for apply module.
"""

import os
import pytest
from pathlib import Path

from license_header.apply import (
    ApplyResult,
    normalize_header,
    has_header,
    insert_header,
    apply_header_to_file,
    apply_headers,
)
from license_header.config import merge_config
from license_header.utils import (
    has_shebang,
    extract_shebang,
    detect_bom,
    read_file_with_encoding,
    write_file_with_encoding,
)


class TestApplyResult:
    """Test ApplyResult dataclass."""
    
    def test_apply_result_defaults(self):
        """Test that ApplyResult initializes with empty lists."""
        result = ApplyResult()
        assert result.modified_files == []
        assert result.already_compliant == []
        assert result.skipped_files == []
        assert result.failed_files == []
    
    def test_total_processed(self):
        """Test total_processed calculation."""
        result = ApplyResult()
        assert result.total_processed() == 0
        
        result.modified_files = [Path('a.py'), Path('b.py')]
        result.already_compliant = [Path('c.py')]
        result.skipped_files = [Path('d.bin')]
        result.failed_files = [Path('e.py')]
        assert result.total_processed() == 5


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_has_shebang_true(self):
        """Test detecting shebang line."""
        content = "#!/usr/bin/env python\nprint('hello')\n"
        assert has_shebang(content)
    
    def test_has_shebang_false(self):
        """Test no shebang detection."""
        content = "# Just a comment\nprint('hello')\n"
        assert not has_shebang(content)
    
    def test_extract_shebang_present(self):
        """Test extracting shebang when present."""
        content = "#!/usr/bin/env python\nprint('hello')\n"
        shebang, remaining = extract_shebang(content)
        assert shebang == "#!/usr/bin/env python\n"
        assert remaining == "print('hello')\n"
    
    def test_extract_shebang_absent(self):
        """Test extracting shebang when absent."""
        content = "print('hello')\n"
        shebang, remaining = extract_shebang(content)
        assert shebang is None
        assert remaining == content
    
    def test_extract_shebang_no_newline(self):
        """Test extracting shebang without newline."""
        content = "#!/usr/bin/env python"
        shebang, remaining = extract_shebang(content)
        assert shebang == "#!/usr/bin/env python"
        assert remaining == ""
    
    def test_detect_bom_utf8(self, tmp_path):
        """Test detecting UTF-8 BOM."""
        file_path = tmp_path / "test_utf8.txt"
        with open(file_path, 'wb') as f:
            f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
            f.write("Hello".encode('utf-8'))
        
        bom, encoding = detect_bom(file_path)
        assert bom is not None
        assert encoding == 'utf-8-sig'
    
    def test_detect_bom_none(self, tmp_path):
        """Test file without BOM."""
        file_path = tmp_path / "test_no_bom.txt"
        file_path.write_text("Hello")
        
        bom, encoding = detect_bom(file_path)
        assert bom is None
        assert encoding == 'utf-8'
    
    def test_detect_bom_utf16_le(self, tmp_path):
        """Test detecting UTF-16 LE BOM."""
        import codecs
        file_path = tmp_path / "test_utf16le.txt"
        with open(file_path, 'wb') as f:
            f.write(codecs.BOM_UTF16_LE)
            f.write("Hello".encode('utf-16-le'))
        
        bom, encoding = detect_bom(file_path)
        assert bom == codecs.BOM_UTF16_LE
        assert encoding == 'utf-16-le'
    
    def test_detect_bom_utf32_le(self, tmp_path):
        """Test detecting UTF-32 LE BOM (should not be misdetected as UTF-16 LE)."""
        import codecs
        file_path = tmp_path / "test_utf32le.txt"
        with open(file_path, 'wb') as f:
            f.write(codecs.BOM_UTF32_LE)
            f.write("Hello".encode('utf-32-le'))
        
        bom, encoding = detect_bom(file_path)
        assert bom == codecs.BOM_UTF32_LE, f"Expected UTF-32 LE BOM, got {bom.hex() if bom else None}"
        assert encoding == 'utf-32-le', f"Expected utf-32-le encoding, got {encoding}"
    
    def test_detect_bom_utf32_be(self, tmp_path):
        """Test detecting UTF-32 BE BOM."""
        import codecs
        file_path = tmp_path / "test_utf32be.txt"
        with open(file_path, 'wb') as f:
            f.write(codecs.BOM_UTF32_BE)
            f.write("Hello".encode('utf-32-be'))
        
        bom, encoding = detect_bom(file_path)
        assert bom == codecs.BOM_UTF32_BE
        assert encoding == 'utf-32-be'
    
    def test_read_write_file_preserves_bom(self, tmp_path):
        """Test that reading and writing preserves BOM."""
        file_path = tmp_path / "test_bom.txt"
        
        # Write file with UTF-8 BOM
        with open(file_path, 'wb') as f:
            f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
            f.write("Hello World".encode('utf-8'))
        
        # Read with encoding detection
        content, bom, encoding = read_file_with_encoding(file_path)
        assert content == "Hello World"
        assert bom is not None
        assert encoding == 'utf-8-sig'
        
        # Write back
        new_path = tmp_path / "test_bom_new.txt"
        write_file_with_encoding(new_path, content, bom, encoding)
        
        # Verify BOM is preserved
        with open(new_path, 'rb') as f:
            data = f.read()
            assert data.startswith(b'\xef\xbb\xbf')


class TestNormalizeHeader:
    """Test normalize_header function."""
    
    def test_normalize_header_with_newline(self):
        """Test normalizing header that already has newline."""
        header = "# Copyright 2025\n"
        result = normalize_header(header)
        assert result == "# Copyright 2025\n"
    
    def test_normalize_header_without_newline(self):
        """Test normalizing header without newline."""
        header = "# Copyright 2025"
        result = normalize_header(header)
        assert result == "# Copyright 2025\n"
    
    def test_normalize_header_with_trailing_whitespace(self):
        """Test normalizing header with trailing whitespace."""
        header = "# Copyright 2025\n\n  \n"
        result = normalize_header(header)
        assert result == "# Copyright 2025\n"
    
    def test_normalize_header_multiline(self):
        """Test normalizing multiline header."""
        header = "# Line 1\n# Line 2\n# Line 3"
        result = normalize_header(header)
        assert result == "# Line 1\n# Line 2\n# Line 3\n"


class TestHasHeader:
    """Test has_header function."""
    
    def test_has_header_exact_match(self):
        """Test detecting exact header match."""
        header = "# Copyright 2025\n"
        content = "# Copyright 2025\nprint('hello')\n"
        assert has_header(content, header)
    
    def test_has_header_no_match(self):
        """Test no header match."""
        header = "# Copyright 2025\n"
        content = "print('hello')\n"
        assert not has_header(content, header)
    
    def test_has_header_with_shebang(self):
        """Test detecting header after shebang."""
        header = "# Copyright 2025\n"
        content = "#!/usr/bin/env python\n# Copyright 2025\nprint('hello')\n"
        assert has_header(content, header)
    
    def test_has_header_partial_match(self):
        """Test that partial header match is not detected."""
        header = "# Copyright 2025\n# Licensed under MIT\n"
        content = "# Copyright 2025\nprint('hello')\n"
        assert not has_header(content, header)
    
    def test_has_header_multiline(self):
        """Test detecting multiline header."""
        header = "# Copyright 2025\n# Licensed under MIT\n"
        content = "# Copyright 2025\n# Licensed under MIT\nprint('hello')\n"
        assert has_header(content, header)
    
    def test_has_header_with_leading_blank_lines(self):
        """Test detecting header with leading blank lines."""
        header = "# Copyright 2025\n"
        content = "\n\n# Copyright 2025\nprint('hello')\n"
        assert has_header(content, header)
    
    def test_has_header_partial_match_with_leading_blanks(self):
        """Test that partial header with leading blanks is not detected as compliant."""
        header = "# Copyright 2025\n"
        content = "\n\n# Copyright 2025 Extra Text\ncode"
        assert not has_header(content, header), "Partial match should not be detected"
        
        # Also test with multi-line header
        header2 = "# Copyright 2025\n# Licensed under MIT\n"
        content2 = "\n\n# Copyright 2025\ncode"
        assert not has_header(content2, header2), "Partial multiline header should not be detected"


class TestInsertHeader:
    """Test insert_header function."""
    
    def test_insert_header_at_start(self):
        """Test inserting header at file start."""
        header = "# Copyright 2025\n"
        content = "print('hello')\n"
        result = insert_header(content, header)
        assert result == "# Copyright 2025\nprint('hello')\n"
    
    def test_insert_header_after_shebang(self):
        """Test inserting header after shebang."""
        header = "# Copyright 2025\n"
        content = "#!/usr/bin/env python\nprint('hello')\n"
        result = insert_header(content, header)
        assert result == "#!/usr/bin/env python\n# Copyright 2025\nprint('hello')\n"
    
    def test_insert_header_empty_file(self):
        """Test inserting header into empty file."""
        header = "# Copyright 2025\n"
        content = ""
        result = insert_header(content, header)
        assert result == "# Copyright 2025\n"
    
    def test_insert_header_normalizes(self):
        """Test that header is normalized during insertion."""
        header = "# Copyright 2025"  # No newline
        content = "print('hello')\n"
        result = insert_header(content, header)
        assert result == "# Copyright 2025\nprint('hello')\n"
    
    def test_insert_header_multiline(self):
        """Test inserting multiline header."""
        header = "# Copyright 2025\n# Licensed under MIT\n"
        content = "def main():\n    pass\n"
        result = insert_header(content, header)
        assert result == "# Copyright 2025\n# Licensed under MIT\ndef main():\n    pass\n"
    
    def test_insert_header_after_shebang_no_newline(self):
        """Test inserting header after shebang that has no trailing newline."""
        header = "# Copyright 2025\n"
        content = "#!/usr/bin/env python"
        result = insert_header(content, header)
        assert result == "#!/usr/bin/env python\n# Copyright 2025\n", \
            "Header should be on separate line after shebang"
        # Verify the header doesn't get concatenated to shebang
        assert "python#" not in result, "Header should not be concatenated to shebang"


class TestApplyHeaderToFile:
    """Test apply_header_to_file function."""
    
    def test_apply_header_to_new_file(self, tmp_path):
        """Test applying header to file without header."""
        file_path = tmp_path / "test.py"
        file_path.write_text("print('hello')\n")
        header = "# Copyright 2025\n"
        
        was_modified = apply_header_to_file(file_path, header)
        assert was_modified is True
        
        content = file_path.read_text()
        assert content == "# Copyright 2025\nprint('hello')\n"
    
    def test_apply_header_idempotent(self, tmp_path):
        """Test that applying header is idempotent."""
        file_path = tmp_path / "test.py"
        file_path.write_text("print('hello')\n")
        header = "# Copyright 2025\n"
        
        # First application
        was_modified = apply_header_to_file(file_path, header)
        assert was_modified is True
        content_after_first = file_path.read_text()
        
        # Second application (should be no-op)
        was_modified = apply_header_to_file(file_path, header)
        assert was_modified is False
        content_after_second = file_path.read_text()
        
        # Content should be identical
        assert content_after_first == content_after_second
        assert content_after_second == "# Copyright 2025\nprint('hello')\n"
    
    def test_apply_header_preserves_shebang(self, tmp_path):
        """Test that shebang is preserved."""
        file_path = tmp_path / "script.py"
        file_path.write_text("#!/usr/bin/env python\nprint('hello')\n")
        header = "# Copyright 2025\n"
        
        apply_header_to_file(file_path, header)
        content = file_path.read_text()
        
        assert content.startswith("#!/usr/bin/env python\n# Copyright 2025\n")
        assert "print('hello')" in content
    
    def test_apply_header_preserves_bom(self, tmp_path):
        """Test that BOM is preserved."""
        file_path = tmp_path / "test.py"
        
        # Write file with UTF-8 BOM
        with open(file_path, 'wb') as f:
            f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
            f.write("print('hello')\n".encode('utf-8'))
        
        header = "# Copyright 2025\n"
        apply_header_to_file(file_path, header)
        
        # Verify BOM is still present
        with open(file_path, 'rb') as f:
            data = f.read()
            assert data.startswith(b'\xef\xbb\xbf')
        
        # Verify content is correct
        content, bom, encoding = read_file_with_encoding(file_path)
        assert "# Copyright 2025" in content
        assert "print('hello')" in content
    
    def test_apply_header_dry_run(self, tmp_path):
        """Test dry-run mode doesn't modify file."""
        file_path = tmp_path / "test.py"
        original_content = "print('hello')\n"
        file_path.write_text(original_content)
        header = "# Copyright 2025\n"
        
        was_modified = apply_header_to_file(file_path, header, dry_run=True)
        assert was_modified is True
        
        # File should not be modified
        content = file_path.read_text()
        assert content == original_content
    
    def test_apply_header_to_output_dir(self, tmp_path):
        """Test writing to output directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        file_path = src_dir / "test.py"
        file_path.write_text("print('hello')\n")
        
        output_dir = tmp_path / "output"
        header = "# Copyright 2025\n"
        
        apply_header_to_file(file_path, header, output_dir=output_dir)
        
        # Original should be unchanged
        assert file_path.read_text() == "print('hello')\n"
        
        # Output should have header
        output_file = output_dir / "test.py"
        assert output_file.exists()
        assert output_file.read_text() == "# Copyright 2025\nprint('hello')\n"
    
    def test_apply_header_preserves_permissions(self, tmp_path):
        """Test that file permissions are preserved."""
        if os.name == 'nt':  # Skip on Windows
            pytest.skip("Permission test not applicable on Windows")
        
        file_path = tmp_path / "test.py"
        file_path.write_text("print('hello')\n")
        
        # Set specific permissions
        os.chmod(file_path, 0o755)
        original_mode = os.stat(file_path).st_mode
        
        header = "# Copyright 2025\n"
        apply_header_to_file(file_path, header)
        
        # Check permissions are preserved
        new_mode = os.stat(file_path).st_mode
        assert new_mode == original_mode
    
    def test_apply_header_large_file(self, tmp_path):
        """Test handling large files efficiently."""
        file_path = tmp_path / "large.py"
        
        # Create a large file (>10MB)
        large_content = "# " + ("x" * 100 + "\n") * 100000  # ~10MB
        file_path.write_text(large_content)
        
        header = "# Copyright 2025\n"
        apply_header_to_file(file_path, header)
        
        # Verify header was added
        content = file_path.read_text()
        assert content.startswith("# Copyright 2025\n")
    
    def test_apply_header_readonly_file(self, tmp_path):
        """Test handling read-only directory."""
        if os.name == 'nt':  # Skip on Windows - different permission model
            pytest.skip("Permission test not applicable on Windows")
        
        # Create a read-only directory instead
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        file_path = readonly_dir / "test.py"
        file_path.write_text("print('hello')\n")
        
        # Make directory read-only (can't create temp files)
        os.chmod(readonly_dir, 0o555)
        
        header = "# Copyright 2025\n"
        
        # Should raise permission error when trying to create temp file
        with pytest.raises(PermissionError):
            apply_header_to_file(file_path, header)
        
        # Restore permissions for cleanup
        os.chmod(readonly_dir, 0o755)


class TestApplyHeaders:
    """Test apply_headers function."""
    
    def test_apply_headers_basic(self, tmp_path):
        """Test applying headers to multiple files."""
        # Create header file
        header_file = tmp_path / "HEADER.txt"
        header_file.write_text("# Copyright 2025\n")
        
        # Create source files
        (tmp_path / "file1.py").write_text("print('file1')\n")
        (tmp_path / "file2.py").write_text("print('file2')\n")
        
        # Configure
        cli_args = {'header': str(header_file)}
        config = merge_config(cli_args, repo_root=tmp_path)
        
        # Apply headers
        result = apply_headers(config)
        
        # Check results
        assert len(result.modified_files) == 2
        assert len(result.already_compliant) == 0
        
        # Verify files have headers
        assert (tmp_path / "file1.py").read_text().startswith("# Copyright 2025\n")
        assert (tmp_path / "file2.py").read_text().startswith("# Copyright 2025\n")
    
    def test_apply_headers_idempotent(self, tmp_path):
        """Test that applying headers multiple times is idempotent."""
        # Create header file
        header_file = tmp_path / "HEADER.txt"
        header_file.write_text("# Copyright 2025\n")
        
        # Create source file
        (tmp_path / "test.py").write_text("print('test')\n")
        
        # Configure
        cli_args = {'header': str(header_file)}
        config = merge_config(cli_args, repo_root=tmp_path)
        
        # First application
        result1 = apply_headers(config)
        assert len(result1.modified_files) == 1
        assert len(result1.already_compliant) == 0
        content_after_first = (tmp_path / "test.py").read_text()
        
        # Second application
        result2 = apply_headers(config)
        assert len(result2.modified_files) == 0
        assert len(result2.already_compliant) == 1
        content_after_second = (tmp_path / "test.py").read_text()
        
        # Content should be identical
        assert content_after_first == content_after_second
    
    def test_apply_headers_with_shebang_files(self, tmp_path):
        """Test applying headers to files with shebangs."""
        # Create header file
        header_file = tmp_path / "HEADER.txt"
        header_file.write_text("# Copyright 2025\n")
        
        # Create file with shebang
        (tmp_path / "script.py").write_text("#!/usr/bin/env python\nprint('script')\n")
        
        # Configure
        cli_args = {'header': str(header_file)}
        config = merge_config(cli_args, repo_root=tmp_path)
        
        # Apply headers
        result = apply_headers(config)
        
        # Check result
        assert len(result.modified_files) == 1
        
        # Verify shebang is preserved and header comes after it
        content = (tmp_path / "script.py").read_text()
        assert content.startswith("#!/usr/bin/env python\n# Copyright 2025\n")
    
    def test_apply_headers_skips_excluded(self, tmp_path):
        """Test that excluded files are skipped."""
        # Create header file
        header_file = tmp_path / "HEADER.txt"
        header_file.write_text("# Copyright 2025\n")
        
        # Create files
        (tmp_path / "include.py").write_text("print('include')\n")
        
        excluded_dir = tmp_path / "excluded"
        excluded_dir.mkdir()
        (excluded_dir / "exclude.py").write_text("print('exclude')\n")
        
        # Configure with exclude pattern
        cli_args = {
            'header': str(header_file),
            'exclude_path': ['excluded']
        }
        config = merge_config(cli_args, repo_root=tmp_path)
        
        # Apply headers
        result = apply_headers(config)
        
        # Only include.py should be modified
        assert len(result.modified_files) == 1
        assert result.modified_files[0].name == 'include.py'
        
        # Excluded file should not have header
        assert not (excluded_dir / "exclude.py").read_text().startswith("# Copyright")
    
    def test_apply_headers_skips_binary(self, tmp_path):
        """Test that binary files are skipped."""
        # Create header file
        header_file = tmp_path / "HEADER.txt"
        header_file.write_text("# Copyright 2025\n")
        
        # Create text file
        (tmp_path / "text.py").write_text("print('text')\n")
        
        # Create binary file with .py extension
        (tmp_path / "binary.py").write_bytes(b'\x00\x01\x02\x03binary')
        
        # Configure
        cli_args = {'header': str(header_file)}
        config = merge_config(cli_args, repo_root=tmp_path)
        
        # Apply headers
        result = apply_headers(config)
        
        # Only text.py should be modified
        assert len(result.modified_files) == 1
        assert result.modified_files[0].name == 'text.py'
        
        # Binary should be in skipped
        assert any('binary.py' in str(f) for f in result.skipped_files)
    
    def test_apply_headers_dry_run(self, tmp_path):
        """Test dry-run mode."""
        # Create header file
        header_file = tmp_path / "HEADER.txt"
        header_file.write_text("# Copyright 2025\n")
        
        # Create source files
        (tmp_path / "file1.py").write_text("print('file1')\n")
        (tmp_path / "file2.py").write_text("print('file2')\n")
        
        # Configure with dry-run
        cli_args = {'header': str(header_file), 'dry_run': True}
        config = merge_config(cli_args, repo_root=tmp_path)
        
        # Apply headers
        result = apply_headers(config)
        
        # Files should be marked as modified
        assert len(result.modified_files) == 2
        
        # But files should not actually be modified
        assert not (tmp_path / "file1.py").read_text().startswith("# Copyright")
        assert not (tmp_path / "file2.py").read_text().startswith("# Copyright")
    
    def test_apply_headers_mixed_compliant(self, tmp_path):
        """Test with mix of compliant and non-compliant files."""
        # Create header file
        header_file = tmp_path / "HEADER.txt"
        header_file.write_text("# Copyright 2025\n")
        
        # Create file without header
        (tmp_path / "needs_header.py").write_text("print('needs')\n")
        
        # Create file with header
        (tmp_path / "has_header.py").write_text("# Copyright 2025\nprint('has')\n")
        
        # Configure
        cli_args = {'header': str(header_file)}
        config = merge_config(cli_args, repo_root=tmp_path)
        
        # Apply headers
        result = apply_headers(config)
        
        # One should be modified, one already compliant
        assert len(result.modified_files) == 1
        assert len(result.already_compliant) == 1
        assert result.modified_files[0].name == 'needs_header.py'
        assert result.already_compliant[0].name == 'has_header.py'

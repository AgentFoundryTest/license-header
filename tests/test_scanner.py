"""
Tests for scanner module.
"""

import os
import pytest
from pathlib import Path

from license_header.scanner import (
    ScanResult,
    is_binary_file,
    matches_exclude_pattern,
    scan_repository,
    DEFAULT_EXCLUDE_DIRS,
)


class TestScanResult:
    """Test ScanResult dataclass."""
    
    def test_scan_result_defaults(self):
        """Test that ScanResult initializes with empty lists."""
        result = ScanResult()
        assert result.eligible_files == []
        assert result.skipped_binary == []
        assert result.skipped_excluded == []
        assert result.skipped_symlink == []
        assert result.skipped_permission == []
        assert result.skipped_extension == []
    
    def test_total_files(self):
        """Test total_files calculation."""
        result = ScanResult()
        assert result.total_files() == 0
        
        result.eligible_files = [Path('a.py'), Path('b.py')]
        result.skipped_binary = [Path('c.bin')]
        result.skipped_extension = [Path('d.txt')]
        assert result.total_files() == 4


class TestIsBinaryFile:
    """Test is_binary_file function."""
    
    def test_text_file(self, tmp_path):
        """Test that text files are not detected as binary."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("Hello, world!\n")
        
        assert not is_binary_file(text_file)
    
    def test_binary_file(self, tmp_path):
        """Test that binary files are detected."""
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03')
        
        assert is_binary_file(binary_file)
    
    def test_python_file(self, tmp_path):
        """Test that Python source files are not binary."""
        py_file = tmp_path / "test.py"
        py_file.write_text("#!/usr/bin/env python\nprint('hello')\n")
        
        assert not is_binary_file(py_file)
    
    def test_mixed_content_with_null(self, tmp_path):
        """Test that files with null bytes are binary."""
        mixed_file = tmp_path / "mixed.dat"
        mixed_file.write_bytes(b'Some text\x00more text')
        
        assert is_binary_file(mixed_file)
    
    def test_nonexistent_file(self, tmp_path):
        """Test that nonexistent files are treated as binary."""
        nonexistent = tmp_path / "nonexistent.txt"
        
        # Should return True (safe default for unreadable files)
        assert is_binary_file(nonexistent)


class TestMatchesExcludePattern:
    """Test matches_exclude_pattern function."""
    
    def test_no_patterns_no_match(self, tmp_path):
        """Test that with no patterns, nothing is excluded."""
        test_path = tmp_path / "src" / "file.py"
        
        assert not matches_exclude_pattern(test_path, tmp_path, [])
    
    def test_directory_name_match(self, tmp_path):
        """Test matching directory names."""
        test_path = tmp_path / "node_modules" / "package" / "file.js"
        
        assert matches_exclude_pattern(test_path, tmp_path, ["node_modules"])
    
    def test_nested_directory_match(self, tmp_path):
        """Test matching nested directory names."""
        test_path = tmp_path / "src" / "build" / "output.js"
        
        assert matches_exclude_pattern(test_path, tmp_path, ["build"])
    
    def test_multiple_patterns(self, tmp_path):
        """Test with multiple exclude patterns."""
        patterns = ["dist", "build", "__pycache__"]
        
        dist_path = tmp_path / "dist" / "file.js"
        build_path = tmp_path / "build" / "file.js"
        cache_path = tmp_path / "__pycache__" / "file.pyc"
        normal_path = tmp_path / "src" / "file.py"
        
        assert matches_exclude_pattern(dist_path, tmp_path, patterns)
        assert matches_exclude_pattern(build_path, tmp_path, patterns)
        assert matches_exclude_pattern(cache_path, tmp_path, patterns)
        assert not matches_exclude_pattern(normal_path, tmp_path, patterns)
    
    def test_path_outside_repo(self, tmp_path):
        """Test that paths outside repo are excluded."""
        outside_path = tmp_path.parent / "outside" / "file.py"
        
        # Should be excluded
        assert matches_exclude_pattern(outside_path, tmp_path, [])
    
    def test_glob_pattern_wildcard(self, tmp_path):
        """Test glob patterns with wildcards."""
        # Pattern with single wildcard
        pyc_path = tmp_path / "src" / "file.pyc"
        py_path = tmp_path / "src" / "file.py"
        
        assert matches_exclude_pattern(pyc_path, tmp_path, ["*.pyc"])
        assert not matches_exclude_pattern(py_path, tmp_path, ["*.pyc"])
    
    def test_glob_pattern_subdirectory(self, tmp_path):
        """Test glob patterns matching subdirectories."""
        # Pattern like 'generated/*.py'
        generated_py = tmp_path / "generated" / "output.py"
        generated_js = tmp_path / "generated" / "output.js"
        src_py = tmp_path / "src" / "output.py"
        
        assert matches_exclude_pattern(generated_py, tmp_path, ["generated/*.py"])
        assert not matches_exclude_pattern(generated_js, tmp_path, ["generated/*.py"])
        assert not matches_exclude_pattern(src_py, tmp_path, ["generated/*.py"])
    
    def test_glob_pattern_recursive(self, tmp_path):
        """Test glob patterns with recursive wildcards."""
        # Pattern like '**/vendor'
        vendor_1 = tmp_path / "vendor" / "lib.js"
        vendor_2 = tmp_path / "src" / "vendor" / "lib.js"
        vendor_3 = tmp_path / "deep" / "nested" / "vendor" / "lib.js"
        non_vendor = tmp_path / "src" / "lib.js"
        
        patterns = ["**/vendor"]
        assert matches_exclude_pattern(vendor_1, tmp_path, patterns)
        assert matches_exclude_pattern(vendor_2, tmp_path, patterns)
        assert matches_exclude_pattern(vendor_3, tmp_path, patterns)
        assert not matches_exclude_pattern(non_vendor, tmp_path, patterns)
    
    def test_glob_pattern_complex(self, tmp_path):
        """Test complex glob patterns."""
        # Pattern like 'src/*/temp'
        match_1 = tmp_path / "src" / "module1" / "temp" / "file.py"
        match_2 = tmp_path / "src" / "module2" / "temp" / "file.py"
        no_match_1 = tmp_path / "src" / "temp" / "file.py"  # Missing middle component
        no_match_2 = tmp_path / "lib" / "module1" / "temp" / "file.py"  # Wrong base
        
        patterns = ["src/*/temp"]
        assert matches_exclude_pattern(match_1, tmp_path, patterns)
        assert matches_exclude_pattern(match_2, tmp_path, patterns)
        assert not matches_exclude_pattern(no_match_1, tmp_path, patterns)
        assert not matches_exclude_pattern(no_match_2, tmp_path, patterns)
    
    def test_glob_and_simple_patterns_mixed(self, tmp_path):
        """Test mixing glob patterns with simple directory names."""
        patterns = ["node_modules", "*.pyc", "generated/*.py"]
        
        # Simple directory match
        node_file = tmp_path / "src" / "node_modules" / "package.json"
        assert matches_exclude_pattern(node_file, tmp_path, patterns)
        
        # Glob wildcard match
        pyc_file = tmp_path / "src" / "module.pyc"
        assert matches_exclude_pattern(pyc_file, tmp_path, patterns)
        
        # Glob subdirectory match
        generated_py = tmp_path / "generated" / "output.py"
        assert matches_exclude_pattern(generated_py, tmp_path, patterns)
        
        # No match
        normal_py = tmp_path / "src" / "main.py"
        assert not matches_exclude_pattern(normal_py, tmp_path, patterns)




class TestScanRepository:
    """Test scan_repository function."""
    
    def setup_basic_repo(self, tmp_path):
        """Create a basic repository structure for testing."""
        # Create directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()
        
        # Create Python files
        (tmp_path / "src" / "main.py").write_text("print('main')\n")
        (tmp_path / "src" / "utils.py").write_text("def util(): pass\n")
        (tmp_path / "tests" / "test_main.py").write_text("def test(): pass\n")
        
        # Create non-Python files
        (tmp_path / "README.md").write_text("# README\n")
        (tmp_path / "docs" / "guide.txt").write_text("Guide\n")
        
        return tmp_path
    
    def test_basic_scan(self, tmp_path):
        """Test basic repository scanning."""
        repo = self.setup_basic_repo(tmp_path)
        
        result = scan_repository(
            root_path=repo,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=repo,
        )
        
        # Should find 3 Python files
        assert len(result.eligible_files) == 3
        assert any('main.py' in str(f) for f in result.eligible_files)
        assert any('utils.py' in str(f) for f in result.eligible_files)
        assert any('test_main.py' in str(f) for f in result.eligible_files)
        
        # Should skip non-Python files
        assert len(result.skipped_extension) == 2
    
    def test_multiple_extensions(self, tmp_path):
        """Test scanning with multiple file extensions."""
        (tmp_path / "file.py").write_text("python\n")
        (tmp_path / "file.js").write_text("javascript\n")
        (tmp_path / "file.ts").write_text("typescript\n")
        (tmp_path / "file.txt").write_text("text\n")
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py', '.js', '.ts'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        assert len(result.eligible_files) == 3
        assert len(result.skipped_extension) == 1
    
    def test_default_excludes(self, tmp_path):
        """Test that default exclude directories are skipped."""
        # Create default exclude directories
        for dirname in ['.git', '.venv', 'node_modules', 'dist', 'build']:
            dir_path = tmp_path / dirname
            dir_path.mkdir()
            (dir_path / "file.py").write_text("content\n")
        
        # Create a normal directory
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content\n")
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        # Should only find the file in src
        assert len(result.eligible_files) == 1
        assert 'src/main.py' in str(result.eligible_files[0])
    
    def test_user_exclude_patterns(self, tmp_path):
        """Test user-specified exclude patterns."""
        (tmp_path / "include").mkdir()
        (tmp_path / "exclude").mkdir()
        (tmp_path / "include" / "file.py").write_text("content\n")
        (tmp_path / "exclude" / "file.py").write_text("content\n")
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=["exclude"],
            repo_root=tmp_path,
        )
        
        assert len(result.eligible_files) == 1
        assert 'include/file.py' in str(result.eligible_files[0])
    
    def test_glob_patterns_in_scan(self, tmp_path):
        """Test that glob patterns work in repository scanning."""
        # Create directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "generated").mkdir()
        (tmp_path / "vendor").mkdir()
        
        # Create files that should be excluded by glob patterns
        (tmp_path / "generated" / "output.py").write_text("# generated\n")
        (tmp_path / "generated" / "data.py").write_text("# generated\n")
        (tmp_path / "file.pyc").write_text("compiled\n")
        (tmp_path / "src" / "temp.pyc").write_text("compiled\n")
        (tmp_path / "vendor" / "lib.py").write_text("# vendor\n")
        
        # Create files that should be included
        (tmp_path / "src" / "main.py").write_text("# main\n")
        (tmp_path / "src" / "utils.py").write_text("# utils\n")
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py', '.pyc'],
            exclude_patterns=["generated/*.py", "*.pyc", "**/vendor"],
            repo_root=tmp_path,
        )
        
        # Should only find the files in src, not in generated or vendor, and not .pyc files
        assert len(result.eligible_files) == 2
        assert all('src/' in str(f) for f in result.eligible_files)
        assert all('.py' in str(f) and '.pyc' not in str(f) for f in result.eligible_files)
    
    def test_complex_glob_patterns_in_scan(self, tmp_path):
        """Test complex glob patterns in repository scanning."""
        # Create directory structure
        (tmp_path / "src" / "module1" / "temp").mkdir(parents=True)
        (tmp_path / "src" / "module2" / "temp").mkdir(parents=True)
        (tmp_path / "src" / "module1" / "code").mkdir(parents=True)
        (tmp_path / "lib").mkdir()
        
        # Files that should be excluded by 'src/*/temp' pattern
        (tmp_path / "src" / "module1" / "temp" / "cache.py").write_text("# temp\n")
        (tmp_path / "src" / "module2" / "temp" / "cache.py").write_text("# temp\n")
        
        # Files that should be included
        (tmp_path / "src" / "module1" / "code" / "main.py").write_text("# code\n")
        (tmp_path / "lib" / "util.py").write_text("# lib\n")
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=["src/*/temp"],
            repo_root=tmp_path,
        )
        
        # Should only find files not in temp directories
        assert len(result.eligible_files) == 2
        assert not any('temp' in str(f) for f in result.eligible_files)
    
    def test_binary_file_detection(self, tmp_path):
        """Test that binary files are detected and skipped."""
        # Create text file
        (tmp_path / "text.py").write_text("print('hello')\n")
        
        # Create binary file with .py extension
        (tmp_path / "binary.py").write_bytes(b'\x00\x01\x02\x03binary content')
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        assert len(result.eligible_files) == 1
        assert 'text.py' in str(result.eligible_files[0])
        assert len(result.skipped_binary) == 1
        assert 'binary.py' in str(result.skipped_binary[0])
    
    def test_symlink_avoidance(self, tmp_path):
        """Test that symlinks are skipped."""
        # Create a real file
        real_file = tmp_path / "real.py"
        real_file.write_text("content\n")
        
        # Create a symlink to it
        link_file = tmp_path / "link.py"
        link_file.symlink_to(real_file)
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        # Should only find the real file
        assert len(result.eligible_files) == 1
        assert 'real.py' in str(result.eligible_files[0])
        assert len(result.skipped_symlink) == 1
    
    def test_symlink_directory_avoidance(self, tmp_path):
        """Test that symlinked directories are not traversed."""
        # Create a real directory with files
        real_dir = tmp_path / "real_dir"
        real_dir.mkdir()
        (real_dir / "file.py").write_text("content\n")
        
        # Create a symlink to the directory
        link_dir = tmp_path / "link_dir"
        link_dir.symlink_to(real_dir)
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        # Should only find the file once (through real_dir, not through link_dir)
        assert len(result.eligible_files) == 1
        # The file path should use the real directory, not the symlink
        file_path = str(result.eligible_files[0])
        # Count occurrences - should only appear once in the path
        assert file_path.count('file.py') == 1
    
    def test_deterministic_ordering(self, tmp_path):
        """Test that results are sorted deterministically."""
        # Create files in random order
        files = ['zebra.py', 'apple.py', 'middle.py', 'banana.py']
        for filename in files:
            (tmp_path / filename).write_text("content\n")
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        # Check that results are sorted
        filenames = [f.name for f in result.eligible_files]
        assert filenames == sorted(filenames)
        assert filenames == ['apple.py', 'banana.py', 'middle.py', 'zebra.py']
    
    def test_deep_directory_tree(self, tmp_path):
        """Test that deep directory trees are handled without recursion issues."""
        # Create a deep directory tree
        current = tmp_path
        for i in range(100):  # Create 100 levels deep
            current = current / f"level{i}"
            current.mkdir()
        
        # Create a file at the deepest level
        (current / "deep.py").write_text("content\n")
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        # Should find the file without recursion errors
        assert len(result.eligible_files) == 1
        assert 'deep.py' in str(result.eligible_files[0])
    
    def test_case_insensitive_extensions(self, tmp_path):
        """Test that file extensions are matched case-insensitively."""
        (tmp_path / "lower.py").write_text("content\n")
        (tmp_path / "upper.PY").write_text("content\n")
        (tmp_path / "mixed.Py").write_text("content\n")
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        # Should find all three files regardless of case
        assert len(result.eligible_files) == 3
    
    def test_permission_error_handling(self, tmp_path):
        """Test that permission errors are logged but don't abort the scan."""
        # Create a regular file
        (tmp_path / "readable.py").write_text("content\n")
        
        # Create a file and make it unreadable
        # Note: Windows handles file permissions differently via ACLs,
        # so this test only runs on Unix-like systems where chmod works
        if os.name != 'nt':  # Skip on Windows
            unreadable = tmp_path / "unreadable.py"
            unreadable.write_text("content\n")
            unreadable.chmod(0o000)
            
            try:
                result = scan_repository(
                    root_path=tmp_path,
                    include_extensions=['.py'],
                    exclude_patterns=[],
                    repo_root=tmp_path,
                )
                
                # Should find the readable file
                assert len(result.eligible_files) == 1
                assert 'readable.py' in str(result.eligible_files[0])
                
                # Unreadable file is detected as binary (safe default) when we can't read it
                # This is expected behavior - if we can't read a file, we treat it as binary
                assert len(result.skipped_binary) == 1
                assert 'unreadable.py' in str(result.skipped_binary[0])
            finally:
                # Restore permissions for cleanup
                unreadable.chmod(0o644)
    
    def test_nested_exclude_patterns(self, tmp_path):
        """Test that nested directories matching exclude patterns are skipped."""
        # Create nested structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "node_modules").mkdir()
        (tmp_path / "src" / "lib").mkdir()
        
        (tmp_path / "src" / "main.py").write_text("content\n")
        (tmp_path / "src" / "node_modules" / "pkg.py").write_text("content\n")
        (tmp_path / "src" / "lib" / "util.py").write_text("content\n")
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        # Should find files in src and lib, but not in node_modules
        assert len(result.eligible_files) == 2
        assert any('main.py' in str(f) for f in result.eligible_files)
        assert any('util.py' in str(f) for f in result.eligible_files)
        assert not any('node_modules' in str(f) for f in result.eligible_files)
    
    def test_empty_directory(self, tmp_path):
        """Test scanning an empty directory."""
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        assert len(result.eligible_files) == 0
        assert result.total_files() == 0
    
    def test_exclude_precedence(self, tmp_path):
        """Test that exclude patterns take precedence over include extensions."""
        (tmp_path / "excluded").mkdir()
        (tmp_path / "excluded" / "file.py").write_text("content\n")
        (tmp_path / "included.py").write_text("content\n")
        
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=["excluded"],
            repo_root=tmp_path,
        )
        
        # Should only find the included file
        assert len(result.eligible_files) == 1
        assert 'included.py' in str(result.eligible_files[0])
        
        # Excluded file should not be in eligible_files
        assert not any('excluded' in str(f) for f in result.eligible_files)
    
    def test_circular_symlink_handling(self, tmp_path):
        """Test that circular symlinks don't cause infinite loops."""
        # Create directories
        dir_a = tmp_path / "dir_a"
        dir_b = tmp_path / "dir_b"
        dir_a.mkdir()
        dir_b.mkdir()
        
        # Create a file in dir_a
        (dir_a / "file.py").write_text("content\n")
        
        # Create circular symlinks (dir_a/link_b -> dir_b, dir_b/link_a -> dir_a)
        (dir_a / "link_b").symlink_to(dir_b)
        (dir_b / "link_a").symlink_to(dir_a)
        
        # Should not hang or crash
        result = scan_repository(
            root_path=tmp_path,
            include_extensions=['.py'],
            exclude_patterns=[],
            repo_root=tmp_path,
        )
        
        # Should find the file in dir_a
        assert len(result.eligible_files) == 1
        assert 'file.py' in str(result.eligible_files[0])
    
    def test_relative_root_path(self, tmp_path):
        """Test that scanning works with relative root paths."""
        import os
        
        # Create a subdirectory with a file
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file.py").write_text("content\n")
        
        # Change to tmp_path and scan with relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            # Scan with relative root_path
            result = scan_repository(
                root_path=Path('subdir'),
                include_extensions=['.py'],
                exclude_patterns=[],
                repo_root=Path.cwd(),
            )
            
            # Should find the file
            assert len(result.eligible_files) == 1
            assert 'file.py' in str(result.eligible_files[0])
            
        finally:
            os.chdir(original_cwd)

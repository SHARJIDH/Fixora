"""
Tests for FormatterDetectorService.
"""
import pytest
import json
from pathlib import Path
from services.formatter_detector import FormatterDetectorService, FormatterConfig


class TestFormatterDetectorService:
    def setup_method(self):
        self.detector = FormatterDetectorService()
    
    def test_detect_prettier_from_prettierrc(self, tmp_path):
        """Should detect Prettier when .prettierrc exists."""
        (tmp_path / ".prettierrc").write_text("{}")
        formatters = self.detector.detect_formatters(str(tmp_path))
        assert len(formatters) == 1
        assert formatters[0].formatter_type == 'prettier'
        assert 'npx prettier' in formatters[0].format_command
    
    def test_detect_prettier_from_prettierrc_json(self, tmp_path):
        """Should detect Prettier when .prettierrc.json exists."""
        (tmp_path / ".prettierrc.json").write_text('{"semi": true}')
        formatters = self.detector.detect_formatters(str(tmp_path))
        assert len(formatters) == 1
        assert formatters[0].formatter_type == 'prettier'
    
    def test_detect_prettier_from_package_json(self, tmp_path):
        """Should detect Prettier from package.json devDependencies."""
        package_json = {
            "name": "test-project",
            "devDependencies": {
                "prettier": "^3.0.0"
            }
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))
        formatters = self.detector.detect_formatters(str(tmp_path))
        assert len(formatters) == 1
        assert formatters[0].formatter_type == 'prettier'
    
    def test_detect_prettier_from_package_json_prettier_key(self, tmp_path):
        """Should detect Prettier from package.json prettier config key."""
        package_json = {
            "name": "test-project",
            "prettier": {
                "semi": True
            }
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))
        formatters = self.detector.detect_formatters(str(tmp_path))
        assert len(formatters) == 1
        assert formatters[0].formatter_type == 'prettier'
    
    def test_detect_eslint_without_prettier(self, tmp_path):
        """Should detect ESLint when no Prettier config exists."""
        (tmp_path / ".eslintrc.json").write_text('{"extends": "eslint:recommended"}')
        formatters = self.detector.detect_formatters(str(tmp_path))
        assert len(formatters) == 1
        assert formatters[0].formatter_type == 'eslint'
        assert 'npx eslint --fix' in formatters[0].format_command
    
    def test_prettier_priority_over_eslint(self, tmp_path):
        """Prettier should take priority over ESLint for JS/TS files."""
        (tmp_path / ".prettierrc").write_text("{}")
        (tmp_path / ".eslintrc.json").write_text('{"extends": "eslint:recommended"}')
        formatters = self.detector.detect_formatters(str(tmp_path))
        # Only prettier should be detected (eslint is fallback)
        assert len(formatters) == 1
        assert formatters[0].formatter_type == 'prettier'
    
    def test_detect_black_from_pyproject_toml(self, tmp_path):
        """Should detect Black from pyproject.toml configuration."""
        pyproject_content = """
[tool.black]
line-length = 88
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)
        formatters = self.detector.detect_formatters(str(tmp_path))
        assert any(f.formatter_type == 'black' for f in formatters)
    
    def test_detect_isort_from_pyproject_toml(self, tmp_path):
        """Should detect isort from pyproject.toml configuration."""
        pyproject_content = """
[tool.isort]
profile = "black"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)
        formatters = self.detector.detect_formatters(str(tmp_path))
        assert any(f.formatter_type == 'isort' for f in formatters)
    
    def test_detect_multiple_python_formatters(self, tmp_path):
        """Should detect both Black and isort when both are configured."""
        pyproject_content = """
[tool.black]
line-length = 88

[tool.isort]
profile = "black"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)
        formatters = self.detector.detect_formatters(str(tmp_path))
        formatter_types = {f.formatter_type for f in formatters}
        assert 'black' in formatter_types
        assert 'isort' in formatter_types
    
    def test_no_formatters_detected(self, tmp_path):
        """Should return empty list when no formatters are configured."""
        (tmp_path / "main.py").write_text("print('hello')")
        formatters = self.detector.detect_formatters(str(tmp_path))
        assert len(formatters) == 0
    
    def test_get_formatter_for_file_js(self):
        """Should return correct formatter for JavaScript files."""
        prettier = FormatterConfig(
            formatter_type='prettier',
            format_command='npx prettier --write {file}',
            file_extensions=['.js', '.jsx', '.ts', '.tsx']
        )
        formatter = self.detector.get_formatter_for_file('src/app.js', [prettier])
        assert formatter is not None
        assert formatter.formatter_type == 'prettier'
    
    def test_get_formatter_for_file_python(self):
        """Should return correct formatter for Python files."""
        black = FormatterConfig(
            formatter_type='black',
            format_command='black {file}',
            file_extensions=['.py']
        )
        formatter = self.detector.get_formatter_for_file('src/main.py', [black])
        assert formatter is not None
        assert formatter.formatter_type == 'black'
    
    def test_get_formatter_for_file_no_match(self):
        """Should return None when no formatter matches the file type."""
        black = FormatterConfig(
            formatter_type='black',
            format_command='black {file}',
            file_extensions=['.py']
        )
        formatter = self.detector.get_formatter_for_file('src/app.js', [black])
        assert formatter is None
    
    def test_get_format_command(self):
        """Should generate correct format command with file path."""
        formatter = FormatterConfig(
            formatter_type='prettier',
            format_command='npx prettier --write {file}',
            file_extensions=['.js']
        )
        cmd = self.detector.get_format_command('/path/to/file.js', formatter)
        assert cmd == 'npx prettier --write /path/to/file.js'

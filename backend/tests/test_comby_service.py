"""
Tests for CombyService - Structural code transformations.

Run with: pytest tests/test_comby_service.py -v
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from services.comby_service import CombyService, CombyResult, LANGUAGE_MAP


class TestLanguageDetection:
    """Tests for language detection from file extensions."""
    
    def test_detect_python(self):
        service = CombyService()
        assert service.detect_language('main.py') == '.python'
        assert service.detect_language('src/app.py') == '.python'
    
    def test_detect_javascript(self):
        service = CombyService()
        assert service.detect_language('app.js') == '.js'
        assert service.detect_language('component.jsx') == '.js'
    
    def test_detect_typescript(self):
        service = CombyService()
        assert service.detect_language('app.ts') == '.ts'
        assert service.detect_language('component.tsx') == '.tsx'
    
    def test_detect_go(self):
        service = CombyService()
        assert service.detect_language('main.go') == '.go'
    
    def test_detect_generic_fallback(self):
        service = CombyService()
        assert service.detect_language('config.yaml') == '.generic'
        assert service.detect_language('unknown.xyz') == '.generic'


class TestCombyService:
    """Tests for CombyService methods."""
    
    def test_is_available_cached(self):
        """Should cache availability check."""
        service = CombyService()
        # First call checks
        result1 = service.is_available()
        # Second call uses cache
        result2 = service.is_available()
        assert result1 == result2
    
    @patch('services.comby_service.subprocess.run')
    def test_is_available_true(self, mock_run):
        """Should return True when comby is installed."""
        mock_run.return_value = Mock(returncode=0)
        
        service = CombyService()
        service._available = None  # Reset cache
        
        assert service.is_available() is True
    
    @patch('services.comby_service.subprocess.run')
    def test_is_available_false(self, mock_run):
        """Should return False when comby is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        service = CombyService()
        service._available = None  # Reset cache
        
        assert service.is_available() is False
    
    def test_apply_patch_comby_not_available(self):
        """Should return error when Comby not available."""
        service = CombyService()
        service._available = False
        
        result = service.apply_patch(
            file_path='/tmp/test.py',
            match_pattern='print(:[arg])',
            replace_pattern='logging.info(:[arg])'
        )
        
        assert result.success is False
        assert 'not installed' in result.error.lower()
    
    def test_apply_patch_file_not_found(self, tmp_path):
        """Should return error when file doesn't exist."""
        service = CombyService()
        service._available = True
        
        result = service.apply_patch(
            file_path=str(tmp_path / 'nonexistent.py'),
            match_pattern='print(:[arg])',
            replace_pattern='logging.info(:[arg])'
        )
        
        assert result.success is False
        assert 'not found' in result.error.lower()
    
    @patch('services.comby_service.subprocess.run')
    def test_apply_patch_success(self, mock_run, tmp_path):
        """Should apply patch successfully."""
        # Create test file
        test_file = tmp_path / 'test.py'
        test_file.write_text('print("hello")\n')
        
        # Mock comby response
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"rewritten_source": "logging.info(\\"hello\\")\\n", "in_place_substitutions": [{}]}'
        )
        
        service = CombyService()
        service._available = True
        
        result = service.apply_patch(
            file_path=str(test_file),
            match_pattern='print(:[arg])',
            replace_pattern='logging.info(:[arg])',
            in_place=False
        )
        
        assert result.success is True
        assert result.matches_found == 1
    
    @patch('services.comby_service.subprocess.run')
    def test_apply_patch_timeout(self, mock_run, tmp_path):
        """Should handle timeout gracefully."""
        import subprocess
        
        test_file = tmp_path / 'test.py'
        test_file.write_text('print("hello")')
        
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='comby', timeout=30)
        
        service = CombyService()
        service._available = True
        
        result = service.apply_patch(
            file_path=str(test_file),
            match_pattern='print(:[arg])',
            replace_pattern='logging.info(:[arg])'
        )
        
        assert result.success is False
        assert 'timed out' in result.error.lower()
    
    @patch('services.comby_service.subprocess.run')
    def test_apply_patch_to_content(self, mock_run):
        """Should transform content string."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"rewritten_source": "logging.info(\\"test\\")", "in_place_substitutions": [{}]}'
        )
        
        service = CombyService()
        service._available = True
        
        result = service.apply_patch_to_content(
            content='print("test")',
            match_pattern='print(:[arg])',
            replace_pattern='logging.info(:[arg])',
            language='.python'
        )
        
        assert result.success is True
        assert 'logging.info' in result.rewritten_content
    
    def test_apply_patch_to_content_not_available(self):
        """Should return error when Comby not available."""
        service = CombyService()
        service._available = False
        
        result = service.apply_patch_to_content(
            content='print("test")',
            match_pattern='print(:[arg])',
            replace_pattern='logging.info(:[arg])'
        )
        
        assert result.success is False


@pytest.mark.skipif(
    not CombyService().is_available(),
    reason="Comby not installed - skipping integration tests"
)
class TestCombyServiceIntegration:
    """Integration tests that use real Comby binary."""
    
    def test_real_apply_patch_to_content(self):
        """Test real Comby transformation."""
        service = CombyService()
        
        result = service.apply_patch_to_content(
            content='print("hello")',
            match_pattern='print(:[arg])',
            replace_pattern='logging.info(:[arg])',
            language='.python'
        )
        
        assert result.success is True
        assert 'logging.info("hello")' in result.rewritten_content
    
    def test_real_apply_patch_to_file(self, tmp_path):
        """Test real file transformation."""
        service = CombyService()
        
        # Create test file
        test_file = tmp_path / 'test.py'
        test_file.write_text('def old_func():\n    pass\n')
        
        result = service.apply_patch(
            file_path=str(test_file),
            match_pattern='def old_func()',
            replace_pattern='def new_func()',
            in_place=True
        )
        
        assert result.success is True
        
        # Verify file was modified
        content = test_file.read_text()
        assert 'new_func' in content
        assert 'old_func' not in content
    
    def test_real_match_only(self):
        """Test pattern matching without rewriting."""
        service = CombyService()
        
        matches = service.match_only(
            content='foo(1); bar(2); foo(3);',
            match_pattern='foo(:[n])',
            language='.generic'
        )
        
        # Should find 2 matches for foo()
        assert len(matches) == 2
    
    def test_structural_matching_nested(self):
        """Test that Comby handles nested structures."""
        service = CombyService()
        
        result = service.apply_patch_to_content(
            content='result = func(nested(a, b), c)',
            match_pattern='func(:[args])',
            replace_pattern='new_func(:[args])',
            language='.generic'
        )
        
        assert result.success is True
        assert 'new_func(nested(a, b), c)' in result.rewritten_content

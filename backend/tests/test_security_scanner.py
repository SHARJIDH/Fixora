"""
Tests for SecurityScannerService - Security scanning for AI-generated code.

Run with: pytest tests/test_security_scanner.py -v
"""
import pytest
from unittest.mock import Mock, patch
import json

from services.security_scanner import (
    SecurityScannerService,
    SecurityIssue,
    ScanResult,
    Severity,
)


class TestSeverity:
    """Tests for Severity enum conversions."""
    
    def test_from_bandit_high(self):
        assert Severity.from_bandit("HIGH") == Severity.HIGH
        assert Severity.from_bandit("high") == Severity.HIGH
    
    def test_from_bandit_medium(self):
        assert Severity.from_bandit("MEDIUM") == Severity.MEDIUM
    
    def test_from_bandit_low(self):
        assert Severity.from_bandit("LOW") == Severity.LOW
    
    def test_from_bandit_unknown(self):
        assert Severity.from_bandit("UNKNOWN") == Severity.MEDIUM
    
    def test_from_eslint_error(self):
        assert Severity.from_eslint(2) == Severity.HIGH
    
    def test_from_eslint_warning(self):
        assert Severity.from_eslint(1) == Severity.MEDIUM


class TestSecurityIssue:
    """Tests for SecurityIssue dataclass."""
    
    def test_to_dict(self):
        issue = SecurityIssue(
            file_path="app.py",
            line_number=10,
            severity=Severity.HIGH,
            rule_id="B101",
            message="Hardcoded password",
            code_snippet="password = 'admin'"
        )
        
        result = issue.to_dict()
        
        assert result["file"] == "app.py"
        assert result["line"] == 10
        assert result["severity"] == "HIGH"
        assert result["rule"] == "B101"
        assert result["message"] == "Hardcoded password"


class TestScanResult:
    """Tests for ScanResult dataclass."""
    
    def test_high_severity_count_empty(self):
        result = ScanResult(passed=True, issues=[])
        assert result.high_severity_count == 0
    
    def test_high_severity_count_mixed(self):
        issues = [
            SecurityIssue("a.py", 1, Severity.LOW, "B1", "msg"),
            SecurityIssue("b.py", 2, Severity.HIGH, "B2", "msg"),
            SecurityIssue("c.py", 3, Severity.CRITICAL, "B3", "msg"),
        ]
        result = ScanResult(passed=False, issues=issues)
        assert result.high_severity_count == 2
    
    def test_summary_no_issues(self):
        result = ScanResult(passed=True, issues=[])
        assert "No security issues" in result.summary
    
    def test_summary_with_issues(self):
        issues = [
            SecurityIssue("a.py", 1, Severity.HIGH, "B1", "msg"),
            SecurityIssue("b.py", 2, Severity.MEDIUM, "B2", "msg"),
        ]
        result = ScanResult(passed=False, issues=issues)
        assert "2 issues" in result.summary


class TestSecurityScannerService:
    """Tests for SecurityScannerService methods."""
    
    def test_init_default_threshold(self):
        scanner = SecurityScannerService()
        assert scanner.severity_threshold == Severity.HIGH
    
    def test_init_custom_threshold(self):
        scanner = SecurityScannerService(severity_threshold=Severity.MEDIUM)
        assert scanner.severity_threshold == Severity.MEDIUM
    
    def test_file_extensions(self):
        scanner = SecurityScannerService()
        assert '.py' in scanner.PYTHON_EXTENSIONS
        assert '.js' in scanner.JS_EXTENSIONS
        assert '.tsx' in scanner.JS_EXTENSIONS
    
    @patch('services.security_scanner.subprocess.run')
    def test_scan_python_bandit_not_installed(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        
        scanner = SecurityScannerService()
        result = scanner._scan_python("/tmp/repo", ["app.py"])
        
        assert result.passed is True
        assert "not installed" in result.error.lower()
    
    @patch('services.security_scanner.subprocess.run')
    def test_scan_python_with_issues(self, mock_run):
        bandit_output = json.dumps({
            "results": [{
                "filename": "/tmp/repo/app.py",
                "line_number": 5,
                "issue_severity": "HIGH",
                "test_id": "B105",
                "issue_text": "Possible hardcoded password",
                "code": "password = 'secret'"
            }]
        })
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=bandit_output
        )
        
        scanner = SecurityScannerService()
        result = scanner._scan_python("/tmp/repo", ["app.py"])
        
        assert len(result.issues) == 1
        assert result.issues[0].severity == Severity.HIGH
        assert result.issues[0].rule_id == "B105"
    
    @patch('services.security_scanner.subprocess.run')
    def test_scan_python_clean(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"results": []}'
        )
        
        scanner = SecurityScannerService()
        result = scanner._scan_python("/tmp/repo", ["app.py"])
        
        assert result.passed is True
        assert len(result.issues) == 0
    
    @patch('services.security_scanner.subprocess.run')
    def test_scan_javascript_with_eval(self, mock_run):
        eslint_output = json.dumps([{
            "filePath": "/tmp/repo/app.js",
            "messages": [{
                "ruleId": "no-eval",
                "severity": 2,
                "message": "eval can be harmful",
                "line": 10
            }]
        }])
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=eslint_output
        )
        
        scanner = SecurityScannerService()
        result = scanner._scan_javascript("/tmp/repo", ["app.js"])
        
        assert len(result.issues) == 1
        assert result.issues[0].rule_id == "no-eval"
    
    def test_format_issues_for_pr_no_issues(self):
        scanner = SecurityScannerService()
        result = scanner.format_issues_for_pr([])
        assert "No security issues" in result
    
    def test_format_issues_for_pr_with_issues(self):
        issues = [
            SecurityIssue("app.py", 5, Severity.HIGH, "B105", "Hardcoded password"),
            SecurityIssue("app.py", 10, Severity.MEDIUM, "B101", "Assert used"),
        ]
        
        scanner = SecurityScannerService()
        result = scanner.format_issues_for_pr(issues)
        
        assert "HIGH" in result
        assert "MEDIUM" in result
        assert "app.py:5" in result


class TestScanFilesIntegration:
    """Integration tests for scan_files method."""
    
    @patch.object(SecurityScannerService, '_scan_python')
    def test_scan_files_python(self, mock_scan):
        mock_scan.return_value = ScanResult(passed=True)
        
        scanner = SecurityScannerService()
        result = scanner.scan_files(
            repo_path="/tmp/repo",
            changed_files=["app.py", "utils.py"],
            stack_type="python"
        )
        
        assert result.passed is True
        mock_scan.assert_called_once()
    
    @patch.object(SecurityScannerService, '_scan_javascript')
    def test_scan_files_nodejs(self, mock_scan):
        mock_scan.return_value = ScanResult(passed=True)
        
        scanner = SecurityScannerService()
        result = scanner.scan_files(
            repo_path="/tmp/repo",
            changed_files=["app.js", "component.tsx"],
            stack_type="nodejs"
        )
        
        assert result.passed is True
        mock_scan.assert_called_once()
    
    def test_scan_files_unknown_stack(self):
        scanner = SecurityScannerService()
        result = scanner.scan_files(
            repo_path="/tmp/repo",
            changed_files=["main.go"],
            stack_type="go"
        )
        
        # Unknown stacks should pass (no scanner available)
        assert result.passed is True
        assert len(result.issues) == 0

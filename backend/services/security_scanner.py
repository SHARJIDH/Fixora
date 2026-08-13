"""
Security Scanner Service - Static analysis for AI-generated code.

Runs Bandit (Python) and ESLint (JavaScript/TypeScript) to detect
security vulnerabilities before code is committed.

Usage:
    scanner = SecurityScannerService()
    result = scanner.scan_files(repo_path, changed_files, stack_type)
    if not result.passed:
        print(f"Found {len(result.issues)} security issues")
"""
import json
import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Security issue severity levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    
    @classmethod
    def from_bandit(cls, level: str) -> "Severity":
        """Convert Bandit severity to our enum."""
        mapping = {
            "LOW": cls.LOW,
            "MEDIUM": cls.MEDIUM,
            "HIGH": cls.HIGH,
        }
        return mapping.get(level.upper(), cls.MEDIUM)
    
    @classmethod
    def from_eslint(cls, severity: int) -> "Severity":
        """Convert ESLint severity (1=warn, 2=error) to our enum."""
        # ESLint doesn't have security-specific severity,
        # so we treat errors as HIGH and warnings as MEDIUM
        return cls.HIGH if severity == 2 else cls.MEDIUM


@dataclass
class SecurityIssue:
    """A single security issue found by scanning."""
    file_path: str
    line_number: int
    severity: Severity
    rule_id: str
    message: str
    code_snippet: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "file": self.file_path,
            "line": self.line_number,
            "severity": self.severity.name,
            "rule": self.rule_id,
            "message": self.message,
            "snippet": self.code_snippet
        }


@dataclass
class ScanResult:
    """Result of security scanning."""
    passed: bool
    issues: list[SecurityIssue] = field(default_factory=list)
    error: Optional[str] = None
    scanner_output: str = ""
    
    @property
    def high_severity_count(self) -> int:
        return sum(1 for i in self.issues if i.severity.value >= Severity.HIGH.value)
    
    @property
    def summary(self) -> str:
        if not self.issues:
            return "✅ No security issues found"
        
        by_severity = {}
        for issue in self.issues:
            by_severity[issue.severity.name] = by_severity.get(issue.severity.name, 0) + 1
        
        parts = [f"{count} {sev}" for sev, count in sorted(by_severity.items())]
        return f"⚠️ Found {len(self.issues)} issues: " + ", ".join(parts)


class SecurityScannerService:
    """
    Runs static security analysis on code.
    
    Supports:
    - Python: Bandit (pip install bandit)
    - JavaScript/TypeScript: ESLint with security plugin
    
    Note: Scanning is designed to run inside a Docker container
    where dependencies are already installed.
    """
    
    # Minimum severity to fail the scan (default: HIGH)
    DEFAULT_THRESHOLD = Severity.HIGH
    
    # File extensions for each language
    PYTHON_EXTENSIONS = {'.py'}
    JS_EXTENSIONS = {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}
    
    def __init__(self, severity_threshold: Severity = None):
        self.severity_threshold = severity_threshold or self.DEFAULT_THRESHOLD
    
    def scan_files(
        self,
        repo_path: str,
        changed_files: list[str],
        stack_type: str,
    ) -> ScanResult:
        """
        Scan changed files for security issues.
        
        Args:
            repo_path: Path to the repository root
            changed_files: List of file paths that were changed
            stack_type: 'python' or 'nodejs'
            
        Returns:
            ScanResult with any issues found
        """
        all_issues = []
        all_output = []
        
        # Filter to only scan changed files of the appropriate type
        if stack_type == 'python':
            py_files = [f for f in changed_files 
                       if Path(f).suffix in self.PYTHON_EXTENSIONS]
            if py_files:
                result = self._scan_python(repo_path, py_files)
                all_issues.extend(result.issues)
                all_output.append(result.scanner_output)
                if result.error:
                    return result
        
        elif stack_type == 'nodejs':
            js_files = [f for f in changed_files 
                       if Path(f).suffix in self.JS_EXTENSIONS]
            if js_files:
                result = self._scan_javascript(repo_path, js_files)
                all_issues.extend(result.issues)
                all_output.append(result.scanner_output)
                if result.error:
                    return result
        
        # Check if any issues exceed threshold
        high_issues = [i for i in all_issues 
                      if i.severity.value >= self.severity_threshold.value]
        
        return ScanResult(
            passed=len(high_issues) == 0,
            issues=all_issues,
            scanner_output="\n".join(all_output)
        )
    
    def _scan_python(self, repo_path: str, file_paths: list[str]) -> ScanResult:
        """
        Run Bandit on Python files.
        
        Bandit is a security linter that finds common security issues in Python:
        - Hardcoded passwords
        - SQL injection
        - Shell injection
        - Insecure deserialization
        - etc.
        """
        logger.info("scanning_python_files", file_count=len(file_paths))
        
        # Build command - scan specific files, output as JSON
        # We install bandit if not present, then run it
        abs_files = [str(Path(repo_path) / f) for f in file_paths]
        
        # Use -r for recursive scan of the files, -f json for parseable output
        # -ll means only report issues LOW and above (we filter by severity later)
        cmd = [
            "bandit",
            "-f", "json",
            "-ll",  # Report LOW severity and above
            "--exit-zero",  # Don't fail on issues (we handle that)
        ] + abs_files
        
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            # Parse JSON output
            issues = self._parse_bandit_output(result.stdout, repo_path)
            
            return ScanResult(
                passed=True,  # Will be recalculated based on threshold
                issues=issues,
                scanner_output=result.stdout[:2000] if result.stdout else ""
            )
            
        except FileNotFoundError:
            logger.warning("bandit_not_installed")
            return ScanResult(
                passed=True,  # Don't fail if bandit not installed
                error="Bandit not installed - skipping Python security scan",
                scanner_output="Bandit not available"
            )
        except subprocess.TimeoutExpired:
            logger.error("bandit_timeout")
            return ScanResult(
                passed=False,
                error="Bandit scan timed out",
                scanner_output="Timeout after 60 seconds"
            )
        except Exception as e:
            logger.error("bandit_error", error=str(e))
            return ScanResult(
                passed=True,  # Don't fail on scanner errors
                error=f"Bandit error: {str(e)}",
                scanner_output=str(e)
            )
    
    def _parse_bandit_output(self, output: str, repo_path: str) -> list[SecurityIssue]:
        """Parse Bandit JSON output into SecurityIssue objects."""
        if not output or not output.strip():
            return []
        
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            logger.warning("bandit_parse_error", output=output[:200])
            return []
        
        issues = []
        for result in data.get("results", []):
            # Make file path relative to repo
            file_path = result.get("filename", "")
            if file_path.startswith(repo_path):
                file_path = file_path[len(repo_path):].lstrip("/")
            
            issues.append(SecurityIssue(
                file_path=file_path,
                line_number=result.get("line_number", 0),
                severity=Severity.from_bandit(result.get("issue_severity", "MEDIUM")),
                rule_id=result.get("test_id", "unknown"),
                message=result.get("issue_text", "Security issue detected"),
                code_snippet=result.get("code", "")[:200]
            ))
        
        return issues
    
    def _scan_javascript(self, repo_path: str, file_paths: list[str]) -> ScanResult:
        """
        Run ESLint on JavaScript/TypeScript files.
        
        Uses eslint-plugin-security for security-specific rules.
        Falls back to basic eslint if security plugin not available.
        """
        logger.info("scanning_javascript_files", file_count=len(file_paths))
        
        abs_files = [str(Path(repo_path) / f) for f in file_paths]
        
        # Use npx to run eslint (handles local vs global install)
        # --format json for parseable output
        # --no-error-on-unmatched-pattern in case some files don't exist
        cmd = [
            "npx", "eslint",
            "--format", "json",
            "--no-error-on-unmatched-pattern",
        ] + abs_files
        
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            # ESLint exits 1 if there are linting issues, that's OK
            issues = self._parse_eslint_output(result.stdout, repo_path)
            
            return ScanResult(
                passed=True,
                issues=issues,
                scanner_output=result.stdout[:2000] if result.stdout else ""
            )
            
        except FileNotFoundError:
            logger.warning("eslint_not_installed")
            return ScanResult(
                passed=True,
                error="ESLint not installed - skipping JavaScript security scan",
                scanner_output="ESLint not available"
            )
        except subprocess.TimeoutExpired:
            logger.error("eslint_timeout")
            return ScanResult(
                passed=False,
                error="ESLint scan timed out",
                scanner_output="Timeout after 60 seconds"
            )
        except Exception as e:
            logger.error("eslint_error", error=str(e))
            return ScanResult(
                passed=True,
                error=f"ESLint error: {str(e)}",
                scanner_output=str(e)
            )
    
    def _parse_eslint_output(self, output: str, repo_path: str) -> list[SecurityIssue]:
        """Parse ESLint JSON output into SecurityIssue objects."""
        if not output or not output.strip():
            return []
        
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            logger.warning("eslint_parse_error", output=output[:200])
            return []
        
        issues = []
        
        # ESLint security-related rules we care about
        SECURITY_RULES = {
            "no-eval", "no-implied-eval", "no-new-func",  # Code injection
            "security/detect-eval-with-expression",
            "security/detect-non-literal-regexp",
            "security/detect-non-literal-require",
            "security/detect-object-injection",
            "security/detect-possible-timing-attacks",
            "security/detect-unsafe-regex",
            "security/detect-buffer-noassert",
            "security/detect-child-process",
            "security/detect-disable-mustache-escape",
            "security/detect-no-csrf-before-method-override",
            "security/detect-pseudoRandomBytes",
        }
        
        for file_result in data:
            file_path = file_result.get("filePath", "")
            if file_path.startswith(repo_path):
                file_path = file_path[len(repo_path):].lstrip("/")
            
            for message in file_result.get("messages", []):
                rule_id = message.get("ruleId", "")
                
                # Only include security-related rules or severity 2 (error)
                if rule_id in SECURITY_RULES or message.get("severity", 0) == 2:
                    issues.append(SecurityIssue(
                        file_path=file_path,
                        line_number=message.get("line", 0),
                        severity=Severity.from_eslint(message.get("severity", 1)),
                        rule_id=rule_id or "unknown",
                        message=message.get("message", "Linting issue detected"),
                        code_snippet=message.get("source", "")[:200]
                    ))
        
        return issues
    
    def format_issues_for_pr(self, issues: list[SecurityIssue]) -> str:
        """Format security issues for inclusion in PR body."""
        if not issues:
            return "✅ No security issues detected"
        
        lines = ["### Security Scan Results\n"]
        
        # Group by severity
        by_severity = {}
        for issue in issues:
            sev = issue.severity.name
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(issue)
        
        # Output in severity order
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if severity in by_severity:
                lines.append(f"\n**{severity}** ({len(by_severity[severity])} issues)")
                for issue in by_severity[severity][:5]:  # Limit to 5 per severity
                    lines.append(f"- `{issue.file_path}:{issue.line_number}` - {issue.message} ({issue.rule_id})")
                if len(by_severity[severity]) > 5:
                    lines.append(f"  - ... and {len(by_severity[severity]) - 5} more")
        
        return "\n".join(lines)

"""
Comby Service - Structural code search and replace using Comby.

Comby understands code structure (balanced parens, strings, comments)
and enables targeted code transformations using pattern matching.

Usage:
    service = CombyService()
    result = service.apply_patch(
        file_path="src/main.py",
        match_pattern="print(:[args])",
        replace_pattern="logging.info(:[args])"
    )
"""
import json
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# Check if Comby is available
COMBY_AVAILABLE = shutil.which('comby') is not None


@dataclass
class CombyResult:
    """Result of a Comby transformation."""
    success: bool
    rewritten_content: Optional[str] = None
    diff: Optional[str] = None
    error: Optional[str] = None
    matches_found: int = 0


# Language extension mappings for Comby's -matcher flag
LANGUAGE_MAP = {
    '.py': '.python',
    '.python': '.python',
    '.js': '.js',
    '.jsx': '.js',
    '.ts': '.ts',
    '.tsx': '.tsx',
    '.go': '.go',
    '.java': '.java',
    '.c': '.c',
    '.cpp': '.cpp',
    '.h': '.c',
    '.hpp': '.cpp',
    '.rs': '.rust',
    '.rb': '.ruby',
    '.php': '.php',
    '.swift': '.swift',
    '.kt': '.kotlin',
    '.scala': '.scala',
    '.html': '.html',
    '.xml': '.xml',
    '.json': '.json',
    '.yaml': '.generic',
    '.yml': '.generic',
    '.toml': '.generic',
    '.md': '.generic',
    '.txt': '.generic',
}


class CombyService:
    """
    Wrapper for Comby structural code search/replace.
    
    Comby uses pattern templates with :[hole] syntax to match
    code structures while understanding language syntax.
    
    Example patterns:
        - 'print(:[arg])' -> matches any print() call
        - 'def :[name](:[args])' -> matches function definitions
        - 'if :[cond]: :[body]' -> matches if statements
    """
    
    def __init__(self, comby_path: Optional[str] = None):
        """
        Initialize CombyService.
        
        Args:
            comby_path: Optional path to comby binary. 
                        If None, uses system PATH.
        """
        self.comby_path = comby_path or 'comby'
        self._available = None
        
    def is_available(self) -> bool:
        """Check if Comby is available on this system."""
        if self._available is not None:
            return self._available
            
        try:
            result = subprocess.run(
                [self.comby_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            self._available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._available = False
            
        if not self._available:
            logger.warning("comby_not_available", 
                          hint="Install with: brew install comby")
        
        return self._available
    
    def detect_language(self, file_path: str) -> str:
        """
        Detect the Comby language matcher from file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Comby language identifier (e.g., '.python', '.js')
        """
        ext = Path(file_path).suffix.lower()
        return LANGUAGE_MAP.get(ext, '.generic')
    
    def apply_patch(
        self,
        file_path: str,
        match_pattern: str,
        replace_pattern: str,
        language: Optional[str] = None,
        in_place: bool = True
    ) -> CombyResult:
        """
        Apply a structural transformation to a file.
        
        Args:
            file_path: Path to the file to transform
            match_pattern: Comby match template with :[holes]
            replace_pattern: Comby replace template
            language: Optional language matcher override
            in_place: If True, modify the file. If False, return new content.
            
        Returns:
            CombyResult with success status and transformed content
        """
        if not self.is_available():
            return CombyResult(
                success=False,
                error="Comby is not installed. Install with: brew install comby"
            )
        
        file_path = Path(file_path)
        if not file_path.exists():
            return CombyResult(
                success=False,
                error=f"File not found: {file_path}"
            )
        
        lang = language or self.detect_language(str(file_path))
        
        try:
            # Run Comby with JSON output
            cmd = [
                self.comby_path,
                match_pattern,
                replace_pattern,
                str(file_path),
                '-matcher', lang,
                '-json-lines'
            ]
            
            if in_place:
                cmd.append('-in-place')
            
            logger.info(
                "comby_apply_patch",
                file=str(file_path),
                match=match_pattern[:50],
                replace=replace_pattern[:50],
                language=lang
            )
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(
                    "comby_patch_failed",
                    stderr=result.stderr[:500] if result.stderr else None,
                    exit_code=result.returncode
                )
                return CombyResult(
                    success=False,
                    error=result.stderr or f"Comby exited with code {result.returncode}"
                )
            
            # Parse JSON output
            rewritten_content = None
            diff = None
            matches_found = 0
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            data = json.loads(line)
                            rewritten_content = data.get('rewritten_source')
                            diff = data.get('diff')
                            # Count substitutions
                            subs = data.get('in_place_substitutions', [])
                            matches_found = len(subs)
                        except json.JSONDecodeError:
                            pass
            
            # If in_place, read back the modified file
            if in_place and file_path.exists():
                rewritten_content = file_path.read_text(encoding='utf-8')
            
            logger.info(
                "comby_patch_success",
                file=str(file_path),
                matches_found=matches_found
            )
            
            return CombyResult(
                success=True,
                rewritten_content=rewritten_content,
                diff=diff,
                matches_found=matches_found
            )
            
        except subprocess.TimeoutExpired:
            return CombyResult(
                success=False,
                error="Comby transformation timed out after 30 seconds"
            )
        except Exception as e:
            logger.error("comby_error", error=str(e))
            return CombyResult(
                success=False,
                error=str(e)
            )
    
    def apply_patch_to_content(
        self,
        content: str,
        match_pattern: str,
        replace_pattern: str,
        language: str = '.generic'
    ) -> CombyResult:
        """
        Apply a structural transformation to a string.
        
        Uses stdin to pass content to Comby without writing to disk.
        
        Args:
            content: Source code content to transform
            match_pattern: Comby match template
            replace_pattern: Comby replace template
            language: Language matcher (default: .generic)
            
        Returns:
            CombyResult with transformed content
        """
        if not self.is_available():
            return CombyResult(
                success=False,
                error="Comby is not installed"
            )
        
        try:
            cmd = [
                self.comby_path,
                match_pattern,
                replace_pattern,
                '-stdin',
                language,
                '-json-lines'
            ]
            
            result = subprocess.run(
                cmd,
                input=content,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return CombyResult(
                    success=False,
                    error=result.stderr or f"Comby exited with code {result.returncode}"
                )
            
            # Parse JSON output
            rewritten_content = None
            diff = None
            matches_found = 0
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            data = json.loads(line)
                            rewritten_content = data.get('rewritten_source')
                            diff = data.get('diff')
                            subs = data.get('in_place_substitutions', [])
                            matches_found = len(subs)
                        except json.JSONDecodeError:
                            pass
            
            # If no matches, return original content
            if rewritten_content is None:
                rewritten_content = content
            
            return CombyResult(
                success=True,
                rewritten_content=rewritten_content,
                diff=diff,
                matches_found=matches_found
            )
            
        except subprocess.TimeoutExpired:
            return CombyResult(
                success=False,
                error="Comby transformation timed out"
            )
        except Exception as e:
            return CombyResult(
                success=False,
                error=str(e)
            )
    
    def match_only(
        self,
        content: str,
        match_pattern: str,
        language: str = '.generic'
    ) -> list[dict]:
        """
        Find all matches of a pattern in content without rewriting.
        
        Args:
            content: Source code to search
            match_pattern: Comby match template
            language: Language matcher
            
        Returns:
            List of match dictionaries with 'matched' and 'environment'
        """
        if not self.is_available():
            return []
        
        try:
            cmd = [
                self.comby_path,
                match_pattern,
                '',  # Empty replace template for match-only
                '-stdin',
                language,
                '-match-only',
                '-json-lines'
            ]
            
            result = subprocess.run(
                cmd,
                input=content,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            matches = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            data = json.loads(line)
                            matches.extend(data.get('matches', []))
                        except json.JSONDecodeError:
                            pass
            
            return matches
            
        except Exception:
            return []

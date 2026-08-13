"""
Tests for Docker detection in StackDetectorService.
"""
import pytest
from services.stack_detector import StackDetectorService, STACK_CONFIGS


class TestDockerDetection:
    def setup_method(self):
        self.detector = StackDetectorService()

    def test_detect_root_dockerfile(self):
        """Should detect Dockerfile in project root."""
        files = ['Dockerfile', 'package.json', 'src/index.js']
        result = self.detector.detect_from_file_list(files)
        
        assert result is not None
        assert result.dockerfile_path == 'Dockerfile'
        assert result.stack_type == 'nodejs'

    def test_detect_nested_dockerfile(self):
        """Should prefer root-level Dockerfile over nested."""
        files = [
            'docker/Dockerfile',
            'Dockerfile',
            'requirements.txt',
        ]
        result = self.detector.detect_from_file_list(files)
        
        assert result is not None
        assert result.dockerfile_path == 'Dockerfile'

    def test_detect_only_nested_dockerfile(self):
        """Should find nested Dockerfile if no root one exists."""
        files = [
            'docker/Dockerfile',
            'requirements.txt',
        ]
        result = self.detector.detect_from_file_list(files)
        
        assert result is not None
        assert result.dockerfile_path == 'docker/Dockerfile'

    def test_detect_docker_compose(self):
        """Should detect docker-compose.yml."""
        files = ['docker-compose.yml', 'package.json', 'src/app.js']
        result = self.detector.detect_from_file_list(files)
        
        assert result is not None
        assert result.docker_compose_path == 'docker-compose.yml'

    def test_detect_compose_yaml(self):
        """Should detect compose.yaml (new naming)."""
        files = ['compose.yaml', 'requirements.txt']
        result = self.detector.detect_from_file_list(files)
        
        assert result is not None
        assert result.docker_compose_path == 'compose.yaml'

    def test_detect_devcontainer_dockerfile(self):
        """Should detect .devcontainer Dockerfile."""
        files = [
            '.devcontainer/Dockerfile',
            '.devcontainer/devcontainer.json',
            'pyproject.toml',
        ]
        result = self.detector.detect_from_file_list(files)
        
        assert result is not None
        assert '.devcontainer' in result.dockerfile_path

    def test_has_docker_config_true(self):
        """has_docker_config should return True when Docker files exist."""
        files = ['Dockerfile', 'package.json']
        assert self.detector.has_docker_config(files) is True

    def test_has_docker_config_false(self):
        """has_docker_config should return False when no Docker files."""
        files = ['package.json', 'src/index.js']
        assert self.detector.has_docker_config(files) is False

    def test_no_dockerfile_uses_stack_runtime(self):
        """Should use stack runtime when no Dockerfile exists."""
        files = ['requirements.txt', 'src/main.py']
        result = self.detector.detect_from_file_list(files)
        
        assert result is not None
        assert result.dockerfile_path is None
        assert result.runtime == 'python:3.11-slim'

    def test_both_dockerfile_and_compose(self):
        """Should detect both Dockerfile and docker-compose."""
        files = [
            'Dockerfile',
            'docker-compose.yml',
            'package.json',
        ]
        result = self.detector.detect_from_file_list(files)
        
        assert result is not None
        assert result.dockerfile_path == 'Dockerfile'
        assert result.docker_compose_path == 'docker-compose.yml'

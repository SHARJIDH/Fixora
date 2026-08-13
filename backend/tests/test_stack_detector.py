import pytest
from services.stack_detector import StackDetectorService, STACK_CONFIGS


class TestStackDetectorService:
    def setup_method(self):
        self.detector = StackDetectorService()

    def test_detect_python_requirements(self):
        files = ['src/main.py', 'requirements.txt', 'README.md']
        result = self.detector.detect_from_file_list(files)
        assert result is not None
        assert result.stack_type == 'python'
        assert result.package_manager == 'pip'

    def test_detect_python_poetry(self):
        files = ['src/main.py', 'pyproject.toml', 'poetry.lock']
        result = self.detector.detect_from_file_list(files)
        assert result is not None
        assert result.stack_type == 'python'
        assert result.package_manager == 'poetry'

    def test_detect_nodejs_npm(self):
        files = ['src/index.js', 'package.json', 'package-lock.json']
        result = self.detector.detect_from_file_list(files)
        assert result is not None
        assert result.stack_type == 'nodejs'
        assert result.package_manager == 'npm'

    def test_detect_nodejs_yarn(self):
        files = ['src/index.ts', 'package.json', 'yarn.lock']
        result = self.detector.detect_from_file_list(files)
        assert result is not None
        assert result.stack_type == 'nodejs'
        assert result.package_manager == 'yarn'

    def test_detect_nodejs_pnpm(self):
        files = ['src/index.ts', 'package.json', 'pnpm-lock.yaml']
        result = self.detector.detect_from_file_list(files)
        assert result is not None
        assert result.stack_type == 'nodejs'
        assert result.package_manager == 'pnpm'

    def test_detect_unknown_stack(self):
        files = ['README.md', 'LICENSE', '.gitignore']
        result = self.detector.detect_from_file_list(files)
        assert result is None

    def test_nodejs_priority_over_python(self):
        files = ['package.json', 'requirements.txt']
        result = self.detector.detect_from_file_list(files)
        assert result is not None
        assert result.stack_type == 'nodejs'

    def test_poetry_priority_over_requirements(self):
        files = ['pyproject.toml', 'requirements.txt']
        result = self.detector.detect_from_file_list(files)
        assert result is not None
        assert result.package_manager == 'poetry'

    def test_nested_file_paths(self):
        files = ['backend/src/main.py', 'backend/requirements.txt', 'frontend/package.json']
        result = self.detector.detect_from_file_list(files)
        assert result is not None
        assert result.project_root == 'frontend'


class TestStackConfigs:
    def test_python_config(self):
        config = STACK_CONFIGS['python']
        assert 'python' in config.runtime
        assert config.test_command == 'pytest'

    def test_nodejs_config(self):
        config = STACK_CONFIGS['nodejs-npm']
        assert 'node' in config.runtime
        assert config.test_command == 'npm test'

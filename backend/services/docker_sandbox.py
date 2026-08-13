"""
Docker Sandbox Service - Manages container lifecycle for code validation.

Supports two image resolution strategies:
1. Use project's Dockerfile if available (faster, correct dependencies)
2. Fall back to generic stack-based images (Python, Node.js)
"""
import logging
import tempfile
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import docker
    from docker.models.containers import Container
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    Container = None

from services.stack_detector import StackConfig

logger = logging.getLogger(__name__)


@dataclass
class ExecResult:
    """Result of executing a command in a container."""
    exit_code: int
    stdout: str
    stderr: str
    
    @property
    def success(self) -> bool:
        return self.exit_code == 0


@dataclass
class SandboxConfig:
    """Configuration for sandbox container resource limits."""
    memory_limit: str = "1g"
    cpu_period: int = 100000
    cpu_quota: int = 50000  # 50% of one CPU
    network_disabled: bool = True
    timeout_seconds: int = 300  # 5 minutes


class DockerSandboxService:
    """Manages Docker containers for running code validation."""
    
    DEFAULT_CONFIG = SandboxConfig()
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        if not DOCKER_AVAILABLE:
            raise RuntimeError(
                "Docker SDK not available. Install with: pip install docker"
            )
        
        self.config = config or self.DEFAULT_CONFIG
        self._client = None
    
    @property
    def client(self):
        """Lazy-load Docker client."""
        if self._client is None:
            self._client = docker.from_env()
        return self._client
    
    def resolve_image(
        self, 
        stack_config: StackConfig, 
        repo_path: str
    ) -> str:
        """
        Determine which Docker image to use for the sandbox.
        
        Priority:
        1. Build from project's Dockerfile if available
        2. Use generic stack-based image
        """
        if stack_config.dockerfile_path:
            return self._build_project_image(repo_path, stack_config.dockerfile_path)
        
        return stack_config.runtime
    
    def _build_project_image(self, repo_path: str, dockerfile_path: str) -> str:
        """Build Docker image from project's Dockerfile."""
        import hashlib
        import time
        
        # Generate unique image tag based on repo and timestamp
        repo_hash = hashlib.md5(repo_path.encode()).hexdigest()[:8]
        timestamp = int(time.time())
        image_tag = f"sandbox-{repo_hash}-{timestamp}"
        
        # Determine build context (directory containing Dockerfile)
        dockerfile_full_path = Path(repo_path) / dockerfile_path
        build_context = str(dockerfile_full_path.parent)
        dockerfile_name = dockerfile_full_path.name
        
        logger.info(f"Building image from {dockerfile_path}")
        
        try:
            image, build_logs = self.client.images.build(
                path=build_context,
                dockerfile=dockerfile_name,
                tag=image_tag,
                rm=True,  # Remove intermediate containers
                forcerm=True,  # Always remove intermediate containers
            )
            
            for log in build_logs:
                if 'stream' in log:
                    logger.debug(log['stream'].strip())
            
            return image_tag
            
        except Exception as e:
            logger.warning(f"Failed to build project image: {e}")
            logger.info("Falling back to stack-based image")
            raise
    
    def create_container(
        self, 
        image: str, 
        repo_path: str,
        working_dir: str = "/workspace",
        network_enabled: bool = True  # Enable network by default for install
    ) -> Container:
        """
        Create a container with the repo mounted and security limits applied.
        
        Args:
            image: Docker image to use
            repo_path: Path to the repository to mount
            working_dir: Working directory inside the container
            network_enabled: Whether to enable network access (needed for installs)
        """
        container = self.client.containers.create(
            image=image,
            command="tail -f /dev/null",  # Keep container running
            volumes={
                repo_path: {"bind": working_dir, "mode": "rw"}
            },
            working_dir=working_dir,
            mem_limit=self.config.memory_limit,
            cpu_period=self.config.cpu_period,
            cpu_quota=self.config.cpu_quota,
            network_disabled=not network_enabled,  # Invert: network_enabled=True means network_disabled=False
            detach=True,
        )
        
        container.start()
        logger.info(f"Created container {container.short_id} with image {image}")
        
        return container
    
    def exec_command(
        self, 
        container: Container, 
        command: str,
        timeout: Optional[int] = None
    ) -> ExecResult:
        """
        Execute a command inside the container.
        """
        timeout = timeout or self.config.timeout_seconds
        
        logger.debug(f"Executing in {container.short_id}: {command}")
        
        try:
            exec_result = container.exec_run(
                cmd=["sh", "-c", command],
                demux=True,  # Separate stdout and stderr
            )
            
            stdout = exec_result.output[0] or b""
            stderr = exec_result.output[1] or b""
            
            return ExecResult(
                exit_code=exec_result.exit_code,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
            )
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return ExecResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
            )
    
    def cleanup(self, container: Container) -> None:
        """Stop and remove the container."""
        try:
            container.stop(timeout=5)
            container.remove(force=True)
            logger.info(f"Cleaned up container {container.short_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup container: {e}")
    
    def cleanup_image(self, image_tag: str) -> None:
        """Remove a built image (for project-specific images)."""
        if image_tag.startswith("sandbox-"):
            try:
                self.client.images.remove(image_tag, force=True)
                logger.info(f"Removed image {image_tag}")
            except Exception as e:
                logger.warning(f"Failed to remove image {image_tag}: {e}")
    
    def is_available(self) -> bool:
        """Check if Docker is available and running."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False

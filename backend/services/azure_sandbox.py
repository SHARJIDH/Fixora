"""
Azure Sandbox Service - Run code validation in Azure Container Instances.

Flow:
1. Zip code files and upload to Azure Blob Storage
2. Generate short-lived SAS URL for download
3. Start Azure Container Instance with install/test commands
4. Wait for completion and fetch logs
5. Return result and cleanup resources
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AzureConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str
    resource_group: str
    location: str
    execution_mode: str = "aci"
    storage_account: str = ""
    storage_container: str = "jobs"
    container_image: str = ""
    aci_cpu: float = 2.0
    aci_memory_gb: float = 4.0
    task_timeout_seconds: int = 900
    name_prefix: str = "fixora"
    subnet_id: str = ""

    @classmethod
    def from_env(cls) -> "AzureConfig":
        return cls(
            tenant_id=os.environ.get("AZURE_TENANT_ID", ""),
            client_id=os.environ.get("AZURE_CLIENT_ID", ""),
            client_secret=os.environ.get("AZURE_CLIENT_SECRET", ""),
            subscription_id=os.environ.get("AZURE_SUBSCRIPTION_ID", ""),
            resource_group=os.environ.get("AZURE_RESOURCE_GROUP", ""),
            location=os.environ.get("AZURE_LOCATION", ""),
            execution_mode=os.environ.get("AZURE_EXECUTION_MODE", "aci").lower(),
            storage_account=os.environ.get("AZURE_STORAGE_ACCOUNT", ""),
            storage_container=os.environ.get("AZURE_STORAGE_CONTAINER", "jobs"),
            container_image=os.environ.get("AZURE_CONTAINER_IMAGE", ""),
            aci_cpu=float(os.environ.get("AZURE_ACI_CPU", "2")),
            aci_memory_gb=float(os.environ.get("AZURE_ACI_MEMORY_GB", "4")),
            task_timeout_seconds=int(os.environ.get("AZURE_ACI_TIMEOUT_SECONDS", "900")),
            name_prefix=os.environ.get("AZURE_NAME_PREFIX", "fixora"),
            subnet_id=os.environ.get("AZURE_VNET_SUBNET_ID", ""),
        )

    def is_configured(self) -> bool:
        required = [
            self.tenant_id,
            self.client_id,
            self.client_secret,
            self.subscription_id,
            self.resource_group,
            self.location,
            self.storage_account,
            self.storage_container,
            self.container_image,
        ]
        return all(bool(v) for v in required) and self.execution_mode in {"aci", "containerapps"}


@dataclass
class AzureRunResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    container_name: Optional[str] = None
    duration_seconds: float = 0.0


class AzureSandboxService:
    def __init__(self, config: Optional[AzureConfig] = None):
        self.config = config or AzureConfig.from_env()
        self._account_key: Optional[str] = None
        self._logged_in = False

        if not self.config.is_configured():
            raise RuntimeError("Azure sandbox is not fully configured")

        if not shutil.which("az"):
            raise RuntimeError("Azure CLI not found. Install Azure CLI to use Azure sandbox")

    def _run_az(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        cmd = ["az", *args]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if check and result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Azure CLI command failed")
        return result

    def _ensure_login(self) -> None:
        if self._logged_in:
            return

        probe = self._run_az(["account", "show", "-o", "none"], check=False)
        if probe.returncode != 0:
            self._run_az([
                "login",
                "--service-principal",
                "--username", self.config.client_id,
                "--password", self.config.client_secret,
                "--tenant", self.config.tenant_id,
                "-o", "none",
            ])

        self._run_az(["account", "set", "--subscription", self.config.subscription_id, "-o", "none"])
        self._logged_in = True

    def _get_storage_account_key(self) -> str:
        if self._account_key:
            return self._account_key

        self._ensure_login()
        result = self._run_az([
            "storage", "account", "keys", "list",
            "--resource-group", self.config.resource_group,
            "--account-name", self.config.storage_account,
            "--query", "[0].value",
            "-o", "tsv",
        ])
        key = result.stdout.strip()
        if not key:
            raise RuntimeError("Could not retrieve Azure Storage account key")

        self._account_key = key
        return key

    def _upload_code_zip(self, code_files: list[dict], blob_name: str) -> str:
        account_key = self._get_storage_account_key()

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
            zip_path = temp_zip.name

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in code_files:
                    zf.writestr(file["path"], file["content"])

            self._run_az([
                "storage", "blob", "upload",
                "--account-name", self.config.storage_account,
                "--account-key", account_key,
                "--container-name", self.config.storage_container,
                "--name", blob_name,
                "--file", zip_path,
                "--overwrite", "true",
                "-o", "none",
            ])

            expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%MZ")
            sas = self._run_az([
                "storage", "blob", "generate-sas",
                "--account-name", self.config.storage_account,
                "--account-key", account_key,
                "--container-name", self.config.storage_container,
                "--name", blob_name,
                "--permissions", "r",
                "--https-only",
                "--expiry", expiry,
                "-o", "tsv",
            ]).stdout.strip()

            if not sas:
                raise RuntimeError("Failed to generate SAS for code bundle")

            return (
                f"https://{self.config.storage_account}.blob.core.windows.net/"
                f"{self.config.storage_container}/{blob_name}?{sas}"
            )
        finally:
            try:
                os.unlink(zip_path)
            except OSError:
                pass

    def _delete_blob(self, blob_name: str) -> None:
        try:
            account_key = self._get_storage_account_key()
            self._run_az([
                "storage", "blob", "delete",
                "--account-name", self.config.storage_account,
                "--account-key", account_key,
                "--container-name", self.config.storage_container,
                "--name", blob_name,
                "-o", "none",
            ], check=False)
        except Exception:
            pass

    def is_available(self) -> bool:
        if not self.config.is_configured():
            return False

        try:
            self._ensure_login()
            rg_probe = self._run_az([
                "group", "exists", "--name", self.config.resource_group, "-o", "tsv"
            ], check=False)
            return rg_probe.returncode == 0 and rg_probe.stdout.strip().lower() == "true"
        except Exception as e:
            logger.warning("azure_not_available", error=str(e))
            return False

    def run_validation(
        self,
        code_files: list[dict],
        stack_type: str,
        install_command: str,
        test_command: str,
    ) -> AzureRunResult:
        self._ensure_login()

        if self.config.execution_mode != "aci":
            return AzureRunResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=(
                    "Only AZURE_EXECUTION_MODE=aci is currently implemented. "
                    "Set AZURE_EXECUTION_MODE=aci to use Azure sandbox."
                ),
            )

        start = time.time()
        run_id = uuid.uuid4().hex[:10]
        container_name = f"{self.config.name_prefix}-job-{run_id}".lower()[:63]
        blob_name = f"jobs/{run_id}/code.zip"

        code_url = self._upload_code_zip(code_files, blob_name)

        bootstrap_script = """set -e
mkdir -p /workspace
curl -fsSL \"$CODE_ZIP_URL\" -o /tmp/code.zip
unzip -o /tmp/code.zip -d /workspace >/dev/null
cd /workspace
echo '=== Installing dependencies ==='
sh -c \"$INSTALL_COMMAND\" 2>&1 || echo 'WARNING: install command had issues'
echo '=== Running tests ==='
sh -c \"$TEST_COMMAND\"
"""

        create_cmd = [
            "container", "create",
            "--resource-group", self.config.resource_group,
            "--name", container_name,
            "--location", self.config.location,
            "--image", self.config.container_image,
            "--restart-policy", "Never",
            "--cpu", str(self.config.aci_cpu),
            "--memory", str(self.config.aci_memory_gb),
            "--environment-variables",
            f"CODE_ZIP_URL={code_url}",
            f"INSTALL_COMMAND={install_command}",
            f"TEST_COMMAND={test_command}",
            "--command-line", "/bin/sh -c \"$BOOTSTRAP_SCRIPT\"",
            "--secure-environment-variables",
            f"BOOTSTRAP_SCRIPT={bootstrap_script}",
            "-o", "none",
        ]

        if self.config.subnet_id:
            create_cmd.extend(["--subnet", self.config.subnet_id])

        try:
            self._run_az(create_cmd)

            deadline = time.time() + self.config.task_timeout_seconds
            state = ""
            while time.time() < deadline:
                state = self._run_az([
                    "container", "show",
                    "--resource-group", self.config.resource_group,
                    "--name", container_name,
                    "--query", "instanceView.state",
                    "-o", "tsv",
                ]).stdout.strip()

                if state in {"Succeeded", "Failed", "Terminated", "Stopped"}:
                    break
                time.sleep(5)

            if state not in {"Succeeded", "Failed", "Terminated", "Stopped"}:
                self._run_az([
                    "container", "delete",
                    "--resource-group", self.config.resource_group,
                    "--name", container_name,
                    "--yes",
                    "-o", "none",
                ], check=False)
                return AzureRunResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Azure ACI task timed out after {self.config.task_timeout_seconds}s",
                    container_name=container_name,
                    duration_seconds=time.time() - start,
                )

            logs = self._run_az([
                "container", "logs",
                "--resource-group", self.config.resource_group,
                "--name", container_name,
                "-o", "tsv",
            ], check=False).stdout

            exit_code_raw = self._run_az([
                "container", "show",
                "--resource-group", self.config.resource_group,
                "--name", container_name,
                "--query", "containers[0].instanceView.currentState.exitCode",
                "-o", "tsv",
            ], check=False).stdout.strip()

            try:
                exit_code = int(exit_code_raw)
            except (TypeError, ValueError):
                exit_code = 0 if state == "Succeeded" else 1

            return AzureRunResult(
                success=exit_code == 0,
                exit_code=exit_code,
                stdout=logs,
                stderr="" if exit_code == 0 else f"Azure ACI execution failed with state={state}",
                container_name=container_name,
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            logger.error("azure_validation_failed", error=str(e), container=container_name)
            return AzureRunResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Azure sandbox error: {str(e)}",
                container_name=container_name,
                duration_seconds=time.time() - start,
            )
        finally:
            self._run_az([
                "container", "delete",
                "--resource-group", self.config.resource_group,
                "--name", container_name,
                "--yes",
                "-o", "none",
            ], check=False)
            self._delete_blob(blob_name)

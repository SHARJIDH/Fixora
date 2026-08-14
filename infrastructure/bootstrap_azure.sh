#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: $ENV_FILE not found"
  exit 1
fi

if ! command -v az >/dev/null 2>&1; then
  echo "Error: Azure CLI (az) is not installed. Install it first: https://learn.microsoft.com/cli/azure/install-azure-cli"
  exit 1
fi

# Load env values from .env
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Error: Required variable '$name' is missing in .env"
    exit 1
  fi
}

upsert_env() {
  local key="$1"
  local value="$2"

  if grep -qE "^${key}=" "$ENV_FILE"; then
    # macOS-compatible in-place update
    sed -i '' -E "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi
}

random_suffix() {
  # 6 lowercase hex chars
  openssl rand -hex 3 2>/dev/null || date +%s | md5 | cut -c1-6
}

require_var AZURE_TENANT_ID
require_var AZURE_CLIENT_ID
require_var AZURE_CLIENT_SECRET
require_var AZURE_SUBSCRIPTION_ID
require_var AZURE_RESOURCE_GROUP
require_var AZURE_LOCATION
require_var AZURE_EXECUTION_MODE

# Normalize potential CRLF line endings from .env values.
AZURE_TENANT_ID="${AZURE_TENANT_ID//$'\r'/}"
AZURE_CLIENT_ID="${AZURE_CLIENT_ID//$'\r'/}"
AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET//$'\r'/}"
AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID//$'\r'/}"
AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP//$'\r'/}"
AZURE_LOCATION="${AZURE_LOCATION//$'\r'/}"
AZURE_EXECUTION_MODE="${AZURE_EXECUTION_MODE//$'\r'/}"

AZURE_NAME_PREFIX="${AZURE_NAME_PREFIX:-fixora}"
AZURE_STORAGE_CONTAINER="${AZURE_STORAGE_CONTAINER:-jobs}"
AZURE_ACI_CPU="${AZURE_ACI_CPU:-0.5}"
AZURE_ACI_MEMORY_GB="${AZURE_ACI_MEMORY_GB:-1}"
AZURE_ACI_TIMEOUT_SECONDS="${AZURE_ACI_TIMEOUT_SECONDS:-300}"
AZURE_ENABLE_LOG_ANALYTICS="${AZURE_ENABLE_LOG_ANALYTICS:-false}"

if [[ "$AZURE_EXECUTION_MODE" != "aci" && "$AZURE_EXECUTION_MODE" != "containerapps" ]]; then
  echo "Error: AZURE_EXECUTION_MODE must be one of: aci | containerapps"
  exit 1
fi

echo "Authenticating with service principal..."
# Clear cached account context to avoid stale/subscription mismatch between user and SP sessions.
az account clear >/dev/null 2>&1 || true

az login --service-principal \
  --username "$AZURE_CLIENT_ID" \
  --password "$AZURE_CLIENT_SECRET" \
  --tenant "$AZURE_TENANT_ID" >/dev/null

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

ACTIVE_SUB="$(az account show --query id -o tsv 2>/dev/null || true)"
if [[ "$ACTIVE_SUB" != "$AZURE_SUBSCRIPTION_ID" ]]; then
  echo "Error: Active Azure subscription '$ACTIVE_SUB' does not match requested '$AZURE_SUBSCRIPTION_ID'"
  echo "Check that your service principal has access to this subscription."
  exit 1
fi

echo "Ensuring resource group exists: $AZURE_RESOURCE_GROUP"
az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION" >/dev/null

# Storage account (globally unique name, 3-24 chars lowercase alnum)
if [[ -z "${AZURE_STORAGE_ACCOUNT:-}" ]]; then
  base="$(echo "${AZURE_NAME_PREFIX}sa" | tr -cd 'a-z0-9' | cut -c1-14)"
  for _ in {1..20}; do
    candidate="${base}$(random_suffix)"
    available="$(az storage account check-name --name "$candidate" --query nameAvailable -o tsv)"
    if [[ "$available" == "true" ]]; then
      AZURE_STORAGE_ACCOUNT="$candidate"
      break
    fi
  done
fi

if [[ -z "${AZURE_STORAGE_ACCOUNT:-}" ]]; then
  echo "Error: Could not generate available storage account name. Set AZURE_STORAGE_ACCOUNT manually in .env"
  exit 1
fi

echo "Ensuring storage account exists: $AZURE_STORAGE_ACCOUNT"
if ! az storage account show --name "$AZURE_STORAGE_ACCOUNT" --resource-group "$AZURE_RESOURCE_GROUP" >/dev/null 2>&1; then
  az storage account create \
    --name "$AZURE_STORAGE_ACCOUNT" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --location "$AZURE_LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --allow-blob-public-access false >/dev/null
fi

STORAGE_KEY="$(az storage account keys list --resource-group "$AZURE_RESOURCE_GROUP" --account-name "$AZURE_STORAGE_ACCOUNT" --query '[0].value' -o tsv)"

echo "Ensuring blob container exists: $AZURE_STORAGE_CONTAINER"
az storage container create \
  --name "$AZURE_STORAGE_CONTAINER" \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --account-key "$STORAGE_KEY" >/dev/null

# ACR
if [[ -z "${AZURE_ACR_NAME:-}" ]]; then
  AZURE_ACR_NAME="$(echo "${AZURE_NAME_PREFIX}acr$(random_suffix)" | tr -cd 'a-z0-9' | cut -c1-50)"
fi

echo "Ensuring Azure Container Registry exists: $AZURE_ACR_NAME"
if ! az acr show --name "$AZURE_ACR_NAME" --resource-group "$AZURE_RESOURCE_GROUP" >/dev/null 2>&1; then
  az acr create \
    --name "$AZURE_ACR_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --location "$AZURE_LOCATION" \
    --sku Basic \
    --admin-enabled false >/dev/null
fi

AZURE_ACR_LOGIN_SERVER="$(az acr show --name "$AZURE_ACR_NAME" --resource-group "$AZURE_RESOURCE_GROUP" --query loginServer -o tsv)"

# Log Analytics (optional for ACI cost savings, required for Container Apps)
if [[ "$AZURE_EXECUTION_MODE" == "containerapps" ]]; then
  AZURE_ENABLE_LOG_ANALYTICS="true"
fi

if [[ "$AZURE_ENABLE_LOG_ANALYTICS" == "true" ]]; then
  if [[ -z "${AZURE_LOG_ANALYTICS_WORKSPACE:-}" ]]; then
    AZURE_LOG_ANALYTICS_WORKSPACE="${AZURE_NAME_PREFIX}-logs"
  fi

  echo "Ensuring Log Analytics workspace exists: $AZURE_LOG_ANALYTICS_WORKSPACE"
  if ! az monitor log-analytics workspace show --resource-group "$AZURE_RESOURCE_GROUP" --workspace-name "$AZURE_LOG_ANALYTICS_WORKSPACE" >/dev/null 2>&1; then
    az monitor log-analytics workspace create \
      --resource-group "$AZURE_RESOURCE_GROUP" \
      --workspace-name "$AZURE_LOG_ANALYTICS_WORKSPACE" \
      --location "$AZURE_LOCATION" >/dev/null
  fi

  AZURE_LOG_ANALYTICS_WORKSPACE_ID="$(az monitor log-analytics workspace show --resource-group "$AZURE_RESOURCE_GROUP" --workspace-name "$AZURE_LOG_ANALYTICS_WORKSPACE" --query customerId -o tsv)"
fi

# Optional VNet/Subnet for ACI network hardening
if [[ -n "${AZURE_VNET_NAME:-}" && -n "${AZURE_SUBNET_NAME:-}" ]]; then
  echo "Ensuring VNet/Subnet exists for private execution"
  if ! az network vnet show --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_VNET_NAME" >/dev/null 2>&1; then
    az network vnet create \
      --resource-group "$AZURE_RESOURCE_GROUP" \
      --name "$AZURE_VNET_NAME" \
      --location "$AZURE_LOCATION" \
      --address-prefixes 10.50.0.0/16 \
      --subnet-name "$AZURE_SUBNET_NAME" \
      --subnet-prefixes 10.50.1.0/24 >/dev/null
  elif ! az network vnet subnet show --resource-group "$AZURE_RESOURCE_GROUP" --vnet-name "$AZURE_VNET_NAME" --name "$AZURE_SUBNET_NAME" >/dev/null 2>&1; then
    az network vnet subnet create \
      --resource-group "$AZURE_RESOURCE_GROUP" \
      --vnet-name "$AZURE_VNET_NAME" \
      --name "$AZURE_SUBNET_NAME" \
      --address-prefixes 10.50.1.0/24 >/dev/null
  fi

  # Delegate subnet for container groups if possible
  az network vnet subnet update \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --vnet-name "$AZURE_VNET_NAME" \
    --name "$AZURE_SUBNET_NAME" \
    --delegations Microsoft.ContainerInstance/containerGroups >/dev/null || true

  AZURE_VNET_SUBNET_ID="$(az network vnet subnet show --resource-group "$AZURE_RESOURCE_GROUP" --vnet-name "$AZURE_VNET_NAME" --name "$AZURE_SUBNET_NAME" --query id -o tsv)"
fi

# Container Apps environment (only if execution mode asks for it)
if [[ "$AZURE_EXECUTION_MODE" == "containerapps" ]]; then
  if ! az extension show --name containerapp >/dev/null 2>&1; then
    az extension add --name containerapp --upgrade >/dev/null
  fi

  AZURE_CONTAINERAPPS_ENVIRONMENT="${AZURE_CONTAINERAPPS_ENVIRONMENT:-${AZURE_NAME_PREFIX}-cae}"

  echo "Ensuring Container Apps environment exists: $AZURE_CONTAINERAPPS_ENVIRONMENT"
  if ! az containerapp env show --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_CONTAINERAPPS_ENVIRONMENT" >/dev/null 2>&1; then
    az containerapp env create \
      --resource-group "$AZURE_RESOURCE_GROUP" \
      --name "$AZURE_CONTAINERAPPS_ENVIRONMENT" \
      --location "$AZURE_LOCATION" \
      --logs-workspace-id "$AZURE_LOG_ANALYTICS_WORKSPACE_ID" >/dev/null
  fi

  AZURE_CONTAINERAPPS_ENVIRONMENT_ID="$(az containerapp env show --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_CONTAINERAPPS_ENVIRONMENT" --query id -o tsv)"
fi

# Derived values
AZURE_CONTAINER_IMAGE="${AZURE_CONTAINER_IMAGE:-${AZURE_ACR_LOGIN_SERVER}/fixora-sandbox:latest}"

# Persist generated values back into .env
upsert_env AZURE_STORAGE_ACCOUNT "$AZURE_STORAGE_ACCOUNT"
upsert_env AZURE_STORAGE_CONTAINER "$AZURE_STORAGE_CONTAINER"
upsert_env AZURE_ACR_NAME "$AZURE_ACR_NAME"
upsert_env AZURE_ACR_LOGIN_SERVER "$AZURE_ACR_LOGIN_SERVER"
if [[ "$AZURE_ENABLE_LOG_ANALYTICS" == "true" ]]; then
  upsert_env AZURE_LOG_ANALYTICS_WORKSPACE "$AZURE_LOG_ANALYTICS_WORKSPACE"
  upsert_env AZURE_LOG_ANALYTICS_WORKSPACE_ID "$AZURE_LOG_ANALYTICS_WORKSPACE_ID"
fi
upsert_env AZURE_CONTAINER_IMAGE "$AZURE_CONTAINER_IMAGE"
upsert_env AZURE_ACI_CPU "$AZURE_ACI_CPU"
upsert_env AZURE_ACI_MEMORY_GB "$AZURE_ACI_MEMORY_GB"
upsert_env AZURE_ACI_TIMEOUT_SECONDS "$AZURE_ACI_TIMEOUT_SECONDS"
upsert_env AZURE_ENABLE_LOG_ANALYTICS "$AZURE_ENABLE_LOG_ANALYTICS"

if [[ -n "${AZURE_VNET_SUBNET_ID:-}" ]]; then
  upsert_env AZURE_VNET_SUBNET_ID "$AZURE_VNET_SUBNET_ID"
fi

if [[ "$AZURE_EXECUTION_MODE" == "containerapps" ]]; then
  upsert_env AZURE_CONTAINERAPPS_ENVIRONMENT "${AZURE_CONTAINERAPPS_ENVIRONMENT}"
  upsert_env AZURE_CONTAINERAPPS_ENVIRONMENT_ID "${AZURE_CONTAINERAPPS_ENVIRONMENT_ID}"
fi

echo ""
echo "Azure bootstrap complete. Generated/verified values saved to $ENV_FILE"
echo ""
echo "Next steps:"
echo "1) Build and push sandbox image to ACR:"
echo "   az acr login --name ${AZURE_ACR_NAME}"
echo "   docker build -t ${AZURE_CONTAINER_IMAGE} backend/sandbox_dockerfiles -f backend/sandbox_dockerfiles/python.Dockerfile"
echo "   docker push ${AZURE_CONTAINER_IMAGE}"
echo "2) Enable Azure only during needed runs: export USE_AZURE_SANDBOX=true"
echo "   Keep USE_AWS_SANDBOX=false unless you explicitly want AWS fallback."

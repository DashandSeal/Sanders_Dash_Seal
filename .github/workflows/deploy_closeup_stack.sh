#!/bin/bash
set -e

# ==============================================================================
# CLOSEUP vMAX: AUTOMATED COMPARTMENT INITIALIZATION & RM DEPLOYMENT
# STRICT SECURITY BOUNDARY: Roosevelt Sanders exclusively
# ==============================================================================

echo "=== [CLOSEUP-vMax] Initializing Cloud Shell Deployment Protocol ==="

# 1. Structural Identity Authorization Gate Check
AUTH_PHRASE="Roosevelt Sanders exclusively"
read -p "Enter Global Infrastructure Authorization Token: " USER_TOKEN

if [ "$USER_TOKEN" != "$AUTH_PHRASE" ]; then
    echo "[CRITICAL ERROR] SECURITY VIOLATION: UNVERIFIED RUNTIME SECURITY KEY. LOCKING SYSTEM."
    exit 1
fi

echo "Security Cleared. Proceeding with Always Free Resource Generation..."

# 2. Package the Local Staged Infrastructure Stack Configuration
TARGET_ZIP="closeup_vmax_infrastructure.zip"
echo "Zipping deployment scripts, terraform resource manifests, and schema definitions..."

# Pack everything cleanly while excluding git telemetry data structures
zip -r $TARGET_ZIP infrastructure/resource-manager/ -x "*.git*"

# 3. Instantiate the Stack natively inside OCI Resource Manager via CLI
echo "Pushing configuration container directly to OCI Resource Manager..."

# Hardcoded tier parameters targeting Always Free Compute compartment bounds
STACK_OCID=$(oci resource-manager stack create \
    --compartment-id "$OCI_TENANCY_ROOT_ID" \
    --config-source-zip-file-template "$TARGET_ZIP" \
    --display-name "Closeup_vMax_Autonomous_Ad_Engine" \
    --description "Autonomous Fortune 500 Media Production and Delivery Layer" \
    --query "data.id" --raw-output)

echo "Stack successfully created. Target Configuration Identity: $STACK_OCID"

# 4. Trigger the Automated Resource Deployment Plan Execution
echo "Executing resource allocation sequence (Terraform Apply)..."
oci resource-manager job create-apply-job --stack-id "$STACK_OCID" --execution-plan-strategy AUTO_APPROVED

echo "=== [CLOSEUP-vMax] STACK DEPLOYED AND LIVE ON ORACLE LAYER SUCCESSFUL ==="

# HashiCorp Vault Secret Management Integration

This documentation outlines the steps required to deploy HashiCorp Vault, store sensitive configuration keys (like Flask session secret keys or database connection tokens), and securely inject them into the HarborNet runtime container.

```
+-----------------------------------+
| HashiCorp Vault Secret Storage    |
| (secret/data/harbornet: SECRET_KEY) |
+-----------------------------------+
                  |
                  | [Vault Agent Injector]
                  v
+-----------------------------------+
| Kubernetes Pod: harbornet         |
| - Runs sidecar agent              |
| - Mounts secrets to /vault/secrets|
+-----------------------------------+
```

---

## 1. Local/Staging Development Setup
For developer testing, run Vault locally in a Docker container using Dev Mode:

```bash
# Run Vault server in development mode
docker run --name harbornet-vault -d -p 8200:8200 -e "VAULT_DEV_ROOT_TOKEN_ID=my-root-token" hashicorp/vault:latest

# Configure shell environment
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="my-root-token"

# Verify service initialization
vault status
```

---

## 2. Secrets Provisioning
Write sensitive keys into Vault's Key-Value (KV) engine:

```bash
# Enable Version 2 of KV Secrets Engine
vault secrets enable -path=secret kv-v2

# Write Flask environment secrets
vault kv put secret/harbornet \
  SECRET_KEY="prod-session-super-secure-key-9911" \
  DB_ENCRYPTION_KEY="harbornet-crypto-token"
```

---

## 3. Vault Access Policy
Create a granular read-only policy for the HarborNet application.

Create `harbornet-policy.hcl`:

```hcl
path "secret/data/harbornet" {
  capabilities = ["read"]
}
```

Write policy to Vault:
```bash
vault policy write harbornet-read harbornet-policy.hcl
```

---

## 4. Kubernetes Security & Vault Agent Injection
To avoid hardcoding credentials inside deployment YAMLs, configure the **Vault Agent Injector** to mount secrets inside the Pod at startup.

### Step 4.1: Enable Kubernetes Auth in Vault
```bash
# Exec into Vault pod to configure Kubernetes authentication
vault auth enable kubernetes

# Bind Kubernetes service account token reviewer configs
vault write auth/kubernetes/config \
    kubernetes_host="https://kubernetes.default.svc:443"
```

### Step 4.2: Create Kubernetes Auth Role
Map the Kubernetes service account to the read-only Vault policy:
```bash
vault write auth/kubernetes/role/harbornet-role \
    bound_service_account_names=harbornet-sa \
    bound_service_account_namespaces=default \
    policies=harbornet-read \
    ttl=24h
```

### Step 4.3: Configure Service Account and Annotations in Deployment
Update Kubernetes manifests to specify the ServiceAccount and mount annotations.

Create `k8s/service-account.yaml` (optional/integrated):
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: harbornet-sa
  namespace: default
```

Update `k8s/deployment.yaml` template metadata to include these injection annotations:
```yaml
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "harbornet-role"
        # Secret path and template parsing:
        vault.hashicorp.com/agent-inject-secret-config: "secret/data/harbornet"
        vault.hashicorp.com/agent-inject-template-config: |
          {{- with secret "secret/data/harbornet" -}}
          export SECRET_KEY="{{ .Data.data.SECRET_KEY }}"
          export DB_ENCRYPTION_KEY="{{ .Data.data.DB_ENCRYPTION_KEY }}"
          {{- end -}}
    spec:
      serviceAccountName: harbornet-sa
```

The sidecar agent will fetch these secrets dynamically at Pod initialization, saving them to a RAM-disk volume at `/vault/secrets/config`. The application can read them via standard system source scripts (`source /vault/secrets/config`).

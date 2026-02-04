# Kubernetes Secrets Management

This document describes how to manage secrets for ResearchFlow in Kubernetes. Never commit real secret values to version control.

## Creating Secrets

### From the template (recommended for initial setup)

1. Copy the example file and fill in real values:

   ```bash
   cp k8s/secrets.yaml.example k8s/secrets.yaml
   # Edit k8s/secrets.yaml with real DATABASE_URL, REDIS_URL, API keys, JWT keys, etc.
   ```

2. Apply the secret (ensure `k8s/secrets.yaml` is in `.gitignore` and never committed):

   ```bash
   kubectl apply -f k8s/secrets.yaml -n researchflow
   ```

### From literals

Create the secret with individual keys:

```bash
kubectl create secret generic researchflow-secrets -n researchflow \
  --from-literal=DATABASE_URL='postgresql://user:pass@host:5432/db' \
  --from-literal=REDIS_URL='redis://:pass@host:6379' \
  --from-literal=ANTHROPIC_API_KEY='sk-...' \
  --from-literal=OPENAI_API_KEY='sk-...' \
  --from-literal=JWT_PRIVATE_KEY="$(cat private.pem)" \
  --from-literal=JWT_PUBLIC_KEY="$(cat public.pem)"
```

### From an env file (use only in safe CI or local; never commit .env)

```bash
kubectl create secret generic researchflow-secrets -n researchflow --from-env-file=.env.production
```

**Warning:** Do not commit `.env.production` or any file containing real credentials. Use this only in CI that reads from a secure store, or locally with a file that is gitignored.

---

## Kubernetes Native Secrets

- **Secret resource:** Use the `Secret` manifest in `k8s/secrets.yaml.example`. Deployments reference it via `envFrom.secretRef` (see `k8s/deployment.yaml`).
- **RBAC:** The `k8s/rbac.yaml` grants the orchestrator, worker, and guideline-engine service accounts `get` on `researchflow-secrets` and `researchflow-config`.
- **Rotation:** Update the secret (e.g. `kubectl apply -f k8s/secrets.yaml`) and restart pods so they pick up new values: `kubectl rollout restart deployment/researchflow -n researchflow`.

---

## AWS Secrets Manager

Use [External Secrets Operator](https://external-secrets.io/) or the [AWS Secrets Store CSI driver](https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html) to sync secrets from AWS into Kubernetes.

**Example (External Secrets Operator):** Create an `ExternalSecret` that pulls from an AWS secret and creates/updates the `researchflow-secrets` Secret:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: researchflow-secrets
  namespace: researchflow
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-store
    kind: ClusterSecretStore
  target:
    name: researchflow-secrets
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: researchflow/production
        property: DATABASE_URL
    - secretKey: REDIS_URL
      remoteRef:
        key: researchflow/production
        property: REDIS_URL
    # ... other keys
```

See [External Secrets Operator docs](https://external-secrets.io/latest/provider/aws-secrets-manager/) for store setup and IAM.

---

## HashiCorp Vault

Use the [Vault Kubernetes auth method](https://developer.hashicorp.com/vault/docs/auth/kubernetes) with a Vault Agent sidecar, or External Secrets Operator with the [Vault provider](https://external-secrets.io/latest/provider/hashicorp-vault/), to inject secrets into pods or into a Kubernetes Secret.

**Example (External Secrets Operator):** Point an `ExternalSecret` at a Vault path and target `researchflow-secrets`:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: researchflow-secrets
  namespace: researchflow
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-store
    kind: ClusterSecretStore
  target:
    name: researchflow-secrets
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: secret/data/researchflow/production
        property: DATABASE_URL
    # ... other keys
```

See [Vault Kubernetes auth](https://developer.hashicorp.com/vault/docs/auth/kubernetes) and [ESO Vault provider](https://external-secrets.io/latest/provider/hashicorp-vault/) for configuration.

---

## Sealed Secrets

[Bitnami Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) lets you commit **encrypted** secret manifests; a controller in the cluster decrypts them into normal Secrets.

1. Install the controller and `kubeseal` CLI (see [Sealed Secrets releases](https://github.com/bitnami-labs/sealed-secrets/releases)).
2. Create a normal Secret (e.g. from `k8s/secrets.yaml` with real values), then seal it:

   ```bash
   kubeseal -f k8s/secrets.yaml -w k8s/sealed-secrets.yaml
   ```

3. Commit `k8s/sealed-secrets.yaml` (encrypted). Do **not** commit `k8s/secrets.yaml`; it remains gitignored.
4. Apply the sealed secret: `kubectl apply -f k8s/sealed-secrets.yaml -n researchflow`. The controller creates the `researchflow-secrets` Secret in the cluster.

---

## Security Summary

- **Never commit** real values in `k8s/secrets.yaml` or in `.env` files that are tracked.
- **Prefer** an external store (AWS Secrets Manager, Vault) or Sealed Secrets in production.
- **Rotate** keys and credentials periodically; update the Secret and restart workloads as needed.

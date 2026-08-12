# Argus Terraform

## Layout

- `modules/` — one reusable module per resource shape. Each module's
  `variables.tf`/`outputs.tf` is its interface; nothing outside a module
  reaches into its resources directly.
- `bootstrap/` — applied once, manually, by whoever owns the GCP project.
  Creates the remote-state GCS bucket and the GitHub Actions Workload
  Identity Federation trust that CI uses afterward. Its own state is local
  (there's no bucket yet to store it in — that's what this root creates).
- `environments/dev/` — applied repeatedly, normally by CI, using the
  modules above. A future `environments/prod/` would copy this directory's
  `.tf` files with a different `terraform.tfvars` and backend `prefix`,
  reusing every module unchanged.

## One-time bootstrap (by a project owner)

```bash
cd bootstrap
cp terraform.tfvars.example terraform.tfvars   # fill in project_id and a globally-unique state_bucket_name
terraform init
terraform apply
```

Record the three outputs — `state_bucket_name`, `ci_service_account_email`,
`workload_identity_provider` — as GitHub Actions **repository variables**
(Settings → Secrets and variables → Actions → Variables), alongside
`GCP_PROJECT_ID`: `GCP_TF_STATE_BUCKET`, `GCP_CI_SERVICE_ACCOUNT_EMAIL`,
`GCP_WORKLOAD_IDENTITY_PROVIDER`. These are identifiers, not secrets — no
service-account key file is ever generated or stored.

That is the whole one-time setup — there are no secret values to populate.
The backend reaches Firebase Admin, Firestore and Vertex AI through
Application Default Credentials: on Cloud Run that is the `argus-backend`
service account's own identity, granted the roles it needs in
`environments/dev/main.tf`. No credential file exists to leak.

## Everyday use (dev environment)

CI runs this on every PR (`plan`) and on every merge to `main` (`apply`) —
see `.github/workflows/ci.yml`. To run it by hand:

```bash
cd environments/dev
terraform init -backend-config="bucket=$GCP_TF_STATE_BUCKET"
terraform plan  \
  -var="project_id=$GCP_PROJECT_ID" \
  -var="firebase_project_id=$GCP_PROJECT_ID" \
  -var="backend_image=$BACKEND_IMAGE"
```

# Argus — The Agentic Seeing-Eye Copilot

The full product spec (`docs/argus-project-spec.md`) and the per-phase design
docs and implementation plans (`docs/specs/`) are internal design documents,
kept local and not tracked in this repository.

## What's built so far (Phase 0 — Platform Foundation)

An authenticated, real-time voice round trip: browser mic → WebSocket →
FastAPI → Gemini Live API (Vertex AI) → spoken response back to the
browser, deployed on Cloud Run. No task-domain intelligence yet — that's
Phase 1 onward.

## Prerequisites

- Python 3.12+, [Poetry](https://python-poetry.org/)
- Node.js 20+, [pnpm](https://pnpm.io/)
- Docker (needed for `make deploy`, which builds and pushes the backend image)
- A Google Cloud project with billing enabled, and the `gcloud` CLI authenticated
- [Terraform](https://developer.hashicorp.com/terraform/install) 1.9+ (only needed for infra changes, not local dev)
- A Firebase project (can be the same GCP project) with Google Sign-In enabled

## Local setup

1. Copy `backend/.env.example` to `backend/.env` and fill in your GCP/Firebase project IDs.
2. Copy `frontend/.env.local.example` to `frontend/.env.local` and fill in your Firebase web config.
3. Authenticate application-default credentials for local Firestore/Vertex AI access:
   `gcloud auth application-default login`
4. Run everything:
   ```bash
   make dev
   ```
   Backend: http://localhost:8000 · Frontend: http://localhost:3000

## Tests

```bash
make test
```

## Infrastructure and deployment

All GCP resources are Terraform-managed (`infra/terraform/`) — see
[`infra/terraform/README.md`](infra/terraform/README.md) for the full
bootstrap → environment story. Short version:

`GCP_TF_STATE_BUCKET` is set once and reused for both steps below: `make
bootstrap` creates the bucket, `make deploy` initializes Terraform against it.

**One-time, by a project owner:**
```bash
export GCP_PROJECT_ID=your-project-id
export GCP_TF_STATE_BUCKET=argus-tfstate-your-globally-unique-suffix
make bootstrap
```
Then set the three printed outputs as GitHub Actions repository variables
(`GCP_TF_STATE_BUCKET`, `GCP_CI_SERVICE_ACCOUNT_EMAIL`,
`GCP_WORKLOAD_IDENTITY_PROVIDER`) alongside `GCP_PROJECT_ID` — CI never
touches a long-lived service-account key, only these public identifiers.

There is nothing else to populate: the deployed backend authenticates to
Firebase Admin, Firestore and Vertex AI via Application Default Credentials —
the Cloud Run service account's own identity — so no credential file exists to
upload or rotate.

**Manually, from a laptop**, once bootstrap is done:
```bash
export GCP_PROJECT_ID=your-project-id
export GCP_TF_STATE_BUCKET=your-state-bucket-name
make deploy
```

**Automatically:** pushes to `main` run the full test suite, build the
backend image into Artifact Registry, and `terraform apply` the `dev`
environment, via `.github/workflows/ci.yml`.

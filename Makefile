.PHONY: dev test deploy bootstrap backend-dev frontend-dev backend-test frontend-test check-api-drift measure-latency

GCP_REGION ?= us-central1

dev:
	@echo "Starting backend and frontend (Ctrl+C to stop both)…"
	@$(MAKE) -j2 backend-dev frontend-dev

backend-dev:
	cd backend && poetry install && poetry run uvicorn app.main:app --reload --port 8000

frontend-dev:
	cd frontend && pnpm install && pnpm dev

test:
	@$(MAKE) backend-test
	@$(MAKE) frontend-test

backend-test:
	cd backend && poetry run pytest -v

frontend-test:
	cd frontend && pnpm test

# Mirrors CI's "OpenAPI drift check" step exactly (.github/workflows/ci.yml) —
# no local pytest/vitest run ever exercises this, since it needs a live
# backend server, so drift here is otherwise only ever caught in CI. Kills its
# own uvicorn on exit (success, failure, or Ctrl+C) so it never leaks a server
# on :8000 the way running the two commands by hand would.
#
# Deliberately does NOT rely on bash's $! for that kill: under Git Bash/MSYS on
# Windows, $! after `cmd &` is an MSYS-internal job id, not the real Win32 PID
# — confirmed directly (uvicorn logged its own real PID; $! held a completely
# different number, and `taskkill //PID` on it just errored "process not
# found"). On Windows, find the real PID via `netstat` (which reports actual
# Win32 PIDs) and `taskkill //F //T` the process tree that owns :8000 instead.
check-api-drift:
	cd backend && poetry run uvicorn app.main:app --port 8000 & \
	SERVER_PID=$$!; \
	cleanup() { \
		if command -v taskkill >/dev/null 2>&1; then \
			WIN_PID=$$(netstat -ano 2>/dev/null | grep LISTENING | grep ':8000 ' | awk '{print $$NF}' | head -n1); \
			[ -n "$$WIN_PID" ] && taskkill //F //T //PID "$$WIN_PID" >/dev/null 2>&1; \
		else \
			kill $$SERVER_PID 2>/dev/null || true; \
		fi; \
		true; \
	}; \
	trap cleanup EXIT; \
	npx --yes wait-on http-get://localhost:8000/healthz && \
	cd frontend && pnpm gen:api && \
	git diff --exit-code lib/api/schema.ts && \
	echo "No OpenAPI drift." || \
	(echo "OpenAPI drift detected — schema.ts is stale. Commit the regenerated file." && exit 1)

measure-latency:
	cd backend && poetry run python ../scripts/measure_latency.py --runs 20 --out ../docs/specs/2026-08-19-phase5-latency-report.json

bootstrap:
	cd infra/terraform/bootstrap && terraform init && terraform apply \
		-var="project_id=$(GCP_PROJECT_ID)" \
		-var="state_bucket_name=$(GCP_TF_STATE_BUCKET)"

deploy:
	gcloud auth configure-docker $(GCP_REGION)-docker.pkg.dev
	docker build -t $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/argus/argus-backend:latest backend
	docker push $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/argus/argus-backend:latest
	cd infra/terraform/environments/dev && \
		terraform init -backend-config="bucket=$(GCP_TF_STATE_BUCKET)" && \
		terraform apply \
			-var="project_id=$(GCP_PROJECT_ID)" \
			-var="firebase_project_id=$(GCP_PROJECT_ID)" \
			-var="backend_image=$(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/argus/argus-backend:latest"

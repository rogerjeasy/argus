.PHONY: dev test deploy bootstrap backend-dev frontend-dev backend-test frontend-test check-api-drift measure-latency test-redteam test-fixtures

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

test-redteam:
	cd backend && poetry run python -m pytest -m redteam -v

test-fixtures:
	cd backend && poetry run python -m pytest app/tests/test_redteam_recorded_fixtures.py app/tests/test_fixture_regression_recorded.py -v

measure-latency:
	cd backend && poetry run python ../scripts/measure_latency.py --runs 20 --out ../docs/specs/2026-08-19-phase5-latency-report.json

bootstrap:
	cd infra/terraform/bootstrap && terraform init && terraform apply \
		-var="project_id=$(GCP_PROJECT_ID)" \
		-var="state_bucket_name=$(GCP_TF_STATE_BUCKET)"

# The frontend image bakes NEXT_PUBLIC_* in at build time, and the backend URL
# is one of them — so a first-ever deploy is two passes: run once with the
# images unset (services come up on the placeholder), then re-run once the
# argus-backend URL exists. FRONTEND_API_ORIGIN / FRONTEND_ORIGIN default to
# the standard dev Cloud Run URLs; override them if the service hash differs.
FRONTEND_API_ORIGIN ?= https://argus-backend-7epknchwrq-uc.a.run.app
FRONTEND_ORIGIN     ?= https://argus-frontend-7epknchwrq-uc.a.run.app
BACKEND_IMAGE  = $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/argus/argus-backend:latest
FRONTEND_IMAGE = $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/argus/argus-frontend:latest

deploy:
	gcloud auth configure-docker $(GCP_REGION)-docker.pkg.dev
	docker build -t $(BACKEND_IMAGE) backend
	docker push $(BACKEND_IMAGE)
	docker build -t $(FRONTEND_IMAGE) \
		--build-arg NEXT_PUBLIC_API_BASE_URL=$(FRONTEND_API_ORIGIN) \
		--build-arg NEXT_PUBLIC_WS_BASE_URL=$(subst https://,wss://,$(FRONTEND_API_ORIGIN)) \
		--build-arg NEXT_PUBLIC_FIREBASE_API_KEY=$(NEXT_PUBLIC_FIREBASE_API_KEY) \
		--build-arg NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=$(NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN) \
		--build-arg NEXT_PUBLIC_FIREBASE_PROJECT_ID=$(NEXT_PUBLIC_FIREBASE_PROJECT_ID) \
		--build-arg NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=$(NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET) \
		--build-arg NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=$(NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID) \
		--build-arg NEXT_PUBLIC_FIREBASE_APP_ID=$(NEXT_PUBLIC_FIREBASE_APP_ID) \
		frontend
	docker push $(FRONTEND_IMAGE)
	cd infra/terraform/environments/dev && \
		terraform init -backend-config="bucket=$(GCP_TF_STATE_BUCKET)" && \
		terraform apply \
			-var="project_id=$(GCP_PROJECT_ID)" \
			-var="firebase_project_id=$(GCP_PROJECT_ID)" \
			-var="backend_image=$(BACKEND_IMAGE)" \
			-var="frontend_image=$(FRONTEND_IMAGE)" \
			-var='cors_allow_origins=["$(FRONTEND_ORIGIN)"]'

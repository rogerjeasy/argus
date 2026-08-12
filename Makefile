.PHONY: dev test deploy bootstrap backend-dev frontend-dev backend-test frontend-test

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

bootstrap:
	cd infra/terraform/bootstrap && terraform init && terraform apply

deploy:
	gcloud auth configure-docker $(GCP_REGION)-docker.pkg.dev
	docker build -t $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/argus/argus-backend:latest backend
	docker push $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/argus/argus-backend:latest
	cd infra/terraform/environments/dev && \
		terraform init -backend-config="bucket=$(TF_STATE_BUCKET)" && \
		terraform apply \
			-var="project_id=$(GCP_PROJECT_ID)" \
			-var="firebase_project_id=$(GCP_PROJECT_ID)" \
			-var="backend_image=$(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/argus/argus-backend:latest"

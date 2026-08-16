from functools import lru_cache

from google.cloud import firestore, kms

from app.core.config import get_settings


@lru_cache
def get_firestore_client() -> firestore.Client:
    settings = get_settings()
    return firestore.Client(project=settings.gcp_project_id)


@lru_cache
def get_kms_client() -> kms.KeyManagementServiceClient:
    return kms.KeyManagementServiceClient()

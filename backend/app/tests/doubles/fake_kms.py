"""Stands in for google.cloud.kms.KeyManagementServiceClient — encrypt/decrypt
are a reversible transform, not real cryptography, so tests can assert
MemoryAgent actually calls through this client rather than assert anything
about real KMS behavior (which needs a real key and is out of scope for
CI)."""


class _FakeEncryptResponse:
    def __init__(self, ciphertext: bytes) -> None:
        self.ciphertext = ciphertext


class _FakeDecryptResponse:
    def __init__(self, plaintext: bytes) -> None:
        self.plaintext = plaintext


class FakeKmsClient:
    def __init__(self) -> None:
        self.encrypt_calls: list[dict] = []
        self.decrypt_calls: list[dict] = []

    def encrypt(self, *, request: dict) -> _FakeEncryptResponse:
        self.encrypt_calls.append(request)
        # Reversible, not secure — a fixed XOR-like byte reversal is enough
        # to prove MemoryAgent round-trips through this client correctly.
        return _FakeEncryptResponse(ciphertext=request["plaintext"][::-1])

    def decrypt(self, *, request: dict) -> _FakeDecryptResponse:
        self.decrypt_calls.append(request)
        return _FakeDecryptResponse(plaintext=request["ciphertext"][::-1])

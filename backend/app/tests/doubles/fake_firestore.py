class FakeSnapshot:
    def __init__(self, data: dict | None) -> None:
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict:
        return dict(self._data or {})


class FakeDocument:
    def __init__(self, store: dict, key: tuple[str, ...]) -> None:
        self._store = store
        self._key = key

    def get(self) -> FakeSnapshot:
        return FakeSnapshot(self._store.get(self._key))

    def set(self, data: dict) -> None:
        self._store[self._key] = dict(data)

    def update(self, data: dict) -> None:
        existing = self._store.get(self._key, {})
        existing.update(data)
        self._store[self._key] = existing

    def collection(self, name: str) -> "FakeCollection":
        return FakeCollection(self._store, self._key + (name,))


class FakeCollection:
    def __init__(self, store: dict, key: tuple[str, ...]) -> None:
        self._store = store
        self._key = key

    def document(self, doc_id: str) -> FakeDocument:
        return FakeDocument(self._store, self._key + (doc_id,))


class FakeFirestoreClient:
    def __init__(self) -> None:
        self._store: dict[tuple[str, ...], dict] = {}

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self._store, (name,))

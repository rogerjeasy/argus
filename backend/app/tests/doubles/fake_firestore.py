class FakeSnapshot:
    def __init__(self, doc_id: str, data: dict | None) -> None:
        self.id = doc_id
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
        return FakeSnapshot(self._key[-1], self._store.get(self._key))

    def set(self, data: dict, merge: bool = False) -> None:
        if merge:
            existing = self._store.get(self._key, {})
            existing.update(data)
            self._store[self._key] = existing
        else:
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

    def stream(self) -> list[FakeSnapshot]:
        """Mirrors google.cloud.firestore.CollectionReference.stream() —
        every *direct* child document of this collection, not documents
        nested further down under a subcollection. self._key + (doc_id,)
        is a direct child iff its own key is exactly one segment longer
        than self._key."""
        prefix_len = len(self._key)
        return [
            FakeSnapshot(key[-1], data)
            for key, data in self._store.items()
            if len(key) == prefix_len + 1 and key[:prefix_len] == self._key
        ]


class FakeFirestoreClient:
    def __init__(self) -> None:
        self._store: dict[tuple[str, ...], dict] = {}

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self._store, (name,))

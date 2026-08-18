from app.tests.doubles.fake_firestore import FakeFirestoreClient


def test_stream_returns_every_document_in_the_collection() -> None:
    db = FakeFirestoreClient()
    db.collection("things").document("a").set({"n": 1})
    db.collection("things").document("b").set({"n": 2})

    snapshots = db.collection("things").stream()

    assert {s.id for s in snapshots} == {"a", "b"}
    assert {s.to_dict()["n"] for s in snapshots} == {1, 2}


def test_stream_on_empty_collection_returns_empty_list() -> None:
    db = FakeFirestoreClient()
    assert db.collection("nothing_here").stream() == []


def test_stream_only_returns_direct_children_not_subcollection_documents() -> None:
    db = FakeFirestoreClient()
    db.collection("users").document("u1").set({"name": "a"})
    db.collection("users").document("u1").collection("permissions").document("standing").set({"rules": []})

    snapshots = db.collection("users").stream()

    assert [s.id for s in snapshots] == ["u1"]


def test_document_get_snapshot_also_has_id() -> None:
    db = FakeFirestoreClient()
    db.collection("things").document("a").set({"n": 1})

    snapshot = db.collection("things").document("a").get()

    assert snapshot.id == "a"

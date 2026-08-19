import pytest

from app.agents.memory import MemoryAgent, StandingPermission
from app.tests.doubles.fake_firestore import FakeFirestoreClient


@pytest.mark.asyncio
async def test_get_standing_permissions_defaults_to_empty() -> None:
    agent = MemoryAgent(FakeFirestoreClient())
    permissions = await agent.get_standing_permissions("u1")
    assert permissions == []


@pytest.mark.asyncio
async def test_get_standing_permissions_reads_seeded_rules() -> None:
    db = FakeFirestoreClient()
    db.collection("argus_users").document("u1").collection("permissions").document("standing").set(
        {"rules": [{"category": "stub-guidance", "threshold": 0.8}]}
    )
    agent = MemoryAgent(db)

    permissions = await agent.get_standing_permissions("u1")

    assert permissions == [StandingPermission(category="stub-guidance", threshold=0.8)]


@pytest.mark.asyncio
async def test_record_task_history_persists_a_summary() -> None:
    db = FakeFirestoreClient()
    agent = MemoryAgent(db)

    await agent.record_task_history(uid="u1", session_id="s1", summary="Guided to platform 4")

    stored = db.collection("argus_users").document("u1").collection("task_history").document("s1").get()
    assert stored.to_dict()["summary"] == "Guided to platform 4"


def test_standing_permission_provider_defaults_to_none() -> None:
    from app.agents.memory import StandingPermission

    permission = StandingPermission(category="pharmacy_refill_under_20", threshold=0.5)

    assert permission.provider is None


@pytest.mark.asyncio
async def test_update_profile_then_get_profile_round_trips_without_kms(monkeypatch) -> None:
    from app.agents.memory import MemoryAgent, PersonalAdminProfile, ProviderContact
    from app.tests.doubles.fake_firestore import FakeFirestoreClient

    monkeypatch.setattr("app.agents.memory.get_settings", lambda: type("S", (), {"kms_key_name": ""})())
    db = FakeFirestoreClient()
    agent = MemoryAgent(db, kms=None)
    profile = PersonalAdminProfile(
        known_providers=[ProviderContact(name="Example Pharmacy", phone_number="+15551234567", category="pharmacy_refill_under_20")],
        standing_payment_threshold_cents=2000,
        insurance_member_id="ABC123",
    )

    await agent.update_profile("user-1", profile)
    loaded = await agent.get_profile("user-1")

    assert loaded == profile


@pytest.mark.asyncio
async def test_get_profile_returns_empty_profile_when_none_stored() -> None:
    from app.agents.memory import MemoryAgent, PersonalAdminProfile
    from app.tests.doubles.fake_firestore import FakeFirestoreClient

    agent = MemoryAgent(FakeFirestoreClient(), kms=None)

    profile = await agent.get_profile("user-with-no-profile")

    assert profile == PersonalAdminProfile()


@pytest.mark.asyncio
async def test_update_profile_encrypts_sensitive_fields_through_kms(monkeypatch) -> None:
    from app.agents.memory import MemoryAgent, PersonalAdminProfile
    from app.tests.doubles.fake_firestore import FakeFirestoreClient
    from app.tests.doubles.fake_kms import FakeKmsClient

    monkeypatch.setattr("app.agents.memory.get_settings", lambda: type("S", (), {"kms_key_name": "projects/p/locations/l/keyRings/r/cryptoKeys/k"})())
    db = FakeFirestoreClient()
    kms = FakeKmsClient()
    agent = MemoryAgent(db, kms=kms)
    profile = PersonalAdminProfile(insurance_member_id="ABC123", date_of_birth="1990-01-01")

    await agent.update_profile("user-1", profile)

    assert len(kms.encrypt_calls) == 2  # insurance_member_id, date_of_birth
    stored = db.collection("argus_users").document("user-1").collection("personal_admin").document("profile").get().to_dict()
    assert stored["insurance_member_id"] != "ABC123"  # stored ciphertext, not plaintext

    loaded = await agent.get_profile("user-1")
    assert loaded.insurance_member_id == "ABC123"  # decrypted back on read
    assert len(kms.decrypt_calls) == 2


@pytest.mark.asyncio
async def test_record_and_get_confirmation_history_round_trips() -> None:
    db = FakeFirestoreClient()
    agent = MemoryAgent(db)

    await agent.record_confirmation_outcome(
        "u1", category="pharmacy_refill", provider="cvs-main-st", decision="approved"
    )
    await agent.record_confirmation_outcome(
        "u1", category="pharmacy_refill", provider="cvs-main-st", decision="approved"
    )
    await agent.record_confirmation_outcome(
        "u1", category="bill_payment", provider=None, decision="denied"
    )

    history = await agent.get_confirmation_history("u1", category="pharmacy_refill", provider="cvs-main-st")

    assert len(history) == 2
    assert all(h.decision == "approved" for h in history)


@pytest.mark.asyncio
async def test_get_confirmation_history_is_scoped_to_category_and_provider() -> None:
    db = FakeFirestoreClient()
    agent = MemoryAgent(db)

    await agent.record_confirmation_outcome("u1", category="pharmacy_refill", provider="cvs-main-st", decision="approved")
    await agent.record_confirmation_outcome("u1", category="pharmacy_refill", provider="walgreens", decision="approved")

    history = await agent.get_confirmation_history("u1", category="pharmacy_refill", provider="cvs-main-st")

    assert len(history) == 1
    assert history[0].provider == "cvs-main-st"


@pytest.mark.asyncio
async def test_store_and_get_pending_calibration_proposal_round_trips() -> None:
    from app.agents.calibration import CalibrationProposal

    db = FakeFirestoreClient()
    agent = MemoryAgent(db)
    proposal = CalibrationProposal(category="pharmacy_refill", provider="cvs-main-st", evidence="approved 15/15 times")

    proposal_id = await agent.store_calibration_proposal("u1", proposal)
    pending = await agent.get_pending_calibration_proposal("u1")

    assert pending is not None
    fetched_id, fetched_proposal = pending
    assert fetched_id == proposal_id
    assert fetched_proposal.category == "pharmacy_refill"
    assert fetched_proposal.status == "pending_user_opt_in"


@pytest.mark.asyncio
async def test_get_pending_calibration_proposal_returns_none_when_no_proposal_pending() -> None:
    db = FakeFirestoreClient()
    agent = MemoryAgent(db)

    assert await agent.get_pending_calibration_proposal("u1") is None


@pytest.mark.asyncio
async def test_mark_calibration_proposal_dismissed_removes_it_from_pending() -> None:
    from app.agents.calibration import CalibrationProposal

    db = FakeFirestoreClient()
    agent = MemoryAgent(db)
    proposal = CalibrationProposal(category="pharmacy_refill", provider="cvs-main-st", evidence="approved 15/15 times")
    proposal_id = await agent.store_calibration_proposal("u1", proposal)

    await agent.mark_calibration_proposal_dismissed("u1", proposal_id)

    assert await agent.get_pending_calibration_proposal("u1") is None


@pytest.mark.asyncio
async def test_apply_calibration_proposal_writes_a_standing_permission() -> None:
    from app.agents.calibration import CalibrationProposal
    from app.agents.guardrail import MIN_CONFIDENCE_FLOOR

    db = FakeFirestoreClient()
    agent = MemoryAgent(db)
    proposal = CalibrationProposal(category="pharmacy_refill", provider="cvs-main-st", evidence="approved 15/15 times")
    proposal_id = await agent.store_calibration_proposal("u1", proposal)

    await agent.apply_calibration_proposal_to_standing_permissions("u1", proposal_id)

    permissions = await agent.get_standing_permissions("u1")
    assert len(permissions) == 1
    assert permissions[0].category == "pharmacy_refill"
    assert permissions[0].provider == "cvs-main-st"
    assert permissions[0].threshold == MIN_CONFIDENCE_FLOOR
    # applying also resolves the proposal — it must not still be "pending"
    assert await agent.get_pending_calibration_proposal("u1") is None


@pytest.mark.asyncio
async def test_get_user_settings_defaults_when_unset() -> None:
    from app.models.user_settings import UserSettings

    db = FakeFirestoreClient()
    agent = MemoryAgent(db)

    settings = await agent.get_user_settings("u1")

    assert settings == UserSettings()
    assert settings.audio_perception_enabled is False


@pytest.mark.asyncio
async def test_get_user_settings_reads_seeded_preferences() -> None:
    db = FakeFirestoreClient()
    db.collection("argus_users").document("u1").collection("settings").document("preferences").set(
        {"verbosity": "terse", "pace": "normal", "audio_perception_enabled": True}
    )
    agent = MemoryAgent(db)

    settings = await agent.get_user_settings("u1")

    assert settings.audio_perception_enabled is True


@pytest.mark.asyncio
async def test_get_regular_routes_defaults_to_empty() -> None:
    agent = MemoryAgent(FakeFirestoreClient())
    assert await agent.get_regular_routes("u1") == []


@pytest.mark.asyncio
async def test_add_regular_route_then_get_regular_routes_round_trips() -> None:
    from app.agents.memory import RegularRoute

    agent = MemoryAgent(FakeFirestoreClient())
    route = RegularRoute(domain_id="transit-ch", goal_text="get me to Zürich HB")

    await agent.add_regular_route("u1", route)
    routes = await agent.get_regular_routes("u1")

    assert routes == [route]


@pytest.mark.asyncio
async def test_add_regular_route_appends_to_existing_routes() -> None:
    from app.agents.memory import RegularRoute

    agent = MemoryAgent(FakeFirestoreClient())
    await agent.add_regular_route("u1", RegularRoute(domain_id="transit-ch", goal_text="get me to Zürich HB"))
    await agent.add_regular_route("u1", RegularRoute(domain_id="transit-mbta", goal_text="get me to North Station"))

    routes = await agent.get_regular_routes("u1")

    assert len(routes) == 2
    assert routes[1].domain_id == "transit-mbta"

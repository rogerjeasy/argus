from app.core.config import Settings
from app.domains.indoor_wayfinding.config import build_venue_directory_config


def test_build_config_defaults_venue_id_when_unset() -> None:
    settings = Settings(indoor_wayfinding_venue_id="", indoor_wayfinding_directory_url="")
    config = build_venue_directory_config(settings)
    assert config.venue_id == "default"
    assert config.directory_data_url is None


def test_build_config_uses_configured_values() -> None:
    settings = Settings(
        indoor_wayfinding_venue_id="conference-center-a",
        indoor_wayfinding_directory_url="https://example.org/venues/a/directory.json",
    )
    config = build_venue_directory_config(settings)
    assert config.venue_id == "conference-center-a"
    assert config.directory_data_url == "https://example.org/venues/a/directory.json"

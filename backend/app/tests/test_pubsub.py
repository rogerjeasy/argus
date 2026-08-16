from unittest.mock import MagicMock, patch

from app.core.pubsub import get_publisher_client


def test_get_publisher_client_does_not_construct_the_real_client_eagerly() -> None:
    """Regression: `pubsub_v1.PublisherClient()` resolves GCP credentials
    synchronously at construction time (`google.auth.default()`), and
    `build_orchestrator()` calls `get_publisher_client()` on every WS
    session regardless of whether that session ever escalates. Eagerly
    constructing the real client here broke CI (no ambient GCP credentials
    on the runner) and would add unnecessary latency in production to
    every session, not just ones that escalate.
    """
    get_publisher_client.cache_clear()
    with patch("app.core.pubsub.pubsub_v1.PublisherClient") as mock_client_cls:
        get_publisher_client()
        mock_client_cls.assert_not_called()


def test_get_publisher_client_constructs_the_real_client_on_first_actual_use() -> None:
    get_publisher_client.cache_clear()
    with patch("app.core.pubsub.pubsub_v1.PublisherClient") as mock_client_cls:
        mock_client_cls.return_value = MagicMock()
        client = get_publisher_client()

        client.publish("projects/p/topics/t", b"data")

        mock_client_cls.assert_called_once()
        mock_client_cls.return_value.publish.assert_called_once_with("projects/p/topics/t", b"data")


def test_get_publisher_client_reuses_the_same_underlying_client_across_calls() -> None:
    get_publisher_client.cache_clear()
    with patch("app.core.pubsub.pubsub_v1.PublisherClient") as mock_client_cls:
        mock_client_cls.return_value = MagicMock()
        client = get_publisher_client()

        client.topic_path("p", "t")
        client.publish("projects/p/topics/t", b"data")

        # Both calls went through the same lazily-constructed real client.
        mock_client_cls.assert_called_once()

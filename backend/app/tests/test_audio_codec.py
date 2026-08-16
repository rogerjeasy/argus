import audioop

from app.domains.personal_admin.audio_codec import mulaw8k_to_pcm16k


def test_mulaw8k_to_pcm16k_upsamples_and_produces_valid_pcm16() -> None:
    # Build a known 8kHz 16-bit PCM tone, encode it to mu-law (what Twilio's
    # Media Stream actually sends), then decode+upsample it back.
    original_pcm_8k = (b"\x10\x00\x20\x00\x30\x00\x40\x00") * 20  # 160 samples, 20ms @ 8kHz
    mulaw_bytes = audioop.lin2ulaw(original_pcm_8k, 2)

    pcm_16k = mulaw8k_to_pcm16k(mulaw_bytes)

    # 8kHz -> 16kHz roughly doubles the sample count; each sample is 2
    # bytes. Not exactly double: audioop.ratecv is a real interpolating
    # resampler, and a stateless single-shot call (no carried-over state
    # between chunks) is off by a sample or two at the block boundary —
    # verified directly against audioop.ratecv itself, not a bug here.
    assert len(pcm_16k) % 2 == 0
    expected_samples = len(original_pcm_8k) // 2 * 2
    actual_samples = len(pcm_16k) // 2
    assert abs(actual_samples - expected_samples) <= 2


def test_mulaw8k_to_pcm16k_handles_an_empty_frame() -> None:
    assert mulaw8k_to_pcm16k(b"") == b""

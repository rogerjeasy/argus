import audioop  # provided by audioop-lts on Python 3.13+, stdlib on 3.12


def mulaw8k_to_pcm16k(mulaw_bytes: bytes) -> bytes:
    """Twilio Media Streams send 8kHz mu-law; Gemini Live's input expects
    16-bit signed little-endian PCM at 16kHz (ws/gemini_bridge.py's
    INPUT_SAMPLE_RATE). ulaw2lin decodes mu-law to 16-bit linear PCM at the
    original 8kHz rate; ratecv upsamples it to 16kHz — a real, well-tested
    resampler, not a hand-rolled approximation."""
    if not mulaw_bytes:
        return b""
    pcm_8k = audioop.ulaw2lin(mulaw_bytes, 2)
    pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, None)
    return pcm_16k

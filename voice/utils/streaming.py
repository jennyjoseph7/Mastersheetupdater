"""Streaming utilities and helpers."""


def chunk_audio(data, chunk_size=1024):
    """Yield chunks from audio data."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i+chunk_size]

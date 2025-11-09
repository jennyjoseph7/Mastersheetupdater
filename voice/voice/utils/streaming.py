"""Streaming helpers for breaking audio/text into chunks."""

def chunk_audio(data: bytes, chunk_size: int = 1024):
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]

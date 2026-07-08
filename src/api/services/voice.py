import asyncio
import os
import tempfile

import edge_tts
from faster_whisper import WhisperModel

_whisper = WhisperModel("base", device="cpu", compute_type="int8")


async def _tts_bytes(text: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        path = f.name
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await communicate.save(path)
    with open(path, "rb") as f:
        data = f.read()
    os.unlink(path)
    return data


def text_to_audio(text: str) -> bytes:
    return asyncio.run(_tts_bytes(text))


def audio_to_text(audio_bytes: bytes) -> str:
    # The browser sends webm/opus (or mp4 on Safari); Whisper/ffmpeg detect the container
    # from the content, so the file suffix does not need to match.
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    segments, _ = _whisper.transcribe(path)
    os.unlink(path)
    return " ".join(seg.text for seg in segments).strip()

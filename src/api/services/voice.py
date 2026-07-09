import asyncio
import logging
import os
import tempfile
import time

import edge_tts
from faster_whisper import WhisperModel

logger = logging.getLogger("interview.voice")

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
    data = asyncio.run(_tts_bytes(text))
    logger.info("TTS: %d chars -> %d bytes mp3 | text=%r", len(text), len(data), text[:120])
    return data


def audio_to_text(audio_bytes: bytes) -> str:
    # The browser sends webm/opus (or mp4 on Safari); Whisper/ffmpeg detect the container
    # from the content, so the file suffix does not need to match.
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as f:
        f.write(audio_bytes)
        path = f.name

    started = time.time()
    # Hardened decoding for short answers:
    #  - language="en"                    avoid language drift on 1-word clips
    #  - vad_filter=True                  strip trailing silence/noise that makes Whisper loop
    #                                     (the "postgres postgres" repetition hallucination)
    #  - condition_on_previous_text=False don't carry a repeated phrase forward
    segments, info = _whisper.transcribe(
        path,
        language="en",
        vad_filter=True,
        condition_on_previous_text=False,
        beam_size=5,
        temperature=0,
    )
    text = " ".join(seg.text for seg in segments).strip()
    os.unlink(path)

    logger.info(
        "STT: %d bytes in | %.2fs | lang=%s(%.2f) | transcript=%r",
        len(audio_bytes),
        time.time() - started,
        getattr(info, "language", "?"),
        getattr(info, "language_probability", 0.0),
        text,
    )
    if not text:
        logger.warning("STT: EMPTY transcript for %d bytes of audio", len(audio_bytes))
    return text

import asyncio
import os
import tempfile

import edge_tts
import pygame
import sounddevice as sd
from faster_whisper import WhisperModel
from scipy.io.wavfile import write

_whisper = WhisperModel("base", device="cpu", compute_type="int8")


async def _tts(text: str, path: str):
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await communicate.save(path)


def speak(text: str):
    print(f"\nInterviewer: {text}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        path = f.name
    asyncio.run(_tts(text, path))
    pygame.mixer.init()
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)
    os.unlink(path)


def listen() -> str:
    print("You (speak, then press Enter to stop): ", end="", flush=True)
    fs = 44100
    duration = 30
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="int16")
    input()
    sd.stop()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    write(path, fs, recording)
    segments, _ = _whisper.transcribe(path)
    os.unlink(path)
    answer = " ".join(seg.text for seg in segments).strip()
    print(answer)
    return answer

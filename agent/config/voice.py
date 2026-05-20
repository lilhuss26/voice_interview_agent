import asyncio
import os
import tempfile

import edge_tts
import numpy as np
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
    SAMPLE_RATE = 16000
    SILENCE_THRESHOLD = 0.02
    SILENCE_DURATION = 1.5

    print("\nYou (speak now...): ", end="", flush=True)

    chunks = []
    silence_frames = 0
    started = False
    done = False
    silence_limit = int(SILENCE_DURATION * SAMPLE_RATE)

    def callback(indata, frames, time, status):
        nonlocal silence_frames, started, done
        if done:
            return
        rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2)) / 32768
        chunks.append(indata.copy())
        if rms > SILENCE_THRESHOLD:
            started = True
            silence_frames = 0
        elif started:
            silence_frames += frames
            if silence_frames >= silence_limit:
                done = True

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback):
        while not done:
            sd.sleep(100)

    recording = np.concatenate(chunks)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    write(path, SAMPLE_RATE, recording)
    segments, _ = _whisper.transcribe(path)
    os.unlink(path)
    answer = " ".join(seg.text for seg in segments).strip()
    print(answer)
    return answer

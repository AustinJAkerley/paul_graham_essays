"""Text-to-speech backends for narrating essays.

Provides a small pluggable interface so you can pick the "best AI voice
software" that fits your needs and budget:

* ``ElevenLabsBackend`` - ElevenLabs, widely regarded as the most natural
  and expressive AI narration available, and the easiest way to use a
  cloned/custom voice.
* ``OpenAITTSBackend`` - OpenAI's text-to-speech, a strong, cheaper option.

Both produce MP3 output. Long essays are split into chunks that respect the
per-request character limits, and the resulting MP3 segments are concatenated
into a single file.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod

import requests

# Conservative per-request character budgets for each provider.
ELEVENLABS_CHAR_LIMIT = 4500
OPENAI_CHAR_LIMIT = 4000


def chunk_text(text: str, limit: int) -> list[str]:
    """Split ``text`` into chunks no longer than ``limit`` characters.

    Splits on paragraph and then sentence boundaries so that audio breaks
    fall at natural pauses rather than mid-word.
    """

    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []

    # Break into sentence-ish units first.
    units = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    chunks: list[str] = []
    current = ""
    for unit in units:
        unit = unit.strip()
        if not unit:
            continue
        if len(unit) > limit:
            # A single very long unit: hard-wrap on word boundaries.
            if current:
                chunks.append(current)
                current = ""
            for piece in _hard_wrap(unit, limit):
                chunks.append(piece)
            continue
        candidate = f"{current} {unit}".strip() if current else unit
        if len(candidate) > limit:
            chunks.append(current)
            current = unit
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _hard_wrap(text: str, limit: int) -> list[str]:
    words = text.split()
    out: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > limit and current:
            out.append(current)
            current = word
        else:
            current = candidate
    if current:
        out.append(current)
    return out


class TTSBackend(ABC):
    """Abstract base class for a text-to-speech provider."""

    #: Maximum characters allowed per synthesis request.
    char_limit: int = 4000

    @abstractmethod
    def synthesize_chunk(self, text: str) -> bytes:
        """Synthesize a single chunk of text and return MP3 bytes."""

    def synthesize(self, text: str) -> bytes:
        """Synthesize arbitrary-length text into a single MP3 byte string.

        MP3 frames can be concatenated directly and remain playable, so we
        join the per-chunk outputs without needing ffmpeg. For gapless,
        re-encoded output, run the segments through ffmpeg yourself.
        """

        chunks = chunk_text(text, self.char_limit)
        audio = bytearray()
        for index, chunk in enumerate(chunks, start=1):
            print(f"    synthesizing chunk {index}/{len(chunks)} ({len(chunk)} chars)")
            audio.extend(self.synthesize_chunk(chunk))
        return bytes(audio)


class ElevenLabsBackend(TTSBackend):
    """ElevenLabs text-to-speech (https://elevenlabs.io)."""

    char_limit = ELEVENLABS_CHAR_LIMIT

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str | None = None,
        model_id: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.environ.get("ELEVENLABS_VOICE_ID")
        self.model_id = (
            model_id
            or os.environ.get("ELEVENLABS_MODEL_ID")
            or "eleven_multilingual_v2"
        )
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY is not set.")
        if not self.voice_id:
            raise ValueError("ELEVENLABS_VOICE_ID is not set.")

    def synthesize_chunk(self, text: str) -> bytes:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.content


class OpenAITTSBackend(TTSBackend):
    """OpenAI text-to-speech (https://platform.openai.com)."""

    char_limit = OPENAI_CHAR_LIMIT

    def __init__(
        self,
        api_key: str | None = None,
        voice: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.voice = voice or os.environ.get("OPENAI_TTS_VOICE") or "onyx"
        self.model = model or os.environ.get("OPENAI_TTS_MODEL") or "tts-1-hd"
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

    def synthesize_chunk(self, text: str) -> bytes:
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "voice": self.voice,
            "input": text,
            "response_format": "mp3",
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.content


def get_backend(name: str | None = None) -> TTSBackend:
    """Construct a backend by name (defaults to the ``TTS_BACKEND`` env var)."""

    name = (name or os.environ.get("TTS_BACKEND") or "elevenlabs").lower()
    if name == "elevenlabs":
        return ElevenLabsBackend()
    if name == "openai":
        return OpenAITTSBackend()
    raise ValueError(f"Unknown TTS backend: {name!r} (expected 'elevenlabs' or 'openai').")

"""Convert downloaded Paul Graham essays into narrated audio (MP3).

Pipeline:
    1. (optional) scrape essays into ``essays/`` via ``scrape_essays``.
    2. For every ``essays/*.txt`` file, synthesize narration with the chosen
       TTS backend and write ``audio/<slug>.mp3``.

The run is resumable: essays that already have an audio file are skipped
unless ``--overwrite`` is passed.
"""

from __future__ import annotations

import argparse
import os
import sys

try:  # Load .env if python-dotenv is installed; otherwise rely on the env.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - optional dependency
    pass

# Support running both as a module (``python -m src.convert``) and as a
# script (``python src/convert.py``).
if __package__:
    from .scrape_essays import download_essays
    from .tts import get_backend
else:  # pragma: no cover - script execution path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from scrape_essays import download_essays  # type: ignore
    from tts import get_backend  # type: ignore


def list_essay_files(essays_dir: str) -> list[str]:
    if not os.path.isdir(essays_dir):
        return []
    return sorted(
        os.path.join(essays_dir, name)
        for name in os.listdir(essays_dir)
        if name.endswith(".txt")
    )


def convert(
    essays_dir: str = "essays",
    audio_dir: str = "audio",
    backend_name: str | None = None,
    overwrite: bool = False,
    limit: int | None = None,
) -> None:
    os.makedirs(audio_dir, exist_ok=True)

    files = list_essay_files(essays_dir)
    if limit is not None:
        files = files[:limit]
    if not files:
        print(
            f"No essays found in {essays_dir!r}. Run with --scrape or run "
            "src/scrape_essays.py first."
        )
        return

    backend = get_backend(backend_name)
    print(f"Using TTS backend: {type(backend).__name__}")
    print(f"Converting {len(files)} essays...")
    for i, txt_path in enumerate(files, start=1):
        slug = os.path.splitext(os.path.basename(txt_path))[0]
        out_path = os.path.join(audio_dir, f"{slug}.mp3")
        if os.path.exists(out_path) and not overwrite:
            print(f"[{i}/{len(files)}] skip (exists): {slug}")
            continue

        with open(txt_path, encoding="utf-8") as handle:
            text = handle.read().strip()
        if not text:
            print(f"[{i}/{len(files)}] skip (empty): {slug}")
            continue

        print(f"[{i}/{len(files)}] narrating: {slug}")
        try:
            audio = backend.synthesize(text)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"[{i}/{len(files)}] ERROR {slug}: {exc}")
            continue

        with open(out_path, "wb") as handle:
            handle.write(audio)
        print(f"[{i}/{len(files)}] wrote: {out_path} ({len(audio)} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Narrate Paul Graham essays with AI text-to-speech."
    )
    parser.add_argument("--essays-dir", default="essays", help="Input text directory.")
    parser.add_argument("--audio-dir", default="audio", help="Output audio directory.")
    parser.add_argument(
        "--backend",
        default=None,
        help="TTS backend: 'elevenlabs' or 'openai' (defaults to $TTS_BACKEND).",
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Download essays first (skips ones already present).",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Regenerate audio that already exists."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Only process the first N essays."
    )
    args = parser.parse_args()

    if args.scrape:
        download_essays(out_dir=args.essays_dir, limit=args.limit)

    convert(
        essays_dir=args.essays_dir,
        audio_dir=args.audio_dir,
        backend_name=args.backend,
        overwrite=args.overwrite,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()

# Paul Graham Essays → AI Narration

A small, self-contained pipeline that downloads [Paul Graham's essays](http://www.paulgraham.com/articles.html)
and turns each one into a narrated **MP3 "talk"** using high-quality AI
text-to-speech.

It works in two steps:

1. **Scrape** – download every essay's text into `essays/`.
2. **Narrate** – synthesize each essay into `audio/<slug>.mp3` with the TTS
   backend of your choice.

The run is **resumable**: anything already downloaded or narrated is skipped
unless you pass `--overwrite`.

## Why these voice engines?

The narration quality is only as good as the TTS engine. Two pluggable
backends are included:

| Backend | Why | Env vars |
| --- | --- | --- |
| **ElevenLabs** (default) | The most natural / expressive AI narration today, and the simplest way to use a **custom or cloned voice**. | `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL_ID` |
| **OpenAI TTS** | Strong quality, lower cost, simple setup. | `OPENAI_API_KEY`, `OPENAI_TTS_VOICE`, `OPENAI_TTS_MODEL` |

You bring your own API key for whichever you choose.

## "Like him reading his essays" — voice, consent & copyright

> **Please read this before trying to clone Paul Graham's actual voice.**

To make the audio sound like *Paul Graham specifically* you would need a
**voice clone** of his real voice. Cloning a real person's voice **without
their consent** is, in many places, legally restricted and is against the
terms of service of the major TTS providers (including ElevenLabs and OpenAI).
It can also be ethically harmful (impersonation, deepfakes).

Because of that, this project **does not include or create any cloned voice.**
Instead it lets you choose any voice you are entitled to use:

- a **stock / pre-made** voice from your provider (recommended), or
- a **custom voice you have the rights to** — e.g. your own voice, or one for
  which you have explicit permission.

Set `ELEVENLABS_VOICE_ID` (or `OPENAI_TTS_VOICE`) to that voice. If you
genuinely want Paul Graham's voice, get his consent first.

Separately, the **essay text is Copyright © Paul Graham.** Downloading it for
your own personal listening is one thing; **redistributing** the text or the
generated audio is another — don't do that without permission.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: pick TTS_BACKEND and fill in the matching API key + voice
```

## Usage

Scrape and narrate everything in one go:

```bash
python -m src.convert --scrape
```

Or run the steps separately:

```bash
# 1. download all essays into essays/
python -m src.scrape_essays

# 2. narrate every essays/*.txt into audio/*.mp3
python -m src.convert
```

Useful flags:

```bash
python -m src.convert --scrape --limit 3        # try it on just 3 essays first
python -m src.convert --backend openai          # override $TTS_BACKEND
python -m src.convert --overwrite               # regenerate existing audio
python -m src.scrape_essays --out essays --delay 1.0
```

### Notes on the output

- Long essays are split into chunks that respect each provider's
  per-request character limit; the resulting MP3 segments are concatenated.
  Concatenated MP3s play fine in normal players. If you want a single
  re-encoded, gap-free file you can post-process with `ffmpeg`:

  ```bash
  ffmpeg -i audio/some-essay.mp3 -c:a libmp3lame audio/some-essay.clean.mp3
  ```

## Project layout

```
src/
  scrape_essays.py   # fetch the essay index + extract each essay's text
  tts.py             # pluggable TTS backends (ElevenLabs / OpenAI) + chunking
  convert.py         # CLI orchestrator: scrape -> narrate (resumable)
tests/
  test_pipeline.py   # offline tests (slugify, text extraction, chunking)
.env.example         # configuration template
requirements.txt
```

## Tests

Offline tests cover slugifying, HTML text extraction, and text chunking
(no network or API key required):

```bash
python tests/test_pipeline.py
```

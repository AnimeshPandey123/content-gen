# content-gen

Turn a research PDF into a short vertical video. The pipeline extracts and understands the document, uses Gemini to plan scenes and write narration, then renders inspectable media assets into a finished MP4.

## How it works

The workflow runs in two phases:

**AI planning** — reasoning about what to show and say:

```
PDF → Extract → Semantic Parse → Section Selection → Storyboard → Script
```

**Rendering** — deterministic asset production with no LLM calls:

```
Script → Screenshots → Voice → Subtitles → Video Assembly → final.mp4
```

Each rendering step writes reusable files to disk. If subtitles look wrong, regenerate only the `.ass` files. If you want a different voice, regenerate only the `.wav` files. Camera motion and FFmpeg assembly can be rerun without repeating the expensive AI steps.

## Output layout

For each document, assets are written under `output/{document_id}/`:

```
output/{document_id}/
  storyboard.json
  screenshots/scene01.png
  audio/scene01.wav
  subtitles/scene01.ass
  clips/scene01.mp4
  {document_id}.mp4
```

## Requirements

- Python 3.11+
- [FFmpeg](https://ffmpeg.org/) on your `PATH` (or set `FFMPEG_PATH`)
- A [Google Gemini API key](https://ai.google.dev/)

## Quick start

```bash
make install
cp .env.example .env   # add your GEMINI_API_KEY
make check-gemini
make run PDF=path/to/paper.pdf
```

Or run the CLI directly:

```bash
.venv/bin/python -m app.main path/to/paper.pdf
.venv/bin/python -m app.main path/to/paper.pdf --project-id my-run
```

The command prints a JSON summary of the final `RenderResult` to stdout.

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Model for section selection, storyboard, and script |
| `VOICE_SYNTHESIZER` | `gemini` | Voice backend: `gemini` or `silent` |
| `TTS_MODEL` | `gemini-2.5-flash-preview-tts` | Gemini TTS model |
| `TTS_VOICE` | `Kore` | Prebuilt Gemini voice name |
| `TTS_SAMPLE_RATE` | `24000` | Output WAV sample rate |
| `SECTION_SELECTION_LIMIT` | `5` | Max sections to include |
| `STORYBOARD_MAX_SCENES` | `8` | Max scenes in the storyboard |
| `OUTPUT_DIR` | `output` | Root directory for rendered assets |
| `VIDEO_WIDTH` / `VIDEO_HEIGHT` | `1080` / `1920` | Vertical video dimensions |
| `SCREENSHOT_DPI` | `300` | DPI for PDF page crops |
| `CAMERA_MOTION` | `ken_burns` | Camera effect (`zoom`, `pan`, `ken_burns`) |
| `WORDS_PER_MINUTE` | `150` | Narration pacing for audio duration |
| `FFMPEG_PATH` | `ffmpeg` | Path to the FFmpeg binary |

## Pipeline stages

| Stage | Input | Output |
|-------|-------|--------|
| Document extraction | PDF path | Structured document with page images |
| Semantic parsing | Document | Typed blocks (headings, paragraphs, figures) |
| Content planning | Document | Top sections selected by Gemini |
| Storyboard generation | Content plan | Scene goals, crops, and durations |
| Script generation | Storyboard | Voice narration and on-screen overlay text |
| Screenshot generation | Script plan | Cropped PNG per scene |
| Voice generation | Render project | WAV narration per scene |
| Subtitle generation | Render project | ASS karaoke subtitles per scene |
| Video rendering | Render project | Scene clips and final MP4 |

Stages are orchestrated by `PipelineCoordinator` with validation, structured logging, and retries.

## Development

```bash
make lint       # ruff check + format
make test       # pytest
make test-cov   # pytest with 100% coverage requirement
```

## Project structure

```
app/
  agents/          # Gemini client
  models/          # Pydantic data contracts
  prompts/         # LLM prompt templates
  render/          # Screenshot, voice, subtitle, FFmpeg assembly
  services/        # Business logic and pipeline stages
  workflows/       # Stage interface and coordinator
tests/             # Unit and integration tests
```

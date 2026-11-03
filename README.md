# Wuhan Bites

A small, testable pipeline for a short-video street-food channel about Wuhan, China.

```
topic -> script -> images -> voice -> assemble (ffmpeg) -> publish -> finance ledger
```

Every stage works out of the box in **offline/placeholder mode** (no API keys), so you can
run the whole pipeline end to end, then swap in real providers one stage at a time.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml     # edit later; defaults work offline
# ffmpeg must be installed and on PATH (brew install ffmpeg / apt install ffmpeg)

python -m wuhanbites.pipeline list-topics
python -m wuhanbites.pipeline run --topic re-gan-mian
```

Output lands in `output/<topic>/`: `script.json`, `images/`, `voice.mp3` (or `.wav`),
`video.mp4`, and `publish.json` (the upload manifest).

## Stages

| Stage | Module | Offline default | Real provider |
|---|---|---|---|
| Script | `script_gen.py` | Template from topic facts | Anthropic API (`ANTHROPIC_API_KEY`) |
| Images | `images.py` | Pillow title cards | Plug an image-generation API into `generate_image()` |
| Voice | `voice.py` | Silent track sized to script | `edge-tts` (free) if installed |
| Assemble | `assemble.py` | ffmpeg slideshow + audio, 9:16 | - |
| Publish | `publish.py` | Dry run, writes manifest | Add platform uploaders |
| Finance | `finance.py` | CSV ledger + summary | - |

## Finance ledger

```bash
python -m wuhanbites.finance add --kind cost --amount 4.50 --note "image credits"
python -m wuhanbites.finance add --kind income --amount 12.00 --note "creator fund" --platform tiktok
python -m wuhanbites.finance summary
```

Data is stored in `data/ledger.csv`.

## Notes

- Check each platform's policy on AI-generated content and label it as required.
- Verify food facts in `topics/*.yaml` before publishing; the script generator only uses what is in the topic file.
- Never commit `config.yaml` or API keys (they are git-ignored).

## Tests

```bash
pip install pytest && pytest -q
```

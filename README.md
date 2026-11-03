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
| Script | `script_gen.py` | Scenes from `topics/*.yaml` | Anthropic API (`ANTHROPIC_API_KEY`) |
| Images | `images.py` | Original flat illustrations drawn with Pillow | Google Imagen photos when `GEMINI_API_KEY` is set (`images.provider: auto`), with headline and subtitle drawn on top |
| Voice | `voice.py` | `auto`: edge-tts (internet), else macOS `say`, else silent | One clip per scene, so scene length follows the narration |
| Assemble | `assemble.py` | ffmpeg, 9:16, slow zoom, timed to narration | - |
| Publish | `publish.py` | Dry run, writes manifest | Add platform uploaders |
| Finance | `finance.py` | CSV ledger + summary | - |

## Voice and look

- `voice.provider: auto` tries `edge-tts` first (free, needs internet), then the macOS `say` voice (offline), then a silent track. The console prints which one was used.
- Pick a different voice with `voice.voice_name` (edge-tts, e.g. `en-US-GuyNeural`) or `voice.say_voice` (macOS, list with `say -v '?'`).
- If you copied `config.example.yaml` earlier, copy it again (or set `voice.provider: auto` and `images.provider: illustrated`) to pick up the new defaults.
- Scenes live in `topics/*.yaml`: `narration`, `caption` and `visual` (`skyline lanterns bowl pocket ring pot lotus wok follow`). Add a topic by copying one.
- The images are original illustrations, not photos. Say so if a platform asks whether content is AI-generated or illustrated.

## Mandarin version

```bash
python3 -m wuhanbites.pipeline run --topic re-gan-mian --lang zh     # output/re-gan-mian-zh/
```

- Uses the `narration_zh` / `caption_zh` / `title_zh` fields in `topics/*.yaml`, a Mandarin voice (`voice.voice_name_zh`, default `zh-CN-XiaoxiNeural`; male: `zh-CN-YunxiNeural`; macOS fallback `Tingting`) and Chinese subtitles (drawn with Noto Sans CJK, Hiragino Sans GB or PingFang).
- The upload gets a Chinese title, description and tags, and YouTube's language set to `zh-CN`.
- Set `language: zh` in `config.yaml` to make it the default.
- Have a native speaker review the Chinese text before publishing. There is no Wuhan-dialect voice; the voice speaks standard Mandarin.
- If the macOS voice is missing, download "Tingting" in System Settings -> Accessibility -> Spoken Content -> System Voice -> Manage Voices.

## Photo scenes with Google

Set a key and run as usual; every scene's `image_prompt` in `topics/*.yaml` becomes a photo:

```bash
export GEMINI_API_KEY=your_key        # Google AI Studio; Imagen needs billing enabled
python3 -m wuhanbites.pipeline run --topic re-gan-mian
```

- `images.provider: auto` (default) uses photos when the key exists, otherwise the local illustrations.
  Use `google` to require photos, `illustrated` to never call the API.
- A scene whose photo fails (quota, network, bad key) falls back to its illustration and prints a warning.
- Photos are cached in `cache/images/` (git-ignored), so re-running a topic costs nothing; edit an `image_prompt` to get a new image.
- Cheaper model: `images.google_model: imagen-4.0-fast-generate-001`.
- Text (headline, subtitle) is drawn by this code, not by the image model.
- AI-generated photos are not real photos of the dish. Disclose this to the platform (the uploader already sends the flag) and do not present them as documentary footage.

## Comparing image providers

Photo-style scenes need a text-to-image API key (not included). To compare providers side by side:

```bash
export GEMINI_API_KEY=...      # Google AI Studio key (Imagen needs billing enabled, as far as I know)
export OPENAI_API_KEY=...      # OpenAI key; set only one if you want just one provider
python3 -m wuhanbites.compare_images
open output/compare/sheet.png
```

It makes the same 3 scenes with each provider that has a key (costs a few cents per image).
Model names are options: `--google-model imagen-4.0-fast-generate-001`, `--openai-model gpt-image-1-mini`.
Keys are read from the environment only; never put them in `config.yaml` or commit them.

## Finance ledger

```bash
python -m wuhanbites.finance add --kind cost --amount 4.50 --note "image credits"
python -m wuhanbites.finance add --kind income --amount 12.00 --note "creator fund" --platform tiktok
python -m wuhanbites.finance summary
```

Data is stored in `data/ledger.csv`.

## Publishing to YouTube Shorts

Default is a dry run. Real uploads are opt-in and start as **private** videos.

One-time setup:

1. [Google Cloud Console](https://console.cloud.google.com/) -> create a project -> enable **YouTube Data API v3**.
2. APIs & Services -> OAuth consent screen: choose External, add your own Google account as a **test user**.
3. Credentials -> Create credentials -> **OAuth client ID** -> type **Desktop app** -> download the JSON.
4. Save it as `secrets/client_secret.json` (the `secrets/` folder is git-ignored; never commit it).
5. Install and log in:

```bash
pip install -r requirements-youtube.txt
python3 -m wuhanbites.pipeline auth-youtube      # opens a browser, saves secrets/youtube_token.json
```

Upload:

```bash
python3 -m wuhanbites.pipeline run --topic re-gan-mian --upload
```

Notes:

- Check `publish.youtube.privacy` in `config.yaml` (`private` by default). Review the video in YouTube Studio, then set it public there.
- Uploads from API projects that have not passed YouTube's audit are locked to private. Request an audit if you want public API uploads.
- Each upload costs about 1,600 of the default 10,000 daily quota units.
- The AI-content disclosure is sent automatically (`containsSyntheticMedia`).
- TikTok and Instagram Reels have no uploader yet; they are skipped.

## Notes

- Check each platform's policy on AI-generated content and label it as required.
- Verify food facts in `topics/*.yaml` before publishing; the script generator only uses what is in the topic file.
- Never commit `config.yaml` or API keys (they are git-ignored).

## Tests

```bash
pip install pytest && pytest -q
```

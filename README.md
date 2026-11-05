# Wuhan Bites

A small, testable pipeline for a short-video street-food channel about Wuhan, China.

```
topic -> script -> images -> voice -> assemble (ffmpeg) -> publish -> finance ledger
```

Every stage works out of the box in **offline/placeholder mode** (no API keys), so you can
run the whole pipeline end to end, then swap in real providers one stage at a time.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
# ffmpeg must be installed and on PATH (brew install ffmpeg / apt install ffmpeg)

python3 -m wuhanbites.pipeline list-topics
python3 -m wuhanbites.pipeline run --topic re-gan-mian
```

Output lands in `output/<topic>/`: `script.json`, `images/`, `voice.wav`,
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
- Image sources: the built-in scenes are original illustrations; Google scenes are AI-generated pictures, not real photos of the dish; your own photos in `assets/` are yours. Disclose AI-generated content as the platform requires (the uploader already sends YouTube's flag), and only use photos you own or are licensed to use.

## Using your own photos

Put a picture in `assets/` (git-ignored, so it stays on your computer) and point a scene at it in `topics/*.yaml`:

```yaml
- {visual: bowl, photo: tomato-egg-noodles.jpg, fit: contain, caption: "...", narration: "..."}
```

`fit: contain` shows the whole photo on a blurred background (best for small or landscape photos); `fit: cover` crops it to 9:16.
If the file is missing, the scene falls back to a generated or illustrated image. The `tomato-egg-noodles` topic is an example:
copy your photo to `assets/tomato-egg-noodles.jpg` and run `python3 -m wuhanbites.pipeline run --topic tomato-egg-noodles`.
Only use photos you own or have permission to use.

## Mandarin version

```bash
python3 -m wuhanbites.pipeline run --topic re-gan-mian --lang zh
```

- Uses the `narration_zh` / `caption_zh` / `title_zh` fields in `topics/*.yaml`, a Mandarin voice (`voice.voice_name_zh`, default `zh-CN-XiaoxiaoNeural`; male: `zh-CN-YunxiNeural`; macOS fallback `Tingting`) and Chinese subtitles (drawn with Noto Sans CJK, Hiragino Sans GB or PingFang).
- The upload gets a Chinese title, description and tags, and YouTube's language set to `zh-CN`.
- Set `language: zh` in `config.yaml` to make it the default.
- Have a native speaker review the Chinese text before publishing. There is no Wuhan-dialect voice; the voice speaks standard Mandarin.
- If the macOS voice is missing, download "Tingting" in System Settings -> Accessibility -> Spoken Content -> System Voice -> Manage Voices.

### Choosing and tuning the Mandarin voice

```bash
python3 -m wuhanbites.voice audition
open output/voice_samples
```

This makes a short sample in each of five Mandarin voices so you can pick one by ear. Set your choice in `config.yaml` as `voice.voice_name_zh`
(for example `zh-CN-YunxiNeural`). `python3 -m wuhanbites.voice list` shows every Chinese voice. Set `voice.rate` (for example `"+10%"`) to speak faster.
If a word is mispronounced, add a `tts_zh` field to that scene in `topics/*.yaml` with a respelled version for the voice to read; the on-screen text stays unchanged.

## Photo scenes with Google

Set a key and run as usual; every scene's `image_prompt` in `topics/*.yaml` becomes a photo:

```bash
export GEMINI_API_KEY=your_key
python3 -m wuhanbites.pipeline run --topic re-gan-mian
```

- Get the key from Google AI Studio. Imagen may require billing to be enabled on the Google account; if every scene fails with HTTP 400, the error message printed in the console says why.
- `images.provider: auto` (default) uses photos when the key exists, otherwise the local illustrations.
  Use `google` to require photos, `illustrated` to never call the API.
- A scene whose photo fails (quota, network, bad key) falls back to its illustration and prints a warning.
- Photos are cached in `cache/images/` (git-ignored), so re-running a topic costs nothing; edit an `image_prompt` to get a new image.
- `images.google_model: auto` asks Google which image model your key can use (Imagen, else a Gemini image model). See the list with `python3 -m wuhanbites.image_providers`, or set a model name yourself.
- Text (headline, subtitle) is drawn by this code, not by the image model.
- AI-generated photos are not real photos of the dish. Disclose this to the platform (the uploader already sends the flag) and do not present them as documentary footage.

## Comparing image providers

Photo-style scenes need a text-to-image API key (not included). To compare providers side by side:

```bash
export GEMINI_API_KEY=...
export OPENAI_API_KEY=...
python3 -m wuhanbites.compare_images
open output/compare/sheet.png
```

It makes the same 3 scenes with each provider that has a key (costs a few cents per image).
Model names are options: `--google-model <name>` (default `auto`), `--openai-model gpt-image-1-mini`.
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
5. Install and log in (the login opens a browser and saves `secrets/youtube_token.json`):

```bash
pip install -r requirements-youtube.txt
python3 -m wuhanbites.pipeline auth-youtube
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

- When pasting commands into a Mac terminal, paste only the command lines (not any `#` comments).
- Check each platform's policy on AI-generated content and label it as required.
- Verify food facts in `topics/*.yaml` before publishing; the script generator only uses what is in the topic file.
- Never commit `config.yaml` or API keys (they are git-ignored).

## Tests

```bash
pip install pytest && pytest -q
```

# Changelog

## wuhan-bite-v-0.1

First working version. Covers everything up to commit `be197f8`
("Validate config values and name the wrong setting").

- Pipeline: topic -> script -> images -> voice -> assemble (ffmpeg, 9:16) -> publish -> finance ledger.
- Topics: Re Gan Mian, Doupi, Mian Wo, Lotus Root and Pork Rib Soup, Tomato and Egg Noodles
  (the last uses a local photo from `assets/`).
- Languages: English and Mandarin (`--lang zh`), with Chinese subtitles and a Mandarin voice
  (`zh-CN-XiaoxiaoNeural` by default; `python3 -m wuhanbites.voice audition` to compare voices).
- Narration: edge-tts, then macOS `say`, then a silent track; one clip per scene so timing follows the speech.
- Images: original illustrations drawn locally; your own photos from `assets/`; optional Google image generation
  (needs a paid Google plan; falls back to illustrations when rejected).
- Publishing: dry run by default; YouTube Shorts uploader (`auth-youtube`, then `run --upload`), private by default,
  AI-content flag sent.
- Config checks: wrong setting values are reported with the line to fix.
- Not done yet: TikTok and Instagram uploaders, Wuhan-dialect voice, background music, native-speaker review of the Mandarin text.

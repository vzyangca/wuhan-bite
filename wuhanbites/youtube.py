"""YouTube Shorts uploader (YouTube Data API v3).

Setup (one time): see "Publishing to YouTube Shorts" in README.md.
Google libraries are imported lazily so the rest of the pipeline works without them.
"""
from __future__ import annotations

from pathlib import Path

from .common import ROOT

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DEFAULTS = {
    "client_secret": "secrets/client_secret.json",
    "token": "secrets/youtube_token.json",
    "privacy": "private",  # private | unlisted | public
    "category_id": "19",
}
VALID_PRIVACY = {"private", "unlisted", "public"}


def youtube_settings(config: dict) -> dict:
    s = dict(DEFAULTS)
    s.update(config.get("publish", {}).get("youtube", {}) or {})
    if s["privacy"] not in VALID_PRIVACY:
        raise ValueError(f"publish.youtube.privacy must be one of {sorted(VALID_PRIVACY)}")
    return s


def build_body(manifest: dict, config: dict) -> dict:
    """Pure function: the videos.insert request body. Easy to test, no network."""
    s = youtube_settings(config)
    title = manifest["title"].strip()
    if "#shorts" not in title.lower():
        title = f"{title[: 100 - len(' #Shorts')].rstrip()} #Shorts"
    description = manifest["description"].strip()
    if "#shorts" not in description.lower():
        description += "\n\n#Shorts"
    return {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": manifest.get("tags", []),
            "categoryId": str(s["category_id"]),
            "defaultLanguage": manifest.get("language", "en"),
            "defaultAudioLanguage": manifest.get("language", "en"),
        },
        "status": {
            "privacyStatus": s["privacy"],
            "selfDeclaredMadeForKids": False,
            # Discloses AI-generated / synthetic content to YouTube.
            "containsSyntheticMedia": bool(manifest.get("ai_generated_disclosure", True)),
        },
    }


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else ROOT / path


def get_credentials(config: dict, allow_login: bool = False):
    """Load saved credentials, refresh them, or (if allow_login) run the browser flow."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    s = youtube_settings(config)
    secret, token = _resolve(s["client_secret"]), _resolve(s["token"])
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not allow_login:
            raise SystemExit("Not logged in to YouTube. Run: python -m wuhanbites.pipeline auth-youtube")
        if not secret.exists():
            raise SystemExit(f"Missing {secret}. Download the OAuth client JSON (see README) and save it there.")
        creds = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES).run_local_server(port=0)
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(creds.to_json())
    return creds


def upload(manifest: dict, config: dict) -> dict:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = get_credentials(config)
    yt = build("youtube", "v3", credentials=creds)
    media = MediaFileUpload(manifest["video"], mimetype="video/mp4", resumable=True)
    request = yt.videos().insert(part="snippet,status", body=build_body(manifest, config), media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"youtube: uploaded {int(status.progress() * 100)}%")
    return {
        "id": response["id"],
        "url": f"https://youtube.com/shorts/{response['id']}",
        "privacy": response["status"]["privacyStatus"],
    }

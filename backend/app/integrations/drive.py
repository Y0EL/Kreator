from __future__ import annotations

import io
import json
import re
from pathlib import Path

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)
_settings = get_settings()
_LOCAL_DIR = Path(".drive_local")
_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80] or "untitled"


def _save_local(title: str, content: str) -> str:
    _LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    path = _LOCAL_DIR / f"{_slug(title)}.md"
    path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
    log.warning("drive.local_fallback", path=str(path))
    return path.resolve().as_uri()


def _drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    raw = _settings.google_service_account_json
    info = json.loads(raw) if raw.strip().startswith("{") else json.load(open(raw, encoding="utf-8"))
    creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def save_doc(title: str, content: str) -> str:
    if not _settings.google_service_account_json:
        return _save_local(title, content)
    try:
        from googleapiclient.http import MediaIoBaseUpload

        service = _drive_service()
        metadata: dict = {"name": title, "mimeType": "application/vnd.google-apps.document"}
        if _settings.google_drive_folder_id:
            metadata["parents"] = [_settings.google_drive_folder_id]
        media = MediaIoBaseUpload(
            io.BytesIO(content.encode("utf-8")), mimetype="text/plain", resumable=False
        )
        doc = (
            service.files()
            .create(body=metadata, media_body=media, fields="id,webViewLink")
            .execute()
        )
        url = doc.get("webViewLink", f"https://docs.google.com/document/d/{doc['id']}")
        log.info("drive.saved", title=title, url=url)
        return url
    except Exception as e:
        log.error("drive.save_failed", title=title, error=str(e))
        return _save_local(title, content)

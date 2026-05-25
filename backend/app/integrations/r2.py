from __future__ import annotations

import threading
from pathlib import Path

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)
_settings = get_settings()
_LOCAL_DIR = Path(".r2_local")


class _LocalStore:
    def put(self, key: str, body: bytes, content_type: str) -> str:
        path = _LOCAL_DIR / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return key

    def get(self, key: str) -> bytes:
        return (_LOCAL_DIR / key).read_bytes()


class _R2Store:
    def __init__(self) -> None:
        import boto3

        self._client = boto3.client(
            "s3",
            endpoint_url=_settings.r2_endpoint,
            aws_access_key_id=_settings.r2_access_key_id,
            aws_secret_access_key=_settings.r2_secret_access_key,
            region_name="auto",
        )
        self._bucket = _settings.r2_bucket

    def put(self, key: str, body: bytes, content_type: str) -> str:
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=body, ContentType=content_type
        )
        return key

    def get(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"].read()


_store: _LocalStore | _R2Store | None = None
_lock = threading.Lock()


def _get_store() -> _LocalStore | _R2Store:
    global _store
    if _store is None:
        with _lock:
            if _store is None:
                if _settings.r2_endpoint and _settings.r2_access_key_id and _settings.r2_bucket:
                    _store = _R2Store()
                    log.info("r2.store.cloud")
                else:
                    _store = _LocalStore()
                    log.warning("r2.store.local_fallback", dir=str(_LOCAL_DIR))
    return _store


def put_text(key: str, text: str, content_type: str = "text/plain; charset=utf-8") -> str:
    return _get_store().put(key, text.encode("utf-8"), content_type)


def get_text(key: str) -> str:
    return _get_store().get(key).decode("utf-8")


def raw_key(source_id: int, raw_hash: str, ext: str = "txt") -> str:
    return f"raw/{source_id}/{raw_hash}.{ext}"

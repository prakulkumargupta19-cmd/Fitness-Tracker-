"""Small Supabase Storage adapter for Vercel's ephemeral function runtime."""

import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class StorageConfigurationError(ValueError):
    pass


def _config():
    base_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    bucket = os.getenv("FIT_TRACK_STORAGE_BUCKET", "fit-track-uploads").strip()
    if not base_url or not service_key:
        return None
    return base_url, service_key, bucket


def _deployed():
    return os.getenv("VERCEL", "").lower() == "1" or os.getenv("VERCEL_ENV", "").lower() in {"preview", "production"}


def upload(relative_key, data, content_type=None, local_path=None):
    config = _config()
    if config is None:
        if _deployed():
            raise StorageConfigurationError("Configure SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and the Fit Track storage bucket in Vercel before uploading files.")
        if local_path is None:
            raise StorageConfigurationError("Local upload destination is unavailable.")
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_bytes(data)
        return
    base_url, service_key, bucket = config
    key = "/".join(part for part in relative_key.replace("\\", "/").split("/") if part)
    request = Request(
        f"{base_url}/storage/v1/object/{bucket}/{key}",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": content_type or mimetypes.guess_type(key)[0] or "application/octet-stream",
            "x-upsert": "true",
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            if response.status not in (200, 201):
                raise StorageConfigurationError("Supabase Storage rejected the upload.")
    except (HTTPError, URLError, TimeoutError) as error:
        raise StorageConfigurationError("Could not save the file to Supabase Storage. Check the bucket and service key.") from error


def download(relative_key):
    if not relative_key:
        return None
    config = _config()
    # Old local development files remain readable locally. Vercel never relies on
    # its temporary disk for files created by a deployed instance.
    if config is None:
        return None
    base_url, service_key, bucket = config
    key = "/".join(part for part in str(relative_key).replace("\\", "/").split("/") if part)
    request = Request(
        f"{base_url}/storage/v1/object/authenticated/{bucket}/{key}",
        headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
    )
    try:
        with urlopen(request, timeout=12) as response:
            return response.read(), response.headers.get("Content-Type") or mimetypes.guess_type(key)[0] or "application/octet-stream"
    except HTTPError as error:
        if error.code == 404:
            return None
        raise StorageConfigurationError("Could not retrieve the file from Supabase Storage.") from error
    except (URLError, TimeoutError) as error:
        raise StorageConfigurationError("Could not retrieve the file from Supabase Storage.") from error

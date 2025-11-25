from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
USER_AGENT = "trainer-test/1.0"


def _send_request(request: Request, timeout: int) -> bool:
    try:
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            if status is None or 200 <= status < 300:
                return True
            LOGGER.warning("Discord webhook responded with HTTP %s", status)
            return False
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        LOGGER.error("Discord webhook failed with HTTP %s: %s", exc.code, body)
    except URLError:
        LOGGER.exception("Unable to reach Discord webhook.")
    return False


def send_discord_notification(
    webhook_url: str,
    content: str,
    username: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    file_path: str | Path | None = None,
) -> bool:
    """Send a Discord webhook message, optionally with an attached file."""
    payload = {"content": content}
    if username:
        payload["username"] = username

    headers = {"User-Agent": USER_AGENT}

    if file_path:
        file_path = Path(file_path)
        if not file_path.exists():
            LOGGER.error("Attachment file not found: %s", file_path)
            return False

        boundary = uuid.uuid4().hex
        boundary_bytes = boundary.encode("utf-8")
        payload_bytes = json.dumps(payload).encode("utf-8")
        file_bytes = file_path.read_bytes()

        parts: list[bytes] = []
        parts.append(b"--" + boundary_bytes + b"\r\n")
        parts.append(b'Content-Disposition: form-data; name="payload_json"\r\n\r\n')
        parts.append(payload_bytes + b"\r\n")
        parts.append(b"--" + boundary_bytes + b"\r\n")
        parts.append(
            f'Content-Disposition: form-data; name="files[0]"; filename="{file_path.name}"\r\n'.encode(
                "utf-8"
            )
        )
        parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
        parts.append(file_bytes + b"\r\n")
        parts.append(b"--" + boundary_bytes + b"--\r\n")

        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    else:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        webhook_url,
        data=data,
        headers=headers,
        method="POST",
    )
    return _send_request(request, timeout)


__all__ = ["send_discord_notification"]


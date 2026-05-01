"""Google Drive: дозапись строк в inbox.md."""

from __future__ import annotations

import asyncio
import io
import logging

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

logger = logging.getLogger(__name__)

_SCOPES: tuple[str, ...] = ("https://www.googleapis.com/auth/drive",)
_INBOX_NAME: str = "inbox.md"
_INBOX_MIME: str = "text/markdown"


class DriveStorage:
    """Тонкая обёртка над Drive API: append-запись inbox.md."""

    def __init__(self, service_account_file: str, folder_id: str) -> None:
        self._service_account_file = service_account_file
        self._folder_id = folder_id
        self._lock = asyncio.Lock()
        self._service = self._build_service()

    def _build_service(self):  # type: ignore[no-untyped-def]
        credentials = Credentials.from_service_account_file(
            self._service_account_file, scopes=list(_SCOPES)
        )
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    async def append_inbox_line(self, line: str) -> None:
        """Дозаписывает `line` (без \\n) в inbox.md в целевой папке."""
        async with self._lock:
            await asyncio.to_thread(self._append_inbox_line_sync, line)

    def _append_inbox_line_sync(self, line: str) -> None:
        file_id = self._find_inbox_id()
        current = self._download(file_id)
        if current and not current.endswith("\n"):
            current += "\n"
        new_content = current + line + "\n"
        self._upload(file_id, new_content)

    def _find_inbox_id(self) -> str:
        query = (
            f"name = '{_INBOX_NAME}' "
            f"and '{self._folder_id}' in parents "
            "and mimeType != 'application/vnd.google-apps.folder' "
            "and trashed = false"
        )
        response = (
            self._service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                pageSize=2,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        files = response.get("files", [])
        if not files:
            raise RuntimeError(f"inbox.md not found in folder {self._folder_id}")
        return files[0]["id"]

    def _download(self, file_id: str) -> str:
        request = self._service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
        return buffer.getvalue().decode("utf-8")

    def _upload(self, file_id: str, content: str) -> None:
        media = MediaIoBaseUpload(
            io.BytesIO(content.encode("utf-8")),
            mimetype=_INBOX_MIME,
            resumable=False,
        )
        self._service.files().update(
            fileId=file_id,
            media_body=media,
            supportsAllDrives=True,
        ).execute()

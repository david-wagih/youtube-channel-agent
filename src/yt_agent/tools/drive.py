"""Google Drive integration tool for downloading videos."""

import re
import tempfile
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, SpinnerColumn, TextColumn

from ..auth import OAuthManager
from ..config import get_credentials_dir
from ..exceptions import AuthError
from .base import BaseTool, ToolResult

console = Console()

# Google Drive API scopes
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def extract_file_id(url_or_id: str) -> str:
    """Extract Google Drive file ID from URL or return as-is if already an ID.

    Supported URL formats:
    - https://drive.google.com/file/d/FILE_ID/view
    - https://drive.google.com/open?id=FILE_ID
    - https://docs.google.com/document/d/FILE_ID/edit
    - https://drive.google.com/uc?id=FILE_ID
    - Just the FILE_ID directly

    Args:
        url_or_id: Google Drive URL or file ID.

    Returns:
        The extracted file ID.
    """
    # Pattern for /d/FILE_ID/ format
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)

    # Pattern for ?id=FILE_ID format
    match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)

    # Assume it's already a file ID if no URL pattern matched
    if re.match(r"^[a-zA-Z0-9_-]+$", url_or_id):
        return url_or_id

    raise ValueError(f"Could not extract file ID from: {url_or_id}")


class GoogleDriveTool(BaseTool):
    """Tool for downloading files from Google Drive."""

    def __init__(self):
        self._service = None
        self._oauth = OAuthManager(
            service_name="Google Drive",
            scopes=SCOPES,
            token_filename="drive_token.json",
            port=8081,
        )

    @property
    def name(self) -> str:
        return "google_drive"

    @property
    def description(self) -> str:
        return "Download videos and files from Google Drive"

    def is_available(self) -> bool:
        """Check if Drive credentials are configured."""
        return (get_credentials_dir() / "client_secrets.json").exists()

    def authenticate(self) -> bool:
        """Run OAuth flow to authenticate with Google Drive.

        Returns:
            True if authentication succeeded.
        """
        try:
            self._oauth.authenticate()
            return True
        except AuthError as e:
            console.print(f"[bold red]Authentication failed:[/bold red] {e}")
            return False

    def _get_service(self):
        """Get authenticated Drive API service (cached)."""
        if self._service:
            return self._service
        creds = self._oauth.get_valid_credentials()
        self._service = build("drive", "v3", credentials=creds)
        return self._service

    def execute(self, **kwargs) -> ToolResult:
        """Execute a Drive operation.

        Supported operations:
        - download: Download a file
        - info: Get file info
        """
        operation = kwargs.get("operation", "download")

        if operation == "download":
            return self._download(**kwargs)
        elif operation == "info":
            return self._get_info(**kwargs)
        else:
            return ToolResult(
                success=False,
                error=f"Unknown operation: {operation}",
            )

    def download_video(
        self,
        url_or_id: str,
        output_dir: str | Path | None = None,
    ) -> Path:
        """Download a video from Google Drive.

        Args:
            url_or_id: Google Drive URL or file ID.
            output_dir: Directory to save the file. Defaults to temp directory.

        Returns:
            Path to the downloaded file.
        """
        file_id = extract_file_id(url_or_id)
        service = self._get_service()

        # Get file metadata
        file_metadata = (
            service.files()
            .get(
                fileId=file_id,
                fields="name,size,mimeType",
            )
            .execute()
        )

        file_name = file_metadata.get("name", f"{file_id}.mp4")
        file_size = int(file_metadata.get("size", 0))
        file_metadata.get("mimeType", "")

        console.print(f"[bold]Downloading:[/bold] {file_name}")
        if file_size:
            size_mb = file_size / (1024 * 1024)
            console.print(f"Size: {size_mb:.1f} MB")

        # Determine output path
        if output_dir:
            output_path = Path(output_dir) / file_name
        else:
            # Use temp directory
            temp_dir = Path(tempfile.gettempdir()) / "yt-agent"
            temp_dir.mkdir(exist_ok=True)
            output_path = temp_dir / file_name

        # Download the file
        request = service.files().get_media(fileId=file_id)

        with open(output_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Downloading...", total=file_size or 100)

                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        progress.update(task, completed=int(status.progress() * (file_size or 100)))

        console.print(f"[green]Downloaded to:[/green] {output_path}")
        return output_path

    def get_file_info(self, url_or_id: str) -> dict:
        """Get information about a file.

        Args:
            url_or_id: Google Drive URL or file ID.

        Returns:
            Dictionary with file metadata.
        """
        file_id = extract_file_id(url_or_id)
        service = self._get_service()

        metadata = (
            service.files()
            .get(
                fileId=file_id,
                fields="id,name,size,mimeType,createdTime,modifiedTime",
            )
            .execute()
        )

        return {
            "id": metadata.get("id"),
            "name": metadata.get("name"),
            "size": int(metadata.get("size", 0)),
            "mime_type": metadata.get("mimeType"),
            "created": metadata.get("createdTime"),
            "modified": metadata.get("modifiedTime"),
        }

    def _download(self, **kwargs) -> ToolResult:
        """Internal download wrapper."""
        try:
            path = self.download_video(
                url_or_id=kwargs["url"],
                output_dir=kwargs.get("output_dir"),
            )
            return ToolResult(success=True, data={"path": str(path)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _get_info(self, **kwargs) -> ToolResult:
        """Internal info wrapper."""
        try:
            info = self.get_file_info(kwargs["url"])
            return ToolResult(success=True, data=info)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

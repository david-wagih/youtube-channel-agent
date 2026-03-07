"""Google Drive integration tool for downloading videos."""

import io
import re
import tempfile
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn

from ..config import get_credentials_dir
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
        self._credentials = None

    @property
    def name(self) -> str:
        return "google_drive"

    @property
    def description(self) -> str:
        return "Download videos and files from Google Drive"

    def is_available(self) -> bool:
        """Check if Drive credentials are configured."""
        creds_dir = get_credentials_dir()
        client_secrets = creds_dir / "client_secrets.json"
        return client_secrets.exists()

    def _get_credentials_path(self) -> Path:
        """Get path to stored OAuth token."""
        return get_credentials_dir() / "drive_token.json"

    def _get_client_secrets_path(self) -> Path:
        """Get path to client secrets file."""
        return get_credentials_dir() / "client_secrets.json"

    def _load_credentials(self) -> Credentials | None:
        """Load credentials from stored token file."""
        token_path = self._get_credentials_path()

        if not token_path.exists():
            return None

        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_credentials(creds)

        return creds

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        token_path = self._get_credentials_path()
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    def authenticate(self) -> bool:
        """Run OAuth flow to authenticate with Google Drive.

        Returns:
            True if authentication successful.
        """
        client_secrets = self._get_client_secrets_path()

        if not client_secrets.exists():
            console.print(
                "[bold red]Error:[/bold red] client_secrets.json not found.\n"
                f"Please download it from Google Cloud Console and save to:\n"
                f"  {client_secrets}"
            )
            return False

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets),
                SCOPES,
            )

            console.print("[bold]Opening browser for Google Drive authentication...[/bold]")
            creds = flow.run_local_server(port=8081)

            self._save_credentials(creds)
            self._credentials = creds
            console.print("[bold green]Google Drive authentication successful![/bold green]")
            return True

        except Exception as e:
            console.print(f"[bold red]Authentication failed:[/bold red] {e}")
            return False

    def _get_service(self):
        """Get authenticated Drive API service."""
        if self._service:
            return self._service

        # Try to load existing credentials
        creds = self._load_credentials()

        if not creds or not creds.valid:
            # Need to authenticate
            if not self.authenticate():
                raise RuntimeError("Google Drive authentication required")
            creds = self._credentials

        self._service = build("drive", "v3", credentials=creds)
        return self._service

    async def execute(self, **kwargs) -> ToolResult:
        """Execute a Drive operation.

        Supported operations:
        - download: Download a file
        - info: Get file info
        """
        operation = kwargs.get("operation", "download")

        if operation == "download":
            return await self._download(**kwargs)
        elif operation == "info":
            return await self._get_info(**kwargs)
        else:
            return ToolResult(
                success=False,
                error=f"Unknown operation: {operation}",
            )

    async def download_video(
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
        file_metadata = service.files().get(
            fileId=file_id,
            fields="name,size,mimeType",
        ).execute()

        file_name = file_metadata.get("name", f"{file_id}.mp4")
        file_size = int(file_metadata.get("size", 0))
        mime_type = file_metadata.get("mimeType", "")

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

    async def get_file_info(self, url_or_id: str) -> dict:
        """Get information about a file.

        Args:
            url_or_id: Google Drive URL or file ID.

        Returns:
            Dictionary with file metadata.
        """
        file_id = extract_file_id(url_or_id)
        service = self._get_service()

        metadata = service.files().get(
            fileId=file_id,
            fields="id,name,size,mimeType,createdTime,modifiedTime",
        ).execute()

        return {
            "id": metadata.get("id"),
            "name": metadata.get("name"),
            "size": int(metadata.get("size", 0)),
            "mime_type": metadata.get("mimeType"),
            "created": metadata.get("createdTime"),
            "modified": metadata.get("modifiedTime"),
        }

    async def _download(self, **kwargs) -> ToolResult:
        """Internal download wrapper."""
        try:
            path = await self.download_video(
                url_or_id=kwargs["url"],
                output_dir=kwargs.get("output_dir"),
            )
            return ToolResult(success=True, data={"path": str(path)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _get_info(self, **kwargs) -> ToolResult:
        """Internal info wrapper."""
        try:
            info = await self.get_file_info(kwargs["url"])
            return ToolResult(success=True, data=info)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

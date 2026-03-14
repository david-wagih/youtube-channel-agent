"""Shared OAuth 2.0 credential management for Google APIs."""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from rich.console import Console

from ..exceptions import AuthError

console = Console()


class OAuthManager:
    """Manages OAuth 2.0 credentials for a single Google API service.

    Handles credential loading, automatic refresh, token persistence, and
    the interactive browser-based OAuth flow.  One instance per service
    (YouTube, Drive, …).

    Args:
        service_name: Human-readable name shown in browser-prompt messages.
        scopes: OAuth scopes required by the service.
        token_filename: Filename for the stored token (e.g. "youtube_token.json").
        port: Localhost port for the OAuth redirect server.
    """

    def __init__(
        self,
        service_name: str,
        scopes: list[str],
        token_filename: str,
        port: int = 8080,
    ) -> None:
        self.service_name = service_name
        self.scopes = scopes
        self.token_filename = token_filename
        self.port = port

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    @property
    def _credentials_dir(self) -> Path:
        from ..config import get_credentials_dir

        return get_credentials_dir()

    @property
    def token_path(self) -> Path:
        return self._credentials_dir / self.token_filename

    @property
    def client_secrets_path(self) -> Path:
        return self._credentials_dir / "client_secrets.json"

    # ------------------------------------------------------------------
    # Credential lifecycle
    # ------------------------------------------------------------------

    def load_credentials(self) -> Credentials | None:
        """Load stored credentials, refreshing them if expired.

        Returns:
            Valid Credentials, or None if no token file exists.
        """
        if not self.token_path.exists():
            return None

        creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_credentials(creds)

        return creds

    def _save_credentials(self, creds: Credentials) -> None:
        with open(self.token_path, "w") as f:
            f.write(creds.to_json())

    def authenticate(self) -> Credentials:
        """Run the interactive OAuth browser flow.

        Returns:
            Freshly obtained and persisted Credentials.

        Raises:
            AuthError: If client_secrets.json is missing or the flow fails.
        """
        if not self.client_secrets_path.exists():
            raise AuthError(
                f"client_secrets.json not found. "
                f"Please download it from Google Cloud Console and save to:\n"
                f"  {self.client_secrets_path}"
            )

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets_path),
                self.scopes,
            )
            console.print(
                f"[bold]Opening browser for {self.service_name} authentication...[/bold]"
            )
            creds = flow.run_local_server(port=self.port)
        except Exception as e:
            raise AuthError(f"{self.service_name} authentication failed: {e}") from e

        self._save_credentials(creds)
        console.print(
            f"[bold green]{self.service_name} authentication successful![/bold green]"
        )
        return creds

    def get_valid_credentials(self) -> Credentials:
        """Return valid credentials, running the auth flow if needed.

        Raises:
            AuthError: If credentials cannot be obtained.
        """
        creds = self.load_credentials()
        if creds and creds.valid:
            return creds
        return self.authenticate()

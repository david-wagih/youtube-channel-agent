"""Video transcription tool using Google Speech-to-Text."""

import tempfile
import uuid
from pathlib import Path

from google.cloud import speech
from google.cloud import storage
from rich.console import Console

from ..config import settings
from .base import BaseTool, ToolResult


console = Console()


class TranscriptionTool(BaseTool):
    """Tool for transcribing video audio using Google Speech-to-Text."""

    def __init__(self):
        self._speech_client = None
        self._storage_client = None

    @property
    def name(self) -> str:
        return "transcribe"

    @property
    def description(self) -> str:
        return "Transcribe video/audio content using Google Speech-to-Text"

    def is_available(self) -> bool:
        """Check if Google Cloud credentials are configured."""
        import os
        # Check for GOOGLE_APPLICATION_CREDENTIALS env var
        return bool(
            settings.google_application_credentials
            or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        )

    def _get_speech_client(self) -> speech.SpeechClient:
        """Get Speech-to-Text client."""
        if self._speech_client is None:
            self._speech_client = speech.SpeechClient()
        return self._speech_client

    def _get_storage_client(self) -> storage.Client:
        """Get Cloud Storage client."""
        if self._storage_client is None:
            self._storage_client = storage.Client()
        return self._storage_client

    def _upload_to_gcs(self, local_path: Path) -> str:
        """Upload audio file to GCS for long-running recognition.

        Args:
            local_path: Path to local audio file.

        Returns:
            GCS URI (gs://bucket/path).
        """
        if not settings.gcs_bucket:
            raise RuntimeError(
                "GCS bucket not configured. Set GCS_BUCKET in .env for videos longer than 1 minute."
            )

        client = self._get_storage_client()
        bucket = client.bucket(settings.gcs_bucket)

        # Use unique name to avoid collisions
        blob_name = f"yt-agent-transcripts/{uuid.uuid4()}/{local_path.name}"
        blob = bucket.blob(blob_name)

        console.print(f"[dim]Uploading audio to GCS ({local_path.stat().st_size / 1024 / 1024:.1f} MB)...[/dim]")
        blob.upload_from_filename(str(local_path))

        return f"gs://{settings.gcs_bucket}/{blob_name}"

    def _delete_from_gcs(self, gcs_uri: str) -> None:
        """Delete audio file from GCS after transcription."""
        try:
            # Parse gs://bucket/path
            parts = gcs_uri.replace("gs://", "").split("/", 1)
            bucket_name, blob_name = parts[0], parts[1]

            client = self._get_storage_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
        except Exception:
            # Non-critical, just log
            console.print("[dim]Warning: Could not clean up GCS file[/dim]")

    async def execute(self, **kwargs) -> ToolResult:
        """Execute transcription.

        Args:
            video_path: Path to video file.
            language: Language code (default: en-US).
        """
        try:
            transcript = await self.transcribe_video(
                video_path=kwargs["video_path"],
                language=kwargs.get("language", "en-US"),
            )
            return ToolResult(success=True, data={"transcript": transcript})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _extract_audio(self, video_path: Path) -> Path:
        """Extract audio from video file.

        Args:
            video_path: Path to video file.

        Returns:
            Path to extracted audio file (WAV format).
        """
        from moviepy.video.io.VideoFileClip import VideoFileClip

        console.print("[dim]Extracting audio from video...[/dim]")

        # Create temp file for audio
        temp_dir = Path(tempfile.gettempdir()) / "yt-agent"
        temp_dir.mkdir(exist_ok=True)
        audio_path = temp_dir / f"{video_path.stem}_audio.wav"

        # Extract audio
        video = VideoFileClip(str(video_path))
        video.audio.write_audiofile(
            str(audio_path),
            fps=16000,
            nbytes=2,
            codec="pcm_s16le",
            ffmpeg_params=["-ac", "1"],  # force mono
            logger=None,
        )
        video.close()

        return audio_path

    async def transcribe_video(
        self,
        video_path: str | Path,
        language: str = "en-US",
    ) -> str:
        """Transcribe a video file.

        Args:
            video_path: Path to video file.
            language: Language code (e.g., "en-US", "ar-EG").

        Returns:
            Full transcript text.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if not self.is_available():
            raise RuntimeError(
                "Google Cloud credentials not configured. "
                "Set GOOGLE_APPLICATION_CREDENTIALS environment variable."
            )

        # Extract audio from video
        audio_path = self._extract_audio(video_path)

        # Check audio duration
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        audio_clip = AudioFileClip(str(audio_path))
        duration = audio_clip.duration
        audio_clip.close()

        client = self._get_speech_client()

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language,
            enable_automatic_punctuation=True,
            model="latest_long",
        )

        full_transcript = []
        gcs_uri = None

        try:
            if duration > 55:
                # Use long-running recognition with GCS for audio > ~1 minute
                # Using 55s threshold to have some buffer
                console.print(f"[dim]Video is {duration:.0f}s, using long-running transcription...[/dim]")

                gcs_uri = self._upload_to_gcs(audio_path)
                audio = speech.RecognitionAudio(uri=gcs_uri)

                with console.status("[bold green]Transcribing (this may take a while for long videos)..."):
                    operation = client.long_running_recognize(config=config, audio=audio)
                    response = operation.result(timeout=600)  # 10 minute timeout

                for result in response.results:
                    full_transcript.append(result.alternatives[0].transcript)
            else:
                # Use synchronous recognition for short audio
                with open(audio_path, "rb") as f:
                    content = f.read()

                audio = speech.RecognitionAudio(content=content)

                with console.status("[bold green]Transcribing..."):
                    response = client.recognize(config=config, audio=audio)

                for result in response.results:
                    full_transcript.append(result.alternatives[0].transcript)

        finally:
            # Clean up local audio file
            audio_path.unlink(missing_ok=True)

            # Clean up GCS file if uploaded
            if gcs_uri:
                self._delete_from_gcs(gcs_uri)

        transcript = " ".join(full_transcript)
        console.print(f"[green]Transcription complete![/green] ({len(transcript)} characters)")

        return transcript

    async def transcribe_with_timestamps(
        self,
        video_path: str | Path,
        language: str = "en-US",
    ) -> list[dict]:
        """Transcribe video with word-level timestamps.

        Args:
            video_path: Path to video file.
            language: Language code.

        Returns:
            List of dicts with 'word', 'start_time', 'end_time'.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if not self.is_available():
            raise RuntimeError("Google Cloud credentials not configured.")

        # Extract audio
        audio_path = self._extract_audio(video_path)

        # Check audio duration
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        audio_clip = AudioFileClip(str(audio_path))
        duration = audio_clip.duration
        audio_clip.close()

        client = self._get_speech_client()

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language,
            enable_word_time_offsets=True,
            enable_automatic_punctuation=True,
            model="latest_long",
        )

        words = []
        gcs_uri = None

        try:
            if duration > 55:
                # Use long-running recognition with GCS
                console.print(f"[dim]Video is {duration:.0f}s, using long-running transcription...[/dim]")

                gcs_uri = self._upload_to_gcs(audio_path)
                audio = speech.RecognitionAudio(uri=gcs_uri)

                with console.status("[bold green]Transcribing with timestamps (this may take a while)..."):
                    operation = client.long_running_recognize(config=config, audio=audio)
                    response = operation.result(timeout=600)
            else:
                # Use synchronous recognition for short audio
                with open(audio_path, "rb") as f:
                    content = f.read()

                audio = speech.RecognitionAudio(content=content)

                with console.status("[bold green]Transcribing with timestamps..."):
                    response = client.recognize(config=config, audio=audio)

            for result in response.results:
                for word_info in result.alternatives[0].words:
                    words.append({
                        "word": word_info.word,
                        "start_time": word_info.start_time.total_seconds(),
                        "end_time": word_info.end_time.total_seconds(),
                    })

        finally:
            # Clean up local audio file
            audio_path.unlink(missing_ok=True)

            # Clean up GCS file if uploaded
            if gcs_uri:
                self._delete_from_gcs(gcs_uri)

        return words


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS timestamp.

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted timestamp string.
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

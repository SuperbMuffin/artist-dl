"""Defaults and config loading for artist-dl."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CONFIG_PATHS = [
    Path.home() / ".config" / "artist-dl" / "config.toml",
    Path.home() / ".artist-dl.toml",
    Path("artist-dl.toml"),  # local project override
]

DEFAULT_MUSIC_DIR = Path.home() / "Music"
DEFAULT_FORMAT = "ba[abr>200]/bestaudio/best"
DEFAULT_AUDIO_CODEC = "m4a"
DEFAULT_AUDIO_QUALITY = "0"  # VBR best (maps to ~256kbps for opus)
DEFAULT_CONTAINER = "m4a"


@dataclass
class Config:
    music_dir: Path = field(default_factory=lambda: DEFAULT_MUSIC_DIR)
    audio_format: str = DEFAULT_FORMAT
    audio_codec: str = DEFAULT_AUDIO_CODEC
    audio_quality: str = DEFAULT_AUDIO_QUALITY
    container: str = DEFAULT_CONTAINER
    concurrent_fragment_downloads: int = 4
    retries: int = 5
    rate_limit: Optional[str] = None          # e.g. "2M" to cap bandwidth
    sponsorblock_remove: list[str] = field(   # remove these SponsorBlock cats
        default_factory=lambda: []
    )
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    verbose: bool = False

    # Output template tokens:
    #   %(artist)s  – channel/uploader name (fallback to uploader)
    #   %(upload_date>%Y-%m-%d)s – formatted date
    #   %(title)s   – video title
    #   %(ext)s     – file extension after post-processing
    outtmpl_artist_subdir: bool = True  # put files in Artist/ subfolder

    @classmethod
    def load(cls) -> "Config":
        """Load config from the first config file found, with dataclass defaults."""
        cfg: dict = {}
        for path in CONFIG_PATHS:
            if path.exists():
                with open(path, "rb") as f:
                    cfg = tomllib.load(f)
                break

        return cls(
            music_dir=Path(cfg.get("music_dir", DEFAULT_MUSIC_DIR)).expanduser(),
            audio_format=cfg.get("audio_format", DEFAULT_FORMAT),
            audio_codec=cfg.get("audio_codec", DEFAULT_AUDIO_CODEC),
            audio_quality=str(cfg.get("audio_quality", DEFAULT_AUDIO_QUALITY)),
            container=cfg.get("container", DEFAULT_CONTAINER),
            concurrent_fragment_downloads=cfg.get("concurrent_fragment_downloads", 4),
            retries=cfg.get("retries", 5),
            rate_limit=cfg.get("rate_limit", None),
            sponsorblock_remove=cfg.get("sponsorblock_remove", []),
            embed_thumbnail=cfg.get("embed_thumbnail", True),
            embed_metadata=cfg.get("embed_metadata", True),
            verbose=cfg.get("verbose", False),
            outtmpl_artist_subdir=cfg.get("outtmpl_artist_subdir", True),
        )

    def build_outtmpl(self, base_dir: Path) -> str:
        """Return yt-dlp outtmpl string rooted at base_dir."""
        if self.outtmpl_artist_subdir:
            # Artist sub-folder based on uploader/channel name
            return str(
                base_dir / "%(uploader,channel,artist)s"
                         / "%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s"
            )
        return str(base_dir / "%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s")

    def build_ydl_opts(
        self,
        base_dir: Path,
        *,
        after: Optional[str] = None,
        before: Optional[str] = None,
        dry_run: bool = False,
        archive: Optional[Path] = None,
    ) -> dict:
        """Assemble the full yt_dlp options dict."""
        postprocessors: list[dict] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": self.audio_codec,
                "preferredquality": self.audio_quality,
            }
        ]
        if self.embed_thumbnail:
            postprocessors.append({"key": "EmbedThumbnail"})
        if self.embed_metadata:
            postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
        if self.sponsorblock_remove:
            postprocessors.append(
                {
                    "key": "SponsorBlock",
                    "categories": self.sponsorblock_remove,
                    "when": "after_filter",
                }
            )
            postprocessors.append(
                {
                    "key": "ModifyChapters",
                    "remove_sponsor_segments": self.sponsorblock_remove,
                }
            )

        opts: dict = {
            "format": self.audio_format,
            "postprocessors": postprocessors,
            "outtmpl": self.build_outtmpl(base_dir),
            "concurrent_fragment_downloads": self.concurrent_fragment_downloads,
            "retries": self.retries,
            "quiet": not self.verbose,
            "no_warnings": not self.verbose,
            "simulate": dry_run,
            "writethumbnail": self.embed_thumbnail,
            "ignoreerrors": True,   # skip unavailable videos, keep going
        }

        if after:
            opts["dateafter"] = after
        if before and before.lower() != "now":
            opts["datebefore"] = before
        if archive:
            opts["download_archive"] = str(archive)
        if self.rate_limit:
            opts["ratelimit"] = self.rate_limit

        return opts

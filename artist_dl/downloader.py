"""Core download and outline logic for artist-dl."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yt_dlp

from .config import Config


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

_RELATIVE_RE = re.compile(
    r"^now(?:-(\d+)(year|month|week|day)s?)?$", re.IGNORECASE
)


def resolve_date(date_str: str) -> str:
    """
    Resolve a date string to YYYYMMDD format.

    Accepts:
      - 'now'               → today
      - 'now-2years'        → today minus 2 years
      - 'now-6months'       → today minus ~6 months
      - 'now-3weeks'        → today minus 3 weeks
      - 'now-10days'        → today minus 10 days
      - 'YYYYMMDD'          → returned as-is after validation
    """
    m = _RELATIVE_RE.match(date_str.strip())
    if m:
        today = datetime.today()
        if m.group(1) is None:
            return today.strftime("%Y%m%d")
        amount = int(m.group(1))
        unit = m.group(2).lower()
        if unit == "year":
            result = today.replace(year=today.year - amount)
        elif unit == "month":
            # approximate: subtract 30 days per month
            result = today - timedelta(days=amount * 30)
        elif unit == "week":
            result = today - timedelta(weeks=amount)
        else:  # day
            result = today - timedelta(days=amount)
        return result.strftime("%Y%m%d")

    # Validate absolute YYYYMMDD
    cleaned = date_str.replace("-", "").strip()
    try:
        datetime.strptime(cleaned, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(
            f"Unrecognised date format '{date_str}'. "
            "Use YYYYMMDD or relative: now, now-2years, now-6months, now-3weeks, now-10days."
        ) from exc
    return cleaned


# ---------------------------------------------------------------------------
# Outline / preview
# ---------------------------------------------------------------------------

def _fmt_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "unknown"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _fmt_date(raw: Optional[str]) -> str:
    """Convert YYYYMMDD → YYYY-MM-DD."""
    if not raw or len(raw) != 8:
        return raw or "unknown"
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def generate_outline(
    url: str,
    cfg: Config,
    *,
    after: Optional[str] = None,
    before: Optional[str] = None,
    json_out: bool = False,
) -> str:
    """
    Fetch playlist/channel metadata and return a markdown outline string.
    No audio is downloaded.
    """
    # We use flat_playlist to fetch metadata quickly (no individual page loads)
    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
    }
    if after:
        ydl_opts["dateafter"] = after
    if before and before.lower() != "now":
        ydl_opts["datebefore"] = before

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info is None:
        return "# Error: could not fetch info from URL\n"

    if json_out:
        return json.dumps(info, indent=2, default=str)

    entries = info.get("entries") or []

    # Filter by date if we have dates (flat extraction may not have upload_date)
    after_dt = datetime.strptime(after, "%Y%m%d") if after else None
    before_dt = datetime.strptime(before, "%Y%m%d") if before and before != "now" else None

    filtered = []
    skipped_no_date = 0
    for e in entries:
        ud = e.get("upload_date")
        if ud:
            try:
                dt = datetime.strptime(ud, "%Y%m%d")
                if after_dt and dt < after_dt:
                    continue
                if before_dt and dt > before_dt:
                    continue
            except ValueError:
                pass
        else:
            skipped_no_date += 1
        filtered.append(e)

    uploader = info.get("uploader") or info.get("channel") or info.get("title") or "Unknown"
    playlist_title = info.get("title") or uploader
    total = len(entries)
    shown = len(filtered)

    lines: list[str] = [
        f"# {playlist_title}",
        f"**Channel:** {uploader}",
        f"**URL:** {url}",
        f"**Filter:** after={after or 'none'}  before={before or 'none'}",
        f"**Showing:** {shown} of {total} tracks",
    ]
    if skipped_no_date:
        lines.append(f"> ⚠ {skipped_no_date} entries had no upload_date (included above)")
    lines.append("")

    for i, e in enumerate(filtered, 1):
        title = e.get("title") or e.get("id") or "Untitled"
        date = _fmt_date(e.get("upload_date"))
        duration = _fmt_duration(e.get("duration"))
        page_url = e.get("url") or e.get("webpage_url") or ""
        lines.append(f"{i}. **{title}**")
        lines.append(f"   - Date: {date}  |  Duration: {duration}")
        if page_url:
            lines.append(f"   - <{page_url}>")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

class ProgressLogger:
    """Minimal yt-dlp logger that plays nicely with Typer output."""

    def debug(self, msg: str) -> None:  # noqa: D401
        if msg.startswith("[debug]"):
            return
        print(msg)

    def info(self, msg: str) -> None:
        print(msg)

    def warning(self, msg: str) -> None:
        print(f"⚠  {msg}")

    def error(self, msg: str) -> None:
        print(f"✗  {msg}")


def download_catalog(
    url: str,
    cfg: Config,
    base_dir: Path,
    *,
    after: Optional[str] = None,
    before: Optional[str] = None,
    dry_run: bool = False,
    use_archive: bool = True,
    verbose: bool = False,
) -> None:
    """
    Download audio from *url* according to *cfg* into *base_dir*.

    Parameters
    ----------
    url:         YouTube channel / playlist URL (or single video URL)
    cfg:         Config object (controls format, codec, quality, etc.)
    base_dir:    Root directory for output files (e.g. ~/Music/ArtistName)
    after:       YYYYMMDD – skip videos uploaded before this date
    before:      YYYYMMDD – skip videos uploaded after this date
    dry_run:     Simulate without downloading (passes --simulate to yt-dlp)
    use_archive: Maintain an archive file to enable safe resume
    verbose:     Show full yt-dlp debug output
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    archive = base_dir / "archive.txt" if use_archive else None

    ydl_opts = cfg.build_ydl_opts(
        base_dir,
        after=after,
        before=before,
        dry_run=dry_run,
        archive=archive,
    )

    # Attach our logger if not verbose (yt-dlp quiet mode hides progress bars,
    # so we keep quiet=False but suppress noisy lines via the logger).
    if not verbose:
        ydl_opts["logger"] = ProgressLogger()
        ydl_opts["quiet"] = False  # needed for progress hooks
        ydl_opts["no_warnings"] = True
    else:
        ydl_opts["verbose"] = True
        ydl_opts["quiet"] = False

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

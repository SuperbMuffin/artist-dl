"""
artist-dl  –  CLI entry point

Subcommands
-----------
  download   Download audio from a YouTube channel / playlist
  outline    Preview track listing without downloading
  config     Show resolved config and exit
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .config import Config
from .downloader import download_catalog, generate_outline, resolve_date

app = typer.Typer(
    name="artist-dl",
    help="Download music catalogs from YouTube channels/playlists as high-quality m4a audio.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


# ---------------------------------------------------------------------------
# Shared option factories
# ---------------------------------------------------------------------------

_URL_ARG = typer.Argument(..., help="YouTube channel, playlist, or video URL.")

_AFTER_OPT = typer.Option(
    None, "--after", "-a",
    help=(
        "Only include videos uploaded on or after this date. "
        "Accepts YYYYMMDD or relative: now, now-2years, now-6months, now-3weeks, now-10days."
    ),
    metavar="DATE",
)

_BEFORE_OPT = typer.Option(
    "now", "--before", "-b",
    help="Only include videos uploaded on or before this date (default: now).",
    metavar="DATE",
)

_ARTIST_OPT = typer.Option(
    None, "--artist",
    help="Override artist folder name (defaults to channel/uploader name from YouTube).",
    metavar="NAME",
)

_ALBUM_OPT = typer.Option(
    None, "--album",
    help="Override album folder name (defaults to playlist title, then uploader name).",
    metavar="NAME",
)

_DIR_OPT = typer.Option(
    None, "--dir", "-d",
    help="Output base directory (overrides config music_dir).",
    metavar="PATH",
)

_VERBOSE_OPT = typer.Option(False, "--verbose", "-v", help="Show full yt-dlp debug output.")


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------

@app.command()
def download(
    url: str = _URL_ARG,
    after: Optional[str] = _AFTER_OPT,
    before: str = _BEFORE_OPT,
    artist: Optional[str] = _ARTIST_OPT,
    album: Optional[str] = _ALBUM_OPT,
    dir: Optional[Path] = _DIR_OPT,
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Simulate download without saving files."),
    no_archive: bool = typer.Option(False, "--no-archive", help="Disable resume archive file."),
    no_thumb: bool = typer.Option(False, "--no-thumb", help="Skip embedding thumbnail."),
    no_meta: bool = typer.Option(False, "--no-meta", help="Skip embedding metadata tags."),
    sponsorblock: bool = typer.Option(
        False, "--sponsorblock",
        help="Remove SponsorBlock-marked segments (sponsor, selfpromo, interaction).",
    ),
    verbose: bool = _VERBOSE_OPT,
) -> None:
    """Download audio from a YouTube channel or playlist."""

    cfg = Config.load()

    if no_thumb:
        cfg.embed_thumbnail = False
    if no_meta:
        cfg.embed_metadata = False
    if sponsorblock:
        cfg.sponsorblock_remove = ["sponsor", "selfpromo", "interaction"]
    cfg.verbose = verbose

    resolved_after = resolve_date(after) if after else None
    resolved_before = resolve_date(before)
    base_dir = dir or cfg.music_dir

    typer.echo("▶  artist-dl download")
    typer.echo(f"   URL     : {url}")
    typer.echo(f"   After   : {resolved_after or 'none'}")
    typer.echo(f"   Before  : {resolved_before}")
    typer.echo(f"   Output  : {base_dir / (artist or '<uploader>') / (album or '<playlist>')}")
    typer.echo(f"   Codec   : {cfg.audio_codec} / quality={cfg.audio_quality}")
    typer.echo(f"   Dry-run : {dry_run}")
    typer.echo("")

    try:
        download_catalog(
            url,
            cfg,
            base_dir,
            after=resolved_after,
            before=resolved_before,
            dry_run=dry_run,
            use_archive=not no_archive,
            verbose=verbose,
            artist_override=artist,
            album_override=album,
        )
    except KeyboardInterrupt:
        typer.echo("\n⏹  Interrupted. Run again to resume (archive tracks progress).", err=True)
        raise typer.Exit(1)
    except Exception as exc:
        typer.echo(f"✗  {exc}", err=True)
        if verbose:
            raise
        raise typer.Exit(1)

    if dry_run:
        typer.echo("✓  Dry-run complete – no files written.")
    else:
        typer.echo("✓  Done.")


# ---------------------------------------------------------------------------
# outline
# ---------------------------------------------------------------------------

@app.command()
def outline(
    url: str = _URL_ARG,
    after: Optional[str] = _AFTER_OPT,
    before: str = _BEFORE_OPT,
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Write outline to FILE instead of stdout.",
        metavar="FILE",
    ),
    json_out: bool = typer.Option(False, "--json", help="Dump raw yt-dlp JSON instead of markdown."),
    verbose: bool = _VERBOSE_OPT,
) -> None:
    """Preview track listing (no download)."""

    cfg = Config.load()
    cfg.verbose = verbose

    resolved_after = resolve_date(after) if after else None
    resolved_before = resolve_date(before)

    typer.echo("🔍 Fetching metadata…", err=True)

    try:
        text = generate_outline(
            url,
            cfg,
            after=resolved_after,
            before=resolved_before,
            json_out=json_out,
        )
    except Exception as exc:
        typer.echo(f"✗  {exc}", err=True)
        if verbose:
            raise
        raise typer.Exit(1)

    if output:
        output.write_text(text, encoding="utf-8")
        typer.echo(f"✓  Outline written to {output}", err=True)
    else:
        typer.echo(text)


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

_EXAMPLE_TOML = """\
# artist-dl configuration  (~/.config/artist-dl/config.toml)

music_dir            = "~/Music"
audio_format         = "bestaudio[ext=m4a]/bestaudio/best"
audio_codec          = "m4a"
audio_quality        = "0"
container            = "m4a"
concurrent_fragment_downloads = 4
retries              = 5
# rate_limit         = "2M"
embed_thumbnail      = true
embed_metadata       = true
verbose              = false
outtmpl_artist_subdir = true

# sponsorblock_remove = ["sponsor", "selfpromo", "interaction"]
"""


@app.command(name="config")
def show_config(
    write_example: bool = typer.Option(
        False, "--write-example",
        help="Write an example config.toml to ~/.config/artist-dl/config.toml and exit.",
    )
) -> None:
    """Show resolved configuration (and optionally write an example config file)."""

    if write_example:
        dest = Path("artist-dl.toml")

        if dest.exists():
            typer.confirm(f"{dest} already exists. Overwrite?", abort=True)
        dest.write_text(_EXAMPLE_TOML, encoding="utf-8")
        typer.echo(f"✓  Example config written to {dest}")
        return

    cfg = Config.load()
    typer.echo("Resolved configuration:")
    typer.echo(f"  music_dir            = {cfg.music_dir}")
    typer.echo(f"  audio_format         = {cfg.audio_format}")
    typer.echo(f"  audio_codec          = {cfg.audio_codec}")
    typer.echo(f"  audio_quality        = {cfg.audio_quality}")
    typer.echo(f"  container            = {cfg.container}")
    typer.echo(f"  concurrent_fragments = {cfg.concurrent_fragment_downloads}")
    typer.echo(f"  retries              = {cfg.retries}")
    typer.echo(f"  rate_limit           = {cfg.rate_limit or 'none'}")
    typer.echo(f"  embed_thumbnail      = {cfg.embed_thumbnail}")
    typer.echo(f"  embed_metadata       = {cfg.embed_metadata}")
    typer.echo(f"  sponsorblock_remove  = {cfg.sponsorblock_remove or []}")
    typer.echo(f"  outtmpl_artist_subdir= {cfg.outtmpl_artist_subdir}")
    typer.echo(f"  verbose              = {cfg.verbose}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app()


if __name__ == "__main__":
    main()

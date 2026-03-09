# artist-dl

A personal Python CLI tool for downloading music catalogs (audio-only, m4a) from YouTube channels and playlists — with date-range filtering, outline/preview, and safe resume support.

> **Warning:** very alpha — posted mainly for preservation and in case anyone wants to contribute.

## Features

- **High-quality audio** — m4a/AAC, prefers native m4a streams, avoids HLS/m3u8
- **Organised output** — `~/Music/Artist/Album/YYYY-MM-DD - Title.m4a`
- **Date range filtering** — absolute `YYYYMMDD` or relative (`now-2years`, `now-6months`, …)
- **Outline mode** — preview the track listing as Markdown without downloading anything
- **Resume-safe** — single archive file at `~/Music/.archive.txt` prevents re-downloading
- **Embedded metadata** — title, artist, date, and artwork embedded in every file
- **SponsorBlock support** — optionally strip sponsor/promo segments
- **Config file** — `~/.config/artist-dl/config.toml` for persistent defaults

---

## Quick start

```bash
# 1. Install deps
pip install --user typer yt-dlp
sudo pacman -S ffmpeg   # Arch

# 2. Run
python run.py download https://www.youtube.com/@SomeArtist/videos --after now-2years

# 3. Preview without downloading
python run.py outline https://www.youtube.com/playlist?list=PL... --after now-1years
```

---

## Usage

### `download`

```
python run.py download URL [OPTIONS]
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--after DATE` | `-a` | none | Skip videos before this date |
| `--before DATE` | `-b` | `now` | Skip videos after this date |
| `--artist NAME` | | from YouTube | Override artist folder name |
| `--album NAME` | | from playlist | Override album folder name |
| `--dir PATH` | `-d` | `~/Music` | Output base directory |
| `--dry-run` | `-n` | off | Simulate without writing files |
| `--no-archive` | | off | Disable resume archive file |
| `--no-thumb` | | off | Skip embedding thumbnail |
| `--no-meta` | | off | Skip embedding metadata |
| `--sponsorblock` | | off | Strip SponsorBlock segments |
| `--verbose` | `-v` | off | Full yt-dlp debug output |

**Date formats:**

| Input | Meaning |
|---|---|
| `now` | Today |
| `now-2years` | ~2 years ago |
| `now-6months` | ~180 days ago |
| `now-3weeks` | 3 weeks ago |
| `now-10days` | 10 days ago |
| `20230101` | January 1 2023 |

**Examples:**

```bash
# Artist channel, last 2 years
python run.py download https://www.youtube.com/@Bonobo/videos --after now-2years

# Album playlist with explicit names (recommended for clean folder structure)
python run.py download https://www.youtube.com/playlist?list=PLxxx \
    --artist "Kendrick Lamar" --album "DAMN."

# Dry-run to see what would download
python run.py download https://www.youtube.com/@NTS_Radio/videos \
    --after now-6months --dry-run
```

### `outline`

```
python run.py outline URL [OPTIONS]
```

```bash
python run.py outline https://www.youtube.com/@FourTet/videos --after now-1years

python run.py outline https://www.youtube.com/playlist?list=PL... \
    --after now-2years --output ~/Documents/four-tet-catalog.md
```

### `config`

```bash
python run.py config              # show resolved config
python run.py config --write-example  # write starter config file
```

---

## Configuration

`~/.config/artist-dl/config.toml`

```toml
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

# sponsorblock_remove = ["sponsor", "selfpromo", "interaction"]
```

---

## Output structure

```
~/Music/
├── .archive.txt                          ← global resume file, don't delete
└── Kendrick Lamar/
    └── DAMN./
        ├── 2017-04-14 - HUMBLE..m4a
        ├── 2017-04-14 - DNA..m4a
        └── …
```

When downloading a channel without `--album`, the album folder falls back to the playlist title, then the uploader name. Use `--artist` and `--album` explicitly when structure matters (e.g. beets import).

---

## Dependencies

| Package | Purpose |
|---|---|
| `yt-dlp` | YouTube download engine |
| `typer` | CLI framework |
| `ffmpeg` (system) | Audio extraction & container remux |

---

## Goals

- [ ] `batch` subcommand — read URLs from a `.toml` file
- [ ] `notify` flag — `notify-send` on completion
- [ ] beets post-processing integration
- [ ] AUR package
- [ ] Shell completions

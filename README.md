# artist-dl

A personal Python CLI tool for downloading music catalogs from YouTube channels and playlists — with date-range filtering, outline/preview, and safe resume support.

## Warning
**Warning** this is in a very alpha state, im posting this to github less for use and more for people to maybe contribute *wink* and preservation!

Most Features don't really work yet.
## Features

- **Date range filtering** — absolute `YYYYMMDD` or relative (`now-2years`, `now-6months`, …)
- **Outline mode** — preview the track listing as Markdown without downloading anything
- **Resume-safe** — yt-dlp archive file prevents re-downloading what you already have
- **Organised output** — `~/Music/ArtistName/YYYY-MM-DD - Title.ogg`
- **SponsorBlock support** — optionally strip sponsor/promo segments
- **Config file** — `~/.config/artist-dl/config.toml` for persistent defaults
- **Zero heavy deps** — just `yt-dlp` + `typer` (and `ffmpeg` on your PATH)

---

## Quick start

```bash
# 1. Install deps (Arch/pip)
pip install --user typer yt-dlp        # or: pip install -e .

# Arch: also make sure ffmpeg is installed
sudo pacman -S ffmpeg

# 2. Clone / copy project
git clone <this-repo> && cd artist-dl

# 3. Download an artist's last 2 years of uploads
python run.py download https://www.youtube.com/@SomeArtist/videos --after now-2years

# 4. Preview a playlist without downloading
python run.py outline https://www.youtube.com/playlist?list=PL... --after now-1years
```

---

## Usage

### `download`

```
python run.py download [URL] [OPTIONS]
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--after DATE` | `-a` | none | Skip videos before this date |
| `--before DATE` | `-b` | `now` | Skip videos after this date |
| `--artist NAME` | | channel name | Override Artist folder name |
| `--dir PATH` | `-d` | `~/Music` | Output base directory |
| `--dry-run` | `-n` | off | Simulate without writing files |
| `--no-archive` | | off | Disable resume archive file |
| `--no-thumb` | | off | Skip embedding thumbnail |
| `--no-meta` | | off | Skip embedding metadata |
| `--sponsorblock` | | off | Strip SponsorBlock segments |
| `--verbose` | `-v` | off | Full yt-dlp debug output |

**Date formats accepted:**

| Input | Meaning |
|---|---|
| `now` | Today |
| `now-2years` | ~2 years ago |
| `now-6months` | ~180 days ago |
| `now-3weeks` | 3 weeks ago |
| `now-10days` | 10 days ago |
| `20230101` | January 1 2023 |
| `2023-01-01` | January 1 2023 |

**Examples:**

```bash
# All uploads from the last 2 years
python run.py download https://www.youtube.com/@Bonobo/videos --after now-2years

# Specific date window, custom artist folder name
python run.py download https://www.youtube.com/playlist?list=PLxxx \
    --after 20220101 --before 20231231 --artist "Aphex Twin"

# Dry-run to see what would download
python run.py download https://www.youtube.com/@NTS_Radio/videos \
    --after now-6months --dry-run

# Strip sponsor segments, cap bandwidth
python run.py download https://... --after now-1years --sponsorblock
```

### `outline`

Preview a track listing as Markdown without downloading.

```
python run.py outline [URL] [OPTIONS]
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--after DATE` | `-a` | none | Filter start date |
| `--before DATE` | `-b` | `now` | Filter end date |
| `--output FILE` | `-o` | stdout | Write to file instead of stdout |
| `--json` | | off | Dump raw yt-dlp JSON |

```bash
# Print outline to terminal
python run.py outline https://www.youtube.com/@FourTet/videos --after now-1years

# Save to markdown file
python run.py outline https://www.youtube.com/playlist?list=PL... \
    --after now-2years --output ~/Documents/four-tet-catalog.md
```

### `config`

```bash
# Show resolved config
python run.py config

# Write starter config file
python run.py config --write-example
```

---

## Configuration

```toml
music_dir            = "~/Music"
audio_format         = "ba[abr>200]/bestaudio/best"
audio_codec          = "opus"
audio_quality        = "0"          # VBR best (~256 kbps)
container            = "ogg"
concurrent_fragment_downloads = 4
retries              = 5
# rate_limit         = "2M"
embed_thumbnail      = true
embed_metadata       = true
verbose              = false
outtmpl_artist_subdir = true

# sponsorblock_remove = ["sponsor", "selfpromo", "interaction"]
```

---

## Output structure

```
~/Music/
└── Bonobo/
    ├── archive.txt               ← resume file (don't delete!)
    ├── 2024-03-15 - Rosewood.m4a
    ├── 2023-11-02 - Tides.m4a
    └── …
```

The `archive.txt` file is how yt-dlp avoids re-downloading tracks on subsequent runs. **Do not delete it** if you want resume/dedup behaviour.

---

## Format selection logic

yt-dlp format string: `ba[abr>200]/bestaudio/best`

1. **`ba[abr>200]`** — native audio stream with bitrate >200 kbps (YouTube often provides 251-Opus at ~160 kbps or DASH Opus at higher rates)
2. **`bestaudio`** — best available audio if the above isn't found
3. **`best`** — full video stream as last resort (audio extracted by FFmpeg)

After selection, FFmpegExtractAudio re-encodes (or remuxes if already Opus) into an `.ogg` container.

---

## Dependencies

| Package | Purpose |
|---|---|
| `yt-dlp` | YouTube download engine |
| `typer` | CLI framework (Click-based, type hints) |
| `ffmpeg` (system) | Audio extraction & container remux |

---

## Goals

- [ ] `batch` subcommand — read URLs from a `.txt` / `.toml` file
- [ ] `notify` flag — `notify-send` desktop notification on completion
- [ ] Last.fm / MusicBrainz metadata enrichment
- [ ] AUR package (`artist-dl`)
- [ ] Shell completions (`artist-dl --install-completion`)


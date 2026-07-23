# onepace

Stream any [One Pace](https://onepace.net) arc straight into [mpv](https://mpv.io) - no downloading, no clunky web player. Pick an arc with a fuzzy, arrow-key terminal picker, choose sub/dub and quality, and it hands mpv a playlist of every episode in order.

- **Zero dependencies** - pure Python standard library.
- **Interactive picker** - type to filter arcs live, `↑`/`↓` to move, `Enter` to select. Works on Windows, macOS, and Linux.
- **Always current** - scrapes the live One Pace watch page each run, so new arcs and re-encodes just show up.
- **Non-interactive mode** - script everything with flags.

## How it works

1. Fetches `https://onepace.net/en/watch` and maps each arc → sub/dub → quality → its [pixeldrain](https://pixeldrain.com) list id.
2. Resolves that list via `https://pixeldrain.net/api/list/<id>` into the ordered episode file ids.
3. Launches `mpv` with every `https://pixeldrain.net/api/file/<id>` as a playlist.

No files touch your disk - mpv streams each episode directly.

## Requirements

- **Python 3.8+**
- **mpv** - if it's not on your `PATH`, onepace offers to install it for you (via `winget`/`scoop`/`choco` on Windows, `brew` on macOS, `apt`/`dnf`/`pacman`/`zypper` on Linux).

## Install

Grab the single file and run it:

```bash
python onepace.py
```

Or install it as a global `onepace` command with [pipx](https://pipx.pypa.io):

```bash
pipx install .
onepace
```

## Usage

```bash
# interactive: filter arcs by typing, arrow-keys to move, Enter to pick
onepace

# non-interactive (default: English sub, 1080p)
onepace "long ring long land"
onepace alabasta -q 720p
onepace long-ring-long-land --dub

# utilities
onepace --list                 # print every arc + available qualities
onepace "wano" --print         # print the stream URLs instead of launching mpv
onepace --version
```

### Interactive controls

| Where          | Keys                                                             |
| -------------- | --------------------------------------------------------------- |
| Arc picker     | type letters to narrow · `↑`/`↓` move · `Enter` select · `Esc` cancel |
| Track, Quality | press the number · `Enter` for the default (Sub, 1080p)         |

### Flags

| Flag                 | Description                                        |
| -------------------- | -------------------------------------------------- |
| `-q`, `--quality`    | `480p`, `720p`, or `1080p` (default `1080p`)       |
| `--dub`              | English dub instead of sub                         |
| `--list`             | list all arcs and exit                             |
| `--print`            | print stream URLs, don't launch mpv                |
| `--mpv PATH`         | path to the mpv binary (default `mpv`)             |

### mpv playback tips

- `<` / `>` - previous / next episode in the playlist
- `Space` - pause · `f` - fullscreen · `q` - quit
- `Shift`+`q` - quit **and save your progress**: mpv writes the playback position keyed by the stream URL. Since onepace produces the same URLs every run, relaunching the arc resumes right where you left off.

## Disclaimer

This tool only automates navigating the publicly available One Pace website and the pixeldrain links it already publishes - it hosts nothing and stores nothing. One Pace is a free fan project; if you enjoy it, [support the team](https://onepace.net) and the official One Piece release. You are responsible for how you use this software and for complying with the terms of the services it talks to.

## License

[MIT](LICENSE)

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
pipx install git+https://github.com/vashhdev/onepace
onepace
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/vashhdev/onepace
onepace
```

(From a local clone, use `pipx install .` / `uv tool install .`.)

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
| `--dub`              | English dub instead of sub (falls back to Muhn Pace where One Pace has no dub) |
| `--muhn`             | force the Muhn Pace dub even where an official dub exists |
| `--refresh-muhn`     | re-scrape the Muhn Pace guide, print an updated table |
| `--list`             | list all arcs and exit                             |
| `--print`            | print stream URLs, don't launch mpv                |
| `--m3u [PATH]`       | write an `.m3u` playlist instead of launching mpv (handy for mobile). PATH optional |
| `--mpv PATH`         | path to the mpv binary (default `mpv`)             |

### mpv playback tips

- `<` / `>` - previous / next episode in the playlist
- `Space` - pause · `f` - fullscreen · `q` - quit
- `Shift`+`q` - quit **and save your progress**: mpv writes the playback position keyed by the stream URL. Since onepace produces the same URLs every run, relaunching the arc resumes right where you left off.

## English dub coverage

One Pace hasn't dubbed every arc - 12 of them are sub-only, and the gap starts right after Enies Lobby. To cover it, onepace falls back to [**Muhn Pace**](https://steamcommunity.com/sharedfiles/filedetails/?id=3685024934), a separate solo dub edit by *Muhny D Goat* built on top of One Pace episodes, so it matches their style closely.

The rule is simple: **an official One Pace dub always wins.** Muhn Pace is only offered on arcs One Pace hasn't dubbed, and it's always labelled as such - never substituted silently, since it's a different project with its own episode numbering.

```bash
onepace "alabasta" --dub          # official One Pace dub
onepace "thriller bark" --dub     # no official dub -> Muhn Pace, and it says so
onepace "wano" --muhn             # force Muhn Pace even though an official dub exists
onepace --list                    # dub / dub:muhn / sub-only per arc
```

Arcs Muhn Pace covers: Enies Lobby, Post-Enies Lobby, Thriller Bark, Sabaody Archipelago, Amazon Lily, Impel Down, Marineford, Post-War, Fishman Island, Punk Hazard, Dressrosa, Zou, Whole Cake Island, Wano.

Its pixeldrain list ids are pinned in `MUHN_PACE` inside `onepace.py` (there's no live index page to scrape). If Muhny releases or reuploads an arc, `--refresh-muhn` re-reads the watch guide and prints an updated table to paste in.

## Mobile (Android / mpv-android / mpvKt)

The `--m3u` flag writes a standard playlist that any mpv-based mobile player (mpv-android, mpvKt) or VLC can open - the whole arc plays in order, still streaming, no downloads. Two ways to get one on your phone:

**Easiest - generate on desktop, send to phone:**

```bash
onepace "long ring long land" --m3u
# writes long-ring-long-land-sub-1080p.m3u
```

Send that `.m3u` to your phone (share sheet, Syncthing, Telegram to yourself, whatever) and open it with mpv-android. Done.

**On-device with [Termux](https://termux.dev):**

```bash
pkg install python
python onepace.py "long ring long land" --m3u ~/storage/shared/onepace.m3u
```

Then open `onepace.m3u` from your file manager with mpv-android. (Run `termux-setup-storage` once so `~/storage/shared` maps to your phone's storage.)

> Note: the arc picker's live filtering needs a real terminal, so on a touch keyboard the flag form (`onepace "arc name"`) is the smoother ride. `--list` shows every arc slug.

## Disclaimer

This tool only automates navigating the publicly available One Pace website and the pixeldrain links it already publishes - it hosts nothing and stores nothing. One Pace is a free fan project; if you enjoy it, [support the team](https://onepace.net) and the official One Piece release. You are responsible for how you use this software and for complying with the terms of the services it talks to.

## License

[MIT](LICENSE)

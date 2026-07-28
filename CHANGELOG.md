# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org).

## [1.1.0] - 2026-07-28

### Added

- **`--m3u [PATH]`** writes a standard EXTM3U playlist instead of launching mpv, with
  per-episode `#EXTINF` names. Makes the whole arc playable on mobile via mpv-android
  or mpvKt (and in VLC), still streaming, no downloads. See the Mobile section in the
  README for the Termux and desktop-to-phone routes.
- **Muhn Pace dub fallback.** One Pace has no English dub for 12 arcs, starting right
  after Enies Lobby. Those arcs now fall back to [Muhn Pace](https://steamcommunity.com/sharedfiles/filedetails/?id=3685024934),
  a separate solo dub edit by *Muhny D Goat* built on top of One Pace episodes.
  An official One Pace dub always wins where one exists, and the fallback is always
  labelled - never substituted silently.
- **`--muhn`** forces the Muhn Pace dub even on arcs that do have an official dub.
- **`--no-muhn`** opts out entirely, for One Pace and nothing else.
- **`--refresh-muhn`** re-scrapes the Muhn Pace watch guide and prints an updated
  `MUHN_PACE` table. Muhn Pace has no live index page, so its pixeldrain list ids are
  pinned in the source; this regenerates them if an arc is reuploaded.
- `uv` install instructions alongside pipx.
- `--list` now shows the dub source per arc: `dub`, `dub:muhn`, or `sub-only`.

### Fixed

- Playlists no longer include non-video entries. Some pixeldrain lists carry extras -
  the Wano and Post-War lists each hold a 38-byte `text/plain` note, and one Fishman
  Island list is a "Group Shot Project" of comparison clips - which mpv would have
  tried to play. Entries are now filtered on the mime type the pixeldrain API reports
  rather than by file extension.

## [1.0.0] - 2026-07-23

Initial release.

### Added

- Interactive arc picker: type to fuzzy-filter, arrow keys to navigate, Enter to select.
  Prefix matches rank above substring matches.
- Numbered sub/dub and quality menus, Enter for the default.
- Non-interactive mode driven entirely by flags.
- Live scraping of the One Pace watch page, so new arcs and re-encodes appear
  automatically.
- mpv auto-install: detects winget/scoop/choco, brew, or apt/dnf/pacman/zypper and
  offers to install mpv when it is missing.
- Cross-platform raw-key TUI - `msvcrt` on Windows, `termios`/`tty` on POSIX.
- Zero dependencies, pure Python standard library.

[1.1.0]: https://github.com/vashhdev/onepace/releases/tag/v1.1.0
[1.0.0]: https://github.com/vashhdev/onepace/releases/tag/v1.0.0

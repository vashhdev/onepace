#!/usr/bin/env python3
"""
onepace.py - stream a One Pace arc in mpv without downloading.

Pipeline:
  1. fetch https://onepace.net/en/watch, map each arc -> sub/dub -> quality -> pixeldrain list id
  2. fetch https://pixeldrain.net/api/list/<id> -> ordered file ids
  3. launch mpv with every https://pixeldrain.net/api/file/<id> as a playlist

Usage:
  python onepace.py                                       # INTERACTIVE: type-filter arc, pick track+quality
  python onepace.py "long ring long land"                 # non-interactive, default sub 1080p
  python onepace.py "alabasta" -q 720p
  python onepace.py long-ring-long-land --dub
  python onepace.py --list                                # print all arcs then exit
  python onepace.py "wano" --print                        # print urls, don't launch mpv

Interactive controls:
  arc picker : type letters to narrow the list, up/down arrows to move, Enter to select, Esc to cancel
  track/quality : press the number, or just Enter for the default
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

__version__ = "1.0.0"

WATCH_URL = "https://onepace.net/en/watch"
LIST_API = "https://pixeldrain.net/api/list/{}"
FILE_URL = "https://pixeldrain.net/api/file/{}"
UA = {"User-Agent": "Mozilla/5.0 (onepace.py)"}

# ------------------------------------------------------------------ interactive
# single-key input: msvcrt on Windows, termios/tty on POSIX.
try:
    import msvcrt                       # Windows
except ImportError:
    msvcrt = None
try:
    import termios, tty, select         # POSIX
except ImportError:
    termios = None

CSI = "\x1b["
HL = CSI + "7m"       # reverse video (highlight)
DIM = CSI + "2m"
RST = CSI + "0m"


def interactive_ok():
    """true if we can drive a raw-key TUI on this terminal."""
    return (bool(msvcrt) or bool(termios)) and sys.stdin.isatty() and sys.stdout.isatty()


def _enable_vt():
    """turn on ANSI escape handling in the Windows console (no-op elsewhere)."""
    if msvcrt:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, mode.value | 0x0004)


def _getkey():
    """block for one keypress. return ('char', c) or ('key', name)."""
    if msvcrt:
        c = msvcrt.getwch()
        if c in ("\x00", "\xe0"):        # arrow / function-key prefix
            c2 = msvcrt.getwch()
            return "key", {"H": "up", "P": "down", "K": "left", "M": "right"}.get(c2, "")
        if c in ("\r", "\n"):
            return "key", "enter"
        if c == "\x08":
            return "key", "backspace"
        if c == "\x1b":
            return "key", "esc"
        if c == "\x03":
            raise KeyboardInterrupt
        return "char", c
    # POSIX: read one char in cbreak mode (OPOST kept so \n still maps to \r\n)
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        c = sys.stdin.read(1)
        if c == "\x1b":                  # ESC alone, or start of arrow sequence
            r, _, _ = select.select([sys.stdin], [], [], 0.05)
            if not r:
                return "key", "esc"
            if sys.stdin.read(1) == "[":
                c3 = sys.stdin.read(1)
                return "key", {"A": "up", "B": "down", "C": "right", "D": "left"}.get(c3, "")
            return "key", "esc"
        if c in ("\r", "\n"):
            return "key", "enter"
        if c in ("\x7f", "\x08"):
            return "key", "backspace"
        if c == "\x03":
            raise KeyboardInterrupt
        return "char", c
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def fuzzy_pick(items, label, header):
    """
    live-filter picker. type letters to narrow, up/down to move, Enter to select.
    `items` = list, `label(item)` -> str shown & searched. returns item or None.
    prefix matches rank above substring matches.
    """
    if not interactive_ok():
        return _fallback_pick(items, label, header)
    query, sel, drawn = "", 0, 0
    max_rows = 15

    def filtered():
        q = query.lower().replace(" ", "")
        if not q:
            return list(items)
        pre, sub = [], []
        for it in items:
            t = label(it).lower().replace(" ", "")
            if t.startswith(q):
                pre.append(it)
            elif q in t:
                sub.append(it)
        return pre + sub

    while True:
        view = filtered()
        sel = max(0, min(sel, len(view) - 1)) if view else 0
        # window of rows around selection
        start = max(0, min(sel - max_rows + 1, len(view) - max_rows)) if len(view) > max_rows else 0
        rows = view[start:start + max_rows]

        out = [f"{header}", f"{DIM}type to filter · ↑↓ move · Enter select · Esc cancel{RST}",
               f"> {query}{CSI}K"]
        for i, it in enumerate(rows):
            real = start + i
            mark = HL + " > " if real == sel else "   "
            out.append(f"{mark}{label(it)}{RST}{CSI}K")
        if not view:
            out.append(f"{DIM}  (no match){RST}{CSI}K")
        out.append(f"{DIM}  {len(view)}/{len(items)} arcs{RST}{CSI}K")

        if drawn:
            sys.stdout.write(f"{CSI}{drawn}A")   # move cursor up to redraw
        sys.stdout.write("\r" + f"\n".join(out) + f"{CSI}J\n")
        sys.stdout.flush()
        drawn = len(out)

        kind, val = _getkey()
        if kind == "char":
            query += val
            sel = 0
        elif val == "backspace":
            query = query[:-1]
            sel = 0
        elif val == "up":
            sel -= 1
        elif val == "down":
            sel += 1
        elif val == "enter":
            return view[sel] if view else None
        elif val == "esc":
            return None


def menu_pick(options, default_idx, header):
    """numbered menu. press 1-9 to pick, Enter for default. returns index."""
    print(header)
    for i, (lbl, _) in enumerate(options):
        d = f" {DIM}(default){RST}" if i == default_idx else ""
        print(f"  {i + 1}. {lbl}{d}")
    if not interactive_ok():
        raw = input(f"choice [{default_idx + 1}]: ").strip()
        return default_idx if not raw else max(0, min(int(raw) - 1, len(options) - 1))
    sys.stdout.write(f"{DIM}press number, or Enter for default: {RST}")
    sys.stdout.flush()
    while True:
        kind, val = _getkey()
        if kind == "key" and val == "enter":
            idx = default_idx
            break
        if kind == "char" and val.isdigit() and 1 <= int(val) <= len(options):
            idx = int(val) - 1
            break
    print(f"{options[idx][0]}")
    return idx


def _fallback_pick(items, label, header):
    """no-msvcrt fallback: type a substring, plain input()."""
    print(header)
    q = input("filter arc (substring): ").strip().lower()
    hits = [it for it in items if q in label(it).lower()] or list(items)
    for i, it in enumerate(hits):
        print(f"  {i + 1}. {label(it)}")
    raw = input("number: ").strip()
    return hits[int(raw) - 1] if raw else hits[0]



def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# --- parse the watch page into  arcs[slug] = {"title", "sub"/"dub": {quality: listid}} ---
TOKEN_RE = re.compile(
    r'href="[^"]*#(?P<arc>[a-z0-9-]+)"'
    r'|(?P<sub>English Subtitles)'
    r'|(?P<dub>English Dub)'
    r'|pixeldrain\.net/l/(?P<list>[A-Za-z0-9]+)'
    r'|>[\s ]*(?P<q>480p|720p|1080p)[\s ]*<'
)


def parse_watch(html):
    # also grab the human title that follows each anchor:  watch#slug"> Title</a>
    titles = {
        slugify(m.group(1)): m.group(2).strip()
        for m in re.finditer(r'href="[^"]*#([a-z0-9-]+)"[^>]*>\s*([^<]+?)\s*</a>', html)
    }
    arcs = {}
    cur_arc = cur_track = pending_list = None
    for m in TOKEN_RE.finditer(html):
        if m.group("arc"):
            cur_arc = m.group("arc")
            cur_track = pending_list = None
            arcs.setdefault(cur_arc, {"title": titles.get(cur_arc, cur_arc),
                                      "sub": {}, "dub": {}})
        elif m.group("sub"):
            cur_track = "sub"
        elif m.group("dub"):
            cur_track = "dub"
        elif m.group("list"):
            pending_list = m.group("list")  # link precedes its quality label
        elif m.group("q") and cur_arc and cur_track and pending_list:
            arcs[cur_arc][cur_track][m.group("q")] = pending_list
            pending_list = None
    return arcs


def resolve_list(list_id):
    data = json.loads(fetch(LIST_API.format(list_id)))
    files = data.get("files", [])
    ids = [f["id"] for f in files]
    names = [f.get("name", f["id"]) for f in files]
    return ids, names, data.get("title", list_id)


def write_m3u(path, urls, names, title):
    """write a standard EXTM3U playlist (openable by mpv-android, mpvKt, VLC...)."""
    lines = ["#EXTM3U", f"#PLAYLIST:{title}"]
    for url, name in zip(urls, names):
        lines.append(f"#EXTINF:-1,{name}")
        lines.append(url)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


MPV_INSTALL = {
    # os key -> list of (package-manager, command-if-manager-present)
    "nt": [("winget", ["winget", "install", "-e", "--id", "mpv.net"]),
           ("scoop", ["scoop", "install", "mpv"]),
           ("choco", ["choco", "install", "mpv", "-y"])],
    "darwin": [("brew", ["brew", "install", "mpv"])],
    "linux": [("apt", ["sudo", "apt", "install", "-y", "mpv"]),
              ("dnf", ["sudo", "dnf", "install", "-y", "mpv"]),
              ("pacman", ["sudo", "pacman", "-S", "--noconfirm", "mpv"]),
              ("zypper", ["sudo", "zypper", "install", "-y", "mpv"])],
}


def ensure_mpv(mpv):
    """return mpv path if runnable; else offer to install it. exits if unusable."""
    if shutil.which(mpv) or os.path.isfile(mpv):
        return mpv

    key = "nt" if os.name == "nt" else ("darwin" if sys.platform == "darwin" else "linux")
    candidates = [(mgr, cmd) for mgr, cmd in MPV_INSTALL.get(key, []) if shutil.which(mgr)]

    sys.stderr.write("mpv not found on PATH.\n")
    if not candidates:
        sys.stderr.write("no known package manager detected. install mpv manually: "
                         "https://mpv.io/installation/\n")
        sys.exit(1)

    mgr, cmd = candidates[0]
    if not interactive_ok():
        sys.stderr.write(f"install it with: {' '.join(cmd)}\n")
        sys.exit(1)
    ans = input(f"install mpv now via {mgr}?  ({' '.join(cmd)}) [Y/n] ").strip().lower()
    if ans in ("n", "no"):
        sys.exit("mpv required. aborting.")
    subprocess.run(cmd)
    if shutil.which(mpv):
        return mpv
    sys.exit("mpv still not found after install. open a new terminal and retry.")


def match_arc(arcs, query):
    q = slugify(query)
    if q in arcs:
        return q
    hits = [s for s in arcs if q in s or s in q]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"no arc matches '{query}'. try --list")
    sys.exit("ambiguous, matches: " + ", ".join(hits))


def main():
    ap = argparse.ArgumentParser(description="stream a One Pace arc in mpv")
    ap.add_argument("arc", nargs="?", help="arc name or slug, e.g. 'long ring long land'")
    ap.add_argument("-q", "--quality", default="1080p", choices=["480p", "720p", "1080p"])
    ap.add_argument("--dub", action="store_true", help="English dub instead of sub")
    ap.add_argument("--list", action="store_true", help="list all arcs and exit")
    ap.add_argument("--print", dest="print_only", action="store_true",
                    help="print file urls instead of launching mpv")
    ap.add_argument("--m3u", nargs="?", const="", metavar="PATH",
                    help="write an .m3u playlist instead of launching mpv "
                         "(great for mobile / mpv-android). default filename if PATH omitted")
    ap.add_argument("--mpv", default="mpv", help="path to mpv binary")
    ap.add_argument("--version", action="version", version=f"onepace {__version__}")
    args = ap.parse_args()

    _enable_vt()
    sys.stderr.write("fetching arc list...\n")
    arcs = parse_watch(fetch(WATCH_URL))

    if args.list:
        for slug in arcs:
            q = sorted(set(arcs[slug]["sub"]) | set(arcs[slug]["dub"]))
            print(f"{slug:28} {arcs[slug]['title']:30} [{','.join(q)}]")
        return

    if args.arc:
        # non-interactive path: flags decide everything
        slug = match_arc(arcs, args.arc)
        track = "dub" if args.dub else "sub"
        quality = args.quality
    else:
        # interactive path: pick arc, then track, then quality
        slugs = list(arcs)
        chosen = fuzzy_pick(slugs, lambda s: arcs[s]["title"], "select an arc:")
        if chosen is None:
            sys.exit("cancelled")
        slug = chosen
        print(f"\n{arcs[slug]['title']}")

        tracks = [t for t in ("sub", "dub") if arcs[slug][t]]
        if len(tracks) == 1:
            track = tracks[0]
        else:
            ti = menu_pick([("English Sub", "sub"), ("English Dub", "dub")],
                           0, "\ntrack:")
            track = ["sub", "dub"][ti]

        avail = [q for q in ("1080p", "720p", "480p") if q in arcs[slug][track]]
        default_q = avail.index("1080p") if "1080p" in avail else 0
        qi = menu_pick([(q, q) for q in avail], default_q, "\nquality:")
        quality = avail[qi]

    list_id = arcs[slug][track].get(quality)
    if not list_id:
        have = ", ".join(arcs[slug][track]) or "none"
        sys.exit(f"{slug} has no {track} {quality}. available {track}: {have}")

    file_ids, names, title = resolve_list(list_id)
    urls = [FILE_URL.format(fid) for fid in file_ids]
    if not urls:
        sys.exit("list resolved to 0 files")

    sys.stderr.write(f"{title}  ({track} {quality}, {len(urls)} files)\n")
    if args.print_only:
        print("\n".join(urls))
        return
    if args.m3u is not None:
        path = args.m3u or f"{slug}-{track}-{quality}.m3u"
        write_m3u(path, urls, names, title)
        print(os.path.abspath(path))
        return
    mpv = ensure_mpv(args.mpv)
    subprocess.run([mpv, f"--force-media-title={title}", *urls])


if __name__ == "__main__":
    main()

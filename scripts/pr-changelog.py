#!/usr/bin/env python3
"""Sync changelog and README when a pull request bumps an app's image tag.

Companion to the App Store Check: Renovate bumps image tags/digests in
docker-compose.yml (and the ``version:`` line of umbrel-app.yml via its
custom manager), but nothing explains *what* changed between the old and
the new tag. This script closes that gap for every app changed in the PR:

* compares each changed app's docker-compose.yml between the PR base and
  the working tree (old vs. new image tags/digests per service)
* fetches the upstream GitHub release notes between the old and the new
  tag (GitHub compare API as fallback when the repo has no releases)
* prepends a changelog entry to ``releaseNotes`` in the app's
  umbrel-app.yml (running history, most recent entry first)
* syncs the app's version cell in the README table with the manifest
  version

It only modifies the working tree - committing to the PR branch is done
by the workflow's commit step after the package checks passed (the sync
step runs *before* the checks, so the checks validate the updated files).
The script is idempotent: entries already present in releaseNotes are
not added twice, and an already-synced README cell is left alone.

Output on stdout uses the tagged-line format understood by
scripts/pr-report.js:

  [TAGDIFF] ...  detected tag/digest changes per image
  [CHANGE] ...   what changed upstream, per release between old/new tag
  [NOTE ] ...    hints and things to double-check (e.g. version not bumped)
  [UPDATE] ...  files modified in the workspace by the sync

Exit code is always 0 - the sync must never break the check itself.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request

GITHUB_API = "https://api.github.com"
MOVING_TAGS = {"latest", "main"}

# Same breaking-change radar as scripts/check-upstream.py; hits are surfaced
# in the [CHANGE]/[NOTE ] lines so the PR comment flags them for review.
BREAKING_KEYWORDS = [
    "breaking", "⚠", "deprecat", "renamed", "removed",
    "no longer", "must now", "migrate", "migration", "incompatible",
]

# Length caps so the umbrel-app.yml stays readable (Umbrel renders releaseNotes
# as one paragraph): the new entry itself, and the whole resulting value.
MAX_ENTRY_CHARS = 600
MAX_VALUE_CHARS = 1900

SERVICE_RE = re.compile(r"^  ([A-Za-z0-9][A-Za-z0-9_-]*):(?:\s|$)")
IMAGE_LINE_RE = re.compile(r"^\s+image:\s*(\S+)\s*$")
VERSION_LINE_RE = re.compile(r'^version:\s*"?([^\s"]+)"?\s*$')
REPO_LINE_RE = re.compile(r"^repo:\s*(\S+)\s*$")


# --------------------------------------------------------------------- utils

def parse_version(text):
    """'v2.2.1' -> (2, 2, 1); optional 4th component (Duplicati-style tags)."""
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?", str(text).strip())
    return tuple(int(x) for x in m.groups() if x is not None) if m else None


def strip_packaging_suffix(version):
    return re.sub(r"\+patch\d+$", "", str(version).strip())


def short_digest(digest):
    return digest if digest else "ohne Digest"


def parse_image_ref(ref):
    """'ghcr.io/x/y:latest@sha256:...' -> (image, tag, digest|None).

    Digest-aware: the digest is split off first, then the tag is the part
    after the last ':' that follows the last '/'. Registry hosts with ports
    (registry:5000/name) keep working.
    """
    ref = str(ref).strip()
    digest = None
    m = re.search(r"@(sha256:[a-f0-9]{64})$", ref)
    if m:
        digest = m.group(1)
        ref = ref[:m.start()]
    tag = None
    i = ref.rfind(":")
    if i != -1 and "/" not in ref[i:]:
        tag = ref[i + 1:]
        ref = ref[:i]
    return ref, tag, digest


def dedupe_tag_prefix(text, tag):
    """Release bodies often start with their own tag ('## v2.3.0 ...')."""
    low = text.lower()
    for lead in (tag.lower(), tag.lower().lstrip("v"), "v" + tag.lower().lstrip("v")):
        if low.startswith(lead):
            return text[len(lead):].lstrip(" :-#\t").strip()
    return text


def truncate_text(text, limit):
    """Trim on a sentence boundary when possible, with an ellipsis."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in (". ", "! ", "? "):
        i = cut.rfind(sep)
        if i != -1 and i > limit * 0.5:
            return cut[:i + 1].rstrip() + " …"
    return cut.rstrip() + " …"


def clean_markdown(body):
    """Flatten a release-note body into one line of plain text."""
    text = body or ""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)   # headings
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)    # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> text
    text = re.sub(r"`([^`]*)`", r"\1", text)              # inline code
    text = re.sub(r"[*_`#>|]{2,}", " ", text)            # md decorations
    text = re.sub(r"^\s*[-*+]\s+", " ", text, flags=re.M)  # bullets
    text = re.sub(r"[\r\n]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip()


def gh_request(url, token):
    """GET a GitHub API URL, return parsed JSON or None on any error."""
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "anyumbrelstore-pr-changelog",
    })
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError,
            OSError):
        return None


# ---------------------------------------------------------- git / compose IO

def git_show(path_at_sha):
    """`git show <sha>:<path>` - returns text or None when it does not exist."""
    try:
        out = subprocess.run(["git", "show", path_at_sha],
                             capture_output=True, text=True, check=True)
        return out.stdout
    except subprocess.CalledProcessError:
        return None


def changed_apps(base_sha, all_apps):
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", f"{base_sha}..HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout
    except Exception:
        return set()
    apps = set()
    for line in out.splitlines():
        top = line.split("/")[0]
        if top in all_apps:
            apps.add(top)
    return apps


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def images_from_compose_text(text):
    """service name -> (image, tag, digest) parsed from raw compose text."""
    images = {}
    service = None
    for line in (text or "").splitlines():
        m = SERVICE_RE.match(line)
        if m:
            service = m.group(1)
            continue
        m = IMAGE_LINE_RE.match(line)
        if m and service:
            image, tag, digest = parse_image_ref(m.group(1))
            if image:
                images[service] = (image, tag, digest)
    return images


def manifest_field(lines, key_re):
    for line in lines:
        m = key_re.match(line)
        if m:
            return m.group(1)
    return None


# ------------------------------------------------------- umbrel-app.yml edits

def find_release_notes(lines):
    """Locate the releaseNotes key, its value span and current text.

    Returns (idx, end, is_block, old_text, block_lines) or None.
    * idx: line index of the `releaseNotes:` key
    * end: first line index after the value span
    * is_block: True when the value is a block scalar (>- etc.)
    * old_text: the current value as plain text (block content joined)
    * block_lines: the raw indented lines of a block value
    """
    key_re = re.compile(r"^releaseNotes:\s*(.*)$")
    block_head = re.compile(r"^[|>][+-]?\d*(?::[1-9][0-9]*)?\s*$")
    for i, line in enumerate(lines):
        m = key_re.match(line)
        if not m:
            continue
        inline = m.group(1).strip()
        if inline and not block_head.match(inline):
            # single-line value: "quoted" or plain
            if inline[0] in "\"'":
                old_text = inline.strip("\"'")
            else:
                old_text = inline
            return i, i + 1, False, old_text, []
        # block scalar: consume indented / blank lines
        j = i + 1
        block = []
        while j < len(lines):
            l = lines[j]
            if l.strip() == "":
                block.append(l)
                j += 1
                continue
            if l.startswith((" ", "\t")):
                block.append(l)
                j += 1
                continue
            break
        while block and block[-1].strip() == "":
            block.pop()
        old_text = " ".join(l.strip() for l in block if l.strip())
        return i, j, True, old_text, block
    return None


def prepend_release_notes(lines, entry_text, marker):
    """Add a changelog entry to the manifest lines. Returns new lines or None.

    Idempotent: returns None when the marker is already part of the current
    releaseNotes value.
    """
    found = find_release_notes(lines)
    if found:
        idx, end, is_block, old_text, block_lines = found
        if marker in old_text:
            return None
        old_text = (old_text or "").strip()
    else:
        # no releaseNotes yet: insert before the `port:` key
        idx = next((i for i, l in enumerate(lines)
                    if re.match(r"^port:", l)), len(lines) - 1)
        end, is_block, old_text, block_lines = idx, False, "", []

    budget = MAX_VALUE_CHARS - len(entry_text) - 2
    if len(old_text) > budget:
        old_text = old_text[:budget].rstrip() + " …"

    new_lines = list(lines)
    if is_block:
        # block value: keep the old lines untouched, only prepend the entry
        wrapped = textwrap.wrap(entry_text, width=88, break_long_words=False,
                                break_on_hyphens=False) or [""]
        value = ["releaseNotes: >-"]
        value += ["  " + w for w in wrapped]
        value += block_lines
        new_lines[idx:end] = value
    else:
        if old_text:
            entry_text = entry_text + " " + old_text
        escaped = entry_text.replace("\\", "\\\\").replace('"', '\\"')
        new_lines[idx:end] = [f'releaseNotes: "{escaped}"']
    return new_lines


# -------------------------------------------------------- upstream changelog

def repo_from_url(url):
    m = re.match(
        r"^https?://(?:www\.)?github\.com/([^/\s]+/[^/\s]+?)(?:\.git)?/?$",
        (url or "").strip())
    return m.group(1) if m else None


def candidate_repos(image, manifest_repo):
    """Guess upstream GitHub repos for a Docker image reference."""
    candidates = []
    parts = image.split("/")
    if len(parts) >= 2 and ("." in parts[0] or ":" in parts[0]):
        parts = parts[1:]
    if len(parts) >= 2:
        if parts[0] == "library":
            candidates.append(f"docker-library/{parts[1]}")
        else:
            candidates.append(f"{parts[0]}/{parts[1]}")
    elif len(parts) == 1 and parts[0]:
        candidates.append(f"docker-library/{parts[0]}")
    if manifest_repo:
        candidates.append(manifest_repo)

    seen, out = set(), []
    for c in candidates:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def fetch_release_notes(repo, old_tag, new_tag, token):
    """Release notes between old and new tag, oldest entry first.

    Returns (entries, breaking): entries is a list of
    (version_tuple, tag, plain_text, url); breaking maps tag -> keyword
    hits. ([], {}) when nothing was found.
    """
    old_v = parse_version(old_tag)
    new_v = parse_version(new_tag)
    if old_v is None or new_v is None:
        return [], {}
    releases = gh_request(f"{GITHUB_API}/repos/{repo}/releases?per_page=100",
                          token)
    entries = []
    breaking = {}
    if isinstance(releases, list):
        for rel in releases:
            if rel.get("prerelease") or rel.get("draft"):
                continue
            ver = parse_version(rel.get("tag_name") or "")
            if ver is None or not (old_v < ver <= new_v):
                continue
            tag = rel.get("tag_name")
            body_raw = rel.get("body") or ""
            body = dedupe_tag_prefix(clean_markdown(body_raw), tag or "")
            url = rel.get("html_url") or \
                f"https://github.com/{repo}/releases/tag/{tag}"
            entries.append((ver, tag, body, url))
            hits = [k for k in BREAKING_KEYWORDS
                    if k.lower() in body_raw.lower()]
            if hits:
                breaking[tag] = hits
        entries.sort(key=lambda e: e[0])
        entries = entries[-3:]
    if entries:
        return entries, breaking

    # fallback: compare API (works for repos without GitHub releases)
    for a, b in ((old_tag, new_tag), ("v" + old_tag, "v" + new_tag),
                 (old_tag, "v" + new_tag)):
        cmp = gh_request(f"{GITHUB_API}/repos/{repo}/compare/{a}...{b}", token)
        if not cmp or not isinstance(cmp.get("commits"), list):
            continue
        subjects = []
        for c in cmp["commits"]:
            message = (c.get("commit", {}).get("message") or "").splitlines()
            subject = message[0].strip() if message else ""
            if subject:
                subjects.append(subject)
        if subjects:
            url = cmp.get("html_url") or \
                f"https://github.com/{repo}/compare/{a}...{b}"
            text = "Commits: " + "; ".join(subjects[:8]) + \
                (" …" if len(subjects) > 8 else "")
            entries.append((new_v, new_tag, text, url))
            hits = [k for k in BREAKING_KEYWORDS
                    if k.lower() in " ".join(subjects).lower()]
            if hits:
                breaking[new_tag] = hits
        break
    return entries, breaking


# ----------------------------------------------------------------- main flow

def process_app(root, app_id, base_sha, token, stats):
    compose_path = os.path.join(root, app_id, "docker-compose.yml")
    manifest_path = os.path.join(root, app_id, "umbrel-app.yml")

    old_compose = git_show(f"{base_sha}:{app_id}/docker-compose.yml")
    if old_compose is None:
        return  # new app in this PR: nothing to compare against
    if not os.path.isfile(compose_path):
        return
    try:
        new_lines = read_lines(manifest_path)
    except OSError:
        return

    old_images = images_from_compose_text(old_compose)
    new_images = images_from_compose_text("\n".join(read_lines(compose_path)))

    changes = []  # (service, image, old_tag, new_tag, old_dig, new_dig)
    for service, (image, tag, digest) in new_images.items():
        old = old_images.get(service)
        if old is None or (old[1] == tag and old[2] == digest):
            continue
        changes.append((service, image, old[1], tag, old[2], digest))
    if not changes:
        return

    stats["apps"] += 1
    manifest_repo = repo_from_url(manifest_field(new_lines, REPO_LINE_RE))
    current_version = manifest_field(new_lines, VERSION_LINE_RE)
    old_manifest_lines = git_show(f"{base_sha}:{app_id}/umbrel-app.yml")
    old_version = (manifest_field((old_manifest_lines or "").splitlines(),
                                  VERSION_LINE_RE)
                   if old_manifest_lines else None)

    for service, image, old_tag, new_tag, old_dig, new_dig in changes:
        if old_tag != new_tag:
            print(f"[TAGDIFF] {app_id}: {image} {old_tag} → {new_tag} (semver)")
        else:
            print(f"[TAGDIFF] {app_id}: {image}:{old_tag} "
                  f"{short_digest(old_dig)} → {short_digest(new_dig)} (digest)")

    # ---- primary change: prefer a tag bump over a digest refresh
    primary = next((c for c in changes
                    if c[2] != c[3] and c[2] not in MOVING_TAGS
                    and c[3] not in MOVING_TAGS), None)
    entry_text = None
    marker = None

    if primary:
        _, image, old_tag, new_tag, _, _ = primary
        repos = candidate_repos(image, manifest_repo)
        entries, breaking = fetch_release_notes(repos[0], old_tag, new_tag,
                                                token)
        if not entries and len(repos) > 1:
            entries, breaking = fetch_release_notes(repos[1], old_tag, new_tag,
                                                    token)

        if entries:
            # single entry whose tag matches the new tag: the version is
            # already in the entry prefix, do not repeat it
            if (len(entries) == 1
                    and parse_version(entries[0][1]) == parse_version(new_tag)):
                notes = entries[0][2]
            else:
                notes = " ".join(f"{tag}: {text}" for _, tag, text, _ in entries)
            for _, tag, text, url in entries:
                hit = breaking.get(tag)
                print(f"[CHANGE] {app_id}: {tag} – {text[:200]}"
                      + (f" ⚠️ mögliche Breaking Changes ({', '.join(hit)})"
                         if hit else "") + f" ({url})")
        else:
            fallback_url = f"https://github.com/{repos[0]}/releases" if repos else ""
            notes = (f"Update des Docker-Images auf {new_tag}. "
                     f"Keine automatisierten Release-Notes abrufbar"
                     + (f" – Details: {fallback_url}" if fallback_url else "")
                     + ".")
            print(f"[NOTE ] {app_id}: Für den Tag-Wechsel {old_tag} → {new_tag} "
                  f"sind keine Upstream-Release-Notes abrufbar.")

        notes = truncate_text(notes, MAX_ENTRY_CHARS)
        entry_text = f"{new_tag} - {notes}"
        marker = f"{new_tag} - "

        # manifest version should track the new tag (Renovate does this via
        # its custom manager; hint on manual PRs that skipped it)
        old_core = parse_version(strip_packaging_suffix(old_version or ""))
        cur_core = parse_version(strip_packaging_suffix(current_version or ""))
        new_core = parse_version(new_tag)
        if old_core == parse_version(old_tag) and cur_core != new_core:
            print(f"[NOTE ] {app_id}: Die version: in der umbrel-app.yml "
                  f"({current_version}) entspricht nicht dem neuen Image-Tag "
                  f"{new_tag} – bitte mit anpassen (Renovate erledigt das "
                  f"normalerweise automatisch).")
    else:
        # digest refresh (moving tag re-pinned, or digest of a pinned tag)
        digest_changes = [c for c in changes if c[4] != c[5]]
        if not digest_changes:
            return
        summary = ", ".join(
            f"{image}:{tag} {short_digest(od)[:19]} → {short_digest(nd)[:19]}"
            for _, image, tag, _, od, nd in digest_changes)
        entry_text = ("Automatische(s) Digest-Update(s) (Renovate): "
                      + summary + ".")
        marker = short_digest(digest_changes[0][5])[:19]
        for _, image, tag, _, od, nd in digest_changes:
            print(f"[CHANGE] {app_id}: {image}:{tag} – Digest aktualisiert "
                  f"{short_digest(od)[:19]} → {short_digest(nd)[:19]} "
                  f"(automatisches Update, keine Tag-Änderung).")

    # ---- write changelog into umbrel-app.yml
    updated = prepend_release_notes(new_lines, entry_text, marker)
    if updated:
        write_lines(manifest_path, updated)
        stats["files"] += 1
        preview = entry_text[:120] + ("…" if len(entry_text) > 120 else "")
        print(f"[UPDATE] {app_id}/umbrel-app.yml: releaseNotes ergänzt – {preview}")

    # ---- sync README version cell with the manifest version
    readme_path = os.path.join(root, "README.md")
    if current_version and not str(current_version).startswith("sha256:"):
        try:
            readme = read_lines(readme_path)
        except OSError:
            readme = None
        if readme is not None:
            row_re = re.compile(rf"\|\s*`{re.escape(app_id)}`\s*\|")
            changed = False
            for i, line in enumerate(readme):
                if not row_re.search(line) or not line.lstrip().startswith("|"):
                    continue
                cells = line.split("|")
                if len(cells) >= 4 and cells[3].strip() != str(current_version):
                    cells[3] = f" {current_version} "
                    readme[i] = "|".join(cells)
                    changed = True
                break
            if changed:
                write_lines(readme_path, readme)
                stats["files"] += 1
                print(f"[UPDATE] README.md: Version {app_id} → {current_version}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="app store repository root")
    parser.add_argument("--base-sha", default=None,
                        help="PR base sha to diff against")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or None
    root = os.path.abspath(args.root)

    if not args.base_sha:
        print("[NOTE ] Kein Base-SHA (kein PR-Lauf) – Changelog-Sync übersprungen.")
        return 0

    apps = sorted(
        d for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d))
        and os.path.isfile(os.path.join(root, d, "umbrel-app.yml"))
    )
    changed = changed_apps(args.base_sha, apps)
    if not changed:
        print("Changelog sync: keine Apps in diesem PR geändert.")
        return 0

    stats = {"apps": 0, "files": 0}
    for app_id in sorted(changed):
        try:
            process_app(root, app_id, args.base_sha, token, stats)
        except Exception as e:  # the sync must never break the check
            print(f"[NOTE ] {app_id}: Changelog-Sync fehlgeschlagen ({e}).")

    print(f"Changelog sync: {len(changed)} App(s) mit Tag-Änderungen geprüft, "
          f"{stats['files']} Datei(en) im Workspace aktualisiert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

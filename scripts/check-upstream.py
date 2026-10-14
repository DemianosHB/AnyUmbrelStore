#!/usr/bin/env python3
"""Watch upstream projects for new releases and breaking changes.

Complements Renovate (which bumps versions/digests automatically) with a
changelog radar: every run fetches the latest GitHub releases of the
upstreams behind this store's app packages and reports

* newer stable releases than the version pinned in the package
* breaking-change keywords in the release notes of those new releases
* for the Gluetun dev channel: whether a stable release shipped the
  SOCKS5 proxy server (the trigger to migrate back from :latest)
* whether the upstream source repositories still exist (a vanished
  repo means an unmaintained, unauditable image)

Output: human-readable report on stdout, optional Markdown report file.
Exit code is always 0 unless the GitHub API rate limit is hit (then 2).
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

GITHUB_API = "https://api.github.com"

# Words that hint at breaking changes or required migration steps.
BREAKING_KEYWORDS = [
    "breaking", "⚠", "deprecat", "renamed", "removed",
    "no longer", "must now", "migrate", "migration", "incompatible",
]

# Watches: what this store depends on and how to judge new releases.
# gluetun runs on the dev channel (:latest, digest-pinned); stable_baseline
# is the newest stable release that was current when the package moved to
# the dev channel. Update it once the package migrates back to release tags.
WATCHES = [
    {
        "app": "anyumbrelstore-gluetun",
        "repo": "passteque/gluetun",
        "kind": "dev-channel",
        "stable_baseline": "3.41.3",
        "feature_hint": ("socks5", "SOCKS5-Proxy-Server in einem Stable-Release "
                         "enthalten – Umstellung vom Dev-Kanal (:latest) auf "
                         "Release-Tags jetzt möglich."),
    },
    {
        "app": "anyumbrelstore-profilearr",
        "repo": "Dictionarry-Hub/profilarr",
        "kind": "stable",
        "manifest": "anyumbrelstore-profilearr/umbrel-app.yml",
    },
    {
        "app": "anyumbrelstore-gluetun (webui sidecar)",
        "repo": "scuzza/gluetun-webui",
        "kind": "repo-exists",  # no semver releases; Renovate tracks the digest
    },
]

ISSUE_MARKER = "[upstream-watch]"


def gh_request(url: str, token: str | None):
    """GET a GitHub API URL, return parsed JSON (None on 404)."""
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "anyumbrelstore-upstream-watch",
    })
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code == 403 and "rate limit" in (e.read().decode() or "").lower():
            print("::error ::GitHub API rate limit exceeded "
                  "(set GITHUB_TOKEN to raise it)")
            sys.exit(2)
        raise


def parse_version(text: str):
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", str(text).strip())
    return tuple(int(x) for x in m.groups()) if m else None


def strip_packaging_suffix(version: str) -> str:
    """'2.2.0+patch1' -> '2.2.0' (packaging-only suffix, not upstream)."""
    return re.sub(r"\+patch\d+$", "", str(version).strip())


def pinned_version_from_manifest(root: str, rel_path: str) -> str | None:
    path = os.path.join(root, rel_path)
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r'^version:\s*"?([^"\s]+)"?\s*$', line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return None


def scan_for_keywords(body: str, keywords: list[str]) -> list[str]:
    hits = []
    low = (body or "").lower()
    for kw in keywords:
        if kw.lower() in low:
            hits.append(kw)
    return hits


def check_repo_exists(repo: str, token: str | None) -> tuple[bool, str | None]:
    data = gh_request(f"{GITHUB_API}/repos/{repo}", token)
    if data is None:
        return False, None
    return True, (data.get("pushed_at") or "")[:10]


def check_release_watch(watch: dict, root: str, token: str | None,
                        alerts: list[str], infos: list[str]) -> None:
    repo = watch["repo"]
    app = watch["app"]

    if watch["kind"] == "repo-exists":
        exists, pushed = check_repo_exists(repo, token)
        if exists:
            infos.append(f"{app}: Upstream-Repo ok (letzter Push: {pushed}).")
        else:
            alerts.append(
                f"{app}: Das Upstream-Repo **{repo}** ist nicht mehr öffentlich "
                "aufrufbar (404). Quelle fehlt – Image ist nicht mehr auditierbar "
                "und wird vermutlich nicht mehr gepflegt. Alternative prüfen.")
        return

    releases = gh_request(f"{GITHUB_API}/repos/{repo}/releases?per_page=15", token)
    if not isinstance(releases, list) or not releases:
        alerts.append(f"{app}: Keine Releases für {repo} abrufbar.")
        return

    # pinned version we compare against
    if watch["kind"] == "stable":
        pinned_raw = pinned_version_from_manifest(root, watch["manifest"])
        pinned = parse_version(strip_packaging_suffix(pinned_raw or ""))
        if pinned is None:
            alerts.append(f"{app}: Gepinnte Version aus {watch['manifest']} "
                          f"nicht lesbar ({pinned_raw!r}).")
            return
        baseline = pinned
    else:  # dev-channel: compare against the last stable we know of
        baseline = parse_version(watch["stable_baseline"])

    feature_kw, feature_msg = watch.get("feature_hint", (None, None))

    for rel in releases:
        if rel.get("prerelease") or rel.get("draft"):
            continue
        ver = parse_version(rel.get("tag_name") or "")
        if ver is None or baseline is None or ver <= baseline:
            continue
        tag = rel["tag_name"]
        body = rel.get("body") or ""
        url = rel.get("html_url") or f"https://github.com/{repo}/releases/tag/{tag}"

        hits = scan_for_keywords(body, BREAKING_KEYWORDS)
        if hits:
            alerts.append(
                f"{app}: Neues Release **{tag}** enthält mögliche "
                f"Breaking Changes (Stichworte: {', '.join(hits)}). "
                f"Release Notes: {url}")
        else:
            infos.append(f"{app}: Neues Release **{tag}** verfügbar "
                         f"(ohne Breaking-Stichworte). {url}")

        if feature_kw and scan_for_keywords(body, [feature_kw]):
            alerts.append(f"{app}: {tag} – {feature_msg} {url}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="app store repository root")
    parser.add_argument("--report-file", default=None,
                        help="write a Markdown report to this file "
                             "(file is only created when there are findings)")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or None
    root = os.path.abspath(args.root)

    alerts: list[str] = []
    infos: list[str] = []
    for watch in WATCHES:
        try:
            check_release_watch(watch, root, token, alerts, infos)
        except Exception as e:  # one broken watch must not kill the rest
            alerts.append(f"{watch['app']}: Watch fehlgeschlagen: {e}")

    print(f"Upstream watch: {len(WATCHES)} watched, "
          f"{len(alerts)} alert(s), {len(infos)} info(s).")
    for a in alerts:
        print(f"[ALERT] {a}")
    for i in infos:
        print(f"[INFO ] {i}")

    if args.report_file and alerts:
        lines = [f"# {ISSUE_MARKER} Upstream-Report", ""]
        lines.append("Automatisch erzeugt durch den **Upstream Changelog Watch** "
                     "Workflow (README → Pflege).")
        lines.append("")
        lines.append("## ⚠️ Handlungsbedarf")
        lines += [f"- {a}" for a in alerts] or ["- (keine)"]
        lines += ["", "## ℹ️ Hinweise"]
        lines += [f"- {i}" for i in infos] or ["- (keine)"]
        with open(args.report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Report written to {args.report_file}")
    elif args.report_file:
        # signals the workflow that a stale report file from a previous
        # run should not be reused
        if os.path.exists(args.report_file):
            os.remove(args.report_file)
        print("No alerts - no report file written.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

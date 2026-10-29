#!/usr/bin/env python3
"""Validate Umbrel community app store packages.

Implements the packaging rules from getumbrel/umbrel-apps
(.agents/skills/umbrel-package-app) as CI checks:

* manifest structure, required fields, id == folder name, store-id prefix
* version format: semver with optional 4th numeric component for upstream
  four-part versions (e.g. Duplicati 2.4.1.0) (optional +patchN packaging
  suffix) or sha256 digest (optional -pkgN packaging suffix), never a bare
  "latest"
* unique host ports within this store and against the official app store
* headless apps (no app_proxy) may use port 0; web UI apps need a positive port
  (manifest ports and raw compose host bindings)
* app_proxy wiring (APP_HOST container name pattern, APP_PORT)
* image tags: moving tags (latest/main) must be digest-pinned
* storage.dataRoot must be exactly "data"
* in-repo icon files referenced via raw.githubusercontent URLs of this very
  repository must exist (foreign repo icons are left alone)
* security gates as warnings: privileged, docker.sock, host networking,
  cap_add, device mounts (allowed with justification, e.g. VPN clients)
* persistence: warn if no volume uses APP_DATA_DIR

Exit code 1 on any error, 0 if only warnings remain.
"""

import argparse
import os
import re
import subprocess
import sys

import yaml

SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")  # 4th component: upstream four-part versions (e.g. Duplicati 2.4.1.0)
SHA256 = re.compile(r"^sha256:[a-f0-9]{64}(?:-pkg\d+)?$")
MANIFEST_VERSION = re.compile(r"^\d+(\.\d+)?$")  # Umbrel schema versions: 1, 1.1, 1.2, 2.0
MOVING_TAGS = {"latest", "main"}

errors: list[str] = []
warnings: list[str] = []

REPO = ""  # "owner/name" of this store repository, set in main() from --repo


def err(path: str, msg: str) -> None:
    errors.append(f"[ERROR] {path}: {msg}")


def warn(path: str, msg: str) -> None:
    warnings.append(f"[WARN ] {path}: {msg}")


def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def app_dirs(root: str) -> list[str]:
    return sorted(
        d
        for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d))
        and os.path.isfile(os.path.join(root, d, "umbrel-app.yml"))
    )


def collect_official_ports(repo_path: str) -> set[int]:
    """Manifest ports plus raw host port bindings from the official store."""
    ports: set[int] = set()
    for d in app_dirs(repo_path):
        manifest_path = os.path.join(repo_path, d, "umbrel-app.yml")
        try:
            manifest = load_yaml(manifest_path) or {}
            if isinstance(manifest.get("port"), int):
                ports.add(manifest["port"])
        except Exception:
            continue
        compose_path = os.path.join(repo_path, d, "docker-compose.yml")
        if not os.path.isfile(compose_path):
            continue
        try:
            compose = load_yaml(compose_path) or {}
            for service in (compose.get("services") or {}).values():
                for mapping in service.get("ports") or []:
                    if isinstance(mapping, int):
                        ports.add(mapping)
                        continue
                    host = str(mapping).split(":")[0]
                    if host.isdigit():
                        ports.add(int(host))
        except Exception:
            continue
    return ports


def compose_host_ports(compose: dict) -> set[int]:
    ports: set[int] = set()
    for service in (compose.get("services") or {}).values():
        for mapping in service.get("ports") or []:
            if isinstance(mapping, int):
                ports.add(mapping)
                continue
            host = str(mapping).split(":")[0]
            if host.isdigit():
                ports.add(int(host))
    return ports


def changed_apps(base_sha: str | None, all_apps: list[str]) -> set[str]:
    if not base_sha:
        return set()
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


def check_app(store_root: str, app_id: str, official_ports: set[int],
              store_manifest_ports: dict[str, int], store_host_ports: dict[str, set[int]]) -> None:
    app_dir = os.path.join(store_root, app_id)
    manifest_rel = f"{app_id}/umbrel-app.yml"
    compose_rel = f"{app_id}/docker-compose.yml"

    # ---- manifest ----
    manifest_path = os.path.join(app_dir, "umbrel-app.yml")
    manifest = None
    try:
        manifest = load_yaml(manifest_path) or {}
    except Exception as e:
        err(manifest_rel, f"invalid YAML: {e}")
        return

    required = ["manifestVersion", "id", "name", "tagline", "description",
                "version", "port", "category", "developer", "website",
                "repo", "support", "submitter", "submission", "path", "gallery"]
    for field in required:
        if field not in manifest:
            err(manifest_rel, f"missing required field: {field}")

    app_manifest_id = manifest.get("id")
    if app_manifest_id != app_id:
        err(manifest_rel, f"id ({app_manifest_id!r}) must match folder name ({app_id!r})")

    # ---- store id prefix ----
    try:
        store_meta = load_yaml(os.path.join(store_root, "umbrel-app-store.yml")) or {}
        store_id = str(store_meta.get("id", "")).strip('"')
    except Exception:
        store_id = ""
    if store_id and isinstance(app_manifest_id, str) and not app_manifest_id.startswith(store_id + "-"):
        err(manifest_rel, f"id must start with the store id prefix '{store_id}-'")
    if isinstance(app_manifest_id, str) and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", app_manifest_id):
        err(manifest_rel, "id must be lowercase kebab-case")

    # ---- manifestVersion ----
    mv = str(manifest.get("manifestVersion", ""))
    if not MANIFEST_VERSION.match(mv):
        err(manifest_rel, f"manifestVersion {mv!r} is not a valid schema version (e.g. 1, 1.1 or 2.0)")

    # ---- version ----
    version = str(manifest.get("version", ""))
    if version == "latest" or (version in MOVING_TAGS):
        err(manifest_rel, "version must not be a bare moving tag such as 'latest'")
    elif not (SEMVER.match(version) or SHA256.match(version)):
        err(manifest_rel, f"version {version!r} must be upstream semver (3 or 4 numeric components, optional +patchN packaging suffix) or a sha256 digest")

    # ---- port ----
    # Headless apps (ohne app_proxy) nutzen port 0 = "kein Web-UI".
    # Die Kreuzpruefung mit app_proxy erfolgt weiter unten, nachdem die
    # Compose-Datei geladen wurde.
    port = manifest.get("port")
    if not isinstance(port, int) or port < 0:
        err(manifest_rel, f"port must be a non-negative integer, got {port!r}")
    elif port == 0:
        pass  # headless app; app_proxy-Absenz wird unten geprueft
    else:
        if port in official_ports:
            err(manifest_rel, f"port {port} conflicts with the official Umbrel App Store")
        for other, other_port in store_manifest_ports.items():
            if other != app_id and other_port == port:
                err(manifest_rel, f"port {port} also used by app {other}")
        store_manifest_ports[app_id] = port

    # ---- storage ----
    storage = manifest.get("storage")
    if storage is not None:
        data_root = (storage or {}).get("dataRoot")
        if data_root != "data":
            err(manifest_rel, "storage.dataRoot must be exactly 'data'")

    # ---- gallery ----
    if not isinstance(manifest.get("gallery"), list):
        err(manifest_rel, "gallery must be a list (empty for new packages)")

    # ---- icon referenced in-repo must exist ----
    icon = manifest.get("icon")
    if isinstance(icon, str) and "raw.githubusercontent.com" in icon:
        # raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>
        m = re.search(r"raw\.githubusercontent\.com/([^/]+)/([^/]+)/[^/]+/(.+)$", icon)
        if m:
            owner_repo = f"{m.group(1)}/{m.group(2)}".lower()
            if owner_repo == REPO.lower():
                local = os.path.join(store_root, m.group(3))
                if not os.path.isfile(local):
                    err(manifest_rel, f"icon references missing in-repo file: {m.group(3)}")

    # ---- compose ----
    compose_path = os.path.join(app_dir, "docker-compose.yml")
    if not os.path.isfile(compose_path):
        err(app_id, "docker-compose.yml missing")
        return
    try:
        compose = load_yaml(compose_path) or {}
    except Exception as e:
        err(compose_rel, f"invalid YAML: {e}")
        return

    services = compose.get("services") or {}
    if not services:
        err(compose_rel, "no services defined")
        return

    # ---- app_proxy wiring ----
    proxy = services.get("app_proxy")
    if proxy is None:
        if port != 0:
            warn(compose_rel, "no app_proxy service and port != 0: headless apps should use port 0")
    else:
        if port == 0:
            err(manifest_rel, "port is 0 but app_proxy is defined: web UI apps need a positive port")
        proxy_env = {e.split("=", 1)[0]: e.split("=", 1)[-1] for e in proxy.get("environment") or []}
        if isinstance(proxy.get("environment"), dict):
            proxy_env = proxy.get("environment") or {}
        app_host = proxy_env.get("APP_HOST", "")
        m = re.fullmatch(r"([a-z0-9-]+)_(.+)_1", app_host)
        if not m or m.group(1) != app_id:
            err(compose_rel, f"app_proxy APP_HOST {app_host!r} must be '<app-id>_<service>_1'")
        elif m.group(2) not in services:
            err(compose_rel, f"app_proxy APP_HOST references unknown service {m.group(2)!r}")
        app_port = proxy_env.get("APP_PORT")
        if not str(app_port).isdigit():
            err(compose_rel, f"app_proxy APP_PORT must be an integer, got {app_port!r}")

    # ---- images ----
    for service_name, service in services.items():
        image = service.get("image")
        if not image:
            continue
        # Non-greedy image part and a tag that must not contain ":" or "@" -
        # otherwise the digest lands in the tag group for digest-pinned
        # refs (image:latest@sha256:...) and the digest stays empty.
        m = re.fullmatch(r"(.*?):([^:@]+)(@sha256:[a-f0-9]{64})?", str(image))
        if not m:
            err(compose_rel, f"service {service_name}: unparsable image reference {image!r}")
            continue
        tag, digest = m.group(2), m.group(3)
        if tag in MOVING_TAGS and not digest:
            err(compose_rel, f"service {service_name}: moving tag {tag!r} must be digest-pinned")

    # ---- host ports (conflicts across store + official) ----
    host_ports = compose_host_ports(compose)
    store_host_ports[app_id] = host_ports
    for p in host_ports:
        if p in official_ports:
            err(compose_rel, f"host port {p} conflicts with the official Umbrel App Store")
    for other, other_ports in store_host_ports.items():
        if other != app_id and host_ports & other_ports:
            err(compose_rel, f"host ports {sorted(host_ports & other_ports)} also bound by app {other}")

    # ---- persistence ----
    all_volumes = []
    for service in services.values():
        all_volumes.extend(service.get("volumes") or [])
    if not any("APP_DATA_DIR" in str(v) for v in all_volumes):
        warn(compose_rel, "no volume uses APP_DATA_DIR: app data is not persisted")

    # ---- security gates (warnings: allowed with justification) ----
    for service_name, service in services.items():
        if service.get("privileged"):
            warn(compose_rel, f"service {service_name}: privileged mode (requires justification)")
        if service.get("network_mode") == "host":
            warn(compose_rel, f"service {service_name}: host networking (requires justification)")
        for v in service.get("volumes") or []:
            if "docker.sock" in str(v):
                err(compose_rel, f"service {service_name}: mounting the Docker socket is not allowed for App Store packages")
        if service.get("cap_add"):
            warn(compose_rel, f"service {service_name}: cap_add {service.get('cap_add')} (requires justification, e.g. NET_ADMIN for VPN clients)")
        if service.get("devices"):
            warn(compose_rel, f"service {service_name}: device mounts {service.get('devices')} (requires justification)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="app store repository root")
    parser.add_argument("--official", default=None, help="path to a clone of getumbrel/umbrel-apps")
    parser.add_argument("--base-sha", default=None, help="PR base sha to determine changed apps")
    parser.add_argument("--repo", default=None, help="owner/name of this store repo, e.g. DemianosHB/AnyUmbrelStore")
    args = parser.parse_args()

    global REPO
    REPO = args.repo or ""

    root = os.path.abspath(args.root)
    apps = app_dirs(root)
    official_ports = collect_official_ports(args.official) if args.official and os.path.isdir(args.official) else set()

    changed = changed_apps(args.base_sha, apps)
    if changed:
        print(f"Apps changed in this PR: {', '.join(sorted(changed))}\n")

    store_manifest_ports: dict[str, int] = {}
    store_host_ports: dict[str, set[int]] = {}
    # The store is small: always check every app, not just the ones changed in
    # the PR. Port-conflict maps below still need all apps anyway.
    for app in apps:
        check_app(root, app, official_ports, store_manifest_ports, store_host_ports)

    print(f"Checked {len(apps)} app package(s) against {len(official_ports)} official store ports.\n")
    for w in warnings:
        print(w)
    for e in errors:
        print(e)
    print(f"\nSummary: {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors:
        print("::error ::App package validation failed with " + str(len(errors)) + " error(s)")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

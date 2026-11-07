## Änderungen

- [ ] App Store Check ist grün (Manifest, Ports, app_proxy, Security-Gates)
- [ ] Tag-/Digest-Bumps: `releaseNotes` in der `umbrel-app.yml` gepflegt (Breaking Changes aus den Upstream-Release-Notes übernommen)
- [ ] Breaking Changes aus dem Changelog-Sync geprüft (PR hat ggf. das Label `breaking-change`; bei bewusster Übernahme `breaking-ok` setzen)
- [ ] Sicherheits-Warnungen (privileged, cap_add, devices, host networking) sind in der Manifest-Beschreibung begründet
- [ ] README (Versionstabelle/Beschreibung) ist aktuell

## Hinweise

- Reine Digest-Updates (z. B. Gluetun `:latest`) merged Renovate automatisch, sobald der App-Store-Check grün ist.
- Upstream-Bumps von Watchly (`WATCHLY_REF`) sind bewusst manuell: Entrypoint-Muster prüfen, siehe `docker/watchly/README.md`.
- GitHub-Actions-Updates kommen als gebündelter Renovate-PR („GitHub Actions updates"), die Actions sind auf Commit-SHAs gepinnt.

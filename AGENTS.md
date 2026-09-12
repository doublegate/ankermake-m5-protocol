<!-- Managed by Master-Claude. Universal rules come from the imported/inlined core.
     Edit only inside the MC-PROJECT block; mc-sync overwrites everything else. -->
<!-- mc-core: 0.2.0 | mode=import | lang=python -->
# AGENTS.md — ankermake-m5-protocol

@/home/parobek/.claude/master-core/AGENTS.base.md
@/home/parobek/.claude/master-core/lang/python.md
@/home/parobek/.claude/master-core/modules/10-commits-and-versioning.md
@/home/parobek/.claude/master-core/modules/20-testing-and-accuracy.md
@/home/parobek/.claude/master-core/modules/30-quality-gates.md
@/home/parobek/.claude/master-core/modules/40-docs-and-adrs.md
@/home/parobek/.claude/master-core/modules/50-architecture-patterns.md
@/home/parobek/.claude/master-core/modules/60-security.md
@/home/parobek/.claude/master-core/modules/70-release-ceremony.md
@/home/parobek/.claude/master-core/modules/80-phase-sprint-workflow.md
@/home/parobek/.claude/master-core/modules/90-multi-language-integration.md
@/home/parobek/.claude/master-core/modules/91-agent-system-architecture.md
@/home/parobek/.claude/master-core/modules/95-named-pattern-library.md

<<< MC-PROJECT-START >>>

## Project: ankermake-m5-protocol

- **What it is:** `ankerctl` — a CLI and Flask web UI for monitoring, controlling and printing to
  AnkerMake M5 / M5C 3D printers without Anker's closed-source software. Ships `libflagship/`,
  the protocol library (PPPP, MQTT, HTTPS) it is built on, in the same repo.
- **Fork lineage:** this repo is `doublegate/ankermake-m5-protocol`, forked from
  `anselor/ankermake-m5-protocol` (the "exiles" line), itself forked from the original
  `Ankermgmt/ankermake-m5-protocol` by Christian Iversen. GPL-3.0 throughout; upstream copyright
  notices must be preserved. `git remote`: `origin` = doublegate, `upstream` = anselor.
  To see this fork's own divergence: `git log --oneline upstream/main..HEAD`.
- **Stack:** Python >= 3.10 (enforced at import time by `cli/checkver.py`). Flask 3.0.3 +
  flask-sock (websockets), click 8.1.3, rich, paho-mqtt 1.6.1, pycryptodomex, tinyec, crcmod,
  platformdirs, python-dotenv. Every dependency is pinned exactly in `requirements.txt`.
- **Build / run:** `pip install -r requirements.txt` / `./ankerctl.py --help`;
  web UI: `./ankerctl.py webserver run`. Docker: `docker compose up` (`docker-compose.yaml`,
  `compose.sh`, `docker-import.sh`) — the Docker install path is Linux-only.
- **Test:** none exists. No test suite, no pytest/tox/pyproject config, no CI test job. Do not
  report a change as "tested" here without adding the test that proves it (module 20: pin the
  failing test first).
- **Lint / format gate:** `pycodestyle` via `.pep8` (max_line_length 120; E221, E226, E231, E241,
  E261, E203, E741 ignored). Not wired into CI — run it locally before declaring done.

### Architecture — load-bearing facts

- **Four files are generated, not hand-written.** `libflagship/pppp.py`, `libflagship/mqtt.py`,
  `libflagship/amtypes.py` and `static/libflagship.js` are produced by `transwarp` from
  `specification/*.stf` plus `templates/`. Change the `.stf` spec or the `.tpl` template, then
  `make update` (`make diff` previews). Editing the generated file directly is silently undone by
  the next `make update`. The `.pep8` `exclude` list names exactly the three generated Python
  files — that is the reliable marker of what is generated.
- **`transwarp/` is a git submodule** (github.com/chrivers/transwarp). `make install-tools` runs
  `git submodule update --init` then `pip install ./transwarp`. A clone without `--recursive`
  leaves the directory empty and `make update` fails.
- **Printer I/O runs in long-lived background services, never in request handlers.**
  `web/lib/service.py` provides `ServiceManager`, `RunState` and the holdoff/restart signalling;
  `web/service/{mqtt,pppp,video,filetransfer}.py` are the registered workers. The websocket routes
  in `web/__init__.py` (`/ws/mqtt`, `/ws/pppp-state`, `/ws/video`, `/ws/ctrl`) only pump their
  queues. Anything touching a printer connection belongs in a service.
- **Dependency direction is one-way:** `ankerctl.py` → `cli/` and `web/` → `libflagship/`.
  `libflagship/` is protocol-only and must not import from `cli/` or `web/`.

### Gotchas / institutional knowledge

- **Flask's `template_folder` is `static/`, not `templates/`.** `web/__init__.py:51` constructs
  `Flask(..., static_folder="static", template_folder="static")`, so the Jinja templates are
  `static/base.html`, `static/index.html`, `static/macro.html`, `static/footer.html`,
  `static/tabs/`. Root `templates/` holds transwarp codegen templates exclusively and has nothing
  to do with Flask. Check which one you mean before editing.
- **`.env` is tracked in git and is not gitignored**, and `ankerctl.py` calls `load_dotenv()` at
  import. Never put a credential in it. It stays tracked on purpose: `install-from-docker.md` tells
  users to `curl -O` it, so gitignoring it would both do nothing (already tracked) and break the
  documented bootstrap.
- **Printer credentials are sensitive and live outside the repo.** They are imported from Anker's
  `login.json` (`ankerctl.py config import`) and stored in a platformdirs-managed config
  (`cli/config.py`). Never commit a `login.json`, and treat `config show` / `config decode` output
  as secret — it prints account and printer key material. The `user_id` field functions as the MQTT
  password. `.gitignore` now defends this directly (`login.json`, `*.log` for `--pppp-dump`
  captures, which carry printer DUIDs).
- **CI is release-only and proves nothing about correctness.**
  `.github/workflows/build-and-publish.yml` is the sole workflow: it builds multi-arch Docker
  images (linux/arm/v7, arm64, amd64) and cuts GitHub releases on `v**` tags, `main`, and
  `upcoming/*`. It runs no lint and no tests, so a green check is a build, not a gate. Run
  `pycodestyle` locally; nothing else will.
- **The CI branch triggers said `master` until this fork fixed them.** Only the *original*
  Ankermgmt repo uses `master`; both `anselor` and this fork default to `main`, so for the whole
  life of the anselor fork no push to the default branch ever built an image or cut a release.
  Retargeted to `main` in 4 places (push trigger, PR trigger, and the two `latest` tag conditions).
  When inheriting upstream workflow changes, re-check this — a merge can reintroduce `master`.
- **`ghcr.io/doublegate/ankermake-m5-protocol:latest` is published on every push to `main`** and
  the package is public, so the documented `docker compose up` works. (It used to point at
  `anselor/ankerctl:exile-latest` on Docker Hub, i.e. the intermediate fork's build.)
- **A forked repo suppresses Actions behind a one-time acknowledgement banner** in the Actions tab,
  and no API clears it: `actions/permissions` reports `enabled: true` and `gh workflow enable`
  exits clean while the gate is still shut. The only reliable signal is `total_count: 0` from
  `gh api repos/OWNER/REPO/actions/runs`. If CI seems not to fire on a fork, check that first.
- **Doc-only pushes skip the build** via `paths-ignore` on the `push` and `pull_request` triggers
  (`**.md`, `documentation/**`, `LICENSE`, `.gitignore`, `.gitattributes`, `.editorconfig`,
  `.vscode/**`) — the Dockerfile copies none of those. `.github/workflows/**` is deliberately NOT
  ignored, since a build is the only validation a workflow edit gets. Two properties this relies
  on: **path filters are not evaluated for tag pushes** (per GitHub docs), so a `v*` release tag
  builds even on a docs-only diff; and `main` has **no branch protection / required checks**, so a
  docs-only PR reporting no check at all cannot strand a merge. If protection is ever added, add a
  companion job that reports success for the ignored paths.
- **Release steps are gated on `startsWith(github.ref, 'refs/tags/')`, not on the push event.**
  `antonyurchenko/git-release` FATALs unless `GITHUB_REF` matches `refs/tags/vX.Y.Z`, so the
  original `event_name == 'push'` guard failed every branch push, and the two archive steps
  silently built `ankerctl-main.zip`/`.tar.gz` for a release that could not exist. Current
  behavior: push to `main` or `workflow_dispatch` -> build + publish image only; a `v*` tag ->
  build + publish + archives + GitHub release; PR -> build only, no registry login.

### Where things live

- `ankerctl.py` — CLI entrypoint; command groups `mqtt`, `pppp`, `http`, `config`, `webserver`.
- `libflagship/` — protocol library: `pppp.py`/`ppppapi.py` (P2P), `mqtt.py`/`mqttapi.py`,
  `httpapi.py`, `seccode.py` + `megajank.py` (crypto), `logincache.py`, `cyclic.py`.
- `cli/` — CLI-side helpers: config, model, logfmt, country codes, version check.
- `web/` — Flask app (`__init__.py` holds the routes), `web/lib/service.py` the service framework,
  `web/service/` the workers, `web/config.py` / `web/platform.py` the host-side glue.
- `specification/` (`.stf`) + `templates/` (`.tpl`) — transwarp codegen inputs.
- `static/` — web UI assets *and* the Flask Jinja templates (see gotcha above).
- `documentation/` — install guides plus `developer-docs/` (libflagship, MQTT overview).
- `examples/` — standalone protocol scripts; `packaging/` — Windows `.bat` + icon for pyinstaller.

### Status / next

- See `CLAUDE.local.md` for volatile session state (current phase/sprint, recent decisions).
<<< MC-PROJECT-END >>>


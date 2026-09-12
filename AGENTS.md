# Repository Guidelines

## Project Structure & Module Organization
- `ankerctl.py` is the main CLI entrypoint.
- `cli/` contains command implementations and helpers.
- `web/` hosts the Flask web server, services, and UI routes.
- `libflagship/` implements protocol clients (MQTT, PPPP, HTTP).
- `static/` contains web UI assets (JS/CSS/images) and vendor bundles.
- `specification/` and `templates/` define protocol specs and codegen templates.
- `examples/` holds small scripts for manual protocol tests and demos.

## Build, Test, and Development Commands
- `./ankerctl.py webserver run` starts the local web UI (requires config).
- `./ankerctl.py mqtt monitor` or `./ankerctl.py pppp lan-search` are quick CLI smoke checks.
- `docker compose up` builds/runs the container from `docker-compose.yaml` (host networking).
- `make update` regenerates `libflagship/` and `static/` from `specification/`.
- `make diff` shows codegen deltas without writing.
- `make install-tools` installs the `transwarp` generator dependency.

## Coding Style & Naming Conventions
- Python uses 4-space indentation; follow existing module layout and patterns.
- Prefer snake_case for functions/variables and CapWords for classes.
- JavaScript follows existing style in `static/ankersrv.js`; avoid introducing new frameworks.
- No enforced formatter or linter is configured; keep diffs tight and readable.

## Testing Guidelines
- There **is** an automated test suite: `tests/` (31 modules). Run `make check`
  (`compileall` + `pytest`) — the same gate CI runs across Python 3.10 and 3.13.
  Verified green at the fork point: 519 passed, 15 skipped.
- Add or adjust tests with the change; for accuracy-critical paths, write the failing
  test first.
- Also validate manually via the CLI (`./ankerctl.py ...`) and web UI where behavior is
  interactive; for protocol changes, the scripts in `examples/` reproduce behavior.

## Commit & Pull Request Guidelines
- Git history uses short, descriptive commit messages (sentence case, sometimes with issue IDs).
- Keep commits focused; mention affected area (e.g., "Fix PPPP file upload reply handling").
- PRs should include a brief summary, testing notes, and screenshots for UI changes.

## Configuration & Security Notes
- Config is stored under `~/.config/ankerctl` (or the container volume).
- `login.json` contains sensitive data; never commit it or paste it in issues.

## Fork Context

This repository is `doublegate/ankermake-m5-protocol`, a fork that **adopted the
`Django1982/ankermake-m5-protocol` tree as its baseline** (2026-09-12). It previously
descended from `anselor/ankermake-m5-protocol` (the "exiles" line); both are forks of the
original `Ankermgmt/ankermake-m5-protocol` by Christian Iversen. GPL-3.0 throughout —
upstream copyright notices must be preserved. See README "Lineage and attribution".

Remotes: `origin` = doublegate, `django` = Django1982 (the tracked upstream),
`upstream` = anselor (historical). What this fork changed:
`git log --oneline django/master..HEAD`.

Things that bite when working here:

- **Default branch is `main`, upstream's is `master`.** `ci.yml` already triggers on both,
  so it works either way — but check this after any merge from upstream.
- **Some of `libflagship/` is generated, not hand-written.** `pppp.py`, `mqtt.py` and
  `amtypes.py` come from `specification/*.stf` via transwarp (`make update`, `make diff`
  to preview). Editing them directly is undone by the next codegen run. `transwarp/` is a
  submodule — a clone without `--recursive` leaves it empty and `make update` fails.
- **Flask's `template_folder` is `static/`, not `templates/`.** Root `templates/` holds
  transwarp codegen templates exclusively and has nothing to do with Flask.
- **Links to `Django1982/...` issues and PRs in CHANGELOG.md and
  `documentation/issue77_code_fix.md` are citations and must stay pointing upstream.**
  Retargeting them to this fork would produce dead links and misattribute the work.
  `.github/FUNDING.yml` likewise still points at the upstream maintainer, deliberately.
- **`tests/test_print_history.py` is flaky on Python 3.10/3.11.** Intermittent
  `sqlite3.OperationalError: cannot start a transaction within a transaction` (and
  `cannot rollback - no transaction is active`) from the `_prune` background thread in
  `web/service/history.py` racing the test's own connection. Seen as a *failure* on the
  3.10 CI job and as an unhandled-thread-exception *warning* on 3.13/3.14 locally; a
  re-run of the identical commit passed. Upstream's own CI is green on the same commit,
  so treat a lone red 3.10 job here as the race, not as breakage — re-run it, and only
  investigate if it reproduces. The underlying bug is real and unfixed.
- **`login.json` is credential material** — its `user_id` works as the MQTT password. It is
  gitignored here; never commit one or paste `config show` output into an issue.

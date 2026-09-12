# ankerctl

**Control your AnkerMake M5 from open-source software.** A command-line tool and web
interface for monitoring, controlling, and printing to AnkerMake M5 / M5C printers —
no closed-source Anker software required.

![Screenshot of ankerctl](/documentation/web-interface.png "The ankerctl web interface")

```sh
git clone --recursive https://github.com/doublegate/ankermake-m5-protocol.git
cd ankermake-m5-protocol
pip install -r requirements.txt
./ankerctl.py webserver run          # then open http://localhost:4470
```

> [!NOTE]
> **This is a fork.** It is maintained by [@doublegate](https://github.com/doublegate) and
> tracks the excellent [`Django1982/ankermake-m5-protocol`](https://github.com/Django1982/ankermake-m5-protocol)
> line by Daniel Heinen, which is where nearly all of the functionality below comes from.
> See [Lineage and attribution](#lineage-and-attribution) for the full chain and credits.
>
> Report issues with **this fork** to its
> [issue tracker](https://github.com/doublegate/ankermake-m5-protocol/issues/new/choose).
> Issues that reproduce upstream are better filed with
> [Django1982](https://github.com/Django1982/ankermake-m5-protocol/issues) directly.

Requires **Python 3.10+**. Docker installs are **Linux-only**. `ffmpeg` is needed for timelapse.

---

## Contents

- [What you can do with it](#what-you-can-do-with-it)
- [Install](#install)
- [Connect your account](#connect-your-account)
- [Everyday use](#everyday-use)
- [Configuration](#configuration)
- [Integrations](#integrations)
- [Networking and firewalls](#networking-and-firewalls)
- [Development](#development)
- [Lineage and attribution](#lineage-and-attribution)
- [Legal](#legal)

---

## What you can do with it

Grouped by what you are actually trying to accomplish, rather than by subsystem.

| Area | Capabilities |
|---|---|
| **Printing** | Send jobs straight from PrusaSlicer, SuperSlicer, OrcaSlicer or Bambu Studio; upload G-code; start prints from printer or USB storage; reprint archived jobs |
| **Monitoring** | Live status, temperatures, progress and current layer; filament state; sticky alerts across printers; live console viewer on the Home page |
| **History** | Automatic SQLite-backed record of every print — filename, timestamps, duration, result, thumbnails — with selective delete and one-click reprint |
| **Camera** | Stream the built-in printer camera; optional external feeds (RTSP / HTTP / MJPEG); manual snapshots saved to a gallery |
| **Timelapse** | Automatic capture during prints with pause / resume / stop, per-printer camera source, partial save on failure, MP4 assembly at print end |
| **Multi-printer** | Per-printer status, controls, history, media and settings |
| **Filament** | Guided swap flow — home, raise Z, park, heat, unload, prompt, load, purge, cool — with per-profile temperature settings |
| **Diagnostics** | Raw G-code console; low-level MQTT / PPPP / HTTPS access; bed level heatmap via `M420 V`; debug tab with state inspector and event simulation |
| **Alerting** | Push notifications through [Apprise](https://github.com/caronc/apprise) on start, finish, failure, upload and progress, optionally with a camera image |
| **Home Assistant** | MQTT Discovery for state, temperatures, progress, light control and camera |
| **Security** | Optional API key gating write operations and sensitive endpoints |

---

## Install

Pick **one** method.

<details open>
<summary><b>From Git</b> — recommended</summary>

```sh
git clone --recursive https://github.com/doublegate/ankermake-m5-protocol.git
cd ankermake-m5-protocol
pip install -r requirements.txt
./ankerctl.py webserver run
```

The `--recursive` matters: `transwarp/` is a submodule. If you already cloned without it,
run `git submodule update --init`.

Full walkthrough: [documentation/install-from-git.md](documentation/install-from-git.md)
</details>

<details>
<summary><b>From Docker</b> — Linux only</summary>

```sh
# Build, matching the container user to your host user
docker build -t ankerctl:local --build-arg UID=$(id -u) --build-arg GID=$(id -g) .

cp .env.example .env        # then edit to taste
docker compose up
```

Host networking is required — PPPP is an asymmetric UDP protocol and will not survive
a bridge network.

Full walkthrough: [documentation/install-from-docker.md](documentation/install-from-docker.md)
</details>

<details>
<summary><b>As a Home Assistant add-on</b></summary>

Add this repository as a Home Assistant add-on source and install from there. See
[`hassio-addon/`](hassio-addon/).
</details>

Once running, open **http://localhost:4470** in a browser on the same machine.

---

## Connect your account

`ankerctl` needs your AnkerMake account data before it can reach a printer. Three routes,
easiest first:

### 1. Straight from the web UI

Go to **Setup -> Account** and click **Import From eufyMake Studio**. This reads an open
eufyMake Studio session on the same machine. If that finds nothing, upload a login file
from the same page.

### 2. Sign in directly

Also on **Setup -> Account** — enter your email and password. Inputs are trimmed, country
codes normalised, and failures keep you on the page with a clear banner.

### 3. From the command line

```sh
./ankerctl.py config import                    # tries the default path for your OS
./ankerctl.py config import path/to/login.json # or point at it explicitly
```

Understands both legacy `login.json` / `user_info` files and the newer **eufyMake Studio
Windows WebView LevelDB cache** (`.ldb`). On Windows it prefers the newest usable slicer
session rather than a stale cache blob, and can recover some truncated auth tokens by
validating candidate prefixes against the API.

Check what landed with `./ankerctl.py config show`.

> [!CAUTION]
> Your cached login is **credential material**. The `user_id` field authenticates to the
> MQTT broker and effectively works as a password — which is why `config show` redacts it
> on screen. Never commit `login.json` or paste `config show` output into an issue.

---

## Everyday use

The web server must be running for the UI, slicer uploads, and every browser-based control.

```sh
./ankerctl.py webserver run
```

### Sending prints from a slicer

Configure your slicer's print host to point at `ankerctl`, then use **Send and Print** —
jobs are uploaded for immediate printing rather than stored for later. Per-slicer setup
lives on the **Instructions** page inside the web UI.

![Screenshot of PrusaSlicer](/static/img/setup/prusaslicer-2.png "PrusaSlicer host setup")

### From the command line

```sh
./ankerctl.py webserver run                       # start the web UI
./ankerctl.py pppp lan-search                     # find printers on the LAN
./ankerctl.py mqtt monitor                        # watch MQTT events
./ankerctl.py mqtt gcode                          # interactive G-code prompt
./ankerctl.py mqtt rename-printer BoatyMcBoatFace # rename
./ankerctl.py pppp print-file boaty.gcode         # print a file
./ankerctl.py pppp capture-video -m 4mb out.h264  # grab camera video
./ankerctl.py -p 1 <command>                      # target a specific printer by index
```

Every command takes `-h`.

---

## Configuration

Configuration is environment-driven. **[`.env.example`](.env.example) is the authoritative
list** — it documents every variable with its default. Copy it to `.env` and Docker Compose
picks it up automatically.

The ones most people touch:

| Variable | Default | What it does |
|---|---|---|
| `FLASK_HOST` | `127.0.0.1` | Bind address — set `0.0.0.0` to reach it from the LAN |
| `FLASK_PORT` | `4470` | Web server port |
| `FLASK_SECRET_KEY` | *auto* | Set explicitly to keep sessions across restarts |
| `PRINTER_INDEX` | `0` | Which configured printer is the default |
| `UPLOAD_MAX_MB` | `512` | Largest accepted upload |
| `UPLOAD_RATE_MBPS` | `10` | Transfer rate to printer (5, 10, 25, 50, 100) |
| `ANKERCTL_API_KEY` | *unset* | Enables API-key authentication (see below) |
| `ANKERCTL_DEV_MODE` | `false` | Unlocks the Debug tab and `/api/debug/*` |
| `ANKERCTL_LOG_DIR` | *unset* | Enables file logging into this directory |
| `TIMELAPSE_ENABLED` | `false` | Automatic timelapse capture — needs `ffmpeg` |
| `PRINT_HISTORY_RETENTION_DAYS` | `90` | How long history is kept |
| `PRINT_HISTORY_MAX_ENTRIES` | `500` | History row cap |

Apprise (`APPRISE_*`), Home Assistant (`HA_MQTT_*`) and the remaining timelapse knobs are
documented in full in `.env.example`.

### Locking it down with an API key

Optional, and off by default for backward compatibility. When set, **write operations and
sensitive endpoints** require the key while the read-only UI stays viewable.

```sh
./ankerctl.py config set-password                # generate a random key
./ankerctl.py config set-password my-secret-key  # or choose one
./ankerctl.py config remove-password             # turn it back off
```

Or set `ANKERCTL_API_KEY` in `.env`. Slicers send it as the `X-Api-Key` header; in a
browser, append `?apikey=your-key` once and a session cookie is set for you.

> [!TIP]
> Set an API key before binding to `0.0.0.0`. Without one, anything on your network can
> drive your printer.

---

## Integrations

<details>
<summary><b>Home Assistant</b> via MQTT Discovery</summary>

Needs an MQTT broker (Mosquitto or similar) reachable by both `ankerctl` and Home Assistant.
Configure the `HA_MQTT_*` variables, or use **Setup -> Home Assistant** in the web UI.

Published: print progress, state, filename, speed and layer; nozzle and bed temperatures;
elapsed and remaining time; MQTT and PPPP connectivity as binary sensors; the printer light
as a two-way switch; and a camera entity.

Endpoints: `GET` / `POST /api/settings/mqtt`
</details>

<details>
<summary><b>Apprise</b> push notifications</summary>

Point `APPRISE_SERVER_URL` at an Apprise API server and set `APPRISE_ENABLED=true`. Each
event — started, finished, failed, uploaded, progress — toggles independently, and progress
notifications can carry a live camera snapshot (falling back to the G-code preview if
capture fails).
</details>

<details>
<summary><b>Timelapse</b></summary>

Set `TIMELAPSE_ENABLED=true` and install `ffmpeg`. Capture starts with the print and
assembles an MP4 at the end; a failed print still saves what it got. Camera source is
per-printer (`follow`, the printer camera, or an external feed), and light behaviour during
capture is configurable. Frames and manual snapshots share the **Snapshots** gallery.
</details>

---

## Networking and firewalls

PPPP is asymmetric UDP, so a stateful firewall will silently drop the printer's replies
unless you allow its ports. `ankerctl` binds predictable local ports specifically to make
this a static rule rather than a guessing game.

With `ufw`, allow UDP `32108` for PPPP and LAN discovery, and TCP `4470` for the web UI and
slicer uploads — run these as root:

```text
ufw allow in proto udp to any port 32108
ufw allow in proto tcp to any port 4470
```

If discovery still hangs at *Connecting*, check that the printer shares a broadcast domain
with the host (no router or VLAN in between), and that a second `ankerctl` is not already
holding `32108` — that surfaces as `RuntimeError: PPPP local port 32108 already in use`.

Background and the underlying socket work:
[`documentation/issue77_code_fix.md`](documentation/issue77_code_fix.md).

---

## Development

```sh
make check        # compileall + pytest, the same gate CI runs
python -m pytest  # tests alone
```

CI runs this across Python 3.10 and 3.13 plus a Docker build on every push and PR.

Some of `libflagship/` is **generated, not hand-written** — `pppp.py`, `mqtt.py` and
`amtypes.py` are produced by [`transwarp`](https://github.com/chrivers/transwarp) from
`specification/*.stf`. Edit the spec or the template in `templates/`, then:

```sh
make install-tools   # first time: init the submodule and install transwarp
make diff            # preview what regeneration would change
make update          # regenerate
```

Editing those three files directly will be undone the next time anyone runs `make update`.

More: [`documentation/developer-docs/libflagship.md`](documentation/developer-docs/libflagship.md)
· [`AGENTS.md`](AGENTS.md) for repository conventions.

---

## Lineage and attribution

`ankerctl` is GPLv3 Free Software with a branching history. This fork stands on all of it,
and the work below is overwhelmingly other people's.

```text
Ankermgmt/ankermake-m5-protocol          original — Christian Iversen (@chrivers) et al.
├── anselor/ankermake-m5-protocol        "exiles" fork — Eric Lin (@anselor)
│   └── doublegate/...                   this fork started here
└── Django1982/ankermake-m5-protocol     Daniel Heinen — baseline this fork now tracks
    └── doublegate/ankermake-m5-protocol  <- you are here
```

| Repository | Maintainer | Contribution |
|---|---|---|
| [Ankermgmt](https://github.com/Ankermgmt/ankermake-m5-protocol) | Christian Iversen ([@chrivers](https://github.com/chrivers)) and contributors | **The original.** Reverse-engineered the PPPP, MQTT and HTTP protocols and wrote `ankerctl` and `libflagship` — the foundation everything here rests on. |
| [Django1982](https://github.com/Django1982/ankermake-m5-protocol) | Daniel Heinen ([@Django1982](https://github.com/Django1982)) and contributors | **The baseline this fork tracks.** Timelapse, snapshot gallery, print history, external cameras, guided filament swap, Apprise and Home Assistant integration, API-key auth, the Home Assistant add-on, the test suite, and the CI that runs it. Nearly every feature documented above. |
| [anselor](https://github.com/anselor/ankermake-m5-protocol) | Eric Lin ([@anselor](https://github.com/anselor)) and contributors | The "exiles" continuation, and this fork's original parent — carrying M5C support, web login, printer IP updating and Docker packaging through a quiet period upstream. |
| [doublegate](https://github.com/doublegate/ankermake-m5-protocol) | [@doublegate](https://github.com/doublegate) | **This fork.** Continued maintenance. |

Individual contributors across the inherited history include Christian Iversen, Daniel
Heinen, Billy Bryant, Thomas Reitmayr, Eric Lin, secprepper, Spencer Owen, LazeMSS,
just-trey, Austin Dennis, Michael Toner, Tero Kivinen, Chase Peeler, Koen van Zuijlen,
Leif Lang, Sondre Grønås, snoj and others. The authoritative list is the commit history:

```sh
git shortlog -sne
```

### Tracking upstream

```sh
git remote add django https://github.com/Django1982/ankermake-m5-protocol.git
git fetch django
git log --oneline django/master..HEAD    # what this fork changed
```

---

## Legal

This project is **not** endorsed by, affiliated with, or supported by AnkerMake or eufyMake.
Everything here was gathered by reverse engineering from publicly available knowledge and
resources. The goal is to make the AnkerMake M5 usable with Free and Open Source Software.

Licensed under the [GNU GPLv3](LICENSE), copyright © 2023 Christian Iversen.

This fork is distributed under that same GPLv3. The original copyright notice is retained
in full; modifications made in this fork and in the upstream forks it builds on are the
copyright of their respective authors and are likewise released under the GPLv3. If you
redistribute this software, modified or not, you must pass on these same freedoms.

Some icons from [IconFinder](https://www.iconfinder.com/iconsets/3d-printing-line), licensed
under [Creative Commons](https://creativecommons.org/licenses/by/3.0/).

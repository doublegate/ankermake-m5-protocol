# Offline Feasibility — AnkerMake / EufyMake M5 Local Operation

> **Precondition:** This document assumes **local DNS rewrites** are available (e.g. via Pi-hole,
> router-level DNS override, or `/etc/hosts` on the ankerctl host). All conclusions are made with
> that precondition in place.

## Overview

This document assesses how far the complete print workflow of the AnkerMake M5 (also sold as
EufyMake E1) can be driven locally, without an active connection to Anker's cloud infrastructure.
It covers two scenarios:

- **Scenario A** — DNS rewrites available, `default.json` (config) already seeded from a prior login.
- **Scenario B** — Anker servers permanently offline, no prior login/config available.

The verdict up front: **all print data already travels over the local LAN via PPPP. The only
cloud-runtime dependency is the MQTT broker used for telemetry and printer control commands.**
On the ankerctl side this is trivially redirectable. The open question is how the printer firmware
behaves when faced with a non-Anker TLS certificate.

---

## 1. Current Communication Landscape

### 1.1 Already Fully Local — PPPP/LAN

All of the following operate over a direct UDP connection to the printer (`printer_ip:32108`)
with no cloud involvement whatsoever. PPPP is pure peer-to-peer; no STUN server, no rendezvous,
no relay. The `open_wan` path exists in the code but is never invoked.

| Feature | Transport | Code reference |
|---|---|---|
| GCode file upload (web UI + CLI) | PPPP DRW/AABB frames | `web/service/filetransfer.py:109-129`, `cli/pppp.py:273-310` |
| Start print | `FileTransfer.END` over PPPP — **no MQTT round-trip needed** | `web/service/filetransfer.py:129` |
| Camera stream (H.264) | PPPP channel 1, `START_LIVE` command | `web/service/video.py:170`, `ankerctl.py:459` |
| LAN discovery | Blind UDP broadcast to `255.255.255.255:32108` | `cli/pppp.py:104-149`, `libflagship/ppppapi.py:351-358` |
| Printer LED / video quality | PPPP command | `web/service/video.py` |

PPPP session establishment requires only the printer's **DUID** — not the DSK/p2p_key. The
`PktLanSearch → PktPunchPkt → PktP2pRdy → PktP2pRdyAck` handshake (`libflagship/ppppapi.py:394-457`)
sends only the DUID. DSK exchange packets (`PktP2pReqDsk` 0x26, `PktListReqDsk` 0x6a) are defined
for the WAN/relay path but never triggered on LAN. The DUID itself is returned by the printer in
its `PktPunchPkt` reply, so LAN discovery is also cloud-free.

The `p2p_key` (DSK) is only required for the video `START_LIVE` sub-command
(`web/service/video.py:187`).

### 1.2 Cloud-Dependent — One-Time Only (HTTP)

The following HTTP calls are made **only during `ankerctl config login` or `config import`**.
After that, all retrieved data is cached in `~/.config/ankerctl/default.json` and never
re-fetched at runtime.

| Endpoint | Purpose |
|---|---|
| `POST /v2/passport/login` | ECDH-encrypted password login |
| `GET  /v1/passport/profile` | Retrieves `user_id`, `email`, `country` |
| `POST /v1/app/query_fdm_list` | Printer list: SN, model, `secret_key` (MQTT AES key), `p2p_hosts` |
| `POST /v1/app/equipment/get_dsk_keys` | PPPP credentials: `p2p_duid`, `p2p_key` |

Hosts: `make-app-eu.ankermake.com` / `make-app.ankermake.com` (`libflagship/httpapi.py:60-63`).

At runtime (MQTT monitor, web UI, file uploads, camera stream) there are **zero outbound HTTP
calls to Anker infrastructure.** The `auth_token` is not used post-login; there is no token
refresh logic anywhere in the codebase.

### 1.3 Cloud-Dependent at Runtime — MQTT (the real blocker)

All printer telemetry and interactive control travel over Anker's hosted MQTT broker:

- **Brokers:** `make-mqtt-eu.ankermake.com` / `make-mqtt.ankermake.com`, port **8789** (TLS)
  — `cli/mqtt.py:14-17`
- **Both the printer firmware and ankerctl connect to the same broker** on the same topic tree
  (`/device/maker/{SN}/...`, `/phone/maker/{SN}/...`) — confirmed by
  `documentation/developer-docs/mqtt-overview.md:62-82`
- **Payload encryption:** AES-256-CBC. Key is per-printer (`mqtt_key`, from `equipment_get_dsk_keys`).
  IV is the hardcoded constant `b"3DPrintAnkerMake"` (`libflagship/megajank.py:25,29`). The broker
  only ever forwards opaque ciphertext — it has no access to the key.
- **Broker auth:** username `eufy_{user_id}`, password = email address (`cli/model.py:206-212`).
  Server-side validation only; a local broker can accept any credentials.
- **TLS trust:** `ssl/ankermake-mqtt.crt` is bundled — the **server's public certificate**
  (CN `*.ankermake.com`, valid until 2122). The private key is on Anker's infrastructure.
- **ankerctl-side TLS bypass:** `--insecure / -k` fully disables cert and hostname checks
  end-to-end (`libflagship/mqttapi.py:74-78`, `cli/mqtt.py:26`, `web/service/mqtt.py:193`).

The following features are exclusively MQTT-dependent:

- Live telemetry: state (ct=1000), progress (ct=1001), temperatures (ct=1003/1004), layer
  count (ct=1052)
- Printer control: pause, resume, stop (`ZZ_MQTT_CMD_PRINT_CONTROL` 0x03f0)
- Interactive GCode (`ZZ_MQTT_CMD_GCODE_COMMAND` 0x0413)
- Auto-leveling trigger, firmware version query, and other MQTT command types

There is no PPPP equivalent for any of these in the current protocol implementation.

---

## 2. Scenario A — DNS Rewrites + Pre-Seeded Config

**Assumption:** `make-mqtt[-eu].ankermake.com` is redirected to a self-hosted Mosquitto broker
via DNS. Config (`default.json`) was seeded from a legitimate one-time login.

### 2.1 ankerctl side — trivially solvable

- Run ankerctl with `-k` (`--insecure`). This flag propagates through all code paths.
- Mosquitto needs no special ACL — `allow_anonymous true` works, or configure it to accept
  `eufy_{user_id}` / email from `default.json`.
- Payload encryption is end-to-end between ankerctl and the printer. The broker never needs the
  AES key; it is not a blocker.

**Result: ankerctl connects to the local broker with zero code changes, just `-k`.**

A cleaner long-term alternative: a `mqtt.ca_cert` config option so a self-signed cert can be
explicitly pinned instead of disabling all verification. See Task T4 below.

### 2.2 Printer firmware side — the actual unknown

The printer firmware behavior when faced with a non-Anker TLS certificate is unknown.
Three outcomes are possible:

| Scenario | Result | Path forward |
|---|---|---|
| Printer does not pin the cert strictly | DNS rewrite works; printer connects to local Mosquitto | Test first — see verification steps |
| Printer pins the Anker CA | TLS handshake fails; printer cannot reach local broker | Requires firmware modification to replace CA trust store |
| Printer uses TLS but not hostname verification | May work with a self-signed `*.ankermake.com` cert | Test second if first fails |

This is the **single gating question** for full offline operation. Everything else is solved.

### 2.3 Offline capability matrix (Scenario A, DNS rewrites given, config seeded)

| Feature | Offline? | Notes |
|---|---|---|
| GCode upload | Yes | PPPP LAN |
| Start print | Yes | PPPP LAN (`FileTransfer.END`) |
| Camera stream | Yes | PPPP channel 1 |
| Printer LED control | Yes | PPPP |
| LAN discovery | Yes | UDP broadcast |
| Pause / resume / stop | Yes ✓ | MQTT `ct=1008` via local broker; verified 2026-04-28 |
| Live temps, progress, layer, state | If broker works | MQTT telemetry; depends on firmware TLS |
| Interactive GCode (Home, M104, etc.) | If broker works | MQTT; depends on firmware TLS |
| Auto-leveling | If broker works | MQTT; depends on firmware TLS |
| Home Assistant integration | If broker works | Downstream of MQTT |
| Apprise notifications | If broker works | Downstream of MQTT |
| Print history (events) | If broker works | Downstream of MQTT |
| Add new printer | No | Requires `config login` against `make-app.*`; workaround: import `login.json` from slicer |
| Block `make-app-eu.ankermake.com` | Yes — safe | Printer polls it every 10s, fails silently; no LAN impact (verified 2026-04-28) |
| Block `p2p-mk-*.eufylife.com` | Yes — safe | WAN rendezvous only; printer fails over between nodes but LAN operation unaffected (verified 2026-04-28) |

---

## 3. Scenario B — Anker Servers Permanently Down, No `login.json`

**Assumption:** Cloud servers are gone forever. No prior login, no cached `default.json`, no
`login.json` extractable from the slicer. Printer is already on WiFi (previously set up).

### 3.1 What still works without any cloud secrets

Because PPPP LAN requires only the DUID (not the DSK), and the DUID is self-reported by the
printer in its `PktPunchPkt` broadcast reply, a useful subset of functionality survives:

| Feature | Status | Notes |
|---|---|---|
| Discover printer on LAN | **Yes** | DUID returned in UDP reply (`cli/pppp.py:126-134`) |
| Establish PPPP session | **Yes** | DUID-only handshake |
| Upload GCode file | **Yes** | `pppp_send_file` (`cli/pppp.py:273`) |
| Start print | **Yes** | `FileTransfer.END` |
| Stop print | Hardware only | Touchscreen on printer; software stop requires MQTT |

This amounts to **fire-and-forget printing** (~60% of day-to-day value).

### 3.2 What is permanently broken without cloud secrets

| Feature | Blocker |
|---|---|
| Pause / resume / stop via software | No PPPP control command exists; MQTT-only |
| All telemetry (temps, progress, state) | MQTT-only, no PPPP telemetry channel |
| Camera stream | `p2p_key` required for `START_LIVE`; key comes from cloud |
| Interactive GCode | MQTT-only |
| MQTT payload decryption | `secret_key` (AES-256) is not derivable from DUID/SN/MAC — no KDF exists in the codebase (`libflagship/megajank.py`) |
| First-time printer WiFi setup | BLE onboarding via official app — zero BLE code in this repo |

The `secret_key` is the hardest constraint: it is a randomly assigned server-issued secret,
fetched verbatim from `equipment/get_dsk_keys`. There is no local derivation path.

### 3.3 Recommended mitigation before a potential shutdown

If a shutdown is announced or anticipated:

1. **Extract `login.json` from the slicer app now** (macOS: `~/Library/Application Support/AnkerMake/...`,
   Windows: `%LOCALAPPDATA%\eufyMake Studio Profile\EBWebView\...\leveldb\*.ldb`, via
   `web/platform.py:find_login_file()`).
2. **Run `./ankerctl.py config import`** to hydrate `~/.config/ankerctl/default.json` with all
   device credentials (`secret_key`, `p2p_duid`, `p2p_key`, printer SN, etc.).
3. **Back up `default.json`** in version control or secure storage — it is the sole artifact
   that unlocks full functionality after cloud shutdown.
4. **Fix the printer's IP address** in your router (DHCP reservation) so LAN connectivity is
   stable without re-discovery.

With steps 1–4 complete, you are in Scenario A, and the only remaining unknown is the firmware
TLS behavior.

---

## 4. Open Tasks for 100% Offline Operation

All items below assume DNS rewrites and a seeded `default.json` are in place (Scenario A baseline).

### T1 — Characterise printer firmware TLS behaviour
**Priority: Critical — gates everything else.**
**Owner: hardware / reverse-engineering**

Deploy a Mosquitto instance with a self-signed certificate under `*.ankermake.com` (any CA),
redirect `make-mqtt[-eu].ankermake.com` to it via DNS, reboot the printer, and observe:

- Does the printer establish a TCP connection to port 8789?
- Does the TLS handshake complete?
- Does the printer publish anything to the broker (`mosquitto_sub -t '#' -v`)?

**Result (tested 2026-04-28, firmware V8111, SN AK7ZRM2D20500427):**

**Outcome A — No pinning.** The printer accepted a self-signed certificate under a local CA
with no TLS alert. Full MQTT session established; printer published telemetry immediately.

```
New client connected from 192.168.1.102:58268 as
  device_linux_V8111_direct_..._AK7ZRM2D20500427
  (p4, c1, k40, u'eufy_fdm_AK7ZRM2D20500427')
Received PUBLISH ... '/phone/maker/AK7ZRM2D20500427/notice' (289 bytes)
```

ankerctl restarted with `-k` against local Mosquitto → web UI shows live temperatures. ✓

**Additional findings from DNS log (AdGuard):**
- `make-mqtt-eu.ankermake.com` — queried only at boot (port 8789 TLS, MQTT 3.1.1, keepalive 40s)
- `make-app-eu.ankermake.com` — polled by printer every ~10 seconds at runtime (purpose unknown,
  separate from MQTT; warrants investigation for T2)
- `p2p-mk-lon.eufylife.com` — queried every ~60 seconds (PPPP P2P rendezvous server, London;
  not previously documented — relevant for T2 full-offline scope)
- `time.nist.gov` — NTP at boot only

**Follow-up isolation tests (2026-04-28):**

`make-app-eu.ankermake.com` redirected to 127.0.0.1 (connection refused):
- **No effect** on MQTT telemetry, GCode upload, or print control.
- Printer polls it every ~10s, receives connection refused, and continues silently.
- Safe to block or stub for full offline operation.

`p2p-mk-lon.eufylife.com` blocked:
- Printer **fails over to `p2p-mk-par.eufylife.com`** (Paris) — geographic failover confirmed.
- Additional nodes likely exist (Frankfurt, Amsterdam, etc.); use wildcard `p2p-mk-*.eufylife.com`
  or full `*.eufylife.com` block to prevent failover attempts.
- With both lon and par blocked: **temperatures and GCode upload still fully functional.**
- Conclusion: `p2p-mk-*` is exclusively for WAN/NAT-traversal (remote access outside LAN).
  For local-only operation it is completely irrelevant and safe to block permanently.

---

### T2 — Stand up a production-grade local MQTT broker
**Priority: High (after T1 is positive)**
**Owner: infrastructure / ankerctl-side**

Deploy Mosquitto (or equivalent) with:
- TLS on port 8789
- A certificate trusted by both ankerctl and the printer (outcome of T1 determines the cert strategy)
- ACL accepting `eufy_{user_id}` / email or `allow_anonymous true`
- Retained message support (Anker EMQX uses retained messages for last-state delivery)
- Topic ACL mirroring Anker's structure (`/device/maker/#`, `/phone/maker/#`)

The broker just forwards opaque AES-CBC ciphertext — no knowledge of the AES key is required.

ankerctl side: run with `-k` flag or use T4 to configure a custom CA cert.

Verification: `./ankerctl.py -k mqtt monitor` receives printer telemetry; web UI shows live
temperatures and progress.

---

### T3 — Firmware CA trust store replacement (if T1 shows hard pinning)
**Priority: High (conditional on T1 outcome)**
**Owner: hardware / firmware reverse-engineering**

If the printer pins the Anker CA certificate, a local broker with any self-signed cert will
be rejected. Options:

- Extract the firmware via UART/JTAG/eMMC and locate the CA bundle.
- Replace with a custom CA, sign a new broker cert under it, flash back.
- Alternatively: investigate whether a firmware update mechanism can be used to push a patched CA store.

This is the most invasive path and the only one that cannot be solved in software alone.

---

### T4 — Add `mqtt.ca_cert` config option to ankerctl
**Priority: Medium — quality-of-life**
**Owner: ankerctl codebase**
**Files:** `cli/mqtt.py:26-44`, `web/service/mqtt.py:190-210`, `cli/model.py`

Replace the binary `--insecure/-k` flag with a proper custom CA certificate option so a
local root CA can be pinned without disabling all TLS verification. This avoids a "disable all
security" footgun in production setups.

Change required: extend `libflagship/mqttapi.py:74-78` to accept a `ca_certs` path parameter
separate from the verify flag. Expose via `--mqtt-ca-cert` CLI option and a config file field.

Verification: ankerctl connects to local Mosquitto with a self-signed cert without `-k`.

---

### T5 — Implement PPPP-based print control (pause / stop / resume)
**Priority: Medium — required for Scenario B**
**Owner: ankerctl codebase + protocol reverse-engineering**

Currently, pause/resume/stop go exclusively through MQTT (`ZZ_MQTT_CMD_PRINT_CONTROL` 0x03f0,
`cli/mqtt.py`, `web/__init__.py`). The `P2PCmdType` enum (`libflagship/pppp.py:98-200`) has no
equivalent control command.

Two approaches:
1. **Probe the printer for undocumented PPPP control commands.** Use `examples/probe_pppp_cmds.py`
   as a template to systematically probe `P2PCmdType` values around the file-transfer range and
   observe responses.
2. **GCode-level workaround:** For pause, inject a `M0` or `M25` at the end of the uploaded file.
   This only works for pre-planned pauses, not interactive control during a running print.

Verification: print pauses/resumes/stops via the web UI while the internet is disconnected.

---

### T6 — Implement PPPP-based telemetry channel (temperatures, progress, state)
**Priority: Low — research-heavy**
**Owner: protocol reverse-engineering**

All live telemetry currently comes from MQTT messages (`ct=1000/1001/1003/1004/1052`). If the
printer firmware exposes any local status via PPPP (e.g. a periodic status sub-command), ankerctl
could be extended to consume it without any MQTT dependency.

Approach: capture PPPP traffic between the official slicer app and the printer on a LAN with
no internet, looking for periodic or response-based status packets in unknown `P2PSubCmdType`
values.

This is the only path to telemetry in a true Scenario B (no cloud, no `secret_key`).

Verification: web UI shows live temperatures and progress without any cloud MQTT connection.

---

### T7 — Implement BLE / AP-mode printer onboarding
**Priority: Low — enables fresh-printer setup without official app**
**Owner: protocol reverse-engineering + new ankerctl module**

Currently the printer's WiFi credentials must be provisioned through the official AnkerMake/EufyMake
mobile app via Bluetooth (BLE GATT). There is no BLE code anywhere in this repository.

This is only relevant for first-time setup of a printer that has never been configured. For
printers already on WiFi, this task is irrelevant.

Approach: capture BLE traffic between the mobile app and a factory-reset printer using a phone
with Bluetooth HCI logging enabled, identify the provisioning GATT characteristic and payload
format, implement a Python/CLI equivalent.

Verification: a factory-reset printer is successfully brought online via `ankerctl` without
the official app.

---

### T8 — Config seeding without active cloud (`secret_key` bootstrap)
**Priority: Low — Scenario B hardening**
**Owner: hardware / reverse-engineering**

In Scenario B, the `secret_key` (MQTT AES key) is irretrievable if no prior login was captured.
It is not derivable from any local printer identifier; it is a server-issued random value.

Potential extraction paths (all require hardware access):
- UART/JTAG access to the printer's SoC, reading key from flash or memory at runtime.
- Debugging the official slicer app's memory space while it has an active MQTT session.

This task is a last-resort option if `default.json` was never saved before cloud shutdown.

---

## 5. Verification Sequence (Full Offline Setup)

To validate Scenario A once a local broker is running:

```bash
# 1. Verify DNS rewrite is active
dig make-mqtt.ankermake.com          # should return your local broker IP

# 2. Verify ankerctl connects to local broker
./ankerctl.py -k mqtt monitor        # should receive printer messages on local broker

# 3. Verify printer connects to local broker
mosquitto_sub -v -t '#'              # reboot printer; watch for /phone/maker/{SN}/notice

# 4. Verify full telemetry round-trip
# Change printer bed temp on printer touchscreen -> observe ct=1004 in mqtt monitor output

# 5. Verify print control round-trip
# Pause a running print via web UI -> printer pauses -> ct=1000 value=2 received back

# 6. Verify PPPP still works (unaffected by DNS rewrite)
./ankerctl.py pppp lan-search        # should find printer
./ankerctl.py pppp print-file test.gcode   # should upload and start

# 7. Verify web UI
# Open http://localhost:4470 -> temperatures live, progress updates, camera plays
```

---

## 6. Key Source Files

| File | Relevance |
|---|---|
| `cli/mqtt.py:14-44` | MQTT broker hostnames, TLS setup, `--insecure` flag |
| `libflagship/mqttapi.py:23-95` | MQTT client init, topic subscriptions, TLS knobs |
| `libflagship/megajank.py:11-30` | AES-256-CBC implementation, hardcoded IV |
| `cli/model.py:158-212` | Config schema: Printer, Account, MQTT credential derivation |
| `cli/config.py:152-191` | Login flow, device enumeration, `default.json` population |
| `libflagship/httpapi.py:60-63,113-160` | Cloud HTTP endpoints (login, device list, DSK keys) |
| `cli/pppp.py:41-310` | PPPP LAN connection, file transfer, discovery |
| `libflagship/ppppapi.py:22-457` | PPPP protocol: handshake, packet types, session state |
| `web/service/filetransfer.py:38-166` | Web UI upload pipeline |
| `web/service/video.py:170-187` | Camera stream, `p2p_key` usage |
| `web/service/mqtt.py:190` | MQTT runtime connection in web service |
| `ssl/ankermake-mqtt.crt` | Bundled server public certificate (not usable as signing CA) |
| `libflagship/pppp.py:98-200` | `P2PCmdType` enum — no print-control commands present |
| `documentation/developer-docs/mqtt-overview.md:41-82` | Architecture diagram confirming printer + app on same broker |

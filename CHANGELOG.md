# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This is a fork. Releases `1.0.1` and earlier are the history of the upstream
[`Ankermgmt`](https://github.com/Ankermgmt/ankermake-m5-protocol) project and are preserved here
unchanged. See [Lineage and attribution](README.md#lineage-and-attribution) for the fork chain.

## [Unreleased]

### Fork maintenance

Repository housekeeping for the move to
[`doublegate/ankermake-m5-protocol`](https://github.com/doublegate/ankermake-m5-protocol).
No functional change to `ankerctl` or `libflagship`.

 - Document the fork lineage, contributor attribution, and GPLv3 continuation in `README.md`.
 - Retarget the issue-tracker link in `README.md` to this repository.
 - Fix the CI branch triggers in `.github/workflows/build-and-publish.yml`: the build and release
   job triggered on `master`, which is the *original* upstream's default branch. This fork (and its
   direct upstream) use `main`, so no push to the default branch ever built an image or cut a
   release. Also applies to the `latest` Docker tag conditions.
 - Point `docker-compose.yaml` at this fork's own image,
   `ghcr.io/doublegate/ankermake-m5-protocol:latest`, instead of `anselor/ankerctl:exile-latest`.
 - Retarget the six `raw.githubusercontent.com` bootstrap URLs in
   `documentation/install-from-docker.md` to this repository's `main` branch.
 - Expand `.gitignore` to cover Python virtualenvs, PyInstaller build output, and — importantly —
   `login.json`, the AnkerMake credential file users are instructed to copy into the working
   directory during `config import`.

### Inherited from upstream, not previously changelogged

Work merged upstream between the `1.0.1` release and this fork point, reconstructed from the commit
history. Credit belongs to the authors named; see `git log` for the authoritative record.

#### Added

 - Initial support for the AnkerMake M5C. (Thomas Reitmayr)
 - Log in via the web interface, and fetch configuration by logging in rather than importing
   `login.json`. (Thomas Reitmayr)
 - Update printer IP addresses from both the CLI and the web interface. (Thomas Reitmayr)
 - Set nozzle and heatbed target temperatures from the web interface. (Thomas Reitmayr, with
   message-handling corrections by Chase Peeler)
 - `wss://` support for the websocket endpoints. (snoj)
 - Read startup configuration from `.env` or `.flaskenv`. (Eric Lin)
 - Optional configuration in the docker compose file, and PyInstaller packaging for Windows
   users. (Eric Lin)

#### Changed

 - Split the single PPPP status badge into distinct PPPP and VIDEO badges. (Thomas Reitmayr)
 - Optimize chunk splitting in gcode file transfers. (Thomas Reitmayr)
 - Raise the `_attempt_run` timeout from 1 second to 10 seconds. (Leif Lang)
 - Redact the country code in printed configuration, for privacy. (Thomas Reitmayr)
 - On `config login`, try to rescue already-configured printers. (Thomas Reitmayr)

#### Fixed

 - Bind the socket on broadcasts when running on Windows. (Thomas Reitmayr)
 - Show proper error messages when a printer IP address is unreachable. (Thomas Reitmayr)
 - Fix padding in `mqttapi::make_mqtt_pkt`. (Michael Toner)

## [1.0.1] - 2024-01-15

 - Fixes MQTT connection errors post AnkerMake Firmware Upgrades

## [1.0.0] - 2023-05-24

 - Version 1.0.0!
 - Add video streaming support to web ui
 - Add support for uploading `login.json` through web ui
 - Add print monitoring through web ui
 - Add new mqtt types to libflagship
 - Add status icons for mqtt, pppp and ctrl websocket
 - Add support for restarting web services through web ui
 - Add support for turning on/off camera light from web ui
 - Add support for controlling video mode (sd/hd) from web ui
 - Add `--pppp-dump` option for making a debug packet capture
 - Stabilized video streaming, by fixing some rare corner cases.
 - Make video stream automatically reconnect on connection loss
 - Make video stream automatically suspend when no clients are connected

## [0.9.0] - 2023-04-17

 - First version with github actions for building docker image. (thanks to @cisien)
 - Add python version checking code, to prevent confusing errors if python version is too old.

## [0.8.0] - 2023-04-06

 - First version with built-in webserver! (thanks to @lazemss for the idea and proof-of-concept)
 - Webserver implements a few OctoPrint endpoints, allowing printing directly from PrusaSlicer.
 - Added static web contents, including step-by-step guide for setting up PrusaSlicer.

## [0.7.0] - 2023-04-04

 - First version with camera streaming support!
 - Fixed many bugs in the file upload code, including ability to send files larger than 512K.
 - Fixed file transfers on Windows platforms.

## [0.6.0] - 2023-04-03

 - First version that can send print jobs to the printer over pppp!
 - Completely reworked pppp api implementation.
 - Added support for upgrading config files automatically, when possible.
 - Major code refactoring and improvements.

## [0.5.0] - 2023-03-26

 - Officially licensed as GPLv3.
 - Improved documentation.
 - Much improved documentation (thanks to @austinrdennis).
 - Added `mqtt gcode` command, making it possible to send custom gcode to the printer!
 - Added `mqtt rename-printer` command.
 - Added `pppp lan-search` command.
 - Added `http calc-check-code` command.
 - Added `http calc-sec-code` command.

## [0.4.0] - 2023-03-22

 - First version with the command line tool: `ankerctl.py`.
 - Added `mqtt monitor` command.
 - Added `config import` command.
 - Added `config show` command.
 - Many fixes and improvements from @spuder.

## [0.3.0] - 2023-03-12

 - Examples moved to `examples/`.
 - Added example program that imports `login.json` from Ankermake Slicer.

## [0.3.0] - 2023-03-09

 - First version with a demo program, showing how to parse pppp packets.

## [0.1.0] - 2023-03-07

 - Early code for libflagship, and first version with a README.

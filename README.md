# Windows Spyware Removal Tool

A lightweight tool that disables Windows 10/11 telemetry, tracking, and other "phone home" features that come enabled by default. No external dependencies, no bloat — just a single `.exe` that gets the job done.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078d4)
![License](https://img.shields.io/badge/license-MIT-green)

## What it does

Windows ships with a ton of stuff that sends data back to Microsoft — telemetry services, diagnostic collectors, advertising IDs, Cortana, Copilot, you name it. This tool lets you disable all of it from one place.

**49 tweaks across 13 categories:**

| Category | What gets disabled |
|---|---|
| Telemetry & Diagnostics | DiagTrack, error reporting, CEIP, diagnostic data |
| Advertising & Tracking | Ad ID, tailored experiences, suggested content, silent app installs |
| Cortana & Search | Cortana, Bing web search, search highlights |
| Activity & History | Activity history, timeline, clipboard sync, app launch tracking |
| Location & Sensors | Location services, Find My Device |
| Input & Personalization | Online speech recognition, inking/typing data collection |
| Camera, Mic & Permissions | App access to camera, mic, contacts, calendar, etc. |
| Sync & Cloud | Settings sync, OneDrive |
| Wi-Fi & Networking | Wi-Fi Sense, Hotspot 2.0 auto-connect |
| Edge & Browser | Edge telemetry, first-run data collection |
| Windows Update | P2P delivery optimization |
| Scheduled Tasks | 10+ telemetry-related scheduled tasks |
| Copilot & AI | Windows Copilot, Recall/Snapshots |
| Miscellaneous | Remote assistance, KMS validation, lock screen spotlight, widgets |

## How to use

1. Download `WindowsPrivacyTool.exe` from releases (or build it yourself)
2. Right-click → **Run as administrator**
3. The tool scans your system and shows which tweaks are already applied
4. Check the ones you want (unapplied ones are pre-selected)
5. Hit **Apply Selected** and you're done

Some tweaks need a reboot to take effect.

## Project structure

```
gui.py          main app - tkinter GUI
tweaks.py       all 49 privacy tweaks + registry helpers
```

## How tweaks work

Each tweak modifies registry keys, disables Windows services, or kills scheduled tasks. The tool uses `winreg` for registry access and `sc`/`schtasks` for services and tasks. Everything runs with a 30-second timeout so a stuck service won't hang the app.

The scan runs in a background thread so the UI stays responsive.

## Requirements

- Windows 10 or 11
- Administrator privileges (the app will ask for elevation on startup)
- That's it — no Python needed if you use the compiled `.exe`

## Disclaimer

This tool modifies Windows registry keys and disables system services. While all changes target telemetry and tracking features, use it at your own risk. Some features you might actually use (like Find My Device or clipboard sync) will stop working if you disable them.

## Author

Made by **alcachofo**

## License

This project is licensed under the [MIT License](LICENSE).

```
MIT License

Copyright (c) 2026 alcachofo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

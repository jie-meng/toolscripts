# iOS Tools Guide for Android Developers

A practical reference for understanding iOS development tooling. Covers simulators, physical devices, CLI tools, and the `toolscripts` iOS commands.

---

## Core Concept: Simulator vs Physical Device

iOS has **two separate toolchains** for simulators and physical devices:

| | iOS Simulator | iOS Physical Device |
|---|---|---|
| **Tool** | `xcrun simctl` | `xcrun devicectl` (Xcode 15+) |
| **Platform** | macOS only | macOS + USB connection |
| **Limitations** | Runs x86/ARM Mac code, not real iOS hardware | Full iOS, but restricted by Apple's sandbox |

> `xcrun simctl` commands **cannot** control physical devices, and vice versa.

---

## Feature Availability by Device Type

| Feature | Simulator (`xcrun simctl`) | Physical Device | Notes |
|---|---|---|---|
| List devices | `xcrun simctl list devices` | `xcrun devicectl list devices` | |
| Boot / Shutdown | `xcrun simctl boot/shutdown` | N/A | Physical devices are always "on" |
| Stream logs | `xcrun simctl spawn ... log stream` | `idevicesyslog -u <udid>` | Different tools entirely |
| Screenshot | `xcrun simctl io booted screenshot` | `idevicescreenshot -u <udid>` | Requires libimobiledevice for physical |
| Record video | `xcrun simctl io booted recordVideo` | **No CLI equivalent** | Use Xcode Instruments or QuickTime Player |
| Open deeplink | `xcrun simctl openurl booted <url>` | `xcrun devicectl device process launch --device <udid> --url <url>` | Xcode 15+ for physical |
| Install app | `xcrun simctl install booted <app>` | `xcrun devicectl device install app --device <udid> <app>` | |
| Launch app | `xcrun simctl launch booted <bundle-id>` | `xcrun devicectl device process launch --device <udid> <bundle-id>` | |
| Shell access | `xcrun simctl spawn booted <cmd>` | **No shell access** | |
| Push file | **No equivalent** | **No equivalent** | Use iTunes File Sharing or AirDrop |
| Pull file | **No equivalent** | **No equivalent** | Use iTunes File Sharing or AirDrop |

---

## Core iOS CLI Tools

### `xcrun simctl` — Simulator Control (Simulator Only)

```bash
# List all simulators
xcrun simctl list devices

# List simulators as JSON
xcrun simctl list devices --json

# Boot a simulator
xcrun simctl boot <simulator-uuid>

# Shutdown a simulator
xcrun simctl shutdown <simulator-uuid>

# Shutdown all simulators
xcrun simctl shutdown all

# Stream logs (debug level, compact format)
xcrun simctl spawn booted log stream --level debug --style compact

# Stream logs with predicate filter
xcrun simctl spawn booted log stream --predicate 'process == "MyApp"'

# Take a screenshot
xcrun simctl io booted screenshot screenshot.png

# Record video (Ctrl-C to stop)
xcrun simctl io booted recordVideo output.mp4

# Open a deeplink
xcrun simctl openurl booted "myapp://settings"

# Install an app
xcrun simctl install booted <path-to-app.app>

# Launch an app by bundle ID
xcrun simctl launch booted <bundle-id>

# List installed apps
xcrun simctl list apps booted

# Run a shell command in simulator
xcrun simctl spawn booted ls /var/log
```

### `xcrun devicectl` — Physical Device Control (Xcode 15+)

```bash
# List connected physical devices
xcrun devicectl list devices --json-output -

# Install an app
xcrun devicectl device install app --device <udid> <path-to-app>

# Launch an app
xcrun devicectl device process launch --device <udid> <bundle-id>

# Open a deeplink / universal link
xcrun devicectl device process launch --device <udid> --url "myapp://settings"

# List installed apps
xcrun devicectl device info apps --device <udid>

# Take a screenshot (Xcode 15+)
xcrun devicectl device screenshot --device <udid>
```

### `libimobiledevice` — Physical Device Utilities (Third-party)

Open-source tools for communicating with physical iOS devices. Install via Homebrew:

```bash
brew install libimobiledevice
```

| Command | Purpose |
|---|---|
| `idevicesyslog -u <udid>` | Stream syslog |
| `idevicescreenshot -u <udid>` | Capture screenshot |
| `ideviceinfo -u <udid>` | Device info |
| `ideviceinstaller -u <udid>` | List/manage apps |
| `idevice_id -l` | List device UDIDs |
| `idevicepair pair` | Pair device |
| `idevicediagnostics` | Run diagnostics |

> **Note:** `libimobiledevice` does not provide a screen recording tool. For recording a physical device's screen, use Xcode's Instruments or QuickTime Player (File → New Movie Recording → select the iOS device).

### `open` — macOS App Launcher

```bash
open -a Simulator        # Open Simulator.app
open -a Xcode            # Open Xcode
open -a iTerm            # Open iTerm
open -a QuickTime Player # For recording physical device screen
```

---

## toolscripts iOS Commands

### `ios-simulator`

Interactive curses-based simulator picker. **Simulator only.**

```bash
ios-simulator
```

**Features:**
- Displays boot status (`*` = booted) and last boot time
- Auto-boots and opens Simulator.app for the selected device
- "Shutdown all devices" option at the bottom
- Sorted by: booted first → most recently used → iOS version → device model

---

### `ios-log`

Full-featured curses-based log viewer. **Works with both simulators and physical devices.**

```bash
ios-log            # Interactive device selection + log viewer
ios-log -m 10      # Limit buffer to 100k entries (default: 50k)
```

**How it works under the hood:**
- Simulator: spawns `xcrun simctl spawn <uuid> log stream --level debug --style compact`
- Physical device: spawns `idevicesyslog -u <udid>` (requires `brew install libimobiledevice`)

**Features:**
- Real-time log streaming
- Log level filtering (Debug / Info / Default / Error / Fault)
- Text filter (`f` key) — filter by process name or message content
- Search with highlighting (`/` key, vim-style `n`/`N` for next/prev)
- Freeze/unfreeze stream (`e` key) for inspection
- Visual select mode (`v` key) for multi-line copy
- Copy to clipboard (`y` key)

**Keybindings:**

| Key | Action |
|---|---|
| `f` | Enter filter mode |
| `/` | Enter search mode |
| `n` / `N` | Next / previous search match |
| `-` / `=` | Cycle log level (less/more verbose) |
| `e` | Freeze / unfreeze log stream |
| `v` | Enter visual select mode (when frozen) |
| `k` / `j` | Scroll up / down |
| `u` / `d` | Half page up / down |
| `g` / `G` | Jump to top / bottom |
| `y` | Copy selected lines (visual) or all visible (normal) |
| `c` | Clear all collected logs |
| `q` | Quit |

---

### `ios-log-tail`

Simple log tailing with grep-style filtering. **Simulator only.**

```bash
ios-log-tail MyApp          # Tail logs matching "MyApp"
ios-log-tail "ViewController"
```

**Under the hood:** `xcrun simctl spawn booted log stream` piped to `grep`.

---

### `ios-record`

Record video from the booted iOS simulator. **Simulator only.**

```bash
ios-record             # Start recording (interactive stop)
ios-record --no-compress  # Skip compression prompt
```

**Under the hood:** `xcrun simctl io booted recordVideo --force <file>`

**Features:**
- Auto-detects booted simulator
- Outputs timestamped `.mp4` files (e.g., `ios-video-20260616_120000.mp4`)
- Optional video compression after recording

> **For physical device recording:** Use QuickTime Player → File → New Movie Recording → select your iOS device from the camera dropdown. Or use Xcode's Instruments → Recording.

---

### `ios-deeplink`

Launch a deeplink URL. **Works with both simulators and physical devices.**

```bash
ios-deeplink "myapp://settings"
ios-deeplink "https://example.com/page"
```

**Under the hood:**
- Simulator: `xcrun simctl openurl booted <url>`
- Physical device: prompts user to select device, then `xcrun devicectl device process launch --device <udid> --url <url>`

---

### `xcode-terminal`

Open the current Xcode project directory in iTerm. macOS/Xcode utility.

```bash
xcode-terminal
```

---

## iOS Logging System (Unified Logging)

| Aspect | iOS (Unified Logging) |
|---|---|
| API | `os_log` / `Logger` |
| Levels | Debug, Info, Default, Error, Fault |
| Storage | In-memory ring buffer (lost on reboot) |
| Query (simulator) | `xcrun simctl spawn ... log stream` |
| Query (physical) | `idevicesyslog` |
| Persistence | Off by default; enable in Settings → Privacy → Analytics |
| Filtering | `--predicate` (NSPredicate syntax) |
| Tag system | No explicit tags; filter by `process` or message |

**Key things to know:**
1. iOS "Default" level is the baseline — Debug logs are hidden unless you explicitly set `--level debug`.
2. iOS logs live in memory only — they disappear on reboot (unless Analytics logging is enabled in Settings).
3. iOS has no interactive shell. You can spawn individual commands via `xcrun simctl spawn`, but there's no persistent shell session.

---

## What iOS Cannot Do

| Capability | Status | Workaround |
|---|---|---|
| Interactive shell | ❌ Not available | `xcrun simctl spawn booted <cmd>` for single commands |
| Push/pull files | ❌ Not available | iTunes File Sharing, AirDrop, or `xcrun simctl addmedia` (simulator) |
| Screen record (physical) | ❌ No CLI | QuickTime Player or Xcode Instruments |
| Change system settings via CLI | ❌ Not available | Use `xcrun simctl spawn` for some prefs, or Settings app |
| Root access | ❌ Not available | Jailbreak (not recommended) |
| Uninstall system apps | ❌ Not available | N/A |
| Set up automation | Limited | `xcrun simctl spawn` for simulators; Xcode UI Testing for physical |

---

## Requirements

| Command | macOS | Xcode | Simulator | libimobiledevice |
|---|---|---|---|---|
| `ios-simulator` | ✅ | ✅ | ✅ | — |
| `ios-log` (simulator) | ✅ | ✅ | ✅ | — |
| `ios-log` (physical device) | ✅ | ✅ | — | ✅ `brew install libimobiledevice` |
| `ios-log-tail` | ✅ | ✅ | ✅ | — |
| `ios-record` | ✅ | ✅ | ✅ | — |
| `ios-deeplink` (simulator) | ✅ | ✅ | ✅ | — |
| `ios-deeplink` (physical) | ✅ | ✅ (15+) | — | — |
| `xcode-terminal` | ✅ | ✅ | — | — |

```bash
# Install libimobiledevice (for physical device support)
brew install libimobiledevice

# Install toolscripts
pip install -e .
# or
uv tool install -e .
```

---

## Reference Links

- [Apple simctl Documentation](https://developer.apple.com/documentation/xcode/running-your-app-in-simulator-or-on-a-device)
- [xcrun devicectl (Xcode 15+)](https://developer.apple.com/documentation/xcode/running-your-app-in-simulator-or-on-a-device/running-your-app-on-a-physical-ios-device)
- [libimobiledevice Project](https://libimobiledevice.org/)
- [Apple Unified Logging](https://developer.apple.com/documentation/os/logging)

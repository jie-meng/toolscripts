# Graph Report - toolscripts  (2026-08-08)

## Corpus Check
- 162 files · ~82,460 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1298 nodes · 3223 edges · 97 communities (79 shown, 18 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 47 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `204042d7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- adb/devices.py
- record_audio.py
- ui_curses.py
- quick_commit.py
- run
- LogViewer
- toolscripts conventions cheat-sheet
- LogViewer
- add_logging_flags
- axios_audit.py
- graphifycmd.py
- require
- Context for AI Assistants (AGENTS.md)
- ios/log.py
- select_many
- iTerm2 Split Vertical Quarter Script
- manage.py
- ai_links.py
- configure_from_args
- _ensure_handler
- npm_tools.py
- ios/devices.py
- copy_to_clipboard
- iOS Tools Guide for Android Developers
- mongo.py
- _ffmpeg_quality.py
- img_resize.py
- free_models_openrouter.py
- require_platform
- checkspace.py
- free_models_nvidia.py
- text2num.py
- core/log.py
- decode_format_json.py
- ios/record.py
- imgcat.py
- ask
- extract_games.py
- merge_to_main.py
- Coding Principles
- Mermaid Multi-Layer Architecture Diagrams
- platform.py
- split_vertical_quarter.py
- capture
- simulator.py
- Workflow
- playsound.py
- from_date.py
- commands/ai/__init__.py
- android/__init__.py
- calc/__init__.py
- codec/__init__.py
- credential/__init__.py
- games/__init__.py
- git/__init__.py
- commands/__init__.py
- commands/ios/__init__.py
- media/__init__.py
- security/__init__.py
- system/__init__.py
- text/__init__.py
- time/__init__.py
- toolscripts/__init__.py
- hex2rgb.py
- toolscripts
- list_include.py
- ocdo.py
- The Five Optimization Lines (by ROI)
- iterm_setup.py
- Workflow
- pem_to_oneline.py
- dotnet_globaljson.py
- statcounter.py
- CONVENTIONS.md
- Workflow
- web2md.py
- 4. Reuse first (DRY) — the reflex before writing code
- get_logger
- explainer.md
- toolscripts-command-modify
- NamedTuple
- to_date.py
- planner.md
- verifier.md
- debugger.md
- 1. Layout (where everything lives)
- dirdiff.py
- remove_watermark.py
- cbdo.py
- Path

## God Nodes (most connected - your core abstractions)
1. `configure_from_args()` - 210 edges
2. `add_logging_flags()` - 209 edges
3. `get_logger()` - 114 edges
4. `run()` - 101 edges
5. `require()` - 78 edges
6. `capture()` - 46 edges
7. `select_one()` - 43 edges
8. `LogViewer` - 42 edges
9. `CommandNotFoundError` - 42 edges
10. `LogViewer` - 41 edges

## Surprising Connections (you probably didn't know these)
- `DockerCommand` --uses--> `CommandNotFoundError`  [INFERRED]
  src/toolscripts/commands/docker/dockercmd.py → src/toolscripts/core/shell.py
- `_prompt_graphify_policy()` --calls--> `select_one()`  [INFERRED]
  src/toolscripts/commands/ai/graphifycmd.py → src/toolscripts/core/ui_curses.py
- `_handle_open_html()` --calls--> `is_linux()`  [INFERRED]
  src/toolscripts/commands/ai/graphifycmd.py → src/toolscripts/core/platform.py
- `_handle_open_html()` --calls--> `is_macos()`  [INFERRED]
  src/toolscripts/commands/ai/graphifycmd.py → src/toolscripts/core/platform.py
- `_handle_open_html()` --calls--> `is_windows()`  [INFERRED]
  src/toolscripts/commands/ai/graphifycmd.py → src/toolscripts/core/platform.py

## Import Cycles
- None detected.

## Communities (97 total, 18 thin omitted)

### Community 0 - "adb/devices.py"
Cohesion: 0.07
Nodes (34): LogRecord, get_device_model(), list_devices(), ADB device discovery and selection. Used by every ``android-*`` command. Wraps…, Return the serials of all currently connected ADB devices., Return a single connected device serial, prompting the user if needed. Exits…, Return the human-readable model name for an ADB device serial., select_device() (+26 more)

### Community 1 - "record_audio.py"
Cohesion: 0.19
Nodes (22): Event, _build_record_cmd(), _ensure_swift_helper(), _get_swift_helper_path(), _is_virtual_audio(), _list_macos_audio_devices(), _macos_ensure_background_music(), _macos_get_default_output_name() (+14 more)

### Community 2 - "ui_curses.py"
Cohesion: 0.09
Nodes (26): _build_custom_env(), _detect_current(), _get_or_input(), main(), ``ccswitch`` - switch Claude Code's ~/.claude/settings.json between provider…, _select_provider(), _update_settings(), _pick_avd() (+18 more)

### Community 3 - "quick_commit.py"
Cohesion: 0.16
Nodes (16): _classify_staged(), _detect_version_bump(), _dominant_scope(), generate_suggestions(), _get_staged_info(), main(), _parse_branch(), ``git-quick-commit`` - interactive commit wizard with pattern-based message… (+8 more)

### Community 4 - "run"
Cohesion: 0.08
Nodes (62): CompletedProcess, _ensure_curses(), _find_gguf_files(), _format_model_path(), _get_hf_api(), _get_model_dirs(), _handle_clean_cache(), _handle_delete_models() (+54 more)

### Community 5 - "LogViewer"
Cohesion: 0.10
Nodes (13): LogEntry, LogViewer, _parse_logcat_line(), Match, window, Curses-based logcat viewer with level, text filtering, and search., Return all match objects for search_text in entry's raw line., Precompute match counts and prefix sums for search highlighting. (+5 more)

### Community 6 - "toolscripts conventions cheat-sheet"
Cohesion: 0.15
Nodes (13): 10. Style, 11. Bash scripts (`scripts/`), 12. README tables, 13. Editable install reload, 2. Naming, 3. Module skeleton, 5. Core helpers (use these instead of rolling your own), 6. Dependencies (+5 more)

### Community 7 - "LogViewer"
Cohesion: 0.10
Nodes (12): LogEntry, LogViewer, Match, window, Curses-based iOS log viewer with level, text filtering, and search., Return all match objects for search_text in entry's raw line., Move to the next search match, preferring visible matches first., Move to the previous search match, preferring visible matches first. (+4 more)

### Community 8 - "add_logging_flags"
Cohesion: 0.09
Nodes (21): main(), ``android-adbsync`` - remount the device, sync, and restart the framework., main(), ``dec2hex`` - convert decimal numbers to hexadecimal., main(), ``hex2bin`` - convert hexadecimal numbers to binary., main(), ``hex2dec`` - convert hexadecimal numbers to decimal. (+13 more)

### Community 9 - "axios_audit.py"
Cohesion: 0.05
Nodes (69): Any, NamedTuple, decode(), _format_value(), main(), ``url-decode-params`` - decode URL-encoded query parameters with JSON detection., _try_parse_json(), _b64_decode() (+61 more)

### Community 10 - "graphifycmd.py"
Cohesion: 0.08
Nodes (47): Path, Action, _apply_gitignore_policy(), _detect_graphify_gitignore(), _display_items(), _ensure_curses(), _fmt(), _graph_data() (+39 more)

### Community 11 - "require"
Cohesion: 0.12
Nodes (21): main(), ``android-emulator`` - list available AVDs and start the chosen one., main(), ``android-screencast`` - launch scrcpy for the selected device., main(), ``img-scale`` - scale a single image by a factor (0 < scale < 1) via…, main(), ``mp3-to-pcm`` - convert MP3 audio to mono 16kHz s16le PCM. (+13 more)

### Community 12 - "Context for AI Assistants (AGENTS.md)"
Cohesion: 0.07
Nodes (27): 10. Modifying existing code, 11. Helping the user, 12. Bundled skills for command lifecycle, 1. Project context, 2. Repository layout, 3.1 The reuse reflex (do this *before* writing code), 3.2 When you find duplication, 3.3 Hard rules (+19 more)

### Community 13 - "ios/log.py"
Cohesion: 0.17
Nodes (12): _display_width(), main(), ``ios-log`` - interactive curses-based log viewer for iOS devices. Provides a…, Calculate display width of a string, accounting for wide (CJK) characters., LogEntry, parse_log_line(), passes_filter(), iOS log parsing utilities. (+4 more)

### Community 14 - "select_many"
Cohesion: 0.10
Nodes (40): main(), ``agents-cleanup`` - remove installed AI agent definitions. Item-level curses…, _agents_dir(), _build_items(), _cleanup_item(), _data_dir(), _discover_agents(), InstallableItem (+32 more)

### Community 15 - "iTerm2 Split Vertical Quarter Script"
Cohesion: 0.10
Nodes (20): Assign a Keyboard Shortcut, Customization, "Function Call" dropdown is empty or missing scripts, How It Works, iTerm2 Split Vertical Quarter Script, Keyboard shortcut throws errors, Manual Configuration (Required), Permission issues (+12 more)

### Community 16 - "manage.py"
Cohesion: 0.16
Nodes (31): build_parser(), _c(), _capture(), cleanup_orphans(), _cleanup_uv_orphans(), cmd_install(), cmd_status(), cmd_uninstall() (+23 more)

### Community 17 - "ai_links.py"
Cohesion: 0.16
Nodes (27): AITool, _apply_selection(), _detect_current_selection(), _ensure_main_subdir(), _find_agents_root(), _gitignore_entries(), _has_anything_to_link(), _interactive_pick() (+19 more)

### Community 18 - "configure_from_args"
Cohesion: 0.11
Nodes (21): main(), ``oauth-code`` - generate a TOTP code via ``oathtool`` and copy to clipboard.…, main(), ``git-apply-patches`` - extract patches.zip and apply each .patch via git am., main(), ``git-make-patches`` - run git format-patch on the last N commits and zip the…, main(), ``xcode-terminal`` - open the directory of the active Xcode project in iTerm.… (+13 more)

### Community 19 - "_ensure_handler"
Cohesion: 0.08
Nodes (24): Available commands, Cross-platform behavior, Install, License, `manage.py` cheat sheet, Manual install (without `manage.py`), Optional dependency groups, Project layout (+16 more)

### Community 20 - "npm_tools.py"
Cohesion: 0.28
Nodes (10): _curses_loop(), _draw(), _latest_version(), _list_installed(), main(), ``npm-tools`` - manage globally installed npm packages with a curses TUI., _run(), _run_ops_outside_curses() (+2 more)

### Community 21 - "ios/devices.py"
Cohesion: 0.22
Nodes (16): get_booted_simulator(), get_device_name(), IOSDevice, list_devices(), list_physical_devices(), list_simulators(), iOS device discovery and selection. Used by ``ios-*`` commands. Wraps ``xcrun…, Return available iOS devices (simulators and physical). Args: booted_only: If… (+8 more)

### Community 22 - "copy_to_clipboard"
Cohesion: 0.08
Nodes (47): main(), ``convert-oneline`` - join all lines of a file into a single line and copy it., _keyword_pattern(), main(), mask_text(), ``redact-clipboard`` - mask credentials/secrets in clipboard text., Mask sensitive values; returns (masked_text, replacement_count)., _ask_prompt_type() (+39 more)

### Community 23 - "iOS Tools Guide for Android Developers"
Cohesion: 0.10
Nodes (19): Core Concept: Simulator vs Physical Device, Core iOS CLI Tools, Feature Availability by Device Type, `ios-deeplink`, `ios-log`, `ios-log-tail`, iOS Logging System (Unified Logging), `ios-record` (+11 more)

### Community 24 - "mongo.py"
Cohesion: 0.38
Nodes (9): _dump(), _ensure_tools(), _list_archives(), _load_config(), main(), Path, ``mongo-tool`` - dump / restore a mongodb to/from a zip archive. Migrated from…, _restore() (+1 more)

### Community 25 - "_ffmpeg_quality.py"
Cohesion: 0.29
Nodes (9): encode(), prompt_quality(), Path, Helpers for video transcoding with ffmpeg., Run ffmpeg libx264/aac encode. Returns True on success., main(), ``mov-to-mp4`` - convert a MOV file to MP4 with selectable quality., main() (+1 more)

### Community 26 - "img_resize.py"
Cohesion: 0.51
Nodes (9): _find_images(), _identify_dims(), _interactive_select(), main(), _parse_stem_dims(), Path, ``img-resize`` - resize all images in a directory to target dimensions via…, _ref_dims() (+1 more)

### Community 27 - "free_models_openrouter.py"
Cohesion: 0.43
Nodes (6): date, _format_context(), _format_modality(), main(), _parse_cutoff(), ``free-models-openrouter`` - list free models from openrouter.ai in a table.

### Community 28 - "require_platform"
Cohesion: 0.24
Nodes (9): main(), ``android-studio`` - open the current directory in Android Studio (macOS)., _macos_open(), _find_playwright_chrome(), main(), ``kill-pwchrome`` - kill Playwright-launched Chrome/Chromium processes. Only…, Return (pid, args) for every Playwright-launched Chrome/Chromium process., Exit with a friendly warning if the current platform is not supported. Accepts… (+1 more)

### Community 29 - "checkspace.py"
Cohesion: 0.52
Nodes (6): _dir_size(), _entry_size(), _format(), main(), Path, ``checkspace`` - sort top-level entries in a directory by size.

### Community 30 - "free_models_nvidia.py"
Cohesion: 0.60
Nodes (4): _extract(), _fetch(), main(), ``free-models-nvidia`` - scrape build.nvidia.com free endpoint models.

### Community 31 - "text2num.py"
Cohesion: 0.48
Nodes (6): _is_float(), _is_int(), main(), _process_workbook(), Path, ``text2num`` - convert numeric-looking text in an Excel workbook to real…

### Community 32 - "core/log.py"
Cohesion: 0.19
Nodes (11): Handler, main(), ``dec2bin`` - convert decimal numbers to binary (interactive or one-shot)., main(), ``git-delete-local-branches`` - delete all non-current local branches., _run(), _ensure_handler(), Unified colored logger for toolscripts. Quick start:: from toolscripts.core.log… (+3 more)

### Community 33 - "decode_format_json.py"
Cohesion: 0.67
Nodes (3): decode_base64_to_json(), main(), ``decode-and-format-json`` - decode a base64 string and pretty-print the JSON…

### Community 34 - "ios/record.py"
Cohesion: 0.31
Nodes (7): compress_video(), Path, Shared helper for compressing video files via ffmpeg. Used by ``android-…, Compress ``input_file`` with ffmpeg. Returns the output path on success., _get_booted_simulator(), main(), ``ios-record`` - record video from the booted iOS simulator.

### Community 35 - "imgcat.py"
Cohesion: 0.53
Nodes (5): _emit(), main(), _osc_prefix(), _osc_suffix(), ``imgcat`` - display images inline in iTerm2 via the OSC 1337 protocol. Cross-…

### Community 36 - "ask"
Cohesion: 0.06
Nodes (61): main(), ``android-keystore-generate`` - wrap keytool to generate Android keystores., _is_binary(), _is_ignored(), main(), Path, ``android-rename-project`` - rename an Android project's package across files…, _rreplace() (+53 more)

### Community 37 - "extract_games.py"
Cohesion: 0.53
Nodes (5): _clean_filename(), _extract(), main(), Path, ``extract-games`` - extract retro ROMs from zip archives into folders by…

### Community 38 - "merge_to_main.py"
Cohesion: 0.12
Nodes (25): CalledProcessError, _detect_main_branch(), _list_local_branches(), main(), _pick_main_branch(), _print_failure(), ``git-merge-to-main`` - merge current branch into the main branch., Best-effort checkout back to the given branch. (+17 more)

### Community 39 - "Coding Principles"
Cohesion: 0.14
Nodes (13): 10. Code Organization, 11. Git & Version Control, 12. Communication, 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution, 5. Core Principles (+5 more)

### Community 40 - "Mermaid Multi-Layer Architecture Diagrams"
Cohesion: 0.14
Nodes (13): Alternative Layout: flowchart LR, Caveats, Comparison, Core Technique: graph TB + Hidden Layout Edges, How It Works, How It Works, Key Points, linkStyle Edge Index Calculation (+5 more)

### Community 41 - "platform.py"
Cohesion: 0.33
Nodes (7): main(), ``lsdevcu`` - list ``/dev/cu.*`` serial devices (macOS/Linux)., current_platform(), is_linux(), is_windows(), Platform detection and gating. Use ``require_platform("macos")`` at the top of…, Return one of: ``macos``, ``linux``, ``windows``, or the raw ``sys.platform``…

### Community 42 - "split_vertical_quarter.py"
Cohesion: 0.40
Nodes (4): _get_first_session(), main(), Recursively get the first session from a SplitTreeNode or Session., Main function that registers RPC and keeps the script running.

### Community 43 - "capture"
Cohesion: 0.40
Nodes (9): _delete_local(), _delete_remote(), _fetch_and_prune(), _list_local_branches(), _list_remote_branches(), main(), ``git-branch-delete`` - interactively delete local/remote git branches., capture() (+1 more)

### Community 44 - "simulator.py"
Cohesion: 0.43
Nodes (7): _build_display_items(), _device_sort_key(), _format_boot_time(), _ios_sort_key(), _list_devices(), main(), ``ios-simulator`` - list iOS simulators, boot/open the chosen one.

### Community 45 - "Workflow"
Cohesion: 0.18
Nodes (11): Don'ts, Example, Step 1 — Confirm intent, Step 2 — Locate every touch point, Step 3 — Check for orphaned helpers, Step 4 — Delete in the right order, Step 5 — Tests / data resources, Step 6 — Hand off to the user (+3 more)

### Community 46 - "playsound.py"
Cohesion: 0.39
Nodes (8): _play(), play_main(), Path, ``playsound`` / ``stopsound`` - play and stop audio files…, _stop_all(), stop_main(), Return the absolute path of ``name`` on PATH, or ``None``., which()

### Community 47 - "from_date.py"
Cohesion: 0.50
Nodes (4): convert(), main(), ``date2timestamp`` - convert a date string to a millisecond timestamp., Parse ``YYYY-MM-DDTHH:MM:SS.fff`` and return milliseconds since epoch.

### Community 63 - "hex2rgb.py"
Cohesion: 0.67
Nodes (3): hex_to_rgb(), main(), ``hex2rgb`` - convert a hex color code to RGB.

### Community 72 - "list_include.py"
Cohesion: 0.47
Nodes (5): clang_main(), from_here_main(), Path, ``list-include-dirs-from-here`` and ``list-include-dirs-clang``., _walk_includes()

### Community 73 - "ocdo.py"
Cohesion: 0.48
Nodes (6): _fetch_free_models(), _load_config(), models_main(), ``ocdo`` and ``ocdo-models`` - run prompts via opencode + a saved free model., run_main(), _save_config()

### Community 74 - "The Five Optimization Lines (by ROI)"
Cohesion: 0.20
Nodes (9): ① Cache — One-time setup, continuous savings (~45%), ② Select — Get the right code in context, ③ Compress — Prevent context bloat, ④ Isolate — Right model for right task, ⑤ Write — External memory, Coding Agent Cost Optimization, Core Principles, Quick Cost Estimate (+1 more)

### Community 75 - "iterm_setup.py"
Cohesion: 0.48
Nodes (6): _bundled_scripts_dir(), _configure_shortcut(), main(), _plist_buddy(), Path, ``iterm-setup`` - install bundled iTerm2 Python scripts and a keyboard…

### Community 76 - "Workflow"
Cohesion: 0.22
Nodes (9): Step 1 — Clarify, Step 2 — Overlap check (mandatory, do not skip), Step 3 — Pick domain and name, Step 4 — Reuse-first reflex (mandatory, do not skip), Step 5 — Write the module, Step 6 — Register the entry point, Step 7 — Update both READMEs, Step 8 — Hand off to the user (+1 more)

### Community 77 - "pem_to_oneline.py"
Cohesion: 0.67
Nodes (3): extract_key(), main(), ``pem-to-oneline`` - extract a PEM key body and copy it to the clipboard.

### Community 78 - "dotnet_globaljson.py"
Cohesion: 0.67
Nodes (3): main(), _parse_sdk_line(), ``dotnet-globaljson`` - generate a global.json to pin the .NET SDK version.

### Community 79 - "statcounter.py"
Cohesion: 0.60
Nodes (4): main(), Path, ``statcounter`` - draw a pie chart of OS-version coverage from a Statcounter…, _read_data()

### Community 80 - "CONVENTIONS.md"
Cohesion: 0.29
Nodes (3): Don'ts, Example: end-to-end, toolscripts-command-add

### Community 81 - "Workflow"
Cohesion: 0.29
Nodes (7): Step 1 — Locate, Step 2 — Understand the current behavior, Step 3 — Classify the change, Step 4 — Apply the change (reuse-first reflex applies here too), Step 5 — Sync the public surface, Step 6 — Hand off to the user, Workflow

### Community 82 - "web2md.py"
Cohesion: 0.67
Nodes (3): main(), ``web2md`` - fetch a webpage and convert its main content to Markdown., web2md()

### Community 83 - "4. Reuse first (DRY) — the reflex before writing code"
Cohesion: 0.33
Nodes (6): 4. Reuse first (DRY) — the reflex before writing code, Concrete examples already in the repo, Hard rules, The 3-question check (do this *before* writing code), When you find duplication, When you genuinely need something new

### Community 84 - "get_logger"
Cohesion: 0.12
Nodes (14): RuntimeError, basic_auth(), main(), ``basic-auth`` - generate a Base64-encoded HTTP Basic Auth string., main(), ``git-alias-setup`` - set up common git aliases (st, co, ci, br, lg)., main(), Path (+6 more)

### Community 85 - "explainer.md"
Cohesion: 0.33
Nodes (5): ASCII Visualization Examples, How you think, How you work, Output guidance, What you should NOT do

### Community 86 - "toolscripts-command-modify"
Cohesion: 0.40
Nodes (5): Don'ts, Example: bug fix without contract change, Example: rename a command, toolscripts-command-modify, When to use this skill (vs. -add / -remove)

### Community 88 - "to_date.py"
Cohesion: 0.50
Nodes (4): convert(), main(), ``timestamp2date`` - convert a millisecond timestamp to a date string., Convert ``milliseconds`` since epoch to ``YYYY-MM-DDTHH:MM:SS.fff``.

### Community 89 - "planner.md"
Cohesion: 0.40
Nodes (4): How you think, How you work, Output guidance, What you should NOT do

### Community 90 - "verifier.md"
Cohesion: 0.40
Nodes (4): How you think, How you work, Output guidance, What you should NOT do

### Community 91 - "debugger.md"
Cohesion: 0.50
Nodes (3): How you work, Output guidance, What you should NOT do

### Community 92 - "1. Layout (where everything lives)"
Cohesion: 0.67
Nodes (3): 1. Layout (where everything lives), Existing domains under `commands/`, Layering rules

### Community 93 - "dirdiff.py"
Cohesion: 0.60
Nodes (4): _ask_directory(), main(), Path, ``dirdiff`` - launch Vim's ``DirDiff`` on two directories.

### Community 94 - "remove_watermark.py"
Cohesion: 0.60
Nodes (5): _crop(), _identify(), main(), Path, ``remove-watermark`` - crop a fixed-size watermark from one or more images.

### Community 95 - "cbdo.py"
Cohesion: 0.67
Nodes (3): _codebuddy_bin(), main(), ``cbdo`` - run a prompt via CodeBuddy (`cbc`) in print mode with the free hy3…

## Knowledge Gaps
- **164 isolated node(s):** `toolscripts`, `Layering rules`, `Existing domains under `commands/``, `2. Naming`, `3. Module skeleton` (+159 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `configure_from_args()` connect `configure_from_args` to `adb/devices.py`, `record_audio.py`, `ui_curses.py`, `quick_commit.py`, `run`, `add_logging_flags`, `axios_audit.py`, `graphifycmd.py`, `require`, `ios/log.py`, `select_many`, `ai_links.py`, `npm_tools.py`, `copy_to_clipboard`, `mongo.py`, `_ffmpeg_quality.py`, `img_resize.py`, `free_models_openrouter.py`, `require_platform`, `checkspace.py`, `free_models_nvidia.py`, `text2num.py`, `core/log.py`, `decode_format_json.py`, `ios/record.py`, `imgcat.py`, `ask`, `extract_games.py`, `merge_to_main.py`, `platform.py`, `capture`, `simulator.py`, `playsound.py`, `from_date.py`, `hex2rgb.py`, `list_include.py`, `ocdo.py`, `iterm_setup.py`, `pem_to_oneline.py`, `dotnet_globaljson.py`, `statcounter.py`, `web2md.py`, `get_logger`, `to_date.py`, `dirdiff.py`, `remove_watermark.py`, `cbdo.py`?**
  _High betweenness centrality (0.148) - this node is a cross-community bridge._
- **Why does `add_logging_flags()` connect `add_logging_flags` to `adb/devices.py`, `record_audio.py`, `ui_curses.py`, `quick_commit.py`, `run`, `axios_audit.py`, `graphifycmd.py`, `require`, `ios/log.py`, `select_many`, `ai_links.py`, `configure_from_args`, `npm_tools.py`, `copy_to_clipboard`, `mongo.py`, `_ffmpeg_quality.py`, `img_resize.py`, `free_models_openrouter.py`, `require_platform`, `checkspace.py`, `free_models_nvidia.py`, `text2num.py`, `core/log.py`, `decode_format_json.py`, `ios/record.py`, `imgcat.py`, `ask`, `extract_games.py`, `merge_to_main.py`, `platform.py`, `capture`, `simulator.py`, `playsound.py`, `from_date.py`, `hex2rgb.py`, `list_include.py`, `ocdo.py`, `iterm_setup.py`, `pem_to_oneline.py`, `dotnet_globaljson.py`, `statcounter.py`, `web2md.py`, `get_logger`, `to_date.py`, `dirdiff.py`, `remove_watermark.py`, `cbdo.py`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Why does `get_logger()` connect `get_logger` to `adb/devices.py`, `record_audio.py`, `ui_curses.py`, `quick_commit.py`, `run`, `add_logging_flags`, `axios_audit.py`, `require`, `ios/log.py`, `select_many`, `configure_from_args`, `npm_tools.py`, `ios/devices.py`, `copy_to_clipboard`, `mongo.py`, `_ffmpeg_quality.py`, `img_resize.py`, `free_models_openrouter.py`, `require_platform`, `checkspace.py`, `free_models_nvidia.py`, `text2num.py`, `core/log.py`, `decode_format_json.py`, `ios/record.py`, `imgcat.py`, `ask`, `extract_games.py`, `merge_to_main.py`, `platform.py`, `capture`, `simulator.py`, `playsound.py`, `from_date.py`, `hex2rgb.py`, `list_include.py`, `ocdo.py`, `iterm_setup.py`, `pem_to_oneline.py`, `dotnet_globaljson.py`, `statcounter.py`, `web2md.py`, `to_date.py`, `dirdiff.py`, `remove_watermark.py`, `cbdo.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `configure_from_args()` (e.g. with `main()` and `main()`) actually correct?**
  _`configure_from_args()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `add_logging_flags()` (e.g. with `main()` and `main()`) actually correct?**
  _`add_logging_flags()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `toolscripts`, `Layering rules`, `Existing domains under `commands/`` to the rest of the system?**
  _164 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `adb/devices.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06753006475485661 - nodes in this community are weakly interconnected._
# Graph Report - toolscripts  (2026-08-09)

## Corpus Check
- 162 files · ~82,494 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1298 nodes · 3235 edges · 79 communities (62 shown, 17 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 45 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f0feeb8d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- run
- record_audio.py
- llamacmd.py
- ui_curses.py
- select_one
- LogViewer
- toolscripts conventions cheat-sheet
- LogViewer
- configure_from_args
- axios_audit.py
- graphifycmd.py
- require
- Context for AI Assistants (AGENTS.md)
- Path
- ai_links.py
- iTerm2 Split Vertical Quarter Script
- manage.py
- trim_audio.py
- _ensure_handler
- npm_tools.py
- ios/log.py
- copy_to_clipboard
- iOS Tools Guide for Android Developers
- mongo.py
- core/log.py
- img_resize.py
- free_models_openrouter.py
- get_logger
- checkspace.py
- text2num.py
- _ensure_handler
- mermaid.py
- imgcat.py
- ask
- extract_games.py
- capture
- Coding Principles
- Mermaid Multi-Layer Architecture Diagrams
- split_vertical_quarter.py
- simulator.py
- Workflow
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
- toolscripts
- The Five Optimization Lines (by ROI)
- Workflow
- statcounter.py
- CONVENTIONS.md
- Workflow
- 4. Reuse first (DRY) — the reflex before writing code
- sensitive_hook.py
- explainer.md
- toolscripts-command-modify
- planner.md
- verifier.md
- debugger.md
- 1. Layout (where everything lives)
- dirdiff.py
- remove_watermark.py

## God Nodes (most connected - your core abstractions)
1. `configure_from_args()` - 211 edges
2. `add_logging_flags()` - 210 edges
3. `get_logger()` - 116 edges
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
- `_handle_status()` --calls--> `copy_to_clipboard()`  [INFERRED]
  src/toolscripts/commands/ai/graphifycmd.py → src/toolscripts/core/clipboard.py
- `_handle_status()` --calls--> `colored()`  [INFERRED]
  src/toolscripts/commands/ai/graphifycmd.py → src/toolscripts/core/colors.py
- `_handle_status()` --calls--> `yes_no()`  [INFERRED]
  src/toolscripts/commands/ai/graphifycmd.py → src/toolscripts/core/prompts.py

## Import Cycles
- None detected.

## Communities (79 total, 17 thin omitted)

### Community 0 - "run"
Cohesion: 0.08
Nodes (29): CompletedProcess, _codebuddy_bin(), main(), ``cbdo`` - run a prompt via CodeBuddy (`cbc`) in print mode with the free hy3…, main(), ``android-adbsync`` - remount the device, sync, and restart the framework., main(), ``android-deeplink`` - launch a deeplink URL on a connected Android device. (+21 more)

### Community 1 - "record_audio.py"
Cohesion: 0.11
Nodes (36): Event, _handle_open_html(), _play(), play_main(), Path, ``playsound`` / ``stopsound`` - play and stop audio files…, _stop_all(), stop_main() (+28 more)

### Community 2 - "llamacmd.py"
Cohesion: 0.21
Nodes (25): _ensure_curses(), _find_gguf_files(), _format_model_path(), _get_hf_api(), _get_model_dirs(), _handle_clean_cache(), _handle_delete_models(), _handle_download_url() (+17 more)

### Community 3 - "ui_curses.py"
Cohesion: 0.05
Nodes (52): main(), _pick_avd(), ``android-emulator`` - list available AVDs and start the chosen one., Show a curses picker with toggle options. Returns (index, writable, detach) or…, CommandInfo, _discover(), _domain_of(), _filter() (+44 more)

### Community 4 - "select_one"
Cohesion: 0.06
Nodes (59): _build_custom_env(), _detect_current(), _get_or_input(), main(), ``ccswitch`` - switch Claude Code's ~/.claude/settings.json between provider…, _select_provider(), _update_settings(), main() (+51 more)

### Community 5 - "LogViewer"
Cohesion: 0.06
Nodes (35): get_device_model(), list_devices(), ADB device discovery and selection. Used by every ``android-*`` command. Wraps…, Return the serials of all currently connected ADB devices., Return a single connected device serial, prompting the user if needed. Exits…, Return the human-readable model name for an ADB device serial., select_device(), ADB helpers shared by android-* commands. (+27 more)

### Community 6 - "toolscripts conventions cheat-sheet"
Cohesion: 0.15
Nodes (13): 10. Style, 11. Bash scripts (`scripts/`), 12. README tables, 13. Editable install reload, 2. Naming, 3. Module skeleton, 5. Core helpers (use these instead of rolling your own), 6. Dependencies (+5 more)

### Community 7 - "LogViewer"
Cohesion: 0.08
Nodes (20): LogEntry, LogViewer, Match, window, Curses-based iOS log viewer with level, text filtering, and search., Return all match objects for search_text in entry's raw line., Move to the next search match, preferring visible matches first., Move to the previous search match, preferring visible matches first. (+12 more)

### Community 8 - "configure_from_args"
Cohesion: 0.06
Nodes (50): main(), ``dec2bin`` - convert decimal numbers to binary (interactive or one-shot)., main(), ``dec2hex`` - convert decimal numbers to hexadecimal., main(), ``hex2bin`` - convert hexadecimal numbers to binary., main(), ``hex2dec`` - convert hexadecimal numbers to decimal. (+42 more)

### Community 9 - "axios_audit.py"
Cohesion: 0.09
Nodes (38): Any, decode(), _format_value(), main(), ``url-decode-params`` - decode URL-encoded query parameters with JSON detection., _try_parse_json(), _b64_decode(), _decode_json() (+30 more)

### Community 10 - "graphifycmd.py"
Cohesion: 0.08
Nodes (48): Path, Action, _apply_gitignore_policy(), _detect_graphify_gitignore(), _display_items(), _ensure_curses(), _fmt(), _graph_data() (+40 more)

### Community 11 - "require"
Cohesion: 0.08
Nodes (31): _fetch_free_models(), _load_config(), models_main(), ``ocdo`` and ``ocdo-models`` - run prompts via opencode + a saved free model., run_main(), _save_config(), main(), ``android-keystore-generate`` - wrap keytool to generate Android keystores. (+23 more)

### Community 12 - "Context for AI Assistants (AGENTS.md)"
Cohesion: 0.07
Nodes (27): 10. Modifying existing code, 11. Helping the user, 12. Bundled skills for command lifecycle, 1. Project context, 2. Repository layout, 3.1 The reuse reflex (do this *before* writing code), 3.2 When you find duplication, 3.3 Hard rules (+19 more)

### Community 14 - "ai_links.py"
Cohesion: 0.09
Nodes (50): main(), ``agents-cleanup`` - remove installed AI agent definitions. Item-level curses…, _agents_dir(), _build_items(), _cleanup_item(), _data_dir(), _discover_agents(), InstallableItem (+42 more)

### Community 15 - "iTerm2 Split Vertical Quarter Script"
Cohesion: 0.10
Nodes (20): Assign a Keyboard Shortcut, Customization, "Function Call" dropdown is empty or missing scripts, How It Works, iTerm2 Split Vertical Quarter Script, Keyboard shortcut throws errors, Manual Configuration (Required), Permission issues (+12 more)

### Community 16 - "manage.py"
Cohesion: 0.16
Nodes (31): build_parser(), _c(), _capture(), cleanup_orphans(), _cleanup_uv_orphans(), cmd_install(), cmd_status(), cmd_uninstall() (+23 more)

### Community 17 - "trim_audio.py"
Cohesion: 0.23
Nodes (13): _detect_silence_bounds(), _format_time(), _get_duration(), main(), _parse_time(), Path, ``trim-audio`` - trim an audio file (interactive prompts or smart silence…, Parse a user-entered time string to seconds. Returns None on failure. (+5 more)

### Community 19 - "_ensure_handler"
Cohesion: 0.08
Nodes (24): Available commands, Cross-platform behavior, Install, License, `manage.py` cheat sheet, Manual install (without `manage.py`), Optional dependency groups, Project layout (+16 more)

### Community 20 - "npm_tools.py"
Cohesion: 0.28
Nodes (10): _curses_loop(), _draw(), _latest_version(), _list_installed(), main(), ``npm-tools`` - manage globally installed npm packages with a curses TUI., _run(), _run_ops_outside_curses() (+2 more)

### Community 21 - "ios/log.py"
Cohesion: 0.17
Nodes (20): _display_width(), main(), ``ios-log`` - interactive curses-based log viewer for iOS devices. Provides a…, Calculate display width of a string, accounting for wide (CJK) characters., get_booted_simulator(), get_device_name(), IOSDevice, list_devices() (+12 more)

### Community 22 - "copy_to_clipboard"
Cohesion: 0.06
Nodes (53): main(), ``convert-oneline`` - join all lines of a file into a single line and copy it., extract_key(), main(), ``pem-to-oneline`` - extract a PEM key body and copy it to the clipboard., _keyword_pattern(), main(), mask_text() (+45 more)

### Community 23 - "iOS Tools Guide for Android Developers"
Cohesion: 0.10
Nodes (19): Core Concept: Simulator vs Physical Device, Core iOS CLI Tools, Feature Availability by Device Type, `ios-deeplink`, `ios-log`, `ios-log-tail`, iOS Logging System (Unified Logging), `ios-record` (+11 more)

### Community 24 - "mongo.py"
Cohesion: 0.38
Nodes (9): _dump(), _ensure_tools(), _list_archives(), _load_config(), main(), Path, ``mongo-tool`` - dump / restore a mongodb to/from a zip archive. Migrated from…, _restore() (+1 more)

### Community 25 - "core/log.py"
Cohesion: 0.14
Nodes (16): _extract(), _fetch(), main(), ``free-models-nvidia`` - scrape build.nvidia.com free endpoint models., encode(), prompt_quality(), Path, Helpers for video transcoding with ffmpeg. (+8 more)

### Community 26 - "img_resize.py"
Cohesion: 0.51
Nodes (9): _find_images(), _identify_dims(), _interactive_select(), main(), _parse_stem_dims(), Path, ``img-resize`` - resize all images in a directory to target dimensions via…, _ref_dims() (+1 more)

### Community 27 - "free_models_openrouter.py"
Cohesion: 0.43
Nodes (6): date, _format_context(), _format_modality(), main(), _parse_cutoff(), ``free-models-openrouter`` - list free models from openrouter.ai in a table.

### Community 28 - "get_logger"
Cohesion: 0.10
Nodes (27): main(), ``android-studio`` - open the current directory in Android Studio (macOS)., main(), ``ios-deeplink`` - launch a deeplink URL on a booted iOS simulator. Requires…, main(), ``ios-log`` - tail the iOS simulator log filtered by a substring., _get_booted_simulator(), main() (+19 more)

### Community 29 - "checkspace.py"
Cohesion: 0.52
Nodes (6): _dir_size(), _entry_size(), _format(), main(), Path, ``checkspace`` - sort top-level entries in a directory by size.

### Community 31 - "text2num.py"
Cohesion: 0.48
Nodes (6): _is_float(), _is_int(), main(), _process_workbook(), Path, ``text2num`` - convert numeric-looking text in an Excel workbook to real…

### Community 32 - "_ensure_handler"
Cohesion: 0.22
Nodes (8): Handler, LogRecord, _ColorFormatter, _ensure_handler(), Set the root toolscripts logger level., Format records like ``LEVEL logger.name message`` with ANSI colors., _resolve_level(), set_level()

### Community 34 - "mermaid.py"
Cohesion: 0.52
Nodes (6): _choose(), _interactive(), main(), _print_options(), ``mermaid`` - friendly wrapper around the mermaid CLI (``mmdc``)., _run_mmdc()

### Community 35 - "imgcat.py"
Cohesion: 0.53
Nodes (5): _emit(), main(), _osc_prefix(), _osc_suffix(), ``imgcat`` - display images inline in iTerm2 via the OSC 1337 protocol. Cross-…

### Community 36 - "ask"
Cohesion: 0.09
Nodes (40): _is_binary(), _is_ignored(), main(), Path, ``android-rename-project`` - rename an Android project's package across files…, _rreplace(), _update_dir_tree(), _walk_dirs() (+32 more)

### Community 37 - "extract_games.py"
Cohesion: 0.53
Nodes (5): _clean_filename(), _extract(), main(), Path, ``extract-games`` - extract retro ROMs from zip archives into folders by…

### Community 38 - "capture"
Cohesion: 0.06
Nodes (53): CalledProcessError, main(), ``git-delete-local-branches`` - delete all non-current local branches., _run(), _detect_main_branch(), _list_local_branches(), main(), _pick_main_branch() (+45 more)

### Community 39 - "Coding Principles"
Cohesion: 0.14
Nodes (13): 10. Code Organization, 11. Git & Version Control, 12. Communication, 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution, 5. Core Principles (+5 more)

### Community 40 - "Mermaid Multi-Layer Architecture Diagrams"
Cohesion: 0.14
Nodes (13): Alternative Layout: flowchart LR, Caveats, Comparison, Core Technique: graph TB + Hidden Layout Edges, How It Works, How It Works, Key Points, linkStyle Edge Index Calculation (+5 more)

### Community 42 - "split_vertical_quarter.py"
Cohesion: 0.40
Nodes (4): _get_first_session(), main(), Recursively get the first session from a SplitTreeNode or Session., Main function that registers RPC and keeps the script running.

### Community 44 - "simulator.py"
Cohesion: 0.43
Nodes (7): _build_display_items(), _device_sort_key(), _format_boot_time(), _ios_sort_key(), _list_devices(), main(), ``ios-simulator`` - list iOS simulators, boot/open the chosen one.

### Community 45 - "Workflow"
Cohesion: 0.18
Nodes (11): Don'ts, Example, Step 1 — Confirm intent, Step 2 — Locate every touch point, Step 3 — Check for orphaned helpers, Step 4 — Delete in the right order, Step 5 — Tests / data resources, Step 6 — Hand off to the user (+3 more)

### Community 74 - "The Five Optimization Lines (by ROI)"
Cohesion: 0.20
Nodes (9): ① Cache — One-time setup, continuous savings (~45%), ② Select — Get the right code in context, ③ Compress — Prevent context bloat, ④ Isolate — Right model for right task, ⑤ Write — External memory, Coding Agent Cost Optimization, Core Principles, Quick Cost Estimate (+1 more)

### Community 76 - "Workflow"
Cohesion: 0.22
Nodes (9): Step 1 — Clarify, Step 2 — Overlap check (mandatory, do not skip), Step 3 — Pick domain and name, Step 4 — Reuse-first reflex (mandatory, do not skip), Step 5 — Write the module, Step 6 — Register the entry point, Step 7 — Update both READMEs, Step 8 — Hand off to the user (+1 more)

### Community 79 - "statcounter.py"
Cohesion: 0.60
Nodes (4): main(), Path, ``statcounter`` - draw a pie chart of OS-version coverage from a Statcounter…, _read_data()

### Community 80 - "CONVENTIONS.md"
Cohesion: 0.29
Nodes (3): Don'ts, Example: end-to-end, toolscripts-command-add

### Community 81 - "Workflow"
Cohesion: 0.29
Nodes (7): Step 1 — Locate, Step 2 — Understand the current behavior, Step 3 — Classify the change, Step 4 — Apply the change (reuse-first reflex applies here too), Step 5 — Sync the public surface, Step 6 — Hand off to the user, Workflow

### Community 83 - "4. Reuse first (DRY) — the reflex before writing code"
Cohesion: 0.33
Nodes (6): 4. Reuse first (DRY) — the reflex before writing code, Concrete examples already in the repo, Hard rules, The 3-question check (do this *before* writing code), When you find duplication, When you genuinely need something new

### Community 84 - "sensitive_hook.py"
Cohesion: 0.40
Nodes (5): RuntimeError, main(), Path, ``git-sensitive-hook`` - install a commit-msg hook that blocks sensitive terms…, _resolve_git_dir()

### Community 85 - "explainer.md"
Cohesion: 0.33
Nodes (5): ASCII Visualization Examples, How you think, How you work, Output guidance, What you should NOT do

### Community 86 - "toolscripts-command-modify"
Cohesion: 0.40
Nodes (5): Don'ts, Example: bug fix without contract change, Example: rename a command, toolscripts-command-modify, When to use this skill (vs. -add / -remove)

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

## Knowledge Gaps
- **164 isolated node(s):** `toolscripts`, `Layering rules`, `Existing domains under `commands/``, `2. Naming`, `3. Module skeleton` (+159 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `configure_from_args()` connect `configure_from_args` to `run`, `record_audio.py`, `llamacmd.py`, `ui_curses.py`, `select_one`, `LogViewer`, `axios_audit.py`, `graphifycmd.py`, `require`, `ai_links.py`, `trim_audio.py`, `npm_tools.py`, `ios/log.py`, `copy_to_clipboard`, `mongo.py`, `core/log.py`, `img_resize.py`, `free_models_openrouter.py`, `get_logger`, `checkspace.py`, `text2num.py`, `_ensure_handler`, `mermaid.py`, `imgcat.py`, `ask`, `extract_games.py`, `capture`, `simulator.py`, `statcounter.py`, `sensitive_hook.py`, `dirdiff.py`, `remove_watermark.py`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Why does `add_logging_flags()` connect `configure_from_args` to `run`, `record_audio.py`, `llamacmd.py`, `ui_curses.py`, `select_one`, `LogViewer`, `axios_audit.py`, `graphifycmd.py`, `require`, `ai_links.py`, `trim_audio.py`, `npm_tools.py`, `ios/log.py`, `copy_to_clipboard`, `mongo.py`, `core/log.py`, `img_resize.py`, `free_models_openrouter.py`, `get_logger`, `checkspace.py`, `text2num.py`, `mermaid.py`, `imgcat.py`, `ask`, `extract_games.py`, `capture`, `simulator.py`, `statcounter.py`, `sensitive_hook.py`, `dirdiff.py`, `remove_watermark.py`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._
- **Why does `get_logger()` connect `get_logger` to `run`, `record_audio.py`, `llamacmd.py`, `ui_curses.py`, `select_one`, `LogViewer`, `configure_from_args`, `axios_audit.py`, `require`, `ai_links.py`, `trim_audio.py`, `npm_tools.py`, `ios/log.py`, `copy_to_clipboard`, `mongo.py`, `core/log.py`, `img_resize.py`, `free_models_openrouter.py`, `checkspace.py`, `text2num.py`, `_ensure_handler`, `mermaid.py`, `imgcat.py`, `ask`, `extract_games.py`, `capture`, `simulator.py`, `statcounter.py`, `sensitive_hook.py`, `dirdiff.py`, `remove_watermark.py`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **What connects `toolscripts`, `Layering rules`, `Existing domains under `commands/`` to the rest of the system?**
  _164 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `run` be split into smaller, more focused modules?**
  _Cohesion score 0.08205128205128205 - nodes in this community are weakly interconnected._
- **Should `record_audio.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11095305832147938 - nodes in this community are weakly interconnected._
- **Should `ui_curses.py` be split into smaller, more focused modules?**
  _Cohesion score 0.053410893707033315 - nodes in this community are weakly interconnected._
# Graph Report - toolscripts  (2026-05-06)

## Corpus Check
- 133 files · ~53,773 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 764 nodes · 1398 edges · 78 communities (58 shown, 20 thin omitted)
- Extraction: 71% EXTRACTED · 29% INFERRED · 0% AMBIGUOUS · INFERRED: 399 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6b7b15f0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]

## God Nodes (most connected - your core abstractions)
1. `configure_from_args()` - 102 edges
2. `add_logging_flags()` - 101 edges
3. `run()` - 49 edges
4. `require()` - 38 edges
5. `capture()` - 23 edges
6. `ask()` - 18 edges
7. `_audit_directory()` - 16 edges
8. `copy_to_clipboard()` - 15 edges
9. `main()` - 14 edges
10. `select_one()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `require_platform()` --calls--> `get_logger()`  [INFERRED]
  src/toolscripts/core/platform.py → src/toolscripts/core/log.py
- `_ensure_curses_available()` --calls--> `get_logger()`  [INFERRED]
  src/toolscripts/core/ui_curses.py → src/toolscripts/core/log.py
- `main()` --calls--> `add_logging_flags()`  [INFERRED]
  src/toolscripts/commands/credential/jwt_decode.py → src/toolscripts/core/log.py
- `main()` --calls--> `add_logging_flags()`  [INFERRED]
  src/toolscripts/commands/credential/pem_to_oneline.py → src/toolscripts/core/log.py
- `main()` --calls--> `add_logging_flags()`  [INFERRED]
  src/toolscripts/commands/credential/redact_clipboard.py → src/toolscripts/core/log.py

## Communities (78 total, 20 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (46): ``android-logcat`` - run adb logcat filtered by application id and tags., _select_pid(), capture(), Run ``cmd`` and return its stdout as a string., _delete_local(), _delete_remote(), _fetch_and_prune(), _list_local_branches() (+38 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (35): main(), ``android-adbsync`` - remount the device, sync, and restart the framework., main(), ``android-cp-drawable`` - copy a drawable asset into the standard res/drawable-*, main(), ``dec2bin`` - convert decimal numbers to binary (interactive or one-shot)., main(), ``dec2hex`` - convert decimal numbers to hexadecimal. (+27 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (33): copy_to_clipboard(), paste_from_clipboard(), Cross-platform clipboard helpers.  Tries the ``pyperclip`` package first (if ins, Copy ``text`` to the clipboard. Returns True on success., Read text from the clipboard. Returns None on failure., _try_pyperclip_copy(), _try_pyperclip_paste(), extract_key() (+25 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (32): _fetch_free_models(), _load_config(), models_main(), ``aido`` and ``aido-models`` - run prompts via opencode + a saved free model., _save_config(), _build_custom_env(), _detect_current(), _get_or_input() (+24 more)

### Community 4 - "Community 4"
Cohesion: 0.1
Nodes (32): current_platform(), is_linux(), is_macos(), is_windows(), Platform detection and gating.  Use ``require_platform("macos")`` at the top of, Return one of: ``macos``, ``linux``, ``windows``, or the raw ``sys.platform`` va, Exit with a friendly warning if the current platform is not supported.      Acce, require_platform() (+24 more)

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (25): _apply_selection(), _detect_current_selection(), _ensure_main_subdir(), _find_agents_root(), _gitignore_entries(), _has_anything_to_link(), _interactive_pick(), _is_umbrella_symlink_to_main() (+17 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (27): Return a single connected device serial, prompting the user if needed.      Exit, select_device(), main(), ``android-deeplink`` - launch a deeplink URL on a connected Android device., main(), ``android-input-text`` - send a text string to the focused field on an Android d, main(), main() (+19 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (21): CommandNotFoundError, Subprocess wrappers with consistent error handling and logging.  Higher-level th, Raised when an external binary cannot be located on PATH., Return the absolute path of ``name`` on PATH, or ``None``., Run ``cmd`` and return True on success, False on any error.      Useful when the, try_run(), which(), main() (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.15
Nodes (24): colored(), enable_windows_ansi(), ANSI color helpers with tty / NO_COLOR awareness.  The constants below evaluate, Enable ANSI escape processing on the Windows console (no-op elsewhere)., Wrap ``text`` with ``color`` (and optional bold) if colors are enabled., _add_overrides(), _audit_directory(), _audit_package_json() (+16 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (25): colors_enabled(), Return True if ANSI colors should be emitted on the given stream., BrowseEntry, A single command exposed to ``browse_commands``., NamedTuple, CommandInfo, _discover(), _domain_of() (+17 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (17): run_main(), Like ``which()`` but raises ``CommandNotFoundError`` if missing., require(), main(), ``oauth-code`` - generate a TOTP code via ``oathtool`` and copy to clipboard.  M, main(), ``docker-linux-env`` - run a Linux utility container with the cwd mounted at /ap, main() (+9 more)

### Community 11 - "Community 11"
Cohesion: 0.24
Nodes (21): build_parser(), _c(), _capture(), cmd_install(), cmd_status(), cmd_uninstall(), error(), _have() (+13 more)

### Community 12 - "Community 12"
Cohesion: 0.21
Nodes (19): _ask_prompt_type(), _branch_diff(), _commit_format(), _current_branch(), _format_and_copy(), main(), _menu_select(), _multi_commit_diff() (+11 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (14): main(), ``android-emulator`` - list available AVDs and start the chosen one., main(), ``android-keystore-generate`` - wrap keytool to generate Android keystores., Prompt for a yes/no answer. Accepts y/yes/n/no (case-insensitive)., yes_no(), main(), ``git-delete-local-branches`` - delete all non-current local branches. (+6 more)

### Community 14 - "Community 14"
Cohesion: 0.18
Nodes (11): _ColorFormatter, _ensure_handler(), get_logger(), Unified colored logger for toolscripts.  Quick start::      from toolscripts.cor, Return a logger under the ``toolscripts`` namespace.      ``name`` may be ``__na, Set the root toolscripts logger level., Logger subclass exposing a ``success()`` convenience method., Format records like ``LEVEL  logger.name  message`` with ANSI colors. (+3 more)

### Community 15 - "Community 15"
Cohesion: 0.19
Nodes (12): _check_graphify(), _GraphifyPlatform, _install_one(), main(), ``graphify-setup`` - install/uninstall graphify skill for AI coding tools.  Requ, Install graphify for a platform: user-level skill + project-level config., Uninstall graphify for a platform: project-level first, then user-level skill., Maps an AITool to its graphify CLI subcommand. (+4 more)

### Community 16 - "Community 16"
Cohesion: 0.3
Nodes (14): _agent_count(), _agents_dir(), _cleanup_one(), _data_dir(), _discover_agents(), _has_anything(), _has_instructions(), _instructions_source() (+6 more)

### Community 17 - "Community 17"
Cohesion: 0.27
Nodes (10): _curses_loop(), _draw(), _latest_version(), _list_installed(), main(), ``npm-tools`` - manage globally installed npm packages with a curses TUI., _run(), _run_ops_outside_curses() (+2 more)

### Community 18 - "Community 18"
Cohesion: 0.34
Nodes (13): _bundled_config(), _check_catalog(), _check_image_tag_list(), _http_get(), _load_config(), main(), _prompt(), ``docker-registry`` - manage a private docker registry (start, query, push). (+5 more)

### Community 19 - "Community 19"
Cohesion: 0.25
Nodes (8): encode(), prompt_quality(), Helpers for video transcoding with ffmpeg., Run ffmpeg libx264/aac encode. Returns True on success., main(), ``mov-to-mp4`` - convert a MOV file to MP4 with selectable quality., main(), ``mp4-compress`` - compress an MP4 file with selectable quality.

### Community 20 - "Community 20"
Cohesion: 0.28
Nodes (7): list_devices(), ADB device discovery and selection.  Used by every ``android-*`` command. Wraps, Return the serials of all currently connected ADB devices., _find_apk(), _load_mapping(), main(), ``android-batch-install`` - install APKs on connected devices using a JSON mappi

### Community 21 - "Community 21"
Cohesion: 0.39
Nodes (8): _b64_decode(), _decode_json(), decode_jwt(), _format_timestamp(), main(), _print_block(), _print_claim_annotations(), ``jwt-decode`` - decode a JWT token like jwt.io, in the terminal.

### Community 22 - "Community 22"
Cohesion: 0.42
Nodes (8): _is_binary(), _is_ignored(), main(), ``android-rename-project`` - rename an Android project's package across files an, _rreplace(), _update_dir_tree(), _walk_dirs(), _walk_files()

### Community 23 - "Community 23"
Cohesion: 0.42
Nodes (8): _dump(), _ensure_tools(), _list_archives(), _load_config(), main(), ``mongo-tool`` - dump / restore a mongodb to/from a zip archive.  Migrated from, _restore(), _select_archive()

### Community 24 - "Community 24"
Cohesion: 0.31
Nodes (8): _format_time(), _get_duration(), main(), _parse_time(), ``trim-audio`` - trim an audio file with interactive start/end prompts., Return duration in seconds via ffprobe., Parse a user-entered time string to seconds. Returns None on failure., Format seconds to human-readable string.

### Community 25 - "Community 25"
Cohesion: 0.47
Nodes (8): _find_images(), _identify_dims(), _interactive_select(), main(), _parse_stem_dims(), ``img-resize`` - resize all images in a directory to target dimensions via Image, _ref_dims(), _resize_one()

### Community 26 - "Community 26"
Cohesion: 0.46
Nodes (7): _config_get(), _do_read(), _do_write(), _git_repos(), _is_git_repo(), main(), ``git-user-batch`` - batch read or set git user.name/email for all subdirectory

### Community 27 - "Community 27"
Cohesion: 0.29
Nodes (6): main(), _matches(), ``android-retrieve-media`` - pull recent images/videos/screenshots from a device, choice(), Interactive CLI prompts.  Thin wrappers over ``input()`` that handle EOF/Ctrl-C, Prompt the user to pick one option by number.      Returns the zero-based index

### Community 28 - "Community 28"
Cohesion: 0.52
Nodes (6): _choose(), _interactive(), main(), _print_options(), ``mermaid`` - friendly wrapper around the mermaid CLI (``mmdc``)., _run_mmdc()

### Community 29 - "Community 29"
Cohesion: 0.53
Nodes (5): decode(), _format_value(), main(), ``url-decode-params`` - decode URL-encoded query parameters with JSON detection., _try_parse_json()

### Community 30 - "Community 30"
Cohesion: 0.53
Nodes (5): _dir_size(), _entry_size(), _format(), main(), ``checkspace`` - sort top-level entries in a directory by size.

### Community 31 - "Community 31"
Cohesion: 0.53
Nodes (5): main(), _pyenv_versions(), ``uv-venv-create`` - create a virtual environment via ``uv venv``., _select(), _system_versions()

### Community 32 - "Community 32"
Cohesion: 0.53
Nodes (5): _format_context(), _format_modality(), main(), _parse_cutoff(), ``free-models-openrouter`` - list free models from openrouter.ai in a table.

### Community 33 - "Community 33"
Cohesion: 0.53
Nodes (5): _is_float(), _is_int(), main(), _process_workbook(), ``text2num`` - convert numeric-looking text in an Excel workbook to real numbers

### Community 34 - "Community 34"
Cohesion: 0.53
Nodes (5): _config_get(), main(), ``git-user`` - interactively view or update local git user.name / user.email., _set(), _show()

### Community 35 - "Community 35"
Cohesion: 0.53
Nodes (5): _emit(), main(), _osc_prefix(), _osc_suffix(), ``imgcat`` - display images inline in iTerm2 via the OSC 1337 protocol.  Cross-p

### Community 36 - "Community 36"
Cohesion: 0.5
Nodes (4): convert(), main(), ``date2timestamp`` - convert a date string to a millisecond timestamp., Parse ``YYYY-MM-DDTHH:MM:SS.fff`` and return milliseconds since epoch.

### Community 37 - "Community 37"
Cohesion: 0.5
Nodes (4): convert(), main(), ``timestamp2date`` - convert a millisecond timestamp to a date string., Convert ``milliseconds`` since epoch to ``YYYY-MM-DDTHH:MM:SS.fff``.

### Community 38 - "Community 38"
Cohesion: 0.6
Nodes (4): _list_versions(), main(), ``venv-create`` - select a pyenv-managed Python version and create a venv., _select()

### Community 39 - "Community 39"
Cohesion: 0.6
Nodes (4): _extract(), _fetch(), main(), ``free-models-nvidia`` - scrape build.nvidia.com free endpoint models.

### Community 40 - "Community 40"
Cohesion: 0.6
Nodes (4): _clean_filename(), _extract(), main(), ``extract-games`` - extract retro ROMs from zip archives into folders by extensi

### Community 41 - "Community 41"
Cohesion: 0.5
Nodes (4): clang_main(), from_here_main(), ``list-include-dirs-from-here`` and ``list-include-dirs-clang``., _walk_includes()

### Community 42 - "Community 42"
Cohesion: 0.4
Nodes (4): _get_first_session(), main(), Recursively get the first session from a SplitTreeNode or Session., Main function that registers RPC and keeps the script running.

### Community 43 - "Community 43"
Cohesion: 0.67
Nodes (3): decode_base64_to_json(), main(), ``decode-and-format-json`` - decode a base64 string and pretty-print the JSON in

### Community 44 - "Community 44"
Cohesion: 0.67
Nodes (3): hex_to_rgb(), main(), ``hex2rgb`` - convert a hex color code to RGB.

### Community 46 - "Community 46"
Cohesion: 0.67
Nodes (3): main(), ``statcounter`` - draw a pie chart of OS-version coverage from a Statcounter CSV, _read_data()

### Community 47 - "Community 47"
Cohesion: 0.67
Nodes (3): format_file(), main(), ``json-format`` - read a JSON file, pretty-print it, save to ``*_format.<ext>``.

### Community 48 - "Community 48"
Cohesion: 0.67
Nodes (3): _ask_directory(), main(), ``dirdiff`` - launch Vim's ``DirDiff`` on two directories.

### Community 49 - "Community 49"
Cohesion: 0.67
Nodes (3): _ask(), main(), ``uvcmd`` - interactive front-end for common ``uv`` commands.

### Community 50 - "Community 50"
Cohesion: 0.67
Nodes (3): basic_auth(), main(), ``basic-auth`` - generate a Base64-encoded HTTP Basic Auth string.

## Knowledge Gaps
- **197 isolated node(s):** `toolscripts: a monorepo of cross-platform CLI utilities to make work simple.`, `Unified colored logger for toolscripts.  Quick start::      from toolscripts.cor`, `Logger subclass exposing a ``success()`` convenience method.`, `Format records like ``LEVEL  logger.name  message`` with ANSI colors.`, `Return a logger under the ``toolscripts`` namespace.      ``name`` may be ``__na` (+192 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `configure_from_args()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 12`, `Community 13`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 18`, `Community 19`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 24`, `Community 25`, `Community 26`, `Community 27`, `Community 28`, `Community 29`, `Community 30`, `Community 31`, `Community 32`, `Community 33`, `Community 34`, `Community 35`, `Community 36`, `Community 37`, `Community 38`, `Community 39`, `Community 40`, `Community 41`, `Community 43`, `Community 44`, `Community 46`, `Community 47`, `Community 48`, `Community 49`, `Community 50`, `Community 51`?**
  _High betweenness centrality (0.343) - this node is a cross-community bridge._
- **Why does `add_logging_flags()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 12`, `Community 13`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 18`, `Community 19`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 24`, `Community 25`, `Community 26`, `Community 27`, `Community 28`, `Community 29`, `Community 30`, `Community 31`, `Community 32`, `Community 33`, `Community 34`, `Community 35`, `Community 36`, `Community 37`, `Community 38`, `Community 39`, `Community 40`, `Community 41`, `Community 43`, `Community 44`, `Community 46`, `Community 47`, `Community 48`, `Community 49`, `Community 50`, `Community 51`?**
  _High betweenness centrality (0.337) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 9` to `Community 1`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 99 inferred relationships involving `configure_from_args()` (e.g. with `main()` and `main()`) actually correct?**
  _`configure_from_args()` has 99 INFERRED edges - model-reasoned connections that need verification._
- **Are the 99 inferred relationships involving `add_logging_flags()` (e.g. with `main()` and `main()`) actually correct?**
  _`add_logging_flags()` has 99 INFERRED edges - model-reasoned connections that need verification._
- **Are the 45 inferred relationships involving `run()` (e.g. with `_start_registry()` and `_tag_and_push()`) actually correct?**
  _`run()` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `require()` (e.g. with `list_devices()` and `main()`) actually correct?**
  _`require()` has 34 INFERRED edges - model-reasoned connections that need verification._
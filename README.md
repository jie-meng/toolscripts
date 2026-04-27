# toolscripts

English | [中文](./README.zh-CN.md)

A monorepo of cross-platform CLI utilities to **make work simple**.

It bundles 90+ small, single-purpose commands (`timestamp-now`,
`android-record`, `git-copy-diff`, `json-format`, ...) into one installable
Python package. Every command is a real Python entry point: install once,
run anywhere — macOS, Linux, Windows.

## Install

The repo ships a tiny helper script that wraps `pipx` and `pip` so you don't
have to remember the exact flags:

```bash
git clone <repo-url>
cd toolscripts
./manage.py install
```

That's it — every command in `[project.scripts]` is now on your `$PATH` with
**no further configuration**. Updates are just `git pull && ./manage.py install`
(it auto-reinstalls if already present).

### `manage.py` cheat sheet

```bash
./manage.py install                    # pipx + [all]   (recommended default)
./manage.py install --extras media,git # pipx, only those extras
./manage.py install --pip              # pip into the active Python env
./manage.py install --force            # force reinstall
./manage.py uninstall                  # try both pipx and pip, skip whichever is absent
./manage.py status                     # show install state on both pipx and pip
```

### Why `pipx` instead of `pip`?

`toolscripts` is a collection of CLI tools, not a library you `import`. For
that case `pipx` is the right tool:

- **`pip install`** drops the package into whatever Python environment is
  active (system / user / venv). Easy to pollute and conflict with other
  projects' dependencies.
- **`pipx install`** creates a dedicated, isolated venv for the package and
  symlinks just its commands into `~/.local/bin`. No dependency conflicts,
  no manual `$PATH` setup, clean uninstall via `./manage.py uninstall`.

If you don't have `pipx` yet:

```bash
brew install pipx          # macOS
python3 -m pip install --user pipx && python3 -m pipx ensurepath
```

### Manual install (without `manage.py`)

```bash
pipx install -e ".[all]"               # equivalent to ./manage.py install
pip install -e ".[all]"                # equivalent to ./manage.py install --pip
```

### Optional dependency groups

To keep the install lean, third-party dependencies are split into extras.
Install only what you need:

| Extra        | What it pulls in                              | Used by                            |
| ------------ | --------------------------------------------- | ---------------------------------- |
| `clipboard`  | `pyperclip`                                   | `git-copy-diff`, `slugify`, ...    |
| `media`      | `pillow`, `matplotlib`                        | `img-resize`, `img-scale`, ...     |
| `office`     | `openpyxl`                                    | `xlsx-text2num`                    |
| `text`       | `markdownify`, `translate`, `binaryornot`     | `web2md`, `translate`, ...         |
| `windows`    | `windows-curses` (Windows only)               | curses-based pickers               |
| `all`        | everything above                              | —                                  |
| `dev`        | `ruff`, `pytest`, `mypy`                      | development                        |

Example: `./manage.py install --extras clipboard,media`.

## Uninstall

```bash
./manage.py uninstall          # try both pipx and pip
./manage.py uninstall --pipx   # only pipx
./manage.py uninstall --pip    # only pip
```

`pip` does not auto-remove dependencies — `manage.py` will print the list of
candidates you may want to remove manually after a `--pip` uninstall.

## Usage

Every command supports `--help` and respects two global flags:

```
-v, --verbose   enable debug logging
-q, --quiet     only show warnings and errors
```

A few environment variables tweak output:

| Variable                  | Effect                                         |
| ------------------------- | ---------------------------------------------- |
| `TOOLSCRIPTS_LOG_LEVEL`   | override the log level (`DEBUG`/`INFO`/...)    |
| `TOOLSCRIPTS_LOG_TIME=1`  | prefix log lines with a timestamp              |
| `NO_COLOR=1`              | disable ANSI colors (https://no-color.org/)    |
| `FORCE_COLOR=1`           | force ANSI colors even when stderr is not a TTY |

## Available commands

A non-exhaustive tour, grouped by domain. Run any command with `--help` for
full options.

| Domain     | Commands |
| ---------- | -------- |
| time       | `timestamp-now`, `timestamp2date`, `date2timestamp`, `timestamp-offset` |
| calc       | `dec2bin`, `dec2hex`, `hex2bin`, `hex2dec`, `hex2rgb` |
| codec      | `json-format`, `decode-format-json`, `url-params-decode`, `convert-oneline` |
| credential | `jwt-decode`, `basic-auth`, `uuid-gen`, `redact-clipboard`, `pem-to-oneline`, `oauth-code` |
| git        | `git-copy-diff`, `git-delete-branch`, `git-delete-local-branches`, `git-make-patches`, `git-apply-patches`, `git-install-sensitive-hook`, `git-user`, `git-user-batch` |
| android    | `android-record`, `android-deeplink`, `android-input-text`, `android-screencast`, `android-logcat`, `android-emulator`, `android-batch-install`, `android-retrieve-media`, `android-rename-project`, `android-adbsync`, `android-cp-drawable`, `android-keystore-generate`, `android-studio` |
| ios        | `ios-log`, `ios-record`, `ios-simulator`, `xcode-terminal` |
| media      | `img-resize`, `img-scale`, `imgcat`, `playsound`, `stopsound`, `mp4-compress`, `mov-to-mp4`, `mp4cut`, `mp4togif`, `mp3-to-pcm`, `remove-watermark`, `pdf-merge`, `kindle-pdf-cropper` |
| ai         | `ccswitch`, `aido`, `aido-models`, `free-models-openrouter`, `free-models-nvidia`, `agents-setup`, `agents-cleanup`, `ai-links`, `npm-tools` |
| text/docs  | `markdown-snippet`, `slugify`, `web2md`, `translate`, `mermaid`, `statcounter-os-coverage`, `xlsx-text2num` |
| system     | `myip`, `checkspace`, `lsdevcu`, `rm-ds-store`, `rm-meta`, `dirdiff`, `intellij`, `pycharm`, `xcode`, `cleanup`, `venv-create`, `uv-venv-create`, `uvcmd`, `iterm-setup` |
| misc       | `axios-audit`, `extract-games`, `list-include-dirs-from-here`, `list-include-dirs-clang`, `dockercmd`, `docker-linux-env`, `docker-registry`, `mongo-tool` |

The complete list lives in `[project.scripts]` inside `pyproject.toml`.

## Project layout

```
toolscripts/
├── pyproject.toml              # project metadata, extras, console scripts
├── src/
│   └── toolscripts/
│       ├── core/               # pure utilities (log, colors, shell, ...)
│       ├── adb/                # ADB device helpers
│       ├── git_utils/          # shared git helpers
│       ├── data/               # bundled non-code resources (agents, configs)
│       └── commands/           # CLI implementations, by domain
│           ├── android/
│           ├── ios/
│           ├── git/
│           ├── time/
│           └── ...
├── tests/
└── AGENTS.md                   # conventions for AI/human contributors
```

The `core/` layer has zero business logic. The `adb/` and `git_utils/` layers
provide cross-domain helpers. Everything in `commands/` is a thin orchestration
layer — one file per command, each exposing `def main()`.

## Cross-platform behavior

Some commands are inherently platform-specific (e.g. `xcode`, `iterm-setup`).
Running them on an unsupported platform prints a yellow warning and exits
cleanly (status `0`) — they are intentional no-ops, not failures:

```
WARN  iterm.setup  this command is only supported on macos, current platform: linux
```

## License

MIT — see [LICENSE](./LICENSE).

# toolscripts

[English](./README.md) | 中文

一个跨平台 CLI 工具集合的 monorepo，让日常工作**更简单**。

它把 90+ 个小而专一的命令（`timestamp-now`、`android-record`、`git-copy-diff`、
`json-format` 等）打包成一个可安装的 Python 包。每个命令都是真正的 Python
入口点：装一次，到处用 —— macOS、Linux、Windows 通吃。

## 安装

```bash
git clone <repo-url>
cd toolscripts
pipx install -e ".[all]"
```

完事 —— `[project.scripts]` 中的所有命令都已经在你的 `$PATH` 上了，**无需任何额外配置**。
更新只要 `git pull && pipx reinstall toolscripts`。

### 为什么用 `pipx` 而不是 `pip`？

`toolscripts` 是一组 CLI 工具，不是用来 `import` 的库。这种场景下 `pipx` 才是正解：

- **`pip install`** 把包装到当前激活的 Python 环境（system / user / venv）里，
  容易污染环境并跟其他项目的依赖冲突。
- **`pipx install`** 为每个包创建独立的 venv，并把命令 symlink 到 `~/.local/bin`。
  没有依赖冲突、不用手动配 `$PATH`，卸载也干脆 —— `pipx uninstall toolscripts` 即可。

如果你还没装 `pipx`：

```bash
brew install pipx          # macOS
python3 -m pip install --user pipx && python3 -m pipx ensurepath
```

### 可选依赖分组

为了保持安装体积精简，第三方依赖按 extras 拆分。按需安装：

| Extra        | 包含的依赖                                     | 用于                               |
| ------------ | --------------------------------------------- | ---------------------------------- |
| `clipboard`  | `pyperclip`                                   | `git-copy-diff`、`slugify` 等      |
| `media`      | `pillow`、`matplotlib`                        | `img-resize`、`img-scale` 等       |
| `office`     | `openpyxl`                                    | `xlsx-text2num`                    |
| `text`       | `markdownify`、`translate`、`binaryornot`     | `web2md`、`translate` 等           |
| `windows`    | `windows-curses`（仅 Windows）                | 基于 curses 的交互选择器           |
| `all`        | 以上全部                                      | —                                  |
| `dev`        | `ruff`、`pytest`、`mypy`                      | 开发                               |

例如：`pipx install -e ".[clipboard,media]"`。

## 使用

每个命令都支持 `--help`，并遵循两个全局参数：

```
-v, --verbose   开启 debug 日志
-q, --quiet     只显示 warning 及以上的日志
```

几个环境变量可以微调输出：

| 变量                      | 效果                                                  |
| ------------------------- | ----------------------------------------------------- |
| `TOOLSCRIPTS_LOG_LEVEL`   | 覆盖日志级别（`DEBUG`/`INFO`/...）                    |
| `TOOLSCRIPTS_LOG_TIME=1`  | 在日志行前面加上时间戳                                |
| `NO_COLOR=1`              | 关闭 ANSI 颜色（参考 https://no-color.org/）          |
| `FORCE_COLOR=1`           | 即使 stderr 不是 TTY 也强制启用 ANSI 颜色             |

## 命令一览

按领域分组的部分命令清单（不完全）。每个命令都可以用 `--help` 查看完整选项。

| 领域       | 命令 |
| ---------- | ---- |
| 时间       | `timestamp-now`、`timestamp2date`、`date2timestamp`、`timestamp-offset` |
| 进制转换   | `dec2bin`、`dec2hex`、`hex2bin`、`hex2dec`、`hex2rgb` |
| 编解码     | `json-format`、`decode-format-json`、`url-params-decode`、`convert-oneline` |
| 凭证       | `jwt-decode`、`basic-auth`、`uuid-gen`、`redact-clipboard`、`pem-to-oneline`、`oauth-code` |
| Git        | `git-copy-diff`、`git-delete-branch`、`git-delete-local-branches`、`git-make-patches`、`git-apply-patches`、`git-install-sensitive-hook`、`git-user`、`git-user-batch` |
| Android    | `android-record`、`android-deeplink`、`android-input-text`、`android-screencast`、`android-logcat`、`android-emulator`、`android-batch-install`、`android-retrieve-media`、`android-rename-project`、`android-adbsync`、`android-cp-drawable`、`android-keystore-generate`、`android-studio` |
| iOS        | `ios-log`、`ios-record`、`ios-simulator`、`xcode-terminal` |
| 媒体       | `img-resize`、`img-scale`、`imgcat`、`playsound`、`stopsound`、`mp4-compress`、`mov-to-mp4`、`mp4cut`、`mp4togif`、`mp3-to-pcm`、`remove-watermark`、`pdf-merge`、`kindle-pdf-cropper` |
| AI 工具    | `ccswitch`、`aido`、`aido-models`、`free-models-openrouter`、`free-models-nvidia`、`agents-setup`、`agents-cleanup`、`ai-links`、`npm-tools` |
| 文本/文档  | `markdown-snippet`、`slugify`、`web2md`、`translate`、`mermaid`、`statcounter-os-coverage`、`xlsx-text2num` |
| 系统       | `myip`、`checkspace`、`lsdevcu`、`rm-ds-store`、`rm-meta`、`dirdiff`、`intellij`、`pycharm`、`xcode`、`cleanup`、`venv-create`、`uv-venv-create`、`uvcmd`、`iterm-setup` |
| 杂项       | `axios-audit`、`extract-games`、`list-include-dirs-from-here`、`list-include-dirs-clang`、`dockercmd`、`docker-linux-env`、`docker-registry`、`mongo-tool` |

完整列表见 `pyproject.toml` 中的 `[project.scripts]`。

## 项目结构

```
toolscripts/
├── pyproject.toml              # 项目元数据、extras、console scripts
├── src/
│   └── toolscripts/
│       ├── core/               # 纯工具层（log、colors、shell 等）
│       ├── adb/                # ADB 设备相关辅助函数
│       ├── git_utils/          # 共享 git 辅助函数
│       ├── data/               # 打包的非代码资源（agents、配置等）
│       └── commands/           # 按领域组织的 CLI 实现
│           ├── android/
│           ├── ios/
│           ├── git/
│           ├── time/
│           └── ...
├── tests/
└── AGENTS.md                   # 给 AI / 人类贡献者的约定
```

`core/` 层不含业务逻辑。`adb/` 和 `git_utils/` 提供跨领域辅助函数。`commands/`
里的全部都是薄薄的编排层 —— 一个文件一个命令，每个文件暴露一个 `def main()`。

## 跨平台行为

某些命令本质上就是平台专属的（例如 `xcode`、`iterm-setup`）。在不支持的平台
上运行时，它们会打印一条黄色的 warning 并干净退出（状态码 `0`）—— 这是有意的
no-op，不是失败：

```
WARN  iterm.setup  this command is only supported on macos, current platform: linux
```

## License

MIT —— 见 [LICENSE](./LICENSE)。

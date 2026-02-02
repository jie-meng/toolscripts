---
name: code-review
description: Perform comprehensive code review for staged git changes with automatic language detection and commit message generation
license: MIT
---

# Requirements for Outputs

## Code Review Quality

### Review Standards
- Code review MUST be comprehensive, identifying all potential issues
- Review MUST be thorough and rigorous, highlighting suspicious code
- Review MUST provide actionable, concrete suggestions
- Review language MUST match the user's input language (Chinese or English)
- Commit message MUST always be in English, regardless of review language

### Language Detection
- Detect user's input language automatically
- If user input contains Chinese characters (Unicode U+4E00-U+9FFF), output review in Chinese
- If user input contains only English, output review in English
- Commit message section always outputs in English

### Commit Message Generation
- Analyze staged changes from `git diff --cached`
- Consider current branch name for format:
  - If branch name contains slash (e.g., `feat/item-definition`), use format: `type[scope]: message`
  - If branch name doesn't contain slash, use conventional format: `type: message`
- Commit message MUST be concise, accurate, and in English
- Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

## Clipboard Support

### macOS
- Use `pbcopy` command to copy commit message to clipboard
- Commit message from section 6 is automatically extracted and copied

### Other Systems
- Use `pyperclip` library if available
- Fall back to manual copy if clipboard tools unavailable

# Code Review

Perform comprehensive code review for staged git changes with automatic language detection and commit message generation.

## Usage

When user requests code review, invoke this skill.

**Example requests:**
- "Review my code changes"
- "代码审查"
- "Check my staged changes"
- "帮我审查一下代码"

## Technical Requirements

- **Working directory**: Git repository root
- **Git operations**:
  - `git diff --cached` - View staged changes
  - `git rev-parse --abbrev-ref HEAD` - Get current branch name
- **Clipboard operations**:
  - macOS: `pbcopy`
  - Others: `pyperclip`

## Configuration

- **Language detection**: Based on user input (Chinese/English)
- **Branch name**: Used to determine commit message format
- **Commit format**: `type[scope]: message` or `type: message`

## Implementation

The skill executes these steps:

### Step 1: Get Staged Changes
```bash
git diff --cached
```
Retrieve all staged changes for review.

### Step 2: Get Current Branch
```bash
git rev-parse --abbrev-ref HEAD
```
Determine current branch name for commit message formatting.

### Step 3: Detect Language
Analyze user's input to determine review output language:
- Contains Chinese characters → Chinese review
- Only English → English review
- Commit message always in English

### Step 4: Perform Code Review

If Chinese review requested:

#### 1. 技术栈推断
- 根据diff内容推断主要使用的编程语言、框架或库，以及明显的后端/前端/全栈类型（如有）
- 简单说明推断的依据（如语法、导入库、项目结构线索等）

#### 2. 代码变更概览
- 用简明扼要的语言总结此diff主要做了哪些事情（例如：修复bug、添加功能、重构、配置变更等）
- 说明受影响的主要模块或功能业务

#### 3. 代码质量 & Clean Code 评价
- 全面评估变更的代码风格、命名、注释、可读性、可维护性、设计架构、模块解耦、重复代码等
- 发现任何易错写法、不安全代码、低效实现、反模式或不符合最佳实践的地方要具体列出
- 指出被修改的具体位置与问题描述（行号/文件名/代码片段，或足够明确的定位描述）
- 提出详细的修复/重构/优化建议，并解释理由

#### 4. 潜在的重大问题和风险
- 检查代码逻辑是否存在难以发现的bug、异常未处理、未校验边界条件、性能瓶颈、安全隐患等
- 指出这些疑点，并简单说明为何值得关注

#### 5. 增量建议
- 给出进一步增强代码质量、工程可维护性、测试覆盖的建议（如单测、注释、类型声明、文档完善等）

#### 6. 推荐提交信息 (Recommended Commit Message)
- 为此变更生成简洁、准确且符合规范的提交信息，**提交信息使用英文**
- 基于当前分支名，如果分支名包含斜杠（如 `feat/item-definition`），则使用格式：`feat[item-definition] message`
- 如果分支名不包含斜杠，则使用常规格式

If English review requested:

#### 1. Tech Stack Inference
- Infer the primary programming language, frameworks, or libraries used based on the diff
- Briefly explain your reasoning (e.g., language syntax, imported libraries, project structure clues)

#### 2. Overview of Code Changes
- Summarize in concise technical language what the main changes in this diff are (e.g., bug fixes, feature additions, refactoring, configuration changes)
- Indicate the primary modules or business functionalities affected by these changes

#### 3. Code Quality & Clean Code Evaluation
- Thoroughly assess code style, naming conventions, comments and documentation, readability, maintainability, architecture and modularity, code duplication, etc.
- Identify error-prone code, unsafe patterns, inefficient implementations, anti-patterns, or parts that violate best practices
- Clearly specify the exact location and nature of each problem (line number, filename, code snippet, or sufficiently precise description)
- Provide actionable suggestions for fixes/refactoring/optimization, along with explanatory reasoning

#### 4. Major Issues and Risks
- Evaluate whether there are hard-to-detect logic bugs, unhandled exceptions, missing boundary checks, performance bottlenecks, or security vulnerabilities
- Clearly point out these suspicious parts and briefly explain their potential impact

#### 5. Incremental Suggestions
- Offer further suggestions to improve code quality, maintainability, and test coverage (such as unit tests, better comments, type annotations, or improved documentation)

#### 6. Recommended Commit Message
- Generate a concise, accurate, and conventional commit message for this change, **commit message must be in English**
- Based on the branch name, if it contains a slash (e.g., `feat/item-definition`), use the format: `feat[item-definition] message`
- If the branch name doesn't contain a slash, use the conventional format

### Step 5: Copy Commit Message to Clipboard
Extract commit message from section 6 and copy to clipboard:
- macOS: Use `pbcopy`
- Others: Use `pyperclip` or manual copy

## Error Handling

- **No staged changes**: Report that no staged changes found and suggest using `git add`
- **Language detection failure**: Default to English review
- **Clipboard failure**: Report error but provide commit message for manual copy
- **Commit message extraction failure**: Report error and provide full review for manual extraction

## Examples

### Example 1: Chinese Request with Feature Branch
**User input**: "帮我审查一下代码"
**Branch**: `feat/audio-support`
**Changes**: Added new audio codec files
**Review language**: Chinese
**Commit message**: `feat[audio]: add audio codec support for ESP32`

### Example 2: English Request with Bug Fix Branch
**User input**: "Review my code changes"
**Branch**: `fix/wifi-connection`
**Changes**: Fixed WiFi disconnect issue
**Review language**: English
**Commit message**: `fix(network): resolve WiFi disconnection on timeout`

### Example 3: Chinese Request with Refactor Branch
**User input**: "检查我的代码变更"
**Branch**: `refactor/time-manager`
**Changes**: Refactored TimeManager interface
**Review language**: Chinese
**Commit message**: `refactor(datetime): refactor TimeManager interface for better testability`

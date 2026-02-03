---
name: code-review-staged
description: "Comprehensive 6-section structured code review for git STAGED changes (git diff --cached) with smart context awareness. When user requests: 'review staged', '审查暂存', 'staged code review', 'staged CR', '暂存区审查', 'review cached'. Performs tech stack inference, change overview, code quality evaluation, risk analysis, incremental suggestions, and auto-generated commit message (copied to clipboard). ONLY reviews staged changes, NOT unstaged or all changes. Intelligently reads related files (headers, definitions, tests) to validate changes in context."
license: MIT
---

# When to Use This Skill

**ALWAYS invoke this skill when user wants to review STAGED git changes:**
- "review staged changes" / "review staged" / "staged code review"
- "审查暂存区" / "暂存区代码审查" / "审查暂存的代码"
- "staged CR" / "review cached changes"
- "use code-review-staged skill" / "使用 code-review-staged"
- "review my staged code" / "check staged changes"

**This skill is specifically for STAGED changes (git diff --cached):**
- Only reviews changes that have been `git add`ed to staging area
- Does NOT review unstaged changes or all changes
- Provides **structured 6-section comprehensive analysis** with actionable suggestions

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
- **CRITICAL: Commit message MUST be a SINGLE LINE, maximum 72 characters**
- **NO multi-line commit messages - summarize all changes in ONE concise sentence**
- Commit message should be a high-level summary, not a detailed list
- Commit message MUST be concise, accurate, and in English
- Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

## Clipboard Support

### macOS
- **REQUIRED**: Use `pbcopy` command to copy commit message to clipboard
- Commit message from section 6 is automatically extracted and copied
- This is a mandatory step - the commit message MUST be copied to clipboard after review generation

### Other Systems
- Use `pyperclip` library if available
- Fall back to manual copy if clipboard tools unavailable
- IMPORTANT: Commit message must still be clearly displayed for manual copying

# Code Review for Staged Changes

Perform comprehensive code review for git STAGED changes (`git diff --cached`) with automatic language detection and commit message generation.

## Usage

When user requests to review staged changes, invoke this skill.

**Example requests:**
- "Review my staged changes"
- "审查暂存区的代码"
- "Staged code review"
- "帮我审查暂存的代码"
- "Use code-review-staged skill to review"

## Technical Requirements

- **Working directory**: Git repository root
- **Git operations**:
  - `git diff --cached` - View staged changes
  - `git rev-parse --abbrev-ref HEAD` - Get current branch name
- **File operations**:
  - `read_file` - Read related files for context (headers, definitions, etc.)
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

### Step 2: Smart Context Retrieval (Optional but Recommended)
Analyze the `diff` output to determine if external context is needed for a high-quality review.
- **When to read context**:
    - If a function signature changes, check its usages or definition.
    - If a class inherits from a base class not in diff, read the base class definition.
    - If a variable type is unclear, check its declaration.
    - If a config value changes, check where it's consumed if the impact is ambiguous.
    - **Header/Source Pairing**: For C/C++, always check the corresponding `.h` or `.cpp` file if one is modified.
    - **Tests**: Check if existing tests need updates or if new tests are consistent with existing patterns.
- **How to read**: Use the `read_file` tool.
- **Constraints**:
    - **Limit Scope**: Read only 1-3 directly related files. Do not scan the whole directory.
    - **Relevance**: Only read files that are strictly necessary to validate the correctness of the staged changes.
    - **Efficiency**: If the file is huge, read only relevant sections (using `start_line`/`end_line` if possible) or search within it.

### Step 3: Get Current Branch
```bash
git rev-parse --abbrev-ref HEAD
```
Determine current branch name for commit message formatting.

### Step 4: Detect Language
Analyze user's input to determine review output language:
- Contains Chinese characters → Chinese review
- Only English → English review
- Commit message always in English

### Step 5: Perform Code Review

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
- **必须是单行，最多72个字符，不要多行**
- **用一句话高度概括所有变更，不要列举细节**
- 基于当前分支名，如果分支名包含斜杠（如 `feat/item-definition`），则使用格式：`feat[item-definition] message`
- 如果分支名不包含斜杠，则使用常规格式

**[IMPORTANT: After generating the commit message, MUST immediately copy it to clipboard using `echo -n "message" | pbcopy` on macOS - use `-n` flag to avoid trailing newline]**

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
- **MUST be a SINGLE LINE, maximum 72 characters - NO multi-line messages**
- **Provide a high-level summary of all changes in ONE sentence, do NOT list individual changes**
- Based on the branch name, if it contains a slash (e.g., `feat/item-definition`), use the format: `feat[item-definition] message`
- If the branch name doesn't contain a slash, use the conventional format

**[IMPORTANT: After generating the commit message, MUST immediately copy it to clipboard using `echo -n "message" | pbcopy` on macOS - use `-n` flag to avoid trailing newline]**

### Step 6: Copy Commit Message to Clipboard (MANDATORY)
**CRITICAL: This step is REQUIRED and MUST be executed after generating the code review.**

Extract commit message from section 6 and copy to clipboard:
- **IMPORTANT: Trim all leading/trailing whitespace (spaces, newlines, tabs) before copying**
- macOS: Use `echo -n "commit message" | pbcopy` (the `-n` flag prevents trailing newline)
- Alternative: `printf '%s' "commit message" | pbcopy`
- Others: Use `pyperclip` with `.strip()` applied to the message

**Example:**
```bash
# Correct - no trailing newline
echo -n "feat[audio]: add audio codec support" | pbcopy

# Wrong - will include trailing newline
echo "feat[audio]: add audio codec support" | pbcopy
```

**Do NOT skip this step - the commit message must be copied to clipboard automatically.**

## Error Handling

- **No staged changes**: Report that no staged changes found and suggest using `git add`
- **Language detection failure**: Default to English review
- **Clipboard failure**: Report error prominently, but STILL provide commit message for manual copy
- **Commit message extraction failure**: Report error and provide full review for manual extraction

**Note: Clipboard operation is a critical requirement. If automated clipboard copy fails, the commit message MUST still be displayed clearly for manual copying.**

## Examples

### Example 1: Chinese Request with Feature Branch
**User input**: "审查暂存区的代码"
**Branch**: `feat/audio-support`
**Changes**: Added new audio codec files (staged)
**Review language**: Chinese
**Commit message**: `feat[audio]: add audio codec support for ESP32`

### Example 2: English Request with Bug Fix Branch
**User input**: "Review my staged changes"
**Branch**: `fix/wifi-connection`
**Changes**: Fixed WiFi disconnect issue (staged)
**Review language**: English
**Commit message**: `fix(network): resolve WiFi disconnection on timeout`

### Example 3: Explicit Skill Invocation
**User input**: "Use code-review-staged skill to review my code"
**Branch**: `refactor/time-manager`
**Changes**: Refactored TimeManager interface (staged)
**Review language**: English
**Commit message**: `refactor(datetime): refactor TimeManager interface for better testability`


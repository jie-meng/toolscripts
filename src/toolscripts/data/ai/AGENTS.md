# Coding Principles

Universal guidelines that apply to all my projects.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them—don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
- Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it—don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

- Transform tasks into verifiable goals:
  - "Add validation" → "Write tests for invalid inputs, then make them pass."
  - "Fix the bug" → "Write a test that reproduces it, then make it pass."
  - "Refactor X" → "Ensure tests pass before and after."
- For multi-step tasks, state a brief plan before starting.
- Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Core Principles

- **Clarity over cleverness.** Code is read far more often than it is written. Prefer straightforward, boring solutions. If a piece of code needs a comment to explain *what* it does, rewrite it so it doesn't.
- **Single Responsibility.** Every function, class, and module should do one thing well. If you struggle to name it, it's probably doing too much.
- **Small, focused changes.** Each commit or PR should address one concern. Mixing refactors, features, and bug fixes in a single change makes review and rollback harder.
- **Fail fast, fail loudly.** Validate inputs at boundaries. Surface errors early with clear messages rather than letting bad state propagate silently.
- **No dead code.** Remove unused imports, variables, functions, and commented-out blocks. Version control is the archive.
- **DRY, but not at all costs.** Eliminate true duplication—identical logic serving the same purpose. Tolerate similar-looking code when the concepts are different and may diverge later. Premature abstraction is worse than repetition.

## 6. Naming & Readability

- Use descriptive, intention-revealing names. `remaining_retries` beats `r`. `is_valid_email()` beats `check()`.
- Booleans should read as true/false propositions: `is_ready`, `has_permission`, `should_retry`.
- Avoid abbreviations unless they are universally understood in the domain (`url`, `id`, `http`).
- Functions that return values should describe what they return. Functions that perform actions should describe the action.

## 7. Error Handling

- Handle errors at the appropriate level—where you have enough context to do something meaningful.
- Never swallow exceptions silently. At minimum, log them.
- Prefer specific error types over generic ones. Catch what you expect, let the rest propagate.
- Error messages should tell the user (or developer) what went wrong and, when possible, what to do about it.

## 8. Dependencies

- Prefer the standard library. Every external dependency is a liability—it can break, go unmaintained, or introduce vulnerabilities.
- When a dependency is necessary, pin versions and understand what you're pulling in.
- Wrap third-party APIs behind your own interfaces so they can be replaced.

## 9. Testing

- Write tests that verify *behavior*, not implementation details. Tests that break on every refactor aren't protecting you—they're slowing you down.
- Test edge cases and error paths, not just the happy path.
- Keep tests fast and independent.

## 10. Code Organization

- Keep files short. If a file exceeds ~300 lines, consider whether it has a natural split.
- Group related functions together. Separate public interface from internal helpers.
- Avoid deep nesting. Extract early returns and guard clauses to flatten control flow.

## 11. Git & Version Control

- **Always write commit messages in English.** This ensures a universally readable history for any developer, regardless of their native language.
- **Follow standard commit message formatting.** Use the imperative mood in the subject line (e.g., "Add feature" instead of "Added feature" or "Adds feature"). Keep the subject line concise (under 50 characters) and do not end it with a period.
- **Explain the "why", not the "how".** Use the commit body to explain the context, the problem being solved, and why this specific solution was chosen. The code already shows *how* it was done.
- **Keep commits atomic.** Each commit should represent a single logical change. Don't mix refactoring, bug fixes, and new features in a single commit.

## 12. Communication

- Respond in the same language the user is using.
- Be direct. State what you did, why, and any trade-offs.
- When uncertain, say so—and explain what information would resolve the uncertainty.

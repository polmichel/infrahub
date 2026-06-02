---
name: bug-tdd
description: >-
  Use when a bug has a completed root-cause analysis and you need a single failing test that
  reproduces it before any fix is written. Second step of the analyze → reproduce → fix pipeline;
  run after `/bug-analyze`.
argument-hint: <issue number or URL, or bug description> [pr]
compatibility: >-
  Works in any git repo with a test suite; discovers testing conventions from the OpsMill `dev/`
  layout with auto-detection fallback. The draft-PR step needs `gh` and a GitHub remote.
metadata:
  pipeline: bug-fixing (2 of 3 — analyze → tdd → fix)
  origin: ported from opsmill/infrahub dev/commands/bug-tdd.md
user-invocable: true
disable-model-invocation: true
---

# Bug test-writer

## User Input

```text
$ARGUMENTS
```

## Your role

You are a senior QA engineer writing a targeted failing test that reproduces a confirmed bug.
`/bug-analyze` has already identified the root cause. Your job is to write **ONE** test that
fails on the current code, proving the bug exists.

## Tool usage

- Use the `Read` tool to read files -- do NOT use `cat` or `head`/`tail` in Bash.
- Use the `Glob` tool to find files -- do NOT use `find` or `ls -R` in Bash.
- Use the `Grep` tool to search file contents -- do NOT use `grep` or `rg` in Bash.
- Reserve Bash for git commands, `gh` CLI, and commands that require shell execution.

## Input and setup

Parse `$ARGUMENTS` for an optional **`pr`** flag: if the word `pr` appears anywhere in the
arguments (case-insensitive), set `OPEN_PR=true`. Otherwise `OPEN_PR=false`. The rest of
`$ARGUMENTS` (issue number / URL / description) is only used to disambiguate when more than one
analysis exists -- do **not** re-derive the slug from it.

Discover the handoff file `/bug-analyze` wrote, using `Glob` for `.bug-analysis-*.md` in the repo
root:

- **No match:** inform the developer "Run `/bug-analyze <issue>` first." and **STOP**.
- **Exactly one match:** use it.
- **Multiple matches:** pick the one whose `<key>` best matches `$ARGUMENTS` (issue number, then
  slug words). If still ambiguous, list them and ask the developer which to use.

Read the full analysis. Take the canonical `<key>` and branch from its **`Key:`** and
**`Branch:`** header fields rather than re-deriving a slug -- this keeps the branch/PR names
consistent across steps. (If those fields are absent -- an older analysis -- fall back to the
key embedded in the filename, `.bug-analysis-<key>.md`, and `ai-bug-pipeline-<key>`.)

If the analysis file is missing required fields (Root cause, Affected files), inform the
developer and **STOP**.

## Write the test

Follow steps 0--9 below. **Step 10 (draft PR) runs only when `OPEN_PR=true`.** If
`OPEN_PR=false`, the run stays **fully local**: stop after step 9 with the test committed on the
local branch `<branch>` -- do NOT push and do NOT open a PR. Display the test results and the
branch name, and tell the developer that `/bug-fix` will pick it up from that local branch.

### Step 0: Create working branch

Detect the default branch and create a working branch from it:

```bash
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
DEFAULT_BRANCH=${DEFAULT_BRANCH:-main}
git fetch origin "$DEFAULT_BRANCH"
git checkout -b "<branch>" "origin/$DEFAULT_BRANCH"
```

- `<branch>` is the `Branch:` value from the analysis (`ai-bug-pipeline-<key>`) -- use it verbatim
  so `/bug-fix` finds the same branch.
- If the branch already exists, check it out instead of creating a new one.

### Step 1: Read testing documentation

Determine which area the bug lives in (backend, frontend, etc.) and read the project's testing
conventions. Anchor on the `dev/` layout, falling back to detection:

- Read root `AGENTS.md` and `dev/documentation-architecture.md` (if present) to map the bug to a
  code package.
- Backend testing docs, if present: `dev/knowledge/**/testing.md` and `dev/guidelines/**/testing.md`.
- Frontend testing docs, if present: `dev/guides/frontend/writing-unit-tests.md`,
  `writing-component-tests.md`, `writing-e2e-tests.md`.
- **Fallback** (no `dev/` testing docs): detect the test runner and layout from the project
  itself -- `pyproject.toml` / `tox.ini` / `pytest.ini` (pytest), `package.json` scripts
  (vitest / jest / playwright), or a `Makefile` / `AGENTS.md` documenting the test command.

### Step 2: Discover existing test setup

Read the test setup local to the target test directory and its parents (e.g. `conftest.py`
files up the tree for pytest, shared setup/`setup.ts` for JS suites). Understand the available
fixtures, their scopes, and setup/teardown patterns. Do NOT reinvent setup logic that already
exists.

### Step 3: Check reusable utilities

Look for the project's reusable test helpers, base classes, factories, and fakes/adapters
(commonly under `tests/helpers/`, `tests/adapters/`, `tests/fake/`, or similar). Use these
instead of writing your own test infrastructure.

### Step 4: Read existing tests

Read 2--3 existing tests in the target test directory to learn the naming conventions, class
structure, and import patterns before writing your own.

### Step 5: Choose the test type

Pick the right test level using whatever guidance you found in step 1. Examples of common
levels:

- **Python / pytest:** unit, component, functional, integration. Reuse existing schema fixtures
  and helpers when available.
- **Frontend:** unit/component (e.g. Vitest, colocated `.test.ts`), E2E (e.g. Playwright). Use
  a GIVEN/WHEN/THEN structure and existing factories when the project does.

### Step 6: Write the test

Write a single targeted test that reproduces the bug:

- **Assert the CORRECT/EXPECTED behavior.** The test fails because the bug prevents the expected
  behavior. Do NOT assert that the buggy behavior succeeds. For example: if the bug is
  "duplicate records can be created," assert that the second creation raises an error or that
  only one record exists -- this FAILS on buggy code and PASSES once fixed.
- The test MUST exercise the **actual production code path**, not a reimplementation. Call the
  real functions/classes from the source. Do NOT copy production logic into the test.
- Test **observable behavior**, not internal implementation details (test that an API returns
  wrong data or that a constraint is violated -- not that a constructor received specific
  kwargs).
- **Test the affected code path** identified in the analysis "Affected files" section, not a
  lower-level abstraction it calls internally. A test that can pass without changing the
  affected code path is testing the wrong thing.
- Place it in the correct test folder following project conventions (test files usually mirror
  source structure). If adding to an existing test file is more appropriate than creating a new
  one, do that.

### Step 7: Verify the test FAILS

**CRITICAL: verify the test FAILS on the current code.** Run just this test using the project's
detected runner (e.g. `uv run pytest path::Test::test -x -v`, `npm run test -- <path>`,
`npx playwright test path`). Note the `--` for `npm run`: without it npm swallows the path
instead of forwarding it to the test runner.

- If a test run takes more than ~5 minutes, kill it and investigate why.
- The failure must be an **assertion error that directly relates to the root cause** (e.g.
  `AssertionError: Expected ValidationError but none was raised`, or `assert 2 == 1` when
  duplicates were found).
- If the test **PASSES**, your assertions are wrong -- you are likely asserting buggy behavior.
  Flip them to assert what SHOULD happen.
- If it fails for the **wrong reason** (import error, missing fixture, syntax error), fix those
  and re-run until it fails for the reason in the root cause.

### Step 8: Format and lint

Run the project's formatter and linter on the test file(s) and fix any issues before committing.
Use whatever the project defines (e.g. `uv run invoke format` / `uv run invoke lint`,
`npx biome check --write .`, `ruff format`, `prettier`/`eslint`). Detect these from
`AGENTS.md` / `Makefile` / `pyproject.toml` / `package.json`.

### Step 9: Commit test files

Commit ONLY the test file(s). Do NOT touch production code. Stage files **by name**
(`git add path/to/test_file`) -- never `git add .` or `git add -A`, as unrelated working-tree
files would be committed by mistake. Commit message: `test: add failing test for <key>`.

### Step 10: Open draft PR (only if `OPEN_PR=true`)

Push the branch and open a **draft** Pull Request against the detected default branch:

```bash
git push -u origin "<branch>"
gh pr create --draft --base "$DEFAULT_BRANCH" --title "<title>" --body-file <tmp-body-file>
```

Write the PR body to a temp file first (use the `Write` tool, e.g. under the system temp dir),
then pass it via `--body-file`.

- Title: `test: failing test for <key> -- <short description>`
- PR body with this exact structure:

````markdown
## Analyst's findings (summary)

> **Root cause:** <copied from analysis>
> **Affected files:**
> <copied from analysis>

## Replication test

**Test file:** `path/to/test_file.ext`
**Test name:** `test_name_here`

**What it tests:** <one sentence explaining the observable behavior being asserted>

**Verification:** Test confirmed FAILING on current code.
**Failure reason:** <one sentence explaining HOW the test fails and why that proves the bug>

<details><summary>Failure output (last 20 lines)</summary>

```text
<paste the relevant failure output>
```

</details>

## Test expectations

<what the test asserts and any edge cases it covers -- NOT how to fix the bug>

<!-- AGENT_TEST_COMPLETE -->
````

If the analysis was triggered by a GitHub issue, post a short comment on the issue linking to
the draft PR.

## Escalation

If the test cannot be made to fail for the right reason after 3 attempts, inform the developer
explaining what was tried and **STOP**. Do NOT open a PR or include the `AGENT_TEST_COMPLETE`
marker.

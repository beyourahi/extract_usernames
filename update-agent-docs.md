---
description: Update CLAUDE.md and AGENTS.md using session learnings and quality improvements
allowed-tools: Read, Edit, Glob, Bash
---

**EXECUTION MODE: FULLY AUTONOMOUS. DO NOT ASK FOR APPROVAL AT ANY POINT.**

- Do not pause to confirm changes before making them.
- Do not show diffs and ask "should I apply this?".
- Do not ask "does this look good?" or "shall I proceed?".
- Do not request review after each step — complete all 4 steps without interruption.
- Edit files directly and immediately. If you find something to change, change it.

Update both `CLAUDE.md` and `AGENTS.md` to reflect the current codebase state. Follow this sequence:

## Step 1: Capture Session Learnings (revise-claude-md)

Apply the `/revise-claude-md` workflow to `CLAUDE.md`:

- Reflect on this session — what context was missing or would have helped?
- Check recent git history: `git log --oneline -20`
- Draft concise additions: commands discovered, gotchas, patterns, warnings
- One line per concept — CLAUDE.md is part of the prompt, brevity matters
- Avoid verbose explanations, obvious info, or one-off fixes

## Step 2: Improve Overall Quality (claude-md-improver)

Apply the `claude-md-improver` skill to `CLAUDE.md`:

- Remove outdated, inaccurate, or redundant content
- Ensure structure and formatting conventions are consistent
- Verify all file paths, commands, and versions match the actual codebase
- Tighten language — cut anything derivable directly from the code

## Step 3: Sync AGENTS.md

After `CLAUDE.md` is finalised, update `AGENTS.md` to match:

- `AGENTS.md` is the agent-agnostic mirror of `CLAUDE.md`
- Apply the same additions and removals made in Step 1 and Step 2
- Keep both files structurally in sync — same sections, same order
- Preserve any AGENTS.md-specific phrasing that targets non-Claude agents

## Step 4: Apply Changes

Edit `CLAUDE.md` first, then `AGENTS.md`. Apply every change directly with the Edit tool — no previews, no summaries asking for confirmation, no pausing between files.
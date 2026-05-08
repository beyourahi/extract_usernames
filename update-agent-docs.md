---
description: Update CLAUDE.md and AGENTS.md using session learnings and quality improvements
allowed-tools: Read, Edit, Glob, Bash
---

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

Apply all changes immediately. Edit `CLAUDE.md` first, then `AGENTS.md`. No previews, no approval needed.
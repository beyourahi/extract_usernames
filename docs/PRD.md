# Web Port PRD: extract_usernames → Username Extractor

## Overview

Port the existing `extract_usernames` Python CLI to a web application — publicly named **Username Extractor** — built on SvelteKit, Bun, Tailwind CSS v4, and Cloudflare Workers. The CLI becomes a polished web UI that is the new front door for the tool. The dual-engine OCR pipeline (`glm-ocr:bf16` via Ollama + EasyOCR via PyTorch) collapses to a single Workers AI vision model: **`@cf/moonshot/kimi-k2.6`**. All persistent state moves from the local filesystem to Cloudflare primitives (D1, R2, KV, Durable Objects, Queues).

## Identity and placement

The web port is a discrete product with its own identity, separate from the legacy Python repository it replaces.

| Field | Value |
|---|---|
| Display name | Username Extractor |
| Slug / URL segment | `username-extractor` |
| Repo directory | `/Users/beyourahi/Desktop/projects/username-extractor` (new; does **not** overwrite the existing `extract_usernames` Python repo) |
| `package.json` name | `"username-extractor"` |
| Tagline | *Screenshots in, usernames out.* |
| Card description | Extract Instagram usernames from batches of profile screenshots, validate them, and sync clean handles straight to Notion. |
| Card tags (4) | `Instagram OCR` · `Bulk Screenshot Parsing` · `Username Validation` · `Notion Sync` |
| Public placement | Listed on `/tools` on both **beyourahi.com** and **dropoutstudio.com**, alongside `order-processor` and `invoice-generator`. |
| Production routes | `beyourahi.com/tools/username-extractor`, `dropoutstudio.com/tools/username-extractor` |
| Naming pattern | Conforms to the established `[noun]-[verb]` kebab-case family pattern set by the sibling tools. |

## Problem statement

The current tool is a Python CLI that runs locally and depends on a heavyweight ML stack: PyTorch (>=2.0.0), EasyOCR (>=1.7.0), OpenCV (>=4.8.0), Pillow with `pillow-avif-plugin`, and a local Ollama server hosting `glm-ocr:bf16`. Installation requires platform-specific setup (Homebrew, apt, dnf, pacman, manual Windows downloads), GPU configuration (CUDA / ROCm / MPS / CPU), and a 700MB+ PyTorch install. Configuration lives in `~/.config/extract-usernames/config.json`. Cumulative lead state lives in markdown files inside an output directory and is re-parsed via regex on every run.

This setup blocks:

- Use from any machine without Python + Ollama + GPU
- Sharing of the tool with non-technical operators
- Layering of new features (multi-user, scheduled crawls, webhook ingestion, browser-based capture) without rewriting the runtime
- Observability into per-job state
- Any access pattern that is not "open a terminal on the developer's laptop"

The web port resolves all of the above by moving the pipeline to Cloudflare Workers with a SvelteKit frontend, while preserving the algorithmic core (consensus rules where still applicable, Levenshtein near-duplicate detection, Notion smart-dedup scoring).

## Goals and non-goals

### Goals

- The web app is the new primary interface. The CLI may continue to exist locally but is no longer the entry point for new users or features.
- Preserve existing extraction quality and deduplication behavior. Pure-function logic ports unchanged.
- Preserve the existing Notion integration contract: schema autodetect, batch create, dedup by Instagram URL, archive losers (do not hard-delete).
- Architect for forward growth: multi-user accounts, scheduled extraction, webhook ingestion, and browser-based capture should layer on without rework.
- Deploy on Cloudflare Workers via `@sveltejs/adapter-cloudflare`.

### Non-goals

- Reproducing the CLI's terminal output format on the web.
- Preserving the dual-engine OCR architecture. Replaced by a single Workers AI vision model.
- Preserving the fixed crop region `image[165:255, 100:-100]`. Replaced by whole-image OCR.
- Building a marketing site, pricing page, or landing page.
- Building any feature not present in the current CLI surface in v1 (with the explicit additions enumerated in [Functional requirements](#functional-requirements)).

## Users and use cases

Single-operator lead generation. The primary user is the project author running batches of 10–500 Instagram screenshots per session to extract usernames, validate them, and push verified leads to a Notion CRM database. Secondary users (future) are collaborators granted access via Cloudflare Access.

Primary use cases:

1. Upload a batch of Instagram screenshots → receive a list of verified usernames with confidence tiers.
2. Push verified usernames to Notion as new pages with auto-deduplication.
3. Preview a deduplication pass on Notion before committing.
4. Review the lifetime history of extracted leads across sessions.
5. Adjust extraction defaults (diagnostics on/off) and Notion credentials.
6. Run a standalone Notion deduplication pass on the existing database.

## Current state

### Repository structure

Root: `/Users/beyourahi/Desktop/projects/extract_usernames`

Source modules (excluding `_archive/`):

- `extract_usernames/cli.py` (275 lines) — Click CLI shell, flag parsing, orchestration
- `extract_usernames/cli_merge_duplicates.py` (126 lines) — standalone dedup CLI, not registered in `[project.scripts]` (invokable only via `python -m extract_usernames.cli_merge_duplicates`)
- `extract_usernames/config.py` (130 lines) — JSON config manager
- `extract_usernames/main.py` (155 lines) — pipeline wrapper that imports the archived extractor
- `extract_usernames/ocr/prompts.py` (264 lines) — Click setup wizard (despite the path, no OCR prompts here)
- `extract_usernames/integrations/instagram_validator.py` (147 lines) — HTTP-based Instagram profile existence check with `tenacity` retry
- `extract_usernames/integrations/notion_manager.py` (398 lines) — Notion REST client with schema autodetect
- `extract_usernames/integrations/notion_sync.py` (179 lines) — sync orchestrator
- `extract_usernames/integrations/notion_deduplicator.py` (302 lines) — smart dedup with scoring algorithm

Critical runtime dependency: `extract_usernames/_archive/extract_usernames.py` (1375 lines). Despite the folder name, `main.py:54` imports from it at runtime: `from ._archive import extract_usernames as extractor`. This file contains all OCR/VLM/preprocessing/consensus/file-IO logic and is the runtime, not dead code.

### Dependency classification for Workers

| Dependency | Workers verdict | Reason |
|---|---|---|
| `torch>=2.0.0`, `torchvision>=0.15.0` | Blocker | Native binaries, ~700MB, no V8 port, no GPU in Workers |
| `easyocr>=1.7.0` | Blocker | Requires PyTorch + downloads CRAFT weights to filesystem cache |
| `opencv-python>=4.8.0` | Blocker in current form | Native C++. Not needed once preprocessing is dropped |
| `Pillow>=10.1.0`, `pillow-avif-plugin` | Replace | Native libavif. Use Cloudflare image transforms or accept PNG |
| `numpy>=1.24.0` | Drop | Only consumed by OpenCV preprocessing |
| `ollama>=0.1.0` | Replace | Localhost-only; swap to Workers AI binding |
| `notion-client>=2.2.1` | Replace 1:1 | `@notionhq/client` JS SDK |
| `requests`, `urllib3`, `tenacity` | Replace | Native `fetch` + manual exponential backoff |
| `python-dotenv` | Remove | Wrangler vars + Workers Secrets |
| `click>=8.1.0` | Remove | UI moves to SvelteKit forms |
| `tqdm` | Remove | Browser progress UI via WebSocket |
| `multiprocessing.Pool` | Replace | Cloudflare Queues + per-job Durable Object |

### CLI surface to preserve

From `extract_usernames/cli.py:55-69`:

1. positional `input_path`
2. `--output / -o PATH`
3. `--no-vlm`
4. `--vlm-model MODEL`
5. `--diagnostics`
6. `--reconfigure` with sub-choice `all | directories | extraction | notion | cancel`
7. `--initial-setup` (hidden)
8. `--show-config`
9. `--reset-config`
10. `--notion-sync` / `--no-notion-sync`
11. `--deduplicate` / `--no-deduplicate`
12. `--dry-run-dedup`
13. `--version`

From `extract_usernames/cli_merge_duplicates.py:22-28`: `--token`, `--database-id`, `--keep-strategy oldest|newest`, `--dry-run`, `--use-config`.

Interactive flow on first run: `prompts.run_initial_setup` in `extract_usernames/ocr/prompts.py` — four grouped sections (Directories, Extraction, Notion, Notion sub-settings).

### Persistent state today

- `~/.config/extract-usernames/config.json` — settings, including the Notion token
- `<output_dir>/verified_usernames.md` — cumulative; read on every run via regex in `_archive/extract_usernames.py:150-167`
- `<output_dir>/needs_review.md` — cumulative
- `<output_dir>/extraction_report.md` — overwritten each run
- `<output_dir>/cropped_usernames_images/<stem>_crop.avif` — per-image archive, always-on
- `<output_dir>/../ocr_debug/*` — diagnostic artifacts when `--diagnostics`
- External: the user's Notion database

### Portable logic (ports to TypeScript unchanged)

- `clean_username`, `is_valid_instagram_format`, `has_unusual_pattern` (`_archive/extract_usernames.py:470-522, 723-745`)
- `levenshtein_distance`, `find_similar_existing` (`:748-784`)
- `_is_dotted_sibling`, `_find_dotted_sibling`, `_find_confusion_correction`, `_find_confusion_match` (`:256-363`)
- `intelligent_consensus_validator` (`:629-704`) — retained for optional future dual-engine fallback only; not used in v1 single-engine path
- `classify_status` (`:707-720`)
- Confidence-scoring rules from `vlm_primary_extract` (`:563-578`)
- `NotionDeduplicator._score_username` and the full dedup algorithm
- `load_usernames_from_markdown` (`notion_sync.py:24-69`)
- Notion schema autodetect and rate-limit logic from `notion_manager.py`

## Proposed solution

A SvelteKit application deployed to Cloudflare Workers. The user uploads a batch of screenshots; the app stores them in R2, enqueues per-image work onto Cloudflare Queues, and a consumer Worker calls Workers AI (`@cf/moonshot/kimi-k2.6`) to extract the username from each image. Per-image results stream to the browser via a per-job Durable Object that holds active job state and broadcasts over WebSocket. Finalized leads land in D1. Notion sync and deduplication run on demand, reusing the ported logic from the Python modules.

The cumulative markdown output files become D1 tables. The local JSON config becomes a D1 `user_settings` row. The AVIF crop archive becomes an R2 prefix (the format may shift to PNG; see [Open questions](#open-questions)).

## Functional requirements

### Extraction

**FR-1.** The user can upload one or more image files (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.webp`) via drag-and-drop or a file picker on `/`.
*Acceptance:* Uploading 50 valid images creates a job, redirects to `/jobs/[id]`, and shows a placeholder row per image within 2 seconds.

**FR-2.** The system processes each uploaded image through `@cf/moonshot/kimi-k2.6` using the existing prompt from `_archive/extract_usernames.py:547-552`.
*Acceptance:* For each image, a row is emitted with `username`, `confidence`, `status` (`verified` | `review` | `failed`), and `tier` (`HIGH` for confidence ≥95, `MED` for 85–94, `NULL` for review).

**FR-3.** The user sees per-image extraction progress in real time as each image completes.
*Acceptance:* Result rows appear in the UI within 500ms of the consumer Worker writing them to the per-job DO. No polling.

**FR-4.** The system detects near-duplicates against the user's lifetime lead history using Levenshtein distance ≤ 2.
*Acceptance:* When a newly extracted username is within edit-distance 2 of an existing lead, it is flagged with the matching username and the computed distance and routed to the review tier.

**FR-5.** The system detects exact duplicates against the user's lifetime lead history.
*Acceptance:* Usernames already present in the user's `leads` table are tagged `duplicate` and not re-inserted.

**FR-6.** Within a single batch, exact-duplicate usernames are collapsed to one row.
*Acceptance:* A batch with 5 images all yielding `someuser` produces 1 row, not 5.

**FR-7.** A failed extraction is recorded with the image filename and the failure reason.
*Acceptance:* If the vision model returns no parseable username or errors, the `job_items` row records `status: failed` and surfaces the underlying error.

### Job history

**FR-8.** The user can view the list of all past jobs at `/jobs`.
*Acceptance:* `/jobs` shows jobs reverse-chronologically with status, image count, verified count, and review count.

**FR-9.** The user can open any past job at `/jobs/[id]` and see the same result view as live.
*Acceptance:* `/jobs/[id]` for a completed job renders results from D1 with identical layout to the live view.

**FR-10.** *Removed.* No file output. All results live in D1 and are rendered in the UI; the URL field on each row is the canonical "shareable" representation.

**FR-11.** *Removed.* Job-level summary stats (image count, verified/review/failed/duplicate counts, elapsed time, model used, diagnostics flag) render as a summary panel on `/jobs/[id]` directly from D1. No downloadable report.

### Lifetime leads

**FR-12.** The user can view all extracted leads ever recorded at `/leads`.
*Acceptance:* `/leads` paginates the user's `leads` table, supports search by username substring, and supports filters by tier (HIGH / MED), Notion status (`added` / `duplicate` / `invalid` / `unconfigured` / `pending`), and review status.

**FR-13.** The user can manually mark a lead as archived (soft delete).
*Acceptance:* Archived leads no longer participate in dedup matching but remain visible with a filter toggle.

### Notion sync (automatic)

**FR-14.** The system automatically pushes verified leads to Notion as the final step of every job. There is no user-initiated "push to Notion" action for new jobs.
*Acceptance:* As each `job_items` row settles with `status: verified` (HIGH or MED tier), the consumer Worker runs the ported equivalent of `notion_sync.run_notion_sync` for that single handle against the user's configured Notion DB. On success, the resulting `notion_page_id` is written back to the corresponding `leads` row and broadcast to the browser via the per-job DO so the UI badge flips from ⏳ Pending to ✓ Added in real time.

**FR-15.** Instagram validation runs inline in the pipeline for every verified handle before the Notion call.
*Acceptance:* Each verified candidate hits `https://www.instagram.com/<u>/` (or the cache; see FR-16). A 200 response gates Notion creation. A 404 stops the Notion call and the `leads` row records `notion_status: 'invalid'`. A persistent rate-limit failure records `notion_status: 'pending'` and the row is retried on the next job or by a manual "Retry sync" action on `/leads`.

**FR-16.** Instagram validation results are cached in KV for 7 days, keyed by lowercase username.
*Acceptance:* A second extraction within 7 days for the same username does not re-hit Instagram.

**FR-17.** Review-tier and failed handles are **not** auto-pushed to Notion. They remain in D1 with `notion_status: null` and surface in the UI under filters on `/jobs/[id]` and `/leads`.
*Acceptance:* From `/leads`, the user can promote a review-tier handle by clicking "Send to Notion" on that row, which runs the same validation + create flow used by FR-14/FR-15 for that single handle.

**FR-18.** Notion deduplication runs automatically as part of every job after all per-image Notion creates settle.
*Acceptance:* The ported `NotionDeduplicator.deduplicate` runs once per job over the user's full Notion DB (not just this batch's additions), archiving losers and reporting `duplicate_groups`, `duplicates_found`, `duplicates_removed`, `errors` into the job summary panel.

**FR-19.** A standalone Notion dedup action is available on `/settings` as a maintenance tool for cleaning historical data, with dry-run preview and `oldest`/`newest` keep-strategy options (parity with `cli_merge_duplicates.py`).
*Acceptance:* `/settings → Notion → Run dedup now` triggers the same operation as FR-18 on demand. `?dry_run=1` returns the proposed archive list without committing.

### Settings

**FR-20.** The user can view current settings at `/settings`.
*Acceptance:* `/settings` shows extraction defaults and Notion configuration with the token masked (first 10 chars + ellipsis, matching `config.py:122-128`).

**FR-21.** The user can update extraction defaults (diagnostics on/off) at `/settings`.
*Acceptance:* Saved settings apply to all subsequent jobs and persist in D1.

**FR-22.** The user can update Notion credentials (token, database ID) at `/settings`.
*Acceptance:* Saved credentials are validated against Notion (`databases.retrieve`) before persisting. Invalid credentials produce the existing helpful error text from `notion_manager.py:169-217`.

**FR-23.** The user can reset settings to defaults from `/settings`.
*Acceptance:* Reset restores the `DEFAULT_CONFIG` shape from `config.py:15-30` (web-relevant fields only — no input/output dirs).

**FR-24.** On first visit with no settings present, the user sees a first-run onboarding flow equivalent to `prompts.run_initial_setup`.
*Acceptance:* Modal walks Extraction defaults → Notion configuration with the same questions as the CLI wizard. The "Directories" section from the CLI is omitted (uploads replace directories).

### Job control

**FR-25.** The user can cancel an in-flight job from `/jobs/[id]`.
*Acceptance:* Cancellation stops further consumer Worker invocations for that job and marks the job `cancelled`. Already-completed items remain.

**FR-26.** The user can re-run an individual failed item.
*Acceptance:* "Retry" on a failed row re-enqueues that image and replaces the row in place when the new result arrives.

### Diagnostics

**FR-27.** The user can toggle diagnostics mode per job at upload time.
*Acceptance:* When enabled, the raw model response is saved to R2 (`debug/{job_id}/{stem}_response.txt`) and viewable inline from the job results UI.

### Legacy import

**FR-28.** The user can import an existing `verified_usernames.md` file and/or scan an existing Notion database into the `leads` table.
*Acceptance:* `POST /api/import/legacy` ingests the supplied markdown via the ported `load_usernames_from_markdown` and the supplied Notion DB via `notion_manager.get_all_existing_usernames`. Re-running the import does not create duplicate rows (UNIQUE constraint on `(user_id, username)`).

## Non-functional requirements

### Performance

- **NFR-1.** Time-to-first-result for a 10-image batch from upload click to first result row visible: ≤ 8 seconds.
- **NFR-2.** End-to-end processing for 50 images: ≤ 120 seconds.
- **NFR-3.** WebSocket message latency from DO write to browser render: ≤ 500ms p95.
- **NFR-4.** `/jobs` and `/leads` list pages render with Largest Contentful Paint ≤ 1.5s on simulated 4G.

### Accessibility

- **NFR-5.** All interactive surfaces meet WCAG 2.2 AA. Keyboard navigation is fully supported for upload, settings, job list, job detail, and Notion dedup flows.

### Security

- **NFR-6.** The Notion integration token is encrypted at rest in D1 using a Workers Secret as the encryption key. Plaintext token never leaves the encryption helper boundary.
- **NFR-7.** Access to the deployed application is restricted via Cloudflare Access. No anonymous access in production.
- **NFR-8.** R2 objects are not publicly addressable. All access goes through the Worker, which authorizes against the requesting user.

### Observability

- **NFR-9.** Every job emits structured logs at `job_created`, `item_queued`, `item_started`, `item_completed`, `item_failed`, `job_completed`, `job_cancelled`, each with `job_id`, `user_id`, and timing.
- **NFR-10.** Workers AI errors are captured with the source image's R2 key for replay.

### Compatibility

- **NFR-11.** Supports the last two stable versions of Chrome, Safari, Firefox, and Edge on desktop and mobile.
- **NFR-12.** No reliance on browser features unavailable in Safari iOS.

### Cost containment

- **NFR-13.** A per-user daily image quota is enforced (default 1000/day) to bound Workers AI cost. Exceeding the quota returns a clear error and blocks further enqueues for the day.

## Technical architecture

### Stack

- Runtime/package manager: Bun (local dev)
- Framework: SvelteKit with Svelte 5 runes (`$state`, `$derived`, `$props`, `$effect`)
- Styling: Tailwind CSS v4 (CSS-first config via `@import 'tailwindcss'`; no `tailwind.config.*`, no `postcss.config.*`)
- Deployment: Cloudflare Workers via `@sveltejs/adapter-cloudflare`
- Auth: Cloudflare Access in front of the Worker

### Cloudflare primitive assignments

The application runs entirely on Cloudflare. **D1** is the relational store (user data, jobs, leads). **R2** is the blob store (uploaded screenshots, diagnostic artifacts). Both are confirmed primary choices. The full service inventory:

| State / capability | Primitive | Justification |
|---|---|---|
| User identity | **Cloudflare Access** (JWT) | Federated; zero auth code in the app |
| User settings (incl. encrypted Notion token) | **D1** `user_settings` | Relational, one row per user |
| Job metadata | **D1** `jobs` | Status, model, diagnostics flag, timestamps |
| Per-image results | **D1** `job_items` | Replaces in-memory result list passed to `append_to_files` |
| Lifetime leads | **D1** `leads` | Replaces cumulative `verified_usernames.md` regex scan; index `(user_id, username)` |
| Raw uploaded images | **R2** `raw/{job_id}/{filename}` | Blob, expirable via Lifecycle rules + Cron Trigger sweep |
| Diagnostic artifacts | **R2** `debug/{job_id}/*` | Optional per-job, gated by FR-27 |
| Thumbnail rendering | **Cloudflare Image Resizing** (Workers integration via `fetch` with `cf.image` options) | On-the-fly resize/format conversion of R2 originals; resolves [Open question 9](#open-questions) (store PNG, serve AVIF on read) |
| Job progress + WebSocket fan-out | **Durable Object** (one per job) | Single-writer + ordered broadcast |
| Per-image work queue | **Cloudflare Queues** | Replaces `multiprocessing.Pool` fan-out |
| Instagram validation cache | **Workers KV** with 7-day TTL, key `ig:exists:{lowercase_username}` | Eventual consistency acceptable; cuts external traffic |
| Vision inference | **Workers AI** via `env.AI` binding, model `@cf/moonshot/kimi-k2.6` | Single-engine OCR |
| Vision inference wrapper | **AI Gateway** in front of Workers AI | Per-request caching (identical image+prompt → cached result), unified rate limiting, full call logs for accuracy regression debugging, fallback routing if the primary model degrades — directly de-risks the open Kimi K2.6 benchmark (NFR/Risks). |
| Scheduled R2 expiration | **Cron Triggers** | Nightly sweep deletes `raw/{job_id}/*` objects older than the retention window (default 30 days per [Open question 5](#open-questions)) |
| Job metrics + time-series observability | **Workers Analytics Engine** | High-cardinality writes (`job_id`, `user_id`, status counts, latencies) without a SQL hot path; backs NFR-9 observability |
| Secrets (Notion-token encryption key, Access service token, Workers AI key if isolated) | **Workers Secrets** (`wrangler secret put`) | Never committed; encrypted at rest by the platform |

### Cloudflare services considered and not needed

| Service | Why not |
|---|---|
| **Hyperdrive** | D1 is the database; no external SQL pool to accelerate. |
| **Vectorize** | No embedding/similarity workload. Levenshtein on usernames is sub-millisecond in TS. |
| **Browser Rendering** (Puppeteer on Workers) | The app does not take screenshots itself; the user uploads them. Future "browser-side capture" is in [Out of scope](#out-of-scope). |
| **Service Bindings** | The whole app is one Worker plus one DO class and one Queue consumer; there are no second-Worker boundaries to bridge. |
| **Email Workers / Email Routing** | No transactional email (no signup, no notifications) in v1. Could revisit when collaborators are added. |
| **Turnstile** | Cloudflare Access already gates the app; no public surface for bot traffic. |
| **Cloudflare Pages** | Adapter is `@sveltejs/adapter-cloudflare` (Workers), not Pages. Pages adds no capability this app lacks. |
| **Cloudflare Containers** | Held as an escape hatch only if Kimi K2.6 fails the accuracy benchmark (see [Risks](#risks-and-mitigations)). Not in v1 deploy path. |
| **D1 Sessions API / read replicas** | Single-region read pattern; latency is not the bottleneck. |
| **Stream / Calls** | No video/audio. |
| **Workers for Platforms** | No multi-tenant dispatch needed. |

### Data flow

1. Browser POSTs multipart upload to `/api/jobs` (SvelteKit form action).
2. Action writes raw images to R2 at `raw/{job_id}/`, creates `jobs` and `job_items` rows in D1, enqueues one Queue message per image, returns `job_id`.
3. Browser navigates to `/jobs/[id]` and opens a WebSocket to the per-job DO.
4. Queue consumer Worker, for each message:
   a. Pulls image from R2.
   b. Calls `env.AI.run('@cf/moonshot/kimi-k2.6', { ... })` via AI Gateway with the existing prompt.
   c. Applies ported `clean_username`, `is_valid_instagram_format`, `has_unusual_pattern`, confidence scoring, tier classification.
   d. Looks up lifetime dedup via D1 (`SELECT … FROM leads WHERE user_id = ? AND username = ?` plus Levenshtein scan).
   e. Writes the `job_items` row and, if the result is `verified` (HIGH or MED), inserts the corresponding `leads` row with `ig_url = 'https://instagram.com/' || username`.
   f. If verified: validates against Instagram via cache-first KV lookup, then `fetch('https://www.instagram.com/<u>/')`. On 200, creates a Notion page using `@notionhq/client`, stores `notion_page_id` back on the `leads` row, and sets `notion_status: 'added'`. On 404, sets `notion_status: 'invalid'` and skips the Notion call. On configured-but-erroring Notion, sets `notion_status: 'pending'` for later retry. On missing credentials, sets `notion_status: 'unconfigured'`.
   g. Notifies the DO with the final per-item state (including Notion status).
5. DO broadcasts the item-completed event to all connected WebSocket clients. The UI flips the Notion badge live as each step settles.
6. When all items resolve, the consumer runs the ported `NotionDeduplicator.deduplicate` once over the user's full Notion DB, then the DO marks the job complete in D1 (with the dedup summary attached to the job row) and self-destructs.
7. Standalone Notion dedup (`/settings → Run dedup now`, with dry-run option) remains as a maintenance tool for cleaning historical state outside the per-job flow.

### Failure modes

- **Workers AI returns no parseable username** → item marked `failed`. Raw response stored only if diagnostics enabled.
- **Workers AI errors transiently** → automatic single retry; permanent failure marks item `failed`.
- **Queue consumer crashes mid-item** → message returns to queue per default Queue retry policy. Idempotency guard: skip processing if `job_items.status != 'pending'` at write time.
- **DO disconnects from client** → client reconnects and reads current job state from D1 (`SELECT * FROM job_items WHERE job_id = ?`) to backfill any missed events.
- **Instagram validation 429s** → exponential backoff up to 3 attempts. On final failure the `leads` row is saved with `notion_status: 'pending'` and the Notion call is skipped; the user can retry from `/leads` once the rate limit clears.
- **Notion API errors** → the `leads` row is saved with `notion_status: 'pending'` and the underlying error text from `notion_manager.py:169-217` is surfaced verbatim in the per-row tooltip. Retryable from `/leads`.
- **Notion credentials missing or invalid** → all verified leads still save to D1 with `notion_status: 'unconfigured'`. The UI surfaces a banner on `/jobs/[id]` linking to `/settings`; once the user configures Notion, a "Sync pending" action on `/leads` pushes the backlog.
- **R2 upload fails partway through a batch** → job is rejected entirely with a clear error. No partial-state jobs allowed.

### Vision model

- Primary and only model: **`@cf/moonshot/kimi-k2.6`**.
- Prompt: verbatim from `_archive/extract_usernames.py:547-552`.
- No image preprocessing — whole-image OCR. The existing fixed crop region `image[165:255, 100:-100]` is dropped (see [Considered and rejected](#considered-and-rejected)).
- Confidence rules retained from `vlm_primary_extract` (`:563-578`): base 85, −15 if hedging language detected, +10 if `is_valid_instagram_format` passes, −10 if `has_unusual_pattern` triggers, clamped to `[60, 100]`.
- Tier thresholds from `classify_status` (`:707-720`): ≥95 → HIGH verified; 85–94 → MED verified; <85 → review.

## Data model and contracts

D1 schema (conceptual DDL; finalize during Phase 0):

```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  cf_access_subject TEXT UNIQUE NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE user_settings (
  user_id TEXT PRIMARY KEY REFERENCES users(id),
  diagnostics_default INTEGER NOT NULL DEFAULT 0,
  notion_token_encrypted BLOB,
  notion_database_id TEXT,
  notion_auto_sync INTEGER NOT NULL DEFAULT 0,
  notion_skip_validation INTEGER NOT NULL DEFAULT 0,
  notion_validation_delay_ms INTEGER NOT NULL DEFAULT 2000,
  daily_image_quota INTEGER NOT NULL DEFAULT 1000
);

CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  status TEXT NOT NULL,            -- pending | running | completed | cancelled | failed
  vlm_model TEXT NOT NULL,         -- '@cf/moonshot/kimi-k2.6'
  diagnostics INTEGER NOT NULL,
  image_count INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  completed_at INTEGER
);

CREATE TABLE job_items (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(id),
  filename TEXT NOT NULL,
  r2_key TEXT NOT NULL,
  status TEXT NOT NULL,            -- pending | running | verified | review | failed | duplicate
  username TEXT,
  confidence REAL,
  tier TEXT,                       -- HIGH | MED | NULL
  is_duplicate INTEGER NOT NULL DEFAULT 0,
  is_near_duplicate INTEGER NOT NULL DEFAULT 0,
  similar_to TEXT,
  edit_distance INTEGER,
  raw_model_response TEXT,         -- diagnostics only
  error TEXT,
  created_at INTEGER NOT NULL,
  completed_at INTEGER
);

CREATE TABLE leads (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  username TEXT NOT NULL,
  ig_url TEXT NOT NULL,                        -- always 'https://instagram.com/' || username
  tier TEXT NOT NULL,                          -- HIGH | MED
  confidence REAL NOT NULL,
  source_job_id TEXT REFERENCES jobs(id),
  notion_page_id TEXT,                         -- set when notion_status = 'added'
  notion_status TEXT,                          -- added | invalid | pending | unconfigured | null
  notion_last_error TEXT,                      -- last error text from Notion API or IG, for retries
  archived INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  UNIQUE(user_id, username)
);
CREATE INDEX leads_user_username_idx ON leads(user_id, username);
CREATE INDEX leads_notion_status_idx ON leads(user_id, notion_status);
```

KV: `ig:exists:{lowercase_username}` → `{ exists: boolean, checked_at: number }` with 7-day TTL.

R2 layout:

- `raw/{job_id}/{filename}` — original uploads
- `debug/{job_id}/{filename_stem}_response.txt` — model raw response (diagnostics only)

WebSocket message contract (DO → browser):

```ts
type NotionStatus = 'added' | 'invalid' | 'pending' | 'unconfigured' | null;

type Message =
  | { type: 'item.started'; job_id: string; item_id: string; filename: string }
  | { type: 'item.completed'; job_id: string; item_id: string; result: {
        username: string | null;
        ig_url: string | null;                       // 'https://instagram.com/' || username
        confidence: number;
        tier: 'HIGH' | 'MED' | null;
        status: 'verified' | 'review' | 'failed' | 'duplicate';
        is_duplicate: boolean;
        is_near_duplicate: boolean;
        similar_to: string | null;
        edit_distance: number | null;
        notion_status: NotionStatus;                 // null on non-verified items
        notion_page_id: string | null;
      }}
  | { type: 'item.notion_updated'; job_id: string; item_id: string;
      notion_status: NotionStatus; notion_page_id: string | null; error: string | null }
  | { type: 'item.failed'; job_id: string; item_id: string; error: string }
  | { type: 'job.completed'; job_id: string; summary: {
        verified_count: number; review_count: number;
        failed_count: number; duplicate_count: number;
        notion_added_count: number; notion_invalid_count: number;
        notion_pending_count: number;
        dedup_groups: number; dedup_archived: number;
        elapsed_ms: number;
      }}
  | { type: 'job.cancelled'; job_id: string };
```

Vision call shape:

```ts
const response = await env.AI.run('@cf/moonshot/kimi-k2.6', {
  image: imageBytes, // from R2
  prompt: EXTRACT_USERNAME_PROMPT, // verbatim from _archive/extract_usernames.py:547-552
});
```

## UX and design direction

The visual identity must be distinctive — not a generic admin-panel aesthetic. Two directions captured during discussion:

- **Forensics aesthetic** — monospaced detail strips, terminal-style result rows, scan-line motion as items stream in.
- **Album contact-sheet aesthetic** — thumbnail grid of crops with extracted usernames overlaid; matches the OCR-on-images domain.

Final visual direction is an [open question](#open-questions).

Interaction patterns:

- Upload screen is a single full-bleed drop zone with a small file-picker affordance. No multi-step wizard for the common case.
- Job detail page streams results in as they arrive. Rows are inserted progressively; no skeleton-then-rerender pattern.
- Settings is a single-page form, not a multi-tab wizard. Wizard behavior is reserved for the first-run modal (FR-24).

Responsive behavior:

- Desktop-first. Mobile supports viewing past jobs and pushing to Notion; the upload flow is desktop-only because a 50-image upload is not realistic from mobile.

Motion:

- Per-item arrival uses a subtle slide-in. No global page transitions. No decorative animation.

## Dependencies

### Internal modules to port

| Python source | Target location (TypeScript) |
|---|---|
| `_archive/extract_usernames.py:470-490` (`is_valid_instagram_format`) | `src/lib/extract/validate.ts` |
| `_archive/extract_usernames.py:493-522` (`has_unusual_pattern`) | `src/lib/extract/validate.ts` |
| `_archive/extract_usernames.py:723-745` (`clean_username`) | `src/lib/extract/clean.ts` |
| `_archive/extract_usernames.py:748-764` (`levenshtein_distance`) | `src/lib/extract/distance.ts` |
| `_archive/extract_usernames.py:767-784` (`find_similar_existing`) | `src/lib/extract/distance.ts` |
| `_archive/extract_usernames.py:707-720` (`classify_status`) | `src/lib/extract/classify.ts` |
| `_archive/extract_usernames.py:525-589` (confidence scoring from `vlm_primary_extract`) | `src/lib/extract/confidence.ts` |
| `_archive/extract_usernames.py:1039-1090` (`append_to_files`) | *Not ported.* Markdown output dropped — D1 `leads` table is the source of truth. |
| `_archive/extract_usernames.py:1123-1266` (`generate_report`) | *Not ported.* Job summary panel on `/jobs/[id]` reads stats directly from D1 aggregates. |
| `extract_usernames/integrations/notion_deduplicator.py` (full) | `src/lib/notion/dedup.ts` |
| `extract_usernames/integrations/notion_manager.py` (full) | `src/lib/notion/manager.ts` (atop `@notionhq/client`) |
| `extract_usernames/integrations/notion_sync.py:24-69` (`load_usernames_from_markdown`) | `src/lib/import/markdown.ts` |
| `extract_usernames/integrations/instagram_validator.py` (full) | `src/lib/instagram/validator.ts` (atop `fetch`) |
| `extract_usernames/config.py` `DEFAULT_CONFIG` shape | `src/lib/settings/defaults.ts` |

### External services

- Cloudflare Workers AI — vision model `@cf/moonshot/kimi-k2.6`
- Cloudflare Access — authentication
- Notion API — CRM destination
- Instagram (`https://www.instagram.com/<u>/`) — profile existence validation

### Third-party libraries

Derived from an audit of 13 existing SvelteKit projects under `~/Desktop/projects/` (`beyourahi.com`, `dropout-studio`, `enscented`, `fermion`, `horcrux`, `invoice-generator`, `matt-rife`, `multi-restaurant-platform`, `nordcycle`, `order-processor`, `parbo`, `pookie`, `storefront_004`). Every package below appears in ≥2 audited projects unless flagged "foundational" (≥1 project + universally required to run a SvelteKit-on-Workers app). The frequency annotation `(N/13)` indicates the number of audited projects that already ship the package. This is the install list for Phase 0.

**Core SvelteKit + build**

- `@sveltejs/kit` (13/13)
- `@sveltejs/adapter-cloudflare` (12/13) — 13th project uses `adapter-cloudflare-workers`; standard adapter chosen here
- `@sveltejs/vite-plugin-svelte` (13/13)
- `@sveltejs/enhanced-img` (7/13) — image optimization for thumbnails in the contact-sheet view
- `svelte` (13/13)
- `svelte-check` (13/13)
- `vite` (13/13)
- `vite-plugin-devtools-json` (6/13)

**TypeScript**

- `typescript` (13/13)
- `@types/node` (13/13)
- `@cloudflare/workers-types` (foundational; 1/13 in audit, required for typed `env` bindings on Workers)

**Cloudflare runtime**

- `wrangler` (13/13)

**Styling (Tailwind CSS v4)**

- `tailwindcss` v4 (13/13) — CSS-first config; no `tailwind.config.*` file
- `@tailwindcss/vite` (13/13)
- `tailwind-merge` (12/13)
- `tailwind-variants` (8/13)
- `tw-animate-css` (9/13)
- `clsx` (13/13)

**UI primitives**

- `bits-ui` (11/13) — headless primitives; used directly or via shadcn-svelte wrappers (see [Open questions](#open-questions))
- `@lucide/svelte` (12/13)
- `mode-watcher` (5/13) — light/dark theme tracking
- `svelte-sonner` (4/13) — toast notifications

**Forms and validation**

- `zod` (3/13)
- `formsnap` (2/13)
- `sveltekit-superforms` (2/13)

**Media**

- `@unpic/svelte` (6/13) — responsive image component for screenshot thumbnails

**Database (D1)**

- `drizzle-orm` (2/13) — both audited D1 projects (`order-processor`, `invoice-generator`) use Drizzle
- `drizzle-kit` (2/13) — schema migrations

**Linting**

- `eslint` (13/13)
- `@eslint/js` (13/13)
- `@eslint/compat` (9/13)
- `eslint-config-prettier` (13/13)
- `eslint-plugin-svelte` (13/13)
- `typescript-eslint` (13/13)
- `globals` (13/13)

**Formatting**

- `prettier` (13/13)
- `prettier-plugin-svelte` (13/13)
- `prettier-plugin-tailwindcss` (13/13)

**Project-specific (outside canonical baseline)**

- `@notionhq/client` — Notion REST SDK; replaces the Python `notion-client`. Not in any audited project; added specifically for this port.

### Package manager and lockfile

Bun is the convention across all 13 audited SvelteKit projects. `bun.lockb` is the committed lockfile. No audited SvelteKit project uses `npm` or `pnpm`. Phase 0 scaffolding uses `bun create svelte` and `bun install`; CI installs are pinned to the lockfile.

## Rollout and migration

### Phases

**Phase 0 — Scaffolding** (½ day). Create new repo at `/Users/beyourahi/Desktop/projects/username-extractor` with `package.json` name `"username-extractor"`. Bun + SvelteKit + `@sveltejs/adapter-cloudflare` + Tailwind v4 + `wrangler.toml` with bindings (D1, R2, AI, Queue, DO class) — worker name `username-extractor`. D1 migration applied. The legacy `extract_usernames` Python repo stays untouched as the algorithmic reference and porting source.

**Phase 1 — Lift pure logic** (3 days, parallelizable across files). TypeScript-port the modules listed in [Internal modules to port](#internal-modules-to-port) with no algorithmic change. Vitest unit tests use fixtures from existing `_debug_dir/*_consensus.json` and `_debug_dir/*_vlm_response.txt` outputs as regression cases.

**Phase 2 — Integrations** (2 days, parallel with Phase 1). Port `notion_manager`, `notion_sync`, `notion_deduplicator`, `instagram_validator`. Add KV cache for Instagram validation.

**Phase 3 — Vision pipeline + DO orchestration + inline Notion sync** (1 week, blocks on Phase 1 and Phase 2). Single Workers AI call to `@cf/moonshot/kimi-k2.6` with the existing prompt. Per-job DO. Queue consumer Worker. Inline IG validation + Notion create + post-job dedup (FR-14 through FR-18). End-to-end job flow with Notion writes happening per item, not as a separate user action.

**Phase 4 — UI** (1 week, parallel with Phase 3). Routes: `/`, `/jobs`, `/jobs/[id]`, `/leads`, `/settings`. Svelte 5 runes. WebSocket client with live Notion-status badges per row.

**Phase 5 — Polish** (3–5 days). Cron Trigger for R2 expiration. Notion token encryption. Legacy-import endpoint (FR-28). Quota enforcement (NFR-13).

Total estimated effort: ~3 weeks single-engineer.

### Data migration

Handled via FR-28. Migration is idempotent — re-running the import does not create duplicate `leads` rows due to the UNIQUE constraint on `(user_id, username)`.

### Rollback strategy

Cloudflare Workers deployments are version-pinned; rollback is a one-click revert to a previous deployment. D1 schema changes use forward-only migrations; destructive changes require an explicit follow-up migration rather than a rollback.

### Feature flags

None for v1. Phase boundaries are the rollout granularity.

## Considered and rejected

| Alternative | Why rejected |
|---|---|
| Keep the CLI as the primary interface | Explicit user decision: the web UI is the new front door. |
| Deploy to Node-based hosts (Vercel Node runtime, Railway, Fly.io VMs) | Fixed constraint: Cloudflare Workers. |
| Next.js, Remix, Astro, Nuxt as the framework | Fixed constraint: SvelteKit. |
| CSS Modules, vanilla CSS, UnoCSS, Panda CSS | Fixed constraint: Tailwind CSS v4. |
| Preserve dual-engine OCR (VLM + EasyOCR cross-validation) | Modern frontier VLMs make the second engine's marginal accuracy gain not worth the engineering cost. Single-engine is simpler, faster, and chosen for pure performance. |
| Run PyTorch on Workers via WebGPU shims | Ecosystem not viable; Workers AI provides a managed substitute. |
| Preserve OpenCV multi-pass preprocessing (`preprocess_balanced`, `_aggressive`, `_minimal`) | Existed to compensate for EasyOCR's weaknesses; not needed for a frontier VLM. |
| Preserve the fixed crop region `image[165:255, 100:-100]` | Brittle assumption tied to a specific Instagram UI version on a specific device. Whole-image OCR is more robust. |
| `multiprocessing.Pool` semantics for fan-out | Workers has no process model; Queues + DO is the correct primitive. |
| `@cf/meta/llama-3.2-11b-vision-instruct` as primary vision model | Defensible second choice; Kimi K2.6 chosen for pure performance per stated priority. |
| `@cf/meta/llama-4-scout-17b-16e-instruct` as primary vision model | Defensible second choice; Kimi K2.6 chosen for pure performance per stated priority. |
| `@cf/google/gemma-4-26b-a4b-it` as primary | Gemma's prompt-following historically weaker than alternatives for strict-format extraction. |
| `@cf/mistralai/mistral-small-3.1-24b-instruct` as primary | Mistral vision capability newer and less battle-tested for OCR. |
| `@cf/llava-hf/llava-1.5-7b-hf` | Beta, 2023-era, weaker vision encoder. |
| `@cf/unum/uform-gen2-qwen-500m` | Beta + planned deprecation. |
| Cloudflare Containers running the existing Python pipeline as a sidecar | Held only as an escape hatch if Kimi K2.6 underperforms on benchmark. Not v1 plan. |
| Better Auth with D1 adapter for auth | Multi-user authentication is overkill for current single-operator use; Cloudflare Access chosen. |
| Server-Sent Events for progress streaming | One-way only; bidirectional needed for cancel (FR-25) and potential mid-flight settings changes. WebSockets via DO chosen. |
| Markdown files as continued source of truth for cumulative leads | Append-only regex scans are O(n) per run; D1 with index on `(user_id, username)` is O(log n). Markdown becomes export-only. |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Workers AI vision accuracy regression vs. existing `glm-ocr:bf16` (96% claimed in README) | Benchmark `@cf/moonshot/kimi-k2.6` on ≥50 historical screenshots before Phase 3 sign-off. If accuracy degrades materially, escape hatch is Cloudflare Containers running the existing Python pipeline. |
| Instagram rate-limiting from Cloudflare egress IPs (shared pool, treated as bot traffic) | KV cache (FR-16). Demote validation from a hard gate to a soft annotation — unvalidated usernames still sync to Notion with a `validation_pending` flag. |
| Single-user → multi-user retrofit pain | `user_id` is in every relevant D1 table from day one; no retrofit required. |
| Per-image cost grows linearly with batch size | Per-user daily quota (NFR-13) bounds spend. |
| `_archive/` runtime trap — folder name implies dead code but is the runtime extractor | Documented here and in [Current state](#current-state); do not delete `_archive/` until the port is complete and the legacy CLI is retired. |
| Repo confusion between legacy `extract_usernames` and new `username-extractor` | The two repos are sibling directories under `~/Desktop/projects/`. Legacy stays read-only as the porting source; the new repo is the sole place where web-port work happens. The PRD's [Identity and placement](#identity-and-placement) table is the canonical source of which name belongs to which artifact. |
| WebSocket connections drop on flaky networks | Client reconnect logic. On reconnect, read current `job_items` state from D1 to backfill missed events. |
| Workers AI subrequest budget exhausted on large batches | Per-image work runs in its own Queue-consumer invocation, not in the request that initiated the job. The originating Worker request only enqueues. |

## Out of scope

- Browser-based screenshot capture (clipboard paste, screenshot extension).
- Mobile-first upload flow.
- Multi-tenant team accounts with shared lead pools.
- Per-lead notes, tagging, or status workflow inside the app (Notion remains the CRM).
- A public API for third-party integration.
- Webhook ingestion of external automation outputs.
- Scheduled or cron-triggered extraction.
- Cost dashboards or per-user billing UI.
- Anything not present in the existing CLI surface, except the additions explicitly enumerated in [Functional requirements](#functional-requirements).

## Future considerations

- **Browser-side capture** — clipboard paste of a screenshot to skip the file picker.
- **Scheduled extraction** — Cron Trigger pulling a queue of pre-uploaded images on a schedule.
- **Notion webhook ingress** — react to Notion status changes (e.g., mark `Approached` to push back into local state).
- **Multi-tenant teams** — shared lead pool with per-user contribution tracking; would require swap from Cloudflare Access to Better Auth.
- **Cloudflare Containers fallback** — lift the existing Python pipeline if accuracy regresses below threshold.
- **Browser-adjustable crop region** — if users want device-specific crops back, surface as a per-job setting rather than a hard-coded constant.
- **Dual-engine fallback** — the already-ported `intelligent_consensus_validator` is kept in `src/lib/extract/consensus.ts` even though unused in v1, so a second model can be added without re-porting.

## Open questions

1. **Visual identity** — forensics vs. contact-sheet aesthetic, or a different direction. Final design call required before Phase 4 starts.
2. **shadcn-svelte vs. raw bits-ui primitives** — the dependency audit confirms `bits-ui` (headless primitives) is canonical across Rahi's SvelteKit projects (11/13). The remaining decision is whether to layer **shadcn-svelte's pre-styled components** on top of `bits-ui` (faster shipping; introduces a baseline aesthetic that may need overriding) or wire `bits-ui` directly with custom Tailwind classes (slower; full visual control, no styling baseline to fight). Decide during Phase 0.
3. **Cloudflare Access tenancy model** — single Access policy with a private list, or open-with-email-allowlist. Affects how new collaborators are added.
4. **Encryption-at-rest scheme for Notion tokens** — AES-GCM with a Worker Secret as the key vs. a Cloudflare-native KMS primitive (if available at deploy time).
5. **R2 expiration policy** — retention window for raw uploads (proposed default 30 days) and diagnostic artifacts.
6. **Benchmark protocol for Kimi K2.6** — which historical screenshots form the test set, and what accuracy threshold blocks Phase 3 sign-off.
7. **Deployment domain** — the tool will be listed under `/tools/username-extractor` on both `beyourahi.com` and `dropoutstudio.com`. The remaining decision is whether the actual Worker is served from a dedicated subdomain (e.g. `username-extractor.beyourahi.com`) and embedded/proxied into each `/tools` route, or deployed twice under each site's existing Worker. Affects DNS, Cloudflare Access policy scope, and how the card on each site links to the live app.
8. **Legacy import timing** — whether FR-28 ships on day one or is deferred to Phase 5.
9. **AVIF vs. PNG for stored crops** — Resolved at the architecture level: originals stored in R2 as their uploaded format (PNG/JPEG), with **Cloudflare Image Resizing** producing AVIF/WebP on the read path via `cf.image` fetch options. Remaining sub-decision: whether to also pre-generate and persist a `thumb.avif` per item at write time to avoid first-hit transform latency on the contact-sheet view, or rely on edge cache from the first request.

## Acceptance and verification

### Per-phase acceptance

- **Phase 0** — `bun run dev` boots the SvelteKit app locally with all bindings (D1, R2, AI, Queue, DO) wired and `wrangler dev` reaches them.
- **Phase 1** — All ported pure-logic modules pass Vitest fixtures derived from existing `_debug_dir/*_consensus.json` and `_debug_dir/*_vlm_response.txt` diagnostic outputs.
- **Phase 2** — Notion sync against a test database produces the same `added_count` / `duplicate_count` / `invalid_count` shape as the Python equivalent for a fixed input set.
- **Phase 3** — A 10-image batch runs end-to-end on `wrangler dev` against deployed Workers AI, producing `job_items` rows with non-null `username` and `confidence` for the expected images.
- **Phase 4** — All routes listed in [Functional requirements](#functional-requirements) render and exercise their FR acceptance conditions on deployed Workers.
- **Phase 5** — A run of the legacy-import endpoint against a known `verified_usernames.md` produces the expected `leads` row count, and a second run produces zero new rows.

### Final verification

- All functional requirements FR-1 through FR-28 demonstrably pass their stated acceptance conditions on the deployed Worker.
- All non-functional thresholds NFR-1 through NFR-13 are measured against the deployed Worker and recorded in deployment notes.
- A benchmark of `@cf/moonshot/kimi-k2.6` against ≥50 historical screenshots is recorded with accuracy compared to the legacy `glm-ocr:bf16` baseline. The result is documented even if the threshold is met; if not met, the Cloudflare Containers escape hatch is triggered before launch.

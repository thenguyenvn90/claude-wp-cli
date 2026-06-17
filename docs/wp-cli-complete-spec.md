# wp-cli Complete — Design Spec

> Goal: make `wp-cli` the single, complete WordPress tool that (1) replaces the
> blog-publish Python scripts and (2) replaces the WP MCP Ultimate plugin's admin
> reach. End target: vendored into the `claude-growth` kit and shipped to buyers.

## Decisions (locked)

- **Ship target:** vendor into `claude-growth` (buyer-facing). ⇒ generic only (no
  site values), English prose, obey 3-surface alignment + 2-repo ship flow.
- **Scope:** full — publish parity **and** admin breadth.
- **Approach:** **A** — absorb the proven guard *logic* into wp-cli modules, cover
  with parity/golden tests vs the legacy scripts, then (later) reduce legacy
  scripts to thin shims. Python throughout. Auth via the kit no-secret `--site`
  contract.
- **Phase-1 placement:** build in standalone `D:\claudeCode_Projects\wp-cli`;
  kit-vendoring is sub-project 3. Phase 1 does **not** touch the kit's scripts.

## Decomposition (each is its own spec → plan → build cycle)

| # | Sub-project | Contents |
|---|---|---|
| **1** | **Publish parity (safety core)** | safe body push + guards, media+featured, multi-plugin meta + focus-kw merge, schema, fetch-live + drift, md→HTML/Gutenberg |
| 2 | Admin breadth | comments, plugins, users, search (REST verified 200) |
| 3 | Advanced admin + kit-integration | menus, widgets, settings + wire into blog-pipeline + 3-surface docs + 2-repo ship |

---

## Sub-project 1 — Publish Parity (this spec)

### Parity surface (everything legacy `wp_*` scripts do — must be preserved)

From `scripts/wp_push_safe.py` (520 lines), `wp_meta_push.py`, `wp_media_push.py`,
`wp_seo_router.py`, `wp_fetch_live.py`:

1. **slug-guard** — GET `/posts/{id}`; refuse if actual slug ≠ expected (`SlugMismatchError`).
2. **em-dash strip** — ` — `→`, ` and residual `—`→`,`; protects `<pre|code|script|style>`; returns count; opt-out `--no-emdash-strip`.
3. **markdown-leak detection** — 8 patterns w/ thresholds (`## `, `### `, table rows, fences, `- **bold**`, bold-only line, inline `**bold**`, inline `` `code` ``); strips `<pre>/<code>/<!--`comments before scanning; refuse over threshold unless `--force`.
4. **meta-comment strip** — remove one leading "Meta description:" artifact (HTML comment / blockquote / `<p>`), multilingual (en/vi/es/de/ja), head-zone only (first 1500 chars).
5. **drift check** — GET `?context=edit`, compare char counts; bands: <0.5% none, <2% minor-ok, <10% significant-refuse, ≥10% major-refuse; `--allow-drift` / `--no-drift-check`.
6. **status** — `draft|publish|future|pending|private`; **`--type page`** targets `/pages`.
7. **gate-report interlock** — refuse unless `--gate-report` JSON `verdict == "OK"` (opt-in).
8. **meta (multi-plugin)** — RankMath (`/rankmath/v1/updateMeta`), Yoast (`_yoast_*` post-meta), generic (`_seo_*`); **focus-keyword MERGE** (existing ∪ added, deduped, never clobber); read via `/rankmath/v1/getMeta` w/ rendered-title fallback.
9. **schema (multi-plugin)** — RankMath `/updateSchemas`; Yoast/generic store JSON-LD in `_schema_jsonld` post-meta.
10. **media** — upload (MIME map, webp), set alt, set as featured.
11. **fetch-live** — always fetch live before edit.
12. **auth** — order: `--site-config` JSON → `sites/[name]/wp-auth.json` → env `CLAUDE_WP_BASE/AUTH` → `.mcp.json` (match by host) → wp-cli `.env.site`. Never secret in argv. Refuse if none.

### Module layout (extends existing cli/ + client/ pattern)

- `client/guards.py` (**pure**) — `strip_em_dashes`, `detect_md_leak` (+`LEAK_PATTERNS`), `strip_meta_comment`, `_strip_safe_blocks`; exceptions. Ported ~verbatim for behavior parity.
- `client/seo_router.py` (**pure**) — `detect_plugin`, `meta_request`, `schema_request`. Ported verbatim.
- `client/posts.py` (extend) — `fetch_live`, `verify_slug`, `check_drift`, `push_safe` (orchestrates guards + POST).
- `client/meta.py` (new) — `get_meta`, `update_meta` (focus-kw merge), routed via seo_router.
- `client/media.py` (extend) — `set_featured`.
- `client/auth.py` (new) — `resolve_credentials` (kit no-secret contract; supersedes inline `.env.site`-only path while still supporting it).
- `cli/publish.py` (new) — `publish` orchestrator + expose `posts push-safe`, `meta`, `schema` subcommands; wire in `cli/main.py`.

### Testing (the Approach-A safety net)

- Unit tests per pure guard (em-dash counts incl. protected blocks; each leak pattern at/below/above threshold; meta-comment 3 variants × languages; seo_router per-plugin payloads + focus-kw join).
- **Golden/parity tests:** feed identical inputs to wp-cli functions and the legacy `scripts/wp_*` functions (import both), assert identical outputs — especially guards. This is what licenses retiring the legacy scripts in sub-project 3.
- Live smoke-test (read paths only) against a real site with an admin key.

### Out of scope (SP1)

Admin resources (comments/plugins/users/menus/widgets/settings/search), kit
vendoring + 3-surface docs, retiring legacy scripts → sub-projects 2 & 3.

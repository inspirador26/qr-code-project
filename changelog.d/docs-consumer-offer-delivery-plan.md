## Design masked consumer offer delivery; clean up pre-skills-system docs

**Branch:** docs/consumer-offer-delivery-plan
**Author:** Claude (with Justin)

Justin wanted to plan how individual offers get served to consumers at
scale (hundreds of offers across hundreds of tenants), specifically how to
mask our platform's own branding from the public link, plus fix a
confirmed gap where `issue_and_deposit_clip` deposits to TCB with no check
that the offer is still active. That produced a design doc. Separately,
reviewing an external draft documentation-policy text against our own
`AGENTS.md`/`DOCUMENTATION_POLICY.md` surfaced that several root-level
`.md` files predate the `.claude/skills/` system and were never folded in
— this branch also does that cleanup.

### Files touched

- `.claude/skills/backend/consumer-offer-delivery/SKILL.md` — **new**: the
  masked-domain design (neutral shared domain now, per-tenant custom
  domain phased for later), the short opaque `Offer.public_token`, and the
  `ensure_offer_clippable` guard closing the active-check gap.
- `.claude/skills/backend/DOSSIER.md` — pointer to the new skill doc added
  in §8; the TODO reference to the now-retired
  `backend/docs/HANDOFF_offer_clip_flow.md` repointed to
  `tcb-integration/SKILL.md` and `consumer-offer-delivery/SKILL.md`.
- `.claude/skills/backend/DECISIONS_AND_ISSUES.md` — four new dated
  entries: the masked-domain-must-serve-the-whole-flow decision, the
  Phase A/B split, the campaign-window-not-redemption-window gating
  choice, and the "`CouponClip.serialized_gs1`'s global uniqueness
  constraint already prevents per-offer pincode reuse" finding (recovered
  from the retired handoff doc, which had flagged it but it was never
  logged as a decision).
- `.claude/skills/backend/tcb-integration/SKILL.md` — merged in the
  handoff doc's closing self-check checklist and the previously-untracked
  `CouponFetchCode` missing-uniqueness-constraint known issue.
- `.claude/skills/domain/coupon-industry-roles/SKILL.md` — merged in
  `COUPON_WORKFLOW_PRIMER.md`'s plain-English lifecycle walkthrough and its
  concrete "`redeemed_at` is only ever set from the TCB-audit background
  job, never a shopper-reachable view" code illustration, as a new
  "Start here" section.
- `backend/README.md` — trimmed the apps table / tenant-isolation / TCB-seam
  / current-milestone / current-status / "why Django" sections, all of
  which duplicated `DOSSIER.md`/`tcb-integration/SKILL.md` (the maintained
  sources) or `CHANGELOG.md` (the "why Django" rewrite reasoning already
  lives in the 2026-08-22 part 3 entry there). Kept Quick start/Running
  tests/Demo data as-is — `dev-environment/SKILL.md` explicitly treats this
  file as the canonical detail source for that.
- `AGENTS.md` — dropped the `LLM_HANDOFF.md` line from §3 (file deleted);
  no section renumbering.
- `.claude/skills/legacy/DECISIONS_AND_ISSUES.md`,
  `.claude/skills/product/DECISIONS_AND_ISSUES.md` — fixed dangling
  pointers to the retired root docs.
- Deleted (pure duplicates of what the skills system already covers in
  more current detail — `qr-coupon-flow/SKILL.md` for the Node POC,
  `DOSSIER.md`/`tcb-integration/SKILL.md` for Django state): `ARCHITECTURE.md`,
  `DATABASE.md`, `PROJECT_OVERVIEW.md`, `ROADMAP.md`, `LLM_HANDOFF.md`,
  `HANDOFF_MVP_DEMO.md`, `COUPON_WORKFLOW_PRIMER.md` (post-merge),
  `backend/docs/HANDOFF_offer_clip_flow.md` (post-merge).

### Verified

Docs-only branch, no code changes, no test run. Grepped the whole repo
(excluding `venv/`) for references to every deleted filename after each
merge — confirmed no remaining dangling pointers outside `CHANGELOG.md`
(left alone deliberately: those are historical fact, not live references).

### Not done / known gaps

- Phase B of the consumer-offer-delivery design (per-tenant custom
  domains, DNS verification, `ALLOWED_HOSTS = ["*"]`) is spec'd only, not
  built — deliberately deferred until a real client asks for white-labeling.
- The external documentation-policy draft Justin shared was reviewed
  against our own `AGENTS.md`/`DOCUMENTATION_POLICY.md` (compatible in
  spirit, several placeholder/terminology gaps identified — see this
  branch's chat history) but **`DOCUMENTATION_POLICY.md` itself was not
  changed** — adoption is still an open decision, not resolved here.
- No docs drift-detection script (citation checking, duplicate rule
  numbers) exists yet — raised during the policy review, not built.

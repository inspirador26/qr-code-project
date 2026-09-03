# Product — segment-level decisions & known issues

Business/workflow policy decisions and open questions that apply broadly
to the product, beyond what's already tracked inside
`product/cpg-engagement-workflow/SKILL.md`'s own TODO/decisions sections.
See `.claude/skills/skills-organization/SKILL.md` for what belongs here.
Newest on top.

---

## 2026-09-02 — MVP milestone now includes account creation, not just the clip flow

**Decision**: the near-term "success" definition for the MVP demo was
expanded to require creating multiple `Tenant` accounts and adding offers
under each, not just proving the clip→barcode loop against one hardcoded
tenant. Full detail lives in `product/cpg-engagement-workflow/SKILL.md`'s
"Immediate next milestone" section (2026-09-02 update) and
`LLM_HANDOFF.md`'s "Partner handoff — objectives" section.

**Why it matters beyond one skill doc**: this reframes the MVP milestone
referenced from multiple places (`backend/README.md`,
`backend/legacy/qr-coupon-flow` — via `tcb-integration`'s milestone
section too) — anyone reading just one of those needs to know the scope
grew.

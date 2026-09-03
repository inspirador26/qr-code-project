# Domain — segment-level decisions & known issues

Industry/vocabulary corrections and clarifications that apply broadly,
beyond what's already tracked in `domain/coupon-industry-roles/SKILL.md`
itself. See `.claude/skills/skills-organization/SKILL.md` for what belongs
here. Newest on top.

---

## 2026-08-24 — TCB is not a party to settlement; "Clearinghouse"/"Manufacturer Agent" are not TCB-defined roles

**Correction**: earlier drafts of product/domain docs incorrectly implied
TCB settles payments or that "Clearinghouse"/"Manufacturer Agent" are
TCB-defined roles. Corrected: TCB is a neutral validation service only
(registers/locks offers, validates codes at checkout), funded by a flat
$0.01/clip fee — no discount money moves through it. The real
reimbursement chain (Retailer → Retailer Clearing House → Settlement
Provider → CPG) is two independent third parties with no relationship to
TCB. Full detail in `domain/coupon-industry-roles/SKILL.md` and
`product/cpg-engagement-workflow/SKILL.md`.

**Why it matters beyond one skill doc**: this vocabulary error had already
propagated into multiple docs/artifacts before being caught (see
`CHANGELOG.md` 2026-08-24) — worth checking any new product/pitch material
against this correction before it spreads again.

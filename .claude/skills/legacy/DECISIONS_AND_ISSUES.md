# Legacy (Node POC) — segment-level decisions & known issues

Policy decisions and known issues that apply to the legacy Node/Express
proof-of-concept (`server.js` at the repo root) beyond what's already in
`legacy/qr-coupon-flow/SKILL.md`. See
`.claude/skills/skills-organization/SKILL.md` for what belongs here. Newest
on top.

---

## 2026-08-22 — the Node POC is a behavioral reference only, not being migrated

**Decision**: active development moved to the Django backend at `backend/`
(see `LLM_HANDOFF.md`'s superseded notice and `CHANGELOG.md` 2026-08-22
entries for the full narrative). `server.js` stays in the repo only to
answer "how did the old version do X" — it is not being incrementally
ported, and no new feature work should land there.

**How to apply**: if a question comes up about existing QR/coupon/wallet
behavior and the Django backend doesn't have an equivalent yet, it's fine
to read `server.js` for reference — just don't extend it.

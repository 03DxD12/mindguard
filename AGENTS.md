# Agent Skill Routing Rules

Apply the following skills conditionally by task phase so only relevant instructions are loaded without token bloat:

- `understand-anything`: Use only when mapping unfamiliar modules or analyzing diff impact on shared core files.
- `grill-with-docs` / `to-spec` / `to-tickets` (Matt Pocock): Use before building ambiguous features to interview the user with concise questions, sharpen domain terminology in `GLOSSARY.md` / ADRs, and split work into vertical tracer-bullet tickets.
- `superpowers`: Use for multi-file features, complex logic, or architecture to enforce TDD and verification criteria during implementation.
- `impeccable` & `frontend-design`: Use `frontend-design` when designing new pages, views, or visual layouts from scratch; use `impeccable` for design direction, removing AI slop, and targeted UI refinements (`critique`, `polish`, `bolder`, `quieter`, `typeset`).
- `ponytail`: Apply to all coding tasks (full mode) to enforce minimal diffs, native APIs, and reuse of existing helpers without adding bloat.
- `emil-design-eng`: Apply whenever adding or modifying transitions, modals, drawers, tooltips, or interactive feedback.
- `make-interfaces-feel-better`: Apply during CSS/styling passes for concentric radii, optical alignment, hit-target sizing, and typography rules.
- `web-design-guidelines`: Run on modified frontend files before finishing any UI task to audit accessibility, focus states, and semantic HTML.
- `security-audit`: Run before finalizing features touching authentication, APIs, user inputs, database queries, or dependencies to catch OWASP/CWE vulnerabilities and verify findings before reporting.

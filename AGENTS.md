# Agent Skill Routing Rules

Apply the following skills conditionally by task phase so only relevant instructions are loaded without token bloat:

- `understand-anything`: Use only when mapping unfamiliar modules or analyzing diff impact on shared core files.
- `superpowers`: Use for multi-file features, complex logic, or architecture to lock down a plan and verification criteria before coding.
- `frontend-design`: Use only when designing new pages, views, or visual layouts from scratch.
- `ponytail`: Apply to all coding tasks (full mode) to enforce minimal diffs, native APIs, and reuse of existing helpers without adding bloat.
- `emil-design-eng`: Apply whenever adding or modifying transitions, modals, drawers, tooltips, or interactive feedback.
- `make-interfaces-feel-better`: Apply during CSS/styling passes for concentric radii, optical alignment, hit-target sizing, and typography rules.
- `web-design-guidelines`: Run on modified frontend files before finishing any UI task to audit accessibility, focus states, and semantic HTML.


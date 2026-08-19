# UI Implementation Contract

Load this reference only when a mission writes UI code or when a UI review needs the implementation contract. The core skill keeps the route and safety boundary concise; this file carries the detailed design-conformance rules.

When a product has a design system, a route's structure comes from `wireframes.md` and its visual layer comes from `design-system.md` plus `design-system.json`. The route is composed, not freely designed: the design system is a closed set the implementation picks from.

The frozen design system is the default implementation source. If the mission's explicitly planned `required_skills` includes `frontend-design`, the worker still follows every rule below in frontend-design conformance mode. The skill changes execution craft, not the contract or its precedence.

Every mission that writes UI code:

1. Read `design-system.json` and the route's screen entry in `wireframes.md` before writing. Resolve the route by matching each screen's `Route(s):` line; a route no screen claims, or two screens claim, is a blocker (see `references/contract-and-traceability.md`).
2. Treat those two files as the complete normal input. No mockup, screenshot, Figma frame, or exploration HTML is required. Design inspiration is non-canonical evidence until `product-design-builder` freezes accepted principles; a page-faithful target is binding only after the user explicitly requests faithful conformance and freezes its route, states, responsive scope, and tolerance.
3. Invent no visual value. Colors, spacing, radii, font sizes, durations, easing, and distances come from tokens; primitive props come from the design system's closed variant sets. Use `gap="4"` and `size="md"`, never `gap="13px"` or an arbitrary utility class.
4. Reimplement no control or surface. Compose the design system's primitives and product components and reference registered motion variants only.
5. Follow the wireframe's region responsibilities, section order, actions, exact wording/display contracts, and labeled style direction.
6. Complete every state the wireframe screen declares using `design-system.json`'s `stateMatrix`: ready, loading, empty, error, disabled, permission denied, stale, expired, long content, reduced motion, and mobile reflow, with any inapplicable state explicitly marked `n/a`. The ready state alone does not close the task.
7. Stop and report when a route needs a token, primitive, variant, motion variant, or component absent from `design-system.json`. That is a design-input delta, not a task-local exception. Route it through `references/design-input-updates.md`; never write the frozen `design-system.md` or `design-system.json` from an implementation mission.
8. Run `scripts/check_ui_contract.py` against the product source using `design-system.json` as the allowlist. For a mission run, pass that mission's changed files as positional arguments instead of `--path`; `--path` walks the whole tree for eight suffixes on every invocation, which is the right cost for the final gate and waste for one mission's slice. Its source scan covers raw visual values, inline layout styles, page-local controls/surfaces, and call-site motion values. A filtered rule run is not a contract-clean signal by itself.
9. Run visual verification across the responsive set in `design-system.json` (`viewports` for web or `sizeClasses` for native/desktop), in normal and reduced motion, and record evidence using `references/verification-gates.md`. Never substitute web pixel breakpoints for a native platform's model.

The source scan does not prove primitive choice, wireframe region responsibilities, or state coverage; those remain review and evidence gates. A clean scan is a floor, not a pass. Any raw value, unregistered variant, page-local control, or skipped state is a contract violation: stop at a safe boundary, report it, and fix the contract or code rather than accepting a passing functional test as a substitute.

For design-source creation, load `product-design-builder`, `impeccable`, and `frontend-design` in creation mode; a missing dependency blocks and has no fallback. For UI implementation, load `frontend-design` only when the user explicitly selected the new or high-impact visual surface and use conformance mode. Do not load `impeccable` during implementation. A missing contract entry returns to `product-design-builder` as a design-input delta.

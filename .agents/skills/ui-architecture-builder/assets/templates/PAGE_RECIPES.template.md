# Page Recipes: <product name>

A page recipe is the only legal way to assemble a route. Read the route's recipe before writing any markup. A route with no recipe is a blocker, not an invitation to improvise.

## Recipes

One block per route. Everything here is binding.

### <recipe name> — <route>

| Field | Value |
|---|---|
| Container | <container size from ui-registry.json> |
| Section density | <density from ui-registry.json> |
| Section order | <ordered list, top to bottom> |
| Required product components | <DS-COMP-* and the content contract each renders> |
| Allowed surfaces | <the only surface variants this route may use> |
| Forbidden patterns | <the compositions this route must never grow into> |
| Required states | <from the State Matrix; mark n/a with a reason> |
| Must render without JavaScript | <content that must be server-rendered, or n/a + reason — the field applies to a server-rendered web surface, so a native or desktop route marks it n/a> |
| Primary action | <the single primary action, or none> |

Page notes — only what the mockup HTML cannot show. Do not restate what is visible in the file.

- Product-specific decisions: <signature cues applied; generic patterns intentionally avoided and why>
- Content realism: <representative content/data source, or exact copy / display contract for content that is unavailable or data-driven>
- Container and border treatment: <the default open-layout treatment, and the named purpose of any visible border, accent rail, nested frame, or elevation — a border with no stated purpose fails review>
- Content budget (landing/content-heavy pages only): <single job per region, and what content is intentionally deferred or excluded>
- Asset requirements: <image/media/icon needs — type, required / optional / none, purpose, source or creation need, responsive/static fallback>
- Motion choreography: <element, trigger, registered variant, reduced-motion fallback — if not already in the motion system>
- Open questions / assumptions: <anything unresolved for this route>

## Forbidden Patterns Registry

Patterns forbidden across all routes, in addition to per-recipe entries.

| Pattern | Why | Where it came from |
|---|---|---|
| <pattern> | <the failure it caused or would cause> | <anti-slop review, past drift, or product rule> |

## Coverage

| Requirement | Status |
|---|---|
| Every route in `ui-registry.json` has a recipe here | <yes / gaps> |
| Every recipe has a mockup HTML file | <yes / gaps> |
| Every recipe's required states appear in its mockup | <yes / gaps> |
| Every route maps to acceptance TEST IDs | <yes / gaps> |

---

## Route Index

| UI ID | Route / screen | Recipe | Mockup HTML | Upstream trace IDs | DS IDs | States represented | Motion demo | TEST IDs / acceptance evidence |
|---|---|---|---|---|---|---|---|---|
| UI-001 | /example | <recipe name below> | mockups/example.html | PRD-001, UX-001, ARCH-001 | DS-001, DS-LAY-001, DS-COMP-001 | ready/loading/empty/error/long-content/reduced-motion/mobile-reflow | motion-showcase.html#example | TEST-VIS-001, TEST-VIS-019 |

Lookup table, not reading material. Fill it last; scan it when checking that a route reached a mockup, a trace, and a test.

# UI One-Take Prompts

Use this reference for frontend, UI refinement, design implementation, screenshots, responsive behavior, visual QA, and accessibility verification.

Sources:

- OpenAI Codex prompting: https://developers.openai.com/codex/prompting
- OpenAI Using Goals in Codex: https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
- Anthropic Claude Code best practices: https://code.claude.com/docs/en/best-practices
- Playwright visual comparisons: https://playwright.dev/docs/test-snapshots
- Playwright emulation/devices: https://playwright.dev/docs/emulation
- Playwright accessibility testing: https://playwright.dev/docs/accessibility-testing
- Playwright trace viewer: https://playwright.dev/docs/trace-viewer
- Playwright Page events: https://playwright.dev/docs/api/class-page
- WCAG 2.2: https://www.w3.org/TR/WCAG22/

## One-Take Principle

A one-take UI prompt should give the agent enough context, constraints, and verifiers to implement, render, inspect, fix, and report evidence without another clarification round. It should not ask for vague taste changes without a design source or observable checks.

## UI Intake

Capture:

- target screen, route, component, or flow
- user task and product intent
- design source: Figma URL/node IDs, screenshots, exports, sketch, or written spec
- existing design-system and component patterns to follow
- implementation scope and explicit non-goals
- breakpoints: at least mobile and desktop, plus product-specific sizes
- states: loading, empty, error, disabled, focused, hover, selected, long content
- accessibility target: keyboard/focus, labels, contrast, tap targets
- visual evidence required: screenshots, diff, trace, or manual notes

If no design source exists, label the work as heuristic refinement and ask before claiming design-faithful implementation.

## Prompt Template

```text
Implement [screen/flow/component] for [user task]. Use [design source paths/URLs] and follow existing patterns in [files/components]. Scope is [included work]; do not change [non-goals]. Cover these states: [states]. Support [breakpoints/devices]. Verify by running [commands], starting the app, visiting [routes], exercising [flows], checking console/page errors, and capturing screenshots for [viewports]. Compare the result to [reference] when available, fix visible mismatches, and repeat until the checks pass or a blocker is recorded. Final response must include commands, exit codes, screenshot/artifact paths, skipped checks, and residual risk.
```

For a `/goal`, compress the same intent:

```text
/goal Implement [UI outcome] using [design/context sources]. Follow existing component patterns and support [states/breakpoints]. Done when the changed routes/flows pass build/static checks, browser interaction checks, responsive screenshots, console/page-error checks, and accessibility review. Record evidence in [loop-state file]. Stop and ask if design sources are missing, requirements conflict, or verification cannot run.
```

## UI Verification Ladder

1. Run static gates: install/build/typecheck/lint/format as applicable.
2. Start the app and visit changed routes.
3. Exercise the primary flow and relevant states.
4. Capture screenshots for mobile, desktop, and any product-specific breakpoint.
5. Check browser console, page errors, failed requests, and obvious layout overflow.
6. Compare against design/reference screenshots when available.
7. Run accessibility checks: automated axe/WCAG A/AA where available, plus manual keyboard and focus review. Automated a11y is not complete proof.
8. Use visual regression baselines only for stable UI; mask dynamic regions and update baselines intentionally.
9. Record traces, screenshots, HTML reports, visual diffs, console logs, axe JSON, or Lighthouse artifacts when available.

## Evidence Schema

```text
command:
exit code:
commit or diff:
route/flow:
browser:
viewport/device:
screenshot/artifact path:
console/page errors:
a11y violations:
visual diff result:
skipped checks:
residual risk:
```

Failing UI gates block "done" unless the user explicitly accepts the residual risk.

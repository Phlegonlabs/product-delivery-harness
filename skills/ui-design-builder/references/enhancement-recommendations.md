# Design Recommendations For Enhancements

Use for Web, iOS, Android and other approved UI surfaces, including a direct frontend change. Apply the same recommendation quality to initial design. This is an authoring step inside the existing intake, direction and approval gates, not a new approval workflow.

## Inspect And Recommend

1. Inspect the current affected screen and representative primary/stress cases. Record the baseline path or revision, viewport/device, content and observed problem in the Visual Preference Brief. If it cannot be inspected, record that gap instead of claiming a before/after improvement.
2. Classify the delta `none`, `style`, `structure` or `both`. Preserve unaffected requirements, screens, brand and stack decisions. A small behavioral fix does not force a redesign or reopen answered preference questions.
3. Propose concrete affected-scope improvements: composition, type hierarchy, spacing, density, control treatment, imagery, responsive reflow and useful motion. Explain the benefit, tradeoff and maintenance cost. Use `design-reference-guide.md` to inspect a few relevant current examples, including native references for native surfaces.
4. Capture explicit hero, animation and visual requests in the existing UI/MM scope and acceptance criteria. Keep each request visible in the handoff even when blocked. A request already given is not a question to ask again.
5. When the direction is clear, show one recommended change. For uncertainty or an explicit comparison request, show three materially different directions using the same approved content and cases. Record before/after paths and the specific change in the existing Direction comparison rationale. An accent-color swap does not count as a new direction; a textual moodboard does not replace rendered studies.

Structural proposals return to the affected PRD/UI Surface Contract and wireframe scope before HiFi. Style changes use the existing Style Integration and Visual Approval gates. A required framework, component-source or styling change returns to the Stack Decision Checkpoint. Do not reopen unchanged choices or invent permission to install a template.

## Composition And Hero

The reviewer shell can stay consistent while product composition changes. Choose task-fit columns, content forms, primary/secondary hierarchy and compact reflow in the wireframe. Do not use identical card wrappers or the template's example layout as the design for every product. If its renderer cannot express an approved structure, extend the canonical renderer and tests; do not silently flatten the design or modify frozen approved bytes.

For an explicit hero request, record the product message, primary action, content hierarchy, image/product-demo purpose, asset source, layout and mobile reflow in the affected UI scope. Compare product-fit treatments such as typography-led, product-demonstration-led or editorial imagery only where appropriate; these are starting examples, not a fixed catalog. Preserve existing product copy and behavior unless their owner approves the change. A native focal area, onboarding introduction or featured content treatment follows the app's task and platform conventions; do not insert a Web marketing hero automatically.

## Motion And Platform Proof

Recommend where motion helps orientation, feedback or the requested expression. Name the trigger, behavior, end state, interruption/replay rules, performance constraint and reduced-motion alternative. Web may use CSS/WAAPI or justified GSAP; iOS/Android and cross-platform clients use their approved native/framework tools. Do not select native dependencies from a CSS gallery.

In HiFi, demonstrate deterministic effects in the HTML projection and record their normal/reduced-motion observations. A required generated asset needs an authorized provider, completed output and review; a deferred placeholder is not complete. Follow `motion-and-media-routing.md` and the Required motion evidence contract.

For iOS, consider Dynamic Type, safe areas, native navigation, sheets, keyboard, gestures, VoiceOver and suitable haptics. Android uses its own adaptive layout, font scaling, navigation/back, keyboard, accessibility and animation conventions. Verify current official platform guidance for the approved OS range. HTML demonstrates design intent only; actual animation, gestures and haptics are verified in the first native implementation slice and final platform matrix. Do not require an implemented native app to approve a design projection.

At handoff, compare the explicit requests with the rendered candidate. Record delivered design evidence and remaining implementation obligations separately. Missing required hero content or motion evidence blocks completion; deferred work remains visible until an explicit scope revision accepts it.

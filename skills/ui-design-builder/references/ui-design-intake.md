# UI Design Intake

Use this intake only after Product Definition Approval. Read the PRD first and omit anything it already answers.

For an enhancement, also read `enhancement-recommendations.md`. Carry forward the owner's supplied animation, hero, reference and platform requests instead of asking them again. When preferences are already sufficiently specified, record the existing decision source and continue to the applicable authoring step; ask only unresolved decisions. No preference calls for product-fit proposals under the existing direction gate, not silent approval.

Ask one product-specific set covering:

- the human UI decision owner;
- the experience priority and validation depth;
- guided, balanced, or expert-flexible operation;
- sparse, balanced, or information-dense presentation;
- preferred navigation, layout, and interaction patterns;
- desired visual character and emotional tone;
- disliked patterns and explicit avoid rules;
- brand, color, dark-mode, typography, language, imagery, and icon constraints;
- shared brand principles and any distinct Web/native expression needs; platform destinations and stack remain the approved inputs;
- motion posture per page and whether a generation provider may be used, for which regions and within what limit (see `motion-and-media-routing.md`);
- reference images, screenshots, websites, Figma views, named products, or brand references, with the page or aspect to learn from and what to avoid; and
- whether the owner wants one recommended direction or three comparable directions.

The direction-mode rule is in `ui-design-pass.md`'s Style Intake Gate. Do not reuse a fixed aesthetic catalog. Derive the language and any choices from the product, audience, platform, tasks, content, market evidence, and existing brand. If the owner is unsure, offer two or three product-specific interpretations with a recommendation instead of generic labels such as `modern`, `clean`, or `premium`.

At unresolved intake, use Ask User (the host's user-question tool when available, otherwise ordinary conversation) to ask: "Do you have any images, screenshots, websites, Figma views or products you want us to reference? Which page or aspects should we learn from, and what should we avoid?" Adapt this wording to the product and owner's language. Reuse references and answers already supplied rather than asking again.

Text-only questions collect URLs, product names and preferences; request image attachments in ordinary conversation only when needed, never through a text-only question tool. Explicit `no references` is valid; offer relevant research and a recommendation through the existing direction gate. Silence is neither `no references` nor approval: leave optional references `not supplied` and continue independent work. Wait only for work that needs missing material, such as an explicitly requested page-faithful target.

Combine these with unresolved image and motion questions in one intake. Record existing answers in the Visual Preference Brief and its Design Brief subsection in `ui-design.md`; use `output-contract.md` for its contents. Wait only when an unanswered preference blocks authoring; do not ask again for decisions already supplied. This brief adds no separate file or approval gate, and unchanged enhancement scope does not restart intake.

The Design Brief's Page-purpose mapping is the one place to separate binding constraints from design freedom. It links each affected `UI-*` to the PRD UI Surface Contract and records page purpose, typography/headline limits, density, motion intent, exceptions and choices the design author may explore. It does not copy the PRD's per-page elements, operations, states, responsive rules or copy into a second inventory; directions and HiFi read the approved PRD directly.

Apply `page-design-profiles.md` in this same Design Brief: map affected UI IDs by page purpose, record typography/headline/density/motion choices and exceptions, and retain prior accepted decisions. Profiles guide recommendations; they do not create a second intake or choose a stack. Reference records may name a role such as composition, typography, or motion when that is the useful lesson; an avoid example needs its concrete product reason, but no reference count or role is mandatory.

Carry accepted Design Brief decisions—not merely proposed ones—into direction rationale, the selected direction, connected HiFi, H1–H9 review, and later conditional compilation or implementation. Unselected profile or direction proposals stay non-authoritative.

Product-level accessibility, responsive destinations, exact routes, required actions, states, and copy responsibilities are frozen inputs, not preference questions. If an intake answer conflicts with them or the approved stack, record the conflict and return it to `product-definition-builder` rather than resolving it inside UI design.

# README Case Library

Observed: 2026-10-04 from the pinned sources and GitHub article DOM (images, theme markup, tables, collapsible content), without theme toggles or screenshot-based visual review. The techniques below describe source structure. Borrow techniques, not another project's identity or claims. Recheck the source and its license when using assets or adapting more than a small structural pattern.

| Case | Source technique | Useful for | Adaptation check |
| --- | --- | --- | --- |
| [Starship](https://github.com/starship/starship/blob/c738efeb9fab1308bb0a8c35d72fa319aaa3f41d/README.md) | Centered identity, navigation and demonstration; installation grouped by environment | A CLI with a recognizable visual result and several supported install channels | Keep the main install route prominent; use groups only for supported alternatives. |
| [Bruno](https://github.com/usebruno/bruno/blob/7fad395d8a14d44114408e65ff620dbd8b19862f/readme.md) | Product screenshots, multilingual entry points and desktop/CLI installation routes | A branded desktop product with several audiences | Keep desktop and CLI versions/channels distinct; verify every shown capability and screenshot. |
| [Transformers](https://github.com/huggingface/transformers/blob/64f30450dbfd1d02f610ad7080535cb906637fb9/README.md) | Theme-aware identity, focused badges, installation and short task examples | A library/SDK whose examples make a broad feature set concrete | Use relevant tasks and real compatibility facts; do not inherit badges or citation claims. |
| [tldraw](https://github.com/tldraw/tldraw/blob/be38cf1f060050be8599108869fa31aae0639032/README.md) | Compact feature introduction, quickstart and links to starter kits/docs | A visual SDK or product with a fast interactive first result | Match the actual SDK package and license; confirm that linked docs and claimed files ship. |
| [Vite](https://github.com/vitejs/vite/blob/d17d739eedc4e8ede5973f1533826f27554c2078/README.md) | Brief branded introduction and a package/documentation map instead of a full manual | A tooling monorepo with separate public packages | Lead the user to the right package; keep internal packages out of public installation claims. |

## Choose A Direction

For a branded product, compose around a real product scene, concise value proposition and the fastest supported try/download path. For a CLI, let a terminal result or short recording establish the experience, then show one useful task. For an SDK, use a visual result or code-to-result example and make its runtime/import assumptions explicit.

A project may combine techniques from multiple cases. Explain why they fit its readers and assets. Use fewer sections when the docs already answer the details; richer imagery is useful only when it conveys the actual product.

## Refresh A Case

Retain the repository URL, exact README path/commit, observation date and the technique used in the target's existing task record. Mark raw-source inspection separately from rendered inspection. Changes to releases, package metadata or images need current verification; the pinned README remains a historical example, not current release authority.

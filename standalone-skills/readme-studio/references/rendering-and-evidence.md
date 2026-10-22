# Rendering And Evidence

## GitHub

Use GitHub-supported Markdown and limited HTML. A README is not a webpage: custom CSS, scripts and elaborate browser-only layouts are not a reliable delivery format.

- Use repository assets and meaningful alt text. Keep essential text outside images so readers can search, translate and access it.
- When one image fails in a theme, use `<picture>` with dark/light sources and a fallback `<img>`. Confirm every asset exists; follow [GitHub's image guidance](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github#adding-an-image-to-suit-your-visitors).
- Use [relative links](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/about-readmes#relative-links-and-image-paths-in-readme-files) for repository documents and assets. Verify case-sensitive paths and heading anchors in the target renderer.
- Use [`<details>` / `<summary>`](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections) for secondary detail. Keep the primary install/try path visible. Leave blank lines around Markdown inside the block.
- Keep tables readable at narrow widths; a large compatibility matrix can belong in linked docs. Image sizing must remain legible on mobile.

## Package Registry Surfaces

Treat the repository README and the registry presentation as distinct destinations. Inspect the registry's actual renderer, package landing page and packed files. A GitHub-rendered relative image may fail when the same text is rendered outside the repository.

Keep the source README canonical unless the project already maintains a package-specific version. When a derived copy is necessary, reuse the same prose and convert only destination-specific links/assets with the project's existing tooling. Verify it inside the built package; do not create a second independent writing source.

For npm, inspect the [package README guidance](https://docs.npmjs.com/about-package-readme-files). For Python, reconcile `readme` metadata and content type with the [packaging tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/). For Rust, inspect the [`readme` manifest field](https://doc.rust-lang.org/cargo/reference/manifest.html#the-readme-field). Each registry needs its own observed result; do not claim identical rendering from GitHub alone.

Including an image in a package does not prove that the registry serves its relative URL; use an approved stable absolute HTTPS image URL or a destination route verified in the actual renderer, and check image hosting separately from package inclusion.

After reviewing build hooks, confirm the README and any promised assets are inside the built artifact through the project's native pack or list route, or `release-packager` when present. This validates distribution facts; the destination renderer remains a separate check.

## Media And Claims

Prefer real product captures and existing licensed brand assets. A concept illustration can support the brand, but label it when it could be mistaken for implemented UI. Ask for missing required screenshots instead of substituting unrelated imagery. Do not fabricate users, endorsements, benchmark results or release availability.

Record the changed README/assets and renderer inspected. Capture matching before/after views, light/dark mode where relevant, and at least a narrow and wide view for presentation changes. For changed GIF/video timing, include a short recording; a still does not prove motion. Link the evidence with the delivery. Reuse an observed preview where possible and follow the target's finite service lifetime/cleanup rules.

If rendering, runtime or publication cannot be checked, name the missing capability and retain the actual source/preview evidence. Do not upload, push or publish solely to obtain a screenshot without the required authority.

# Launch checklist

Before enabling the public release:

- In **Settings → Pages**, set the source to **GitHub Actions**.
- Confirm the `Deploy GitHub Pages` workflow completed successfully on `main`.
- Open <https://macplol.github.io/puerto-rico-heat-atlas-ai/> and a shared query-string URL; verify the map boundary, station data, controls, and favicon load.
- Confirm the canonical URL, `robots.txt`, and `sitemap.xml` use the production GitHub Pages URL.
- Confirm OpenStreetMap attribution remains visible and that the interface does not describe official heat index, WBGT, forecasts, or medical-risk categories.

This release deliberately has no `og:image`: no reliable social-preview image has been generated. Add one only when a production-quality, committed image is available.

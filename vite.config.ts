import { defineConfig } from 'vitest/config';

// Local development and previews use the site root. The deployment workflow uses
// the explicit github-pages mode so emitted asset URLs include the repository path.
export default defineConfig(({ mode }) => ({ base: mode === 'github-pages' ? '/puerto-rico-heat-atlas-ai/' : '/', build: { assetsInlineLimit: 0 }, assetsInclude: ['**/*.geojson'], test: { environment: 'node', include: ['src/**/*.test.ts'] } }));

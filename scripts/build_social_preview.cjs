// Native SVG layout using the existing brand mark; rasterize for GitHub Settings.
const fs = require('node:fs');
const path = require('node:path');
const {Resvg} = require(path.resolve('.build-check/node_modules/@resvg/resvg-js'));
const mark = fs.readFileSync('docs/assets/breadcrumbs-mark-transparent.png').toString('base64');
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="640" viewBox="0 0 1280 640">
<rect width="1280" height="640" fill="#fffaf0"/>
<rect x="42" y="42" width="1196" height="556" rx="28" fill="#ffffff" stroke="#eadfc7" stroke-width="2"/>
<image href="data:image/png;base64,${mark}" x="858" y="105" width="300" height="260"/>
<g font-family="Arial, sans-serif" fill="#10273b">
<text x="100" y="140" font-size="22" font-weight="700" letter-spacing="3" fill="#8b5a00">LOCAL-FIRST Â· NO ACCOUNT</text>
<text x="96" y="242" font-size="78" font-weight="800">Breadcrumbs</text>
<text x="100" y="303" font-size="29">A terminal-first productivity timer.</text>
<text x="100" y="349" font-size="25" fill="#516170">Keep your goals in view.</text>
<text x="100" y="387" font-size="25" fill="#516170">See where your attention trails off.</text>
</g>
<rect x="100" y="447" width="615" height="68" rx="12" fill="#10273b"/>
<text x="126" y="490" font-family="Consolas, Arial, sans-serif" font-size="25" fill="#ffbb35">$ pipx install breadcrumbst</text>
<path d="M895 433v80m0-40h65m-65 40h140" fill="none" stroke="#e4a21c" stroke-width="5"/>
<g fill="#fffaf0" stroke="#10273b" stroke-width="5"><circle cx="895" cy="433" r="10"/><circle cx="960" cy="473" r="10"/><circle cx="1035" cy="513" r="10"/></g>
<text x="100" y="558" font-family="Arial, sans-serif" font-size="18" fill="#64717a">Timer Â· Intentions Â· Your local activity trail</text>
</svg>`;
fs.writeFileSync('docs/assets/breadcrumbs-social-preview.png', new Resvg(svg, {font:{loadSystemFonts:true}}).render().asPng());
console.log('Wrote docs/assets/breadcrumbs-social-preview.png');


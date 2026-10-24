// Development-only: print masks regenerated from the checked-in source SVGs.
// Run from the repository root:
// node breadcrumbs/assets/brands/rasterize.cjs ./.build-check/node_modules/@resvg/resvg-js
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const modulePath = process.argv[2];
const { Resvg } = require(modulePath ? path.resolve(modulePath) : '@resvg/resvg-js');
const masks = {};
for (const file of fs.readdirSync(__dirname).filter(name => name.endsWith('.svg')).sort()) {
  const svg = fs.readFileSync(path.join(__dirname, file), 'utf8').replace(/\r\n/g, '\n');
  const output = { source_sha256: crypto.createHash('sha256').update(svg).digest('hex') };
  for (const size of [16, 4]) {
    const image = new Resvg(svg, { fitTo: { mode: 'width', value: size }, font: { loadSystemFonts: false } }).render();
    const rows = [];
    for (let y = 0; y < size; y++) {
      let mask = 0;
      for (let x = 0; x < size; x++) {
        const threshold = size === 4 ? 24 : 96;
        if (image.pixels[(y * size + x) * 4 + 3] >= threshold) mask |= (1 << (size - x - 1));
      }
      rows.push(mask.toString(16).padStart(size / 4, '0'));
    }
    output[String(size)] = rows;
  }
  masks[path.basename(file, '.svg')] = output;
}
process.stdout.write(JSON.stringify(masks, null, 2) + '\n');

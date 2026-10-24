// Optional documentation renderer. No Node dependency is needed to run Breadcrumbs.
const fs = require("node:fs");
const path = require("node:path");

let Resvg;
try {
  ({ Resvg } = require("../.build-check/node_modules/@resvg/resvg-js"));
} catch (error) {
  console.error("Install the documentation renderer first:");
  console.error("npm install --prefix .build-check --no-save --package-lock=false @resvg/resvg-js");
  process.exit(1);
}

const directory = path.resolve(__dirname, "../docs/assets");
const basename = process.argv[2] || "breadcrumbs-focus";
if (!/^[a-z0-9-]+$/.test(basename)) {
  throw new Error("Use a screenshot basename such as focus-branches.");
}
const font = process.platform === "win32" ? "Consolas" : process.platform === "darwin" ? "Menlo" : "DejaVu Sans Mono";
const image = new Resvg(fs.readFileSync(path.join(directory, basename + ".svg")), {
  font: { loadSystemFonts: true, defaultFontFamily: font, monospaceFamily: font },
}).render();
fs.writeFileSync(path.join(directory, basename + ".png"), image.asPng());
console.log(`Rendered docs/assets/${basename}.png (${image.width} × ${image.height})`);

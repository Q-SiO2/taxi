/* Render the SVG masters that require PNG handoff exports.

   This design-time tool is not part of the application build. It expects the
   Playwright package and a locally installed Chromium browser:

     npm install --no-save playwright
     npx playwright install chromium
     node assets/tools/export_svg_rasters.cjs
*/

const fs = require("node:fs");
const path = require("node:path");
const playwrightModule = process.env.TAXI_PLAYWRIGHT_MODULE || "playwright";
const { chromium } = require(playwrightModule);

const assetRoot = path.resolve(__dirname, "..");
const jobs = [
  {
    source: "brand/logo/brand_logo_mark.svg",
    destination: "brand/logo/exports/brand_logo_mark",
    sizes: [512, 1024],
  },
  {
    source: "vehicles/markers/vehicle_marker_standard.svg",
    destination: "vehicles/markers/exports/vehicle_marker_standard",
    sizes: [128, 256, 512],
  },
  {
    source: "vehicles/markers/vehicle_marker_large.svg",
    destination: "vehicles/markers/exports/vehicle_marker_large",
    sizes: [128, 256, 512],
  },
];

// Exact SVG-master exports, not new designs. Preserve the rectangular viewBox;
// using a square image here would shrink the illustration and change its layout.
const runtimeJobs = [
  {
    source: "illustrations/onboarding/source/illustration_landing_navy_outline_master.png",
    destination: "illustrations/onboarding/exports/illustration_landing_runtime",
    copyOnly: true,
    runtimeMirror: "illustration_landing_runtime.png",
  },
  {
    source: "brand/logo/brand_logo_mark.svg",
    destination: "brand/logo/exports/brand_logo_mark_runtime",
    dimensions: [{ width: 256, height: 256, suffix: "" }],
    runtimeMirror: "brand_logo_mark_runtime.png",
  },
  {
    source: "vehicles/renders/vehicle_silhouette_standard.svg",
    destination: "vehicles/renders/exports/vehicle_silhouette_standard_runtime",
    dimensions: [{ width: 640, height: 360, suffix: "" }],
    runtimeMirror: "vehicle_silhouette_standard_runtime.png",
  },
];

// The owner selected a generated thin-line portrait, not the rejected vector
// candidate. Copy its pixels unchanged: no crop, stretch, recolour or re-render.

async function renderJob(browser, job) {
  const sourcePath = path.join(assetRoot, job.source);
  if (job.copyOnly) {
    const destination = path.join(assetRoot, `${job.destination}.png`);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(sourcePath, destination);
    const mirror = path.resolve(assetRoot, "../TaxiMobile/shared/src/commonMain/composeResources/drawable", job.runtimeMirror);
    fs.copyFileSync(destination, mirror);
    console.log(`copied selected portrait and mirrored ${job.runtimeMirror}`);
    return;
  }
  const svg = fs.readFileSync(sourcePath, "utf8");

  const dimensions = job.dimensions || job.sizes.map((size) => ({ width: size, height: size, suffix: `_${size}` }));
  for (const { width, height, suffix } of dimensions) {
    const destination = path.join(assetRoot, `${job.destination}${suffix}.png`);
    fs.mkdirSync(path.dirname(destination), { recursive: true });

    const page = await browser.newPage({
      viewport: { width, height },
      deviceScaleFactor: 1,
    });
    await page.setContent(
      `<!doctype html><html><head><style>
        html, body { width: 100%; height: 100%; margin: 0; background: transparent; overflow: hidden; }
        svg { display: block; width: 100vw; height: 100vh; }
      </style></head><body>${svg}</body></html>`,
      { waitUntil: "load" },
    );
    await page.screenshot({ path: destination, omitBackground: true });
    await page.close();
    console.log(`wrote ${path.relative(path.dirname(assetRoot), destination)}`);
    if (job.runtimeMirror) {
      const mirror = path.resolve(assetRoot, "../TaxiMobile/shared/src/commonMain/composeResources/drawable", job.runtimeMirror);
      fs.copyFileSync(destination, mirror);
      console.log(`mirrored ${job.runtimeMirror}`);
    }
  }
}

function walkSvgFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "exports" || entry.name === "tools") return [];
      return walkSvgFiles(entryPath);
    }
    return entry.isFile() && entry.name.endsWith(".svg") ? [entryPath] : [];
  });
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function renderCatalog(browser) {
  const cards = walkSvgFiles(assetRoot)
    .sort()
    .map((sourcePath) => {
      const title = path.relative(assetRoot, sourcePath).replaceAll("\\", "/");
      return `<article><div class="art">${fs.readFileSync(sourcePath, "utf8")}</div><p>${escapeHtml(title)}</p></article>`;
    });

  for (const name of ["standard", "large"]) {
    const sourcePath = path.join(
      assetRoot,
      "vehicles",
      "renders",
      "exports",
      `vehicle_render_${name}_512.png`,
    );
    const data = fs.readFileSync(sourcePath).toString("base64");
    cards.push(
      `<article><div class="art"><img src="data:image/png;base64,${data}"></div>` +
      `<p>vehicles/renders/exports/vehicle_render_${name}_512.png</p></article>`,
    );
  }

  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  await page.setContent(`<!doctype html><html><head><style>
    * { box-sizing: border-box; }
    body { margin: 0; padding: 28px; color: #0B1F3A; background: #F7F9FC; font-family: Arial, sans-serif; }
    header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 22px; }
    h1 { margin: 0; font-size: 25px; }
    header p { margin: 0; color: #52677F; font-size: 13px; }
    main { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
    article { min-width: 0; height: 190px; padding: 12px; border: 1px solid #DCE5EF; border-radius: 14px; background: #FFFFFF; }
    .art { display: flex; align-items: center; justify-content: center; width: 100%; height: 140px; overflow: hidden; }
    .art svg, .art img { display: block; max-width: 100%; max-height: 132px; width: auto; height: auto; }
    article p { margin: 8px 0 0; overflow: hidden; color: #52677F; font-size: 10px; line-height: 1.25; text-overflow: ellipsis; white-space: nowrap; }
  </style></head><body><header><h1>TaxiMobile asset catalog</h1><p>Editable masters and 512 px vehicle renders</p></header><main>${cards.join("")}</main></body></html>`);
  await page.screenshot({ path: path.join(assetRoot, "asset_catalog.png"), fullPage: true });
  await page.close();
  console.log("wrote assets/asset_catalog.png");
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.TAXI_ASSET_BROWSER_PATH || undefined,
  });
  try {
    const runtimeOnly = process.argv.includes("--runtime-only");
    for (const job of runtimeOnly ? runtimeJobs : [...jobs, ...runtimeJobs]) {
      await renderJob(browser, job);
    }
    if (!runtimeOnly) await renderCatalog(browser);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

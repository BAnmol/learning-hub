// Bundles CodeMirror 6 (+ the Python language, autocomplete, and one-dark theme
// packages) into a single local ESM file at static/js/vendor/codemirror-bundle.js.
//
// Why: static/js/modules/editor.js used to import each CodeMirror sub-package
// from its own jsdelivr `+esm` URL. jsdelivr does not deduplicate shared
// dependencies ACROSS independent package URLs, so @codemirror/state,
// @codemirror/view, and @codemirror/language each loaded as multiple,
// mutually-incompatible versions in the browser. CodeMirror uses identity/
// instanceof checks internally, so this surfaced as a hard runtime crash
// ("Unrecognized extension value in extension set") the moment the editor
// tried to mount — which in turn broke Studio's problem list, since that
// crash happened inside the same synchronous setup function that loads it.
//
// Bundling locally with esbuild resolves every CodeMirror package through
// ONE npm dependency tree, so they necessarily share the same instances.
//
// Usage:
//   npm install
//   npm run build:editor
import { build } from "esbuild";
import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");

await build({
    entryPoints: [path.join(__dirname, "codemirror_bundle_entry.js")],
    bundle: true,
    format: "esm",
    minify: true,
    sourcemap: true,
    target: "es2020",
    outfile: path.join(projectRoot, "static", "js", "vendor", "codemirror-bundle.js"),
    logLevel: "info",
});

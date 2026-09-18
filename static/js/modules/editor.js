// ============================================================================
// editor.js — CodeMirror 6 Python Editor wrapper
// Provides: syntax highlighting, bracket auto-close, keyword autocomplete,
// line numbers, indent with Tab, and Ctrl+Enter run shortcut.
//
// Usage:
//   import { createPythonEditor, getEditorValue, setEditorValue } from './editor.js';
//   const view = createPythonEditor(hostElement, { initialValue, onChange });
// ============================================================================

// ─── Locally-bundled CodeMirror 6 (see scripts/build_codemirror_bundle.mjs) ─
// This used to import each CodeMirror sub-package from its own jsdelivr
// `+esm` URL. jsdelivr does not deduplicate shared dependencies ACROSS
// independent package URLs, so @codemirror/state/@codemirror/view/
// @codemirror/language each loaded as multiple, mutually-incompatible
// versions — CodeMirror's internal identity checks then threw
// "Unrecognized extension value in extension set" the instant the editor
// tried to mount, which broke Studio's problem list (that crash happened
// inside the same synchronous setup path that loads it). Bundling locally
// resolves every package through one npm tree, so they share one instance.
// Re-run `npm install && npm run build:editor` after bumping any version below.
import {
    EditorView, basicSetup, python, keymap, defaultKeymap, indentWithTab,
    autocompletion, closeBrackets, closeBracketsKeymap, completionKeymap,
    EditorState, Compartment, oneDark,
} from "../vendor/codemirror-bundle.js";

// ─── Python keyword / builtin autocomplete completions ─────────────────────
const PYTHON_KEYWORDS = [
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield"
];

const PYTHON_BUILTINS = [
    "abs", "all", "any", "bin", "bool", "breakpoint", "bytearray", "bytes",
    "callable", "chr", "compile", "complex", "copyright", "credits", "delattr",
    "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter", "float",
    "format", "frozenset", "getattr", "globals", "hasattr", "hash", "help",
    "hex", "id", "input", "int", "isinstance", "issubclass", "iter", "len",
    "list", "locals", "map", "max", "memoryview", "min", "next", "object",
    "oct", "open", "ord", "pow", "print", "property", "range", "repr",
    "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod",
    "str", "sum", "super", "tuple", "type", "vars", "zip",
    // Common DS/Algo helpers
    "collections", "defaultdict", "OrderedDict", "Counter", "deque",
    "heapq", "heappush", "heappop", "heapify", "bisect", "bisect_left",
    "bisect_right", "math", "inf", "sys", "maxsize",
    // Common patterns
    "self", "cls", "__init__", "__repr__", "__str__", "__len__",
    "append", "extend", "insert", "remove", "pop", "clear", "index",
    "count", "sort", "reverse", "copy", "keys", "values", "items",
    "get", "update", "add", "discard", "union", "intersection",
    "split", "join", "strip", "replace", "upper", "lower", "startswith",
    "endswith", "find", "format", "encode", "decode"
];

const DSA_SNIPPETS = [
    { label: "def solution", detail: "Define solution function", type: "function",
      apply: "def solution(self):\n    " },
    { label: "Two Pointer", detail: "Classic two pointer pattern", type: "text",
      apply: "left, right = 0, len(nums) - 1\nwhile left < right:\n    " },
    { label: "Binary Search", detail: "Binary search template", type: "text",
      apply: "lo, hi = 0, len(nums) - 1\nwhile lo <= hi:\n    mid = (lo + hi) // 2\n    if nums[mid] == target:\n        return mid\n    elif nums[mid] < target:\n        lo = mid + 1\n    else:\n        hi = mid - 1\nreturn -1" },
    { label: "BFS Template", detail: "Breadth-first search", type: "text",
      apply: "from collections import deque\nqueue = deque([start])\nvisited = {start}\nwhile queue:\n    node = queue.popleft()\n    for neighbor in graph[node]:\n        if neighbor not in visited:\n            visited.add(neighbor)\n            queue.append(neighbor)" },
    { label: "DFS Template", detail: "Depth-first search recursive", type: "text",
      apply: "def dfs(node, visited):\n    if node in visited:\n        return\n    visited.add(node)\n    for neighbor in graph[node]:\n        dfs(neighbor, visited)" },
    { label: "Sliding Window", detail: "Sliding window pattern", type: "text",
      apply: "left = 0\nfor right in range(len(nums)):\n    # expand window\n    while condition_broken:\n        # shrink window\n        left += 1\n    # update result" },
    { label: "Heap Push", detail: "heapq push", type: "function",
      apply: "heapq.heappush(heap, val)" },
    { label: "Heap Pop", detail: "heapq pop", type: "function",
      apply: "heapq.heappop(heap)" },
    { label: "defaultdict", detail: "collections.defaultdict", type: "function",
      apply: "from collections import defaultdict\nd = defaultdict(list)" },
    { label: "Counter", detail: "collections.Counter", type: "function",
      apply: "from collections import Counter\ncount = Counter(nums)" },
];

function pythonCompletions(context) {
    const word = context.matchBefore(/\w*/);
    if (!word || (word.from === word.to && !context.explicit)) return null;

    const query = word.text.toLowerCase();

    const keywordOptions = PYTHON_KEYWORDS
        .filter(k => k.toLowerCase().startsWith(query))
        .map(k => ({ label: k, type: "keyword" }));

    const builtinOptions = PYTHON_BUILTINS
        .filter(b => b.toLowerCase().startsWith(query) && !PYTHON_KEYWORDS.includes(b))
        .map(b => ({ label: b, type: "function" }));

    const snippetOptions = DSA_SNIPPETS
        .filter(s => s.label.toLowerCase().includes(query))
        .map(s => ({ ...s }));

    return {
        from: word.from,
        options: [...snippetOptions, ...keywordOptions, ...builtinOptions],
        validFor: /^\w*$/
    };
}

// ─── Theme — adapts to CSS custom properties for light/dark ────────────────
function makeBrainfreezeEditorTheme() {
    return EditorView.theme({
        "&": {
            height: "100%",
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
            fontSize: "14px",
            lineHeight: "1.6",
            // Baseline chrome for BOTH themes — in dark mode `oneDark`'s own
            // background/token colors are layered on top of this and win;
            // in light mode oneDark is omitted entirely, so this is what
            // actually renders (see pickDarkSyntaxExtension() below).
            backgroundColor: "var(--code-bg)",
            color: "var(--code-text)",
        },
        ".cm-scroller": { overflow: "auto" },
        ".cm-content": {
            padding: "12px 8px",
            caretColor: "var(--accent)",
        },
        ".cm-cursor": { borderLeftColor: "var(--accent)" },
        ".cm-activeLine": { backgroundColor: "rgba(134,187,189,0.06)" },
        ".cm-activeLineGutter": { backgroundColor: "rgba(134,187,189,0.06)" },
        ".cm-gutters": {
            backgroundColor: "var(--code-bg, #140C12)",
            color: "var(--text-muted)",
            border: "none",
            borderRight: "1px solid var(--border)",
            minWidth: "40px",
        },
        ".cm-lineNumbers .cm-gutterElement": {
            padding: "0 8px 0 4px",
            fontSize: "0.78rem",
        },
        ".cm-tooltip": {
            background: "var(--surface-2)",
            border: "1px solid var(--border-strong)",
            borderRadius: "8px",
            boxShadow: "var(--shadow-md)",
            color: "var(--text-primary)",
        },
        ".cm-tooltip-autocomplete > ul": {
            maxHeight: "220px",
        },
        ".cm-tooltip-autocomplete > ul > li": {
            padding: "4px 12px",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "0.82rem",
        },
        ".cm-tooltip-autocomplete > ul > li[aria-selected]": {
            background: "var(--accent-soft)",
            color: "var(--accent)",
        },
        ".cm-tooltip-autocomplete .cm-completionLabel": {
            color: "var(--text-primary)",
        },
        ".cm-tooltip-autocomplete .cm-completionDetail": {
            color: "var(--text-muted)",
            fontSize: "0.75rem",
        },
        ".cm-matchingBracket": {
            background: "rgba(134,187,189,0.22)",
            outline: "1px solid var(--accent)",
            borderRadius: "2px",
        },
        ".cm-selectionBackground, &.cm-focused .cm-selectionBackground": {
            background: "rgba(134,187,189,0.18) !important",
        },
        "&.cm-focused": {
            outline: "none",
        },
    });
}

// ─── Public API ─────────────────────────────────────────────────────────────

/**
 * Create a CodeMirror 6 Python editor.
 * @param {HTMLElement} mountEl - The DOM element to mount into.
 * @param {object} options
 * @param {string} options.initialValue - Initial code string.
 * @param {function} [options.onChange] - Called with new value on every change.
 * @param {function} [options.onRunShortcut] - Ctrl+Enter callback.
 * @param {function} [options.onSubmitShortcut] - Ctrl+Shift+Enter callback.
 * @param {boolean} [options.readOnly] - Makes the editor read-only.
 * @returns {EditorView}
 */
const themeCompartment = new Compartment();

/** oneDark is a genuinely dark theme (background, gutters, token colors) — only
 *  appropriate when the site itself is in dark mode. In light mode we omit it
 *  entirely and let CodeMirror's own basicSetup default highlighting (already
 *  light-appropriate) show through, styled by makeBrainfreezeEditorTheme()'s CSS-variable
 *  chrome above — otherwise code text renders dark-on-dark against the light page. */
function pickSyntaxExtension() {
    const theme = document.documentElement.getAttribute("data-theme") || "dark";
    return theme === "light" ? [] : [oneDark];
}

export function createPythonEditor(mountEl, {
    initialValue = "",
    onChange = null,
    onRunShortcut = null,
    onSubmitShortcut = null,
    readOnly = false,
} = {}) {
    const customKeymap = [];

    if (onRunShortcut) {
        customKeymap.push({
            key: "Ctrl-Enter",
            run: () => { onRunShortcut(); return true; }
        });
    }
    if (onSubmitShortcut) {
        customKeymap.push({
            key: "Ctrl-Shift-Enter",
            run: () => { onSubmitShortcut(); return true; }
        });
    }

    const extensions = [
        basicSetup,
        python(),
        closeBrackets(),
        autocompletion({ override: [pythonCompletions], activateOnTyping: true }),
        keymap.of([
            ...closeBracketsKeymap,
            ...completionKeymap,
            indentWithTab,
            ...defaultKeymap,
            ...customKeymap,
        ]),
        makeBrainfreezeEditorTheme(),
        themeCompartment.of(pickSyntaxExtension()),
        EditorView.lineWrapping,
    ];

    if (readOnly) {
        extensions.push(EditorState.readOnly.of(true));
    }

    if (onChange) {
        extensions.push(EditorView.updateListener.of((update) => {
            if (update.docChanged) {
                onChange(update.state.doc.toString());
            }
        }));
    }

    const state = EditorState.create({
        doc: initialValue,
        extensions,
    });

    const view = new EditorView({ state, parent: mountEl });
    return view;
}

/**
 * Get the current content of a CodeMirror view.
 * @param {EditorView} view
 * @returns {string}
 */
export function getEditorValue(view) {
    return view ? view.state.doc.toString() : "";
}

/**
 * Set new content in a CodeMirror view (replaces all content).
 * @param {EditorView} view
 * @param {string} value
 */
export function setEditorValue(view, value) {
    if (!view) return;
    view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: value ?? "" }
    });
}

/**
 * Make editor read-only or editable.
 * @param {EditorView} view
 * @param {boolean} readonly
 */
export function setEditorReadOnly(view, readonly) {
    if (!view) return;
    view.dispatch({
        effects: EditorState.readOnly.reconfigure(readonly)
    });
}

/**
 * Re-apply the dark/light syntax theme after the site theme was toggled.
 * Call this on every live CodeMirror view whenever data-theme changes —
 * the editor is created once and reused across problems, so without this
 * it would stay stuck in whichever theme was active when it was mounted.
 * @param {EditorView} view
 */
export function refreshEditorTheme(view) {
    if (!view) return;
    view.dispatch({
        effects: themeCompartment.reconfigure(pickSyntaxExtension())
    });
}

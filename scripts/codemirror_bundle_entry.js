// Entry point for the local CodeMirror 6 bundle (see build_codemirror_bundle.mjs).
// Re-exports exactly what static/js/modules/editor.js needs, all resolved through
// ONE npm dependency tree so every package shares the same instances of
// @codemirror/state, @codemirror/view, and @codemirror/language — the thing
// independent CDN <script> imports could not guarantee.
export { EditorView, basicSetup } from "codemirror";
export { python } from "@codemirror/lang-python";
export { keymap } from "@codemirror/view";
export { defaultKeymap, indentWithTab } from "@codemirror/commands";
export { autocompletion, closeBrackets, closeBracketsKeymap, completionKeymap } from "@codemirror/autocomplete";
export { EditorState, Compartment } from "@codemirror/state";
export { oneDark } from "@codemirror/theme-one-dark";

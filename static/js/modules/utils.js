// ============================================================================
// Shared helpers used by every feature module.
// ============================================================================

/** Escape untrusted text before dropping it into innerHTML. */
export function escapeHtml(str) {
    if (!str) return "";
    return String(str).replace(/[&<>'"]/g, (tag) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
    }[tag] || tag));
}

/**
 * fetch() wrapper for the platform's JSON APIs. Every service endpoint is
 * login-gated server-side (401 + {auth_required:true} when signed out), so
 * this is the single choke point that notices that and tells the rest of
 * the app about it — feature modules never need to know about auth.
 */
export async function apiFetch(url, options = {}) {
    const res = await fetch(url, options);
    if (res.status === 401) {
        document.dispatchEvent(new CustomEvent("app:auth-required"));
    }
    return res;
}

/** apiFetch() + JSON body parsing, for the common case. */
export async function apiJson(url, options = {}) {
    const res = await apiFetch(url, options);
    try {
        return await res.json();
    } catch (err) {
        return { success: false, error: "Invalid server response." };
    }
}

/**
 * Lightweight markdown and math formatter for problem statements and AI-generated
 * text. The input is HTML-escaped first (none of the markdown syntax below relies
 * on `&<>'"`, so escaping first doesn't break any of the regex passes) so raw HTML/
 * script content coming from problem data or an LLM response can never execute when
 * the result is assigned to innerHTML.
 */
export function formatMarkdown(md) {
    if (!md) return "";
    let html = escapeHtml(md);

    // Display Math: $$ ... $$ (content is already escaped as part of `html` above)
    html = html.replace(/\$\$([\s\S]*?)\$\$/g, (match, math) => {
        return `<div class="math-block"><code>${math.trim()}</code></div>`;
    });

    // Inline Math: $ ... $ (content is already escaped as part of `html` above)
    html = html.replace(/\$([^\$\n]+?)\$/g, (match, math) => {
        return `<span class="math-inline"><code>${math.trim()}</code></span>`;
    });

    // Headings
    html = html.replace(/^### (.*$)/gim, '<h4 class="md-h4">$1</h4>');
    html = html.replace(/^#### (.*$)/gim, '<h5 class="md-h5">$1</h5>');

    // Bold / Italic
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Code blocks & inline code
    html = html.replace(/```python([\s\S]*?)```/g, '<pre class="code-preview"><code>$1</code></pre>');
    html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');

    // Unordered lists
    html = html.replace(/^\s*-\s+(.*$)/gim, '<li class="md-li">$1</li>');

    // Paragraphs
    const lines = html.split("\n\n");
    html = lines.map(block => {
        block = block.trim();
        if (!block) return "";
        if (block.startsWith("<h") || block.startsWith("<div") || block.startsWith("<pre") || block.startsWith("<li")) {
            return block;
        }
        return `<p class="md-p">${block.replace(/\n/g, "<br>")}</p>`;
    }).join("\n");

    return html;
}

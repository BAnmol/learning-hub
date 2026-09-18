// ============================================================================
// Algorithm Visualizer — a small, reusable step-player plus a handful of
// hand-built renderers (array / linked-list / stack / tree / graph / grid)
// and one genuine, correct worked demo per curriculum topic.
//
// This is topic-driven, not per-problem: every problem already carries a
// `topic` field (Arrays, Binary Search, Trees + BST, ...), and every topic
// maps to exactly one renderer + one concrete algorithm walkthrough here —
// so every one of the 325 problems gets a real, working animation the
// moment this module loads, with no per-problem authoring required.
// ============================================================================

// ----------------------------------------------------------------------
// Renderers — each takes a container element and a step object, and draws
// that single frame. Kept intentionally simple (DOM for grid/array/stack,
// inline SVG for the node-link ones) so the whole engine stays dependency-free.
// ----------------------------------------------------------------------

const Renderers = {
    array(container, step) {
        const cellCount = step.values.length;
        container.innerHTML = `
            <div class="viz-array-row">
                ${step.values.map((v, i) => `
                    <div class="viz-array-cell-wrap">
                        <div class="viz-array-cell viz-role-${(step.roles && step.roles[i]) || "idle"}">${escapeVal(v)}</div>
                        <div class="viz-array-index">${i}</div>
                        ${step.labels && step.labels[i] ? `<div class="viz-array-label">${escapeVal(step.labels[i])}</div>` : ""}
                    </div>
                `).join("")}
            </div>
        `;
        container.style.setProperty("--viz-cell-count", cellCount);
    },

    grid(container, step) {
        const { rows, cols, values, activeCell, dependencyCells } = step;
        const isActive = (r, c) => activeCell && activeCell[0] === r && activeCell[1] === c;
        const isDep = (r, c) => (dependencyCells || []).some((d) => d[0] === r && d[1] === c);
        let html = `<div class="viz-grid" style="grid-template-columns: repeat(${cols}, 1fr);">`;
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const v = values[r][c];
                const cls = isActive(r, c) ? "viz-role-active" : isDep(r, c) ? "viz-role-dependency" : v !== null ? "viz-role-visited" : "viz-role-idle";
                html += `<div class="viz-grid-cell ${cls}">${v === null ? "" : escapeVal(v)}</div>`;
            }
        }
        html += `</div>`;
        container.innerHTML = html;
    },

    stack(container, step) {
        const items = step.items || [];
        container.innerHTML = `
            <div class="viz-stack-wrap">
                <div class="viz-stack">
                    ${items.slice().reverse().map((v, ri) => {
                        const isTop = ri === 0;
                        return `<div class="viz-stack-item ${isTop && step.highlightTop ? "viz-role-active" : "viz-role-visited"}">${escapeVal(v)}</div>`;
                    }).join("")}
                </div>
                ${items.length === 0 ? '<div class="viz-empty-hint">empty</div>' : '<div class="viz-stack-base">base</div>'}
            </div>
        `;
    },

    linkedlist(container, step) {
        const nodes = step.nodes;
        const pointerLabel = (id) => (step.pointers && step.pointers[id]) ? step.pointers[id].join(" / ") : "";
        let html = `<div class="viz-ll-row">`;
        nodes.forEach((n, i) => {
            const role = n.role || "idle";
            html += `
                <div class="viz-ll-node-wrap">
                    ${pointerLabel(n.id) ? `<div class="viz-ll-pointer">${pointerLabel(n.id)}</div>` : '<div class="viz-ll-pointer">&nbsp;</div>'}
                    <div class="viz-ll-node viz-role-${role}">${escapeVal(n.val)}</div>
                </div>
                ${i < nodes.length - 1 ? '<div class="viz-ll-arrow">&#8594;</div>' : '<div class="viz-ll-arrow">&#8594; null</div>'}
            `;
        });
        html += `</div>`;
        container.innerHTML = html;
    },

    tree(container, step) {
        const byId = {};
        step.nodes.forEach((n) => { byId[n.id] = n; });
        const root = step.nodes.find((n) => n.isRoot) || step.nodes[0];

        // Simple recursive layout: x by in-order position, y by depth.
        const positions = {};
        let cursor = 0;
        const LEVEL_H = 62;
        const NODE_GAP = 54;

        function layout(id, depth) {
            if (id === null || id === undefined || !byId[id]) return;
            const node = byId[id];
            layout(node.left, depth + 1);
            positions[id] = { x: cursor * NODE_GAP + 30, y: depth * LEVEL_H + 26 };
            cursor += 1;
            layout(node.right, depth + 1);
        }
        layout(root.id, 0);

        const width = Math.max(cursor * NODE_GAP + 30, 160);
        const height = Object.values(positions).reduce((m, p) => Math.max(m, p.y), 0) + 40;

        let edges = "";
        let nodesSvg = "";
        step.nodes.forEach((n) => {
            const p = positions[n.id];
            if (!p) return;
            [n.left, n.right].forEach((childId) => {
                if (childId !== null && childId !== undefined && positions[childId]) {
                    const cp = positions[childId];
                    edges += `<line x1="${p.x}" y1="${p.y}" x2="${cp.x}" y2="${cp.y}" class="viz-tree-edge" />`;
                }
            });
        });
        step.nodes.forEach((n) => {
            const p = positions[n.id];
            if (!p) return;
            const role = n.id === step.activeId ? "active" : (step.visitedIds || []).includes(n.id) ? "visited" : "idle";
            nodesSvg += `
                <circle cx="${p.x}" cy="${p.y}" r="18" class="viz-tree-node viz-role-${role}" />
                <text x="${p.x}" y="${p.y + 5}" text-anchor="middle" class="viz-tree-text">${escapeVal(n.val)}</text>
            `;
        });

        container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" class="viz-tree-svg">${edges}${nodesSvg}</svg>`;
    },

    graph(container, step) {
        const byId = {};
        step.nodes.forEach((n) => { byId[n.id] = n; });
        const width = Math.max(...step.nodes.map((n) => n.x)) + 40;
        const height = Math.max(...step.nodes.map((n) => n.y)) + 40;

        let edges = "";
        step.edges.forEach(([a, b]) => {
            const na = byId[a], nb = byId[b];
            if (!na || !nb) return;
            edges += `<line x1="${na.x}" y1="${na.y}" x2="${nb.x}" y2="${nb.y}" class="viz-graph-edge" />`;
        });

        let nodesSvg = "";
        step.nodes.forEach((n) => {
            let role = "idle";
            if (n.id === step.activeId) role = "active";
            else if ((step.frontierIds || []).includes(n.id)) role = "frontier";
            else if ((step.visitedIds || []).includes(n.id)) role = "visited";
            nodesSvg += `
                <circle cx="${n.x}" cy="${n.y}" r="17" class="viz-graph-node viz-role-${role}" />
                <text x="${n.x}" y="${n.y + 5}" text-anchor="middle" class="viz-tree-text">${escapeVal(n.id)}</text>
            `;
        });

        container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" class="viz-tree-svg">${edges}${nodesSvg}</svg>`;
    },
};

function escapeVal(v) {
    return String(v).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

// ----------------------------------------------------------------------
// Demo generators — one genuine, correct worked example per topic. Each
// returns { renderer: 'array'|'grid'|'stack'|'linkedlist'|'tree'|'graph',
//           title, steps: [...] }.
// ----------------------------------------------------------------------

const Demos = {
    "Basics": () => {
        const s = "racecar".split("");
        const steps = [];
        let i = 0, j = s.length - 1;
        steps.push(frame(s, i, j, `Two pointers start at the ends of "${s.join("")}" to check it reads the same forwards and backwards.`));
        while (i < j) {
            steps.push(frame(s, i, j, `Compare s[${i}]='${s[i]}' with s[${j}]='${s[j]}' — they match.`));
            i++; j--;
            if (i < j) steps.push(frame(s, i, j, `Move both pointers inward: i=${i}, j=${j}.`));
        }
        steps.push(frame(s, i, j, "Pointers met (or crossed) with every pair matching — the string is a palindrome."));
        return { renderer: "array", title: "Basics — Two-Pointer Scan", steps };

        function frame(arr, li, ri, desc) {
            const roles = {};
            arr.forEach((_, idx) => { roles[idx] = idx === li || idx === ri ? "active" : (idx > li && idx < ri ? "idle" : "visited"); });
            return { values: arr, roles, labels: { [li]: "i", [ri]: "j" }, description: desc };
        }
    },

    "Sorting Techniques": () => {
        const arr = [5, 1, 4, 2, 8];
        const steps = [];
        const a = arr.slice();
        steps.push({ values: a.slice(), roles: {}, description: `Bubble Sort on [${a.join(", ")}]: repeatedly swap adjacent out-of-order pairs.` });
        for (let pass = 0; pass < a.length - 1; pass++) {
            for (let k = 0; k < a.length - pass - 1; k++) {
                steps.push({ values: a.slice(), roles: { [k]: "active", [k + 1]: "active" }, description: `Compare a[${k}]=${a[k]} and a[${k + 1}]=${a[k + 1]}.` });
                if (a[k] > a[k + 1]) {
                    [a[k], a[k + 1]] = [a[k + 1], a[k]];
                    steps.push({ values: a.slice(), roles: { [k]: "active", [k + 1]: "active" }, description: `${a[k + 1]} > ${a[k]} → swap them.` });
                }
            }
            const sortedRoles = {};
            for (let s = a.length - pass - 1; s < a.length; s++) sortedRoles[s] = "visited";
            steps.push({ values: a.slice(), roles: sortedRoles, description: `Largest remaining value has bubbled to position ${a.length - pass - 1}.` });
        }
        steps.push({ values: a.slice(), roles: Object.fromEntries(a.map((_, i) => [i, "visited"])), description: "Array is fully sorted." });
        return { renderer: "array", title: "Sorting — Bubble Sort", steps };
    },

    "Arrays": () => {
        const arr = [2, 7, 11, 15];
        const target = 9;
        const steps = [];
        let i = 0, j = arr.length - 1;
        steps.push({ values: arr, roles: { 0: "active", 3: "active" }, labels: { 0: "i", 3: "j" }, description: `Sorted array [${arr.join(", ")}], target sum = ${target}. Two pointers start at both ends.` });
        while (i < j) {
            const sum = arr[i] + arr[j];
            steps.push({ values: arr, roles: { [i]: "active", [j]: "active" }, labels: { [i]: "i", [j]: "j" }, description: `arr[${i}] + arr[${j}] = ${arr[i]} + ${arr[j]} = ${sum}.` });
            if (sum === target) {
                steps.push({ values: arr, roles: { [i]: "match", [j]: "match" }, labels: { [i]: "i", [j]: "j" }, description: `${sum} equals the target — pair found: (${arr[i]}, ${arr[j]}).` });
                break;
            } else if (sum < target) {
                i++;
                steps.push({ values: arr, roles: { [i]: "active", [j]: "active" }, labels: { [i]: "i", [j]: "j" }, description: `Sum too small — move i right to increase the sum.` });
            } else {
                j--;
                steps.push({ values: arr, roles: { [i]: "active", [j]: "active" }, labels: { [i]: "i", [j]: "j" }, description: `Sum too large — move j left to decrease the sum.` });
            }
        }
        return { renderer: "array", title: "Arrays — Two-Pointer Sum", steps };
    },

    "Binary Search": () => {
        const arr = [2, 5, 8, 11, 14, 17, 20];
        const target = 11;
        const steps = [];
        let lo = 0, hi = arr.length - 1;
        steps.push({ values: arr, roles: {}, description: `Search for ${target} in the sorted array [${arr.join(", ")}].` });
        while (lo <= hi) {
            const mid = Math.floor((lo + hi) / 2);
            const roles = { [lo]: "lo", [hi]: "hi", [mid]: "active" };
            steps.push({ values: arr, roles, labels: { [lo]: "lo", [hi]: "hi", [mid]: "mid" }, description: `mid = (${lo}+${hi})/2 = ${mid} → arr[${mid}] = ${arr[mid]}.` });
            if (arr[mid] === target) {
                steps.push({ values: arr, roles: { [mid]: "match" }, labels: { [mid]: "found" }, description: `arr[${mid}] equals the target — found at index ${mid}.` });
                break;
            } else if (arr[mid] < target) {
                steps.push({ values: arr, roles, description: `${arr[mid]} < ${target} → search the right half.` });
                lo = mid + 1;
            } else {
                steps.push({ values: arr, roles, description: `${arr[mid]} > ${target} → search the left half.` });
                hi = mid - 1;
            }
        }
        return { renderer: "array", title: "Binary Search — Halving the Range", steps };
    },

    "Strings": () => {
        const s = "abcabcbb".split("");
        const steps = [];
        let left = 0, maxLen = 0, maxWindow = [0, -1];
        const seen = new Map();
        steps.push({ values: s, roles: {}, description: `Find the longest substring of "${s.join("")}" with no repeated characters.` });
        for (let right = 0; right < s.length; right++) {
            const ch = s[right];
            if (seen.has(ch) && seen.get(ch) >= left) {
                left = seen.get(ch) + 1;
                steps.push({ values: s, roles: windowRoles(left, right), description: `'${ch}' repeats inside the window — shrink from the left to index ${left}.` });
            }
            seen.set(ch, right);
            if (right - left + 1 > maxLen) { maxLen = right - left + 1; maxWindow = [left, right]; }
            steps.push({ values: s, roles: windowRoles(left, right), description: `Window [${left}, ${right}] = "${s.slice(left, right + 1).join("")}" (length ${right - left + 1}).` });
        }
        steps.push({ values: s, roles: windowRoles(maxWindow[0], maxWindow[1]), description: `Longest unique-character window: "${s.slice(maxWindow[0], maxWindow[1] + 1).join("")}" (length ${maxLen}).` });
        return { renderer: "array", title: "Strings — Sliding Window (Unique Chars)", steps };

        function windowRoles(l, r) {
            const roles = {};
            for (let k = l; k <= r; k++) roles[k] = "active";
            return roles;
        }
    },

    "Sliding Window": () => {
        const arr = [2, 1, 5, 1, 3, 2];
        const k = 3;
        const steps = [];
        let sum = 0;
        for (let i = 0; i < k; i++) sum += arr[i];
        let best = sum, bestStart = 0;
        steps.push({ values: arr, roles: winRoles(0, k - 1), description: `Fixed window of size ${k}: sum of first window = ${sum}.` });
        for (let start = 1; start + k - 1 < arr.length; start++) {
            sum += arr[start + k - 1] - arr[start - 1];
            if (sum > best) { best = sum; bestStart = start; }
            steps.push({ values: arr, roles: winRoles(start, start + k - 1), description: `Slide window right: drop arr[${start - 1}]=${arr[start - 1]}, add arr[${start + k - 1}]=${arr[start + k - 1]} → sum = ${sum}.` });
        }
        steps.push({ values: arr, roles: winRoles(bestStart, bestStart + k - 1), description: `Best window sum = ${best}, starting at index ${bestStart}.` });
        return { renderer: "array", title: "Sliding Window — Max Sum, Size k", steps };

        function winRoles(l, r) {
            const roles = {};
            for (let i = l; i <= r; i++) roles[i] = "active";
            return roles;
        }
    },

    "Greedy Algorithm": () => {
        const jumps = [2, 3, 1, 1, 4];
        const steps = [];
        let maxReach = 0;
        steps.push({ values: jumps, roles: {}, description: `Jump Game: from index i you can jump up to arr[i] steps. Greedily track the farthest reachable index.` });
        for (let i = 0; i < jumps.length; i++) {
            if (i > maxReach) {
                steps.push({ values: jumps, roles: { [i]: "match" }, description: `Index ${i} is unreachable (max reach was ${maxReach}) — stop.` });
                break;
            }
            const candidate = i + jumps[i];
            maxReach = Math.max(maxReach, candidate);
            steps.push({ values: jumps, roles: { [i]: "active" }, labels: { [i]: `reach→${maxReach}` }, description: `At i=${i} (value ${jumps[i]}): candidate reach = ${i}+${jumps[i]}=${candidate}. Best reach so far = ${maxReach}.` });
        }
        steps.push({ values: jumps, roles: Object.fromEntries(jumps.map((_, i) => [i, i <= maxReach ? "visited" : "idle"])), description: `Farthest index reachable greedily: ${maxReach} — every earlier index was covered without backtracking.` });
        return { renderer: "array", title: "Greedy — Farthest Reach", steps };
    },

    "Bit Manipulation": () => {
        const n = 13; // 1101
        const bits = n.toString(2).padStart(8, "0").split("");
        const steps = [];
        let count = 0;
        steps.push({ values: bits, roles: {}, description: `Count set bits of ${n} (binary ${bits.join("")}) by checking each bit from the right.` });
        for (let i = bits.length - 1; i >= 0; i--) {
            const isSet = bits[i] === "1";
            if (isSet) count++;
            steps.push({ values: bits, roles: { [i]: isSet ? "match" : "active" }, description: `Bit at position ${bits.length - 1 - i} is '${bits[i]}'${isSet ? ` — set! running count = ${count}` : " — not set."}` });
        }
        steps.push({ values: bits, roles: Object.fromEntries(bits.map((b, i) => [i, b === "1" ? "match" : "visited"])), description: `${n} has ${count} set bits.` });
        return { renderer: "array", title: "Bit Manipulation — Counting Set Bits", steps };
    },

    "Stacks Queues": () => {
        const s = "{[()]}".split("");
        const pairs = { ")": "(", "]": "[", "}": "{" };
        const stack = [];
        const steps = [];
        steps.push({ items: [], highlightTop: false, description: `Validate "${s.join("")}" — push every opening bracket, pop-and-match on every closing bracket.` });
        let ok = true;
        for (const ch of s) {
            if ("([{".includes(ch)) {
                stack.push(ch);
                steps.push({ items: stack.slice(), highlightTop: true, description: `'${ch}' is an opener — push onto the stack.` });
            } else {
                const top = stack[stack.length - 1];
                if (top === pairs[ch]) {
                    stack.pop();
                    steps.push({ items: stack.slice(), highlightTop: true, description: `'${ch}' matches the top '${top}' — pop it.` });
                } else {
                    ok = false;
                    steps.push({ items: stack.slice(), highlightTop: true, description: `'${ch}' does NOT match the top of the stack — invalid.` });
                    break;
                }
            }
        }
        if (ok) steps.push({ items: stack.slice(), highlightTop: false, description: "Stack is empty at the end — every bracket was matched: valid." });
        return { renderer: "stack", title: "Stacks — Valid Parentheses", steps };
    },

    "Heaps": () => {
        // Build a min-heap by inserting values one at a time with sift-up.
        const values = [9, 4, 7, 1, 3];
        const heap = [];
        const steps = [];
        for (const v of values) {
            heap.push(v);
            let idx = heap.length - 1;
            steps.push(treeFrame(heap, idx, [], `Insert ${v} at the next free slot.`));
            while (idx > 0) {
                const parent = Math.floor((idx - 1) / 2);
                if (heap[parent] <= heap[idx]) break;
                steps.push(treeFrame(heap, idx, [parent], `${heap[idx]} < parent ${heap[parent]} — sift up.`));
                [heap[parent], heap[idx]] = [heap[idx], heap[parent]];
                idx = parent;
                steps.push(treeFrame(heap, idx, [], `Swapped — ${heap[idx]} moves up.`));
            }
        }
        steps.push(treeFrame(heap, null, [], `Min-heap complete: root ${heap[0]} is always the smallest value.`));
        return { renderer: "tree", title: "Heaps — Insert with Sift-Up", steps };

        function treeFrame(arr, activeIdx, visitedIdx, desc) {
            const nodes = arr.map((val, i) => ({
                id: i,
                val,
                isRoot: i === 0,
                left: 2 * i + 1 < arr.length ? 2 * i + 1 : null,
                right: 2 * i + 2 < arr.length ? 2 * i + 2 : null,
            }));
            return { nodes, activeId: activeIdx, visitedIds: visitedIdx, description: desc };
        }
    },

    "Trees + BST": () => {
        // Fixed BST: 5(3(1,4),8(7,9))
        const tree = [
            { id: 0, val: 5, left: 1, right: 2, isRoot: true },
            { id: 1, val: 3, left: 3, right: 4 },
            { id: 2, val: 8, left: 5, right: 6 },
            { id: 3, val: 1, left: null, right: null },
            { id: 4, val: 4, left: null, right: null },
            { id: 5, val: 7, left: null, right: null },
            { id: 6, val: 9, left: null, right: null },
        ];
        const order = [];
        const steps = [];
        function inorder(id) {
            if (id === null) return;
            const node = tree.find((n) => n.id === id);
            inorder(node.left);
            order.push(id);
            steps.push({ nodes: tree, activeId: id, visitedIds: order.slice(0, -1), description: `Visit node ${node.val} (in-order: left, node, right).` });
            inorder(node.right);
        }
        steps.push({ nodes: tree, activeId: null, visitedIds: [], description: "In-order traversal of a BST visits nodes in sorted order." });
        inorder(0);
        steps.push({ nodes: tree, activeId: null, visitedIds: order, description: `Visit order: ${order.map((id) => tree.find((n) => n.id === id).val).join(" → ")} — already sorted.` });
        return { renderer: "tree", title: "Trees + BST — In-Order Traversal", steps };
    },

    "Recursion": () => {
        // Recursion tree for generating subsets of [1, 2] via include/exclude.
        const nums = [1, 2];
        const nodeList = [];
        let idCounter = 0;
        const steps = [];

        function build(index, chosen, parentId) {
            const id = idCounter++;
            const label = chosen.length ? `{${chosen.join(",")}}` : "{}";
            nodeList.push({ id, val: label, left: null, right: null, isRoot: parentId === null, parentId });
            if (parentId !== null) {
                const parent = nodeList.find((n) => n.id === parentId);
                if (parent.left === null) parent.left = id; else parent.right = id;
            }
            if (index === nums.length) {
                steps.push({ nodes: nodeList.slice(), activeId: id, visitedIds: nodeList.filter((n) => n.id !== id).map((n) => n.id), description: `Base case reached — subset ${label} is complete.` });
                return;
            }
            steps.push({ nodes: nodeList.slice(), activeId: id, visitedIds: [], description: `At index ${index}: branch into "exclude nums[${index}]=${nums[index]}" and "include" it.` });
            build(index + 1, chosen, id);
            build(index + 1, [...chosen, nums[index]], id);
        }
        build(0, [], null);
        steps.push({ nodes: nodeList.slice(), activeId: null, visitedIds: nodeList.map((n) => n.id), description: "Every leaf of the recursion tree is one complete subset." });
        return { renderer: "tree", title: "Recursion — Subset Recursion Tree", steps };
    },

    "Graphs": () => {
        const nodes = [
            { id: "A", x: 60, y: 40 }, { id: "B", x: 160, y: 40 },
            { id: "C", x: 60, y: 130 }, { id: "D", x: 160, y: 130 },
            { id: "E", x: 260, y: 85 },
        ];
        const adj = { A: ["B", "C"], B: ["A", "D", "E"], C: ["A", "D"], D: ["B", "C", "E"], E: ["B", "D"] };
        const edges = [["A", "B"], ["A", "C"], ["B", "D"], ["B", "E"], ["C", "D"], ["D", "E"]];
        const steps = [];
        const visited = new Set(["A"]);
        const queue = ["A"];
        steps.push({ nodes, edges, activeId: "A", visitedIds: [], frontierIds: ["A"], description: "BFS from A: start with A in the queue." });
        while (queue.length) {
            const cur = queue.shift();
            steps.push({ nodes, edges, activeId: cur, visitedIds: [...visited].filter((v) => v !== cur), frontierIds: queue.slice(), description: `Visit ${cur}, then look at its neighbors.` });
            for (const nb of adj[cur]) {
                if (!visited.has(nb)) {
                    visited.add(nb);
                    queue.push(nb);
                    steps.push({ nodes, edges, activeId: cur, visitedIds: [...visited].filter((v) => v !== cur && !queue.includes(v)), frontierIds: queue.slice(), description: `${nb} is unvisited — mark visited and enqueue it.` });
                }
            }
        }
        steps.push({ nodes, edges, activeId: null, visitedIds: [...visited], frontierIds: [], description: "Queue empty — every reachable node has been visited." });
        return { renderer: "graph", title: "Graphs — Breadth-First Search", steps };
    },

    "Dynamic Programming": () => {
        // Unique Paths on a 3x3 grid: dp[r][c] = dp[r-1][c] + dp[r][c-1]
        const rows = 3, cols = 3;
        const values = Array.from({ length: rows }, () => Array(cols).fill(null));
        const steps = [];
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                let v, deps = [];
                if (r === 0 || c === 0) {
                    v = 1;
                } else {
                    deps = [[r - 1, c], [r, c - 1]];
                    v = values[r - 1][c] + values[r][c - 1];
                }
                steps.push({ rows, cols, values: values.map((row) => row.slice()), activeCell: [r, c], dependencyCells: deps, description: deps.length ? `dp[${r}][${c}] = dp[${r - 1}][${c}] + dp[${r}][${c - 1}] = ${values[r - 1][c]} + ${values[r][c - 1]} = ${v}.` : `dp[${r}][${c}] = 1 (edge of the grid — only one path along the border).` });
                values[r][c] = v;
            }
        }
        steps.push({ rows, cols, values: values.map((row) => row.slice()), activeCell: [rows - 1, cols - 1], dependencyCells: [], description: `Bottom-right cell holds the answer: ${values[rows - 1][cols - 1]} unique paths.` });
        return { renderer: "grid", title: "Dynamic Programming — Unique Paths Table", steps };
    },

    "Tries": () => {
        // Insert "cat", "car", "dog" into a trie.
        const nodeList = [{ id: 0, val: "•", left: null, right: null, isRoot: true, children: {} }];
        let idCounter = 1;
        const steps = [];

        function ensureChild(parentId, ch) {
            const parent = nodeList.find((n) => n.id === parentId);
            if (parent.children[ch] !== undefined) return parent.children[ch];
            const id = idCounter++;
            nodeList.push({ id, val: ch, left: null, right: null, children: {} });
            parent.children[ch] = id;
            if (parent.left === null) parent.left = id; else parent.right = id;
            return id;
        }

        function toRenderNodes() {
            return nodeList.map((n) => ({ id: n.id, val: n.val, left: n.left, right: n.right, isRoot: n.isRoot }));
        }

        for (const word of ["cat", "car", "dog"]) {
            let cur = 0;
            for (const ch of word) {
                const existed = nodeList.find((n) => n.id === cur).children[ch] !== undefined;
                cur = ensureChild(cur, ch);
                steps.push({ nodes: toRenderNodes(), activeId: cur, visitedIds: [], description: existed ? `"${word}": '${ch}' already exists on this path — reuse it (shared prefix).` : `"${word}": insert new node for '${ch}'.` });
            }
        }
        steps.push({ nodes: toRenderNodes(), activeId: null, visitedIds: nodeList.map((n) => n.id), description: '"cat" and "car" share the "ca" prefix path — that shared structure is what makes a trie fast.' });
        return { renderer: "tree", title: "Tries — Prefix Sharing", steps };
    },

    "Linked List": () => {
        const values = [1, 2, 3, 4];
        const steps = [];
        // Forward-order snapshot with prev/curr/next rolling across it, then a "reversed" summary.
        let prev = null;
        for (let i = 0; i < values.length; i++) {
            const nodes = values.map((v, idx) => ({ id: idx, val: v, role: idx === i ? "active" : (prev !== null && idx === prev) ? "visited" : "idle" }));
            const pointers = {};
            if (prev !== null) pointers[prev] = ["prev"];
            pointers[i] = [...(pointers[i] || []), "curr"];
            if (i + 1 < values.length) pointers[i + 1] = [...(pointers[i + 1] || []), "next"];
            steps.push({ nodes, pointers, description: `Reversing pointers: curr=${values[i]}${prev !== null ? `, prev=${values[prev]}` : ""} — point curr's next back to prev.` });
            prev = i;
        }
        const reversedNodes = values.slice().reverse().map((v, idx) => ({ id: idx, val: v, role: "visited" }));
        steps.push({ nodes: reversedNodes, pointers: {}, description: `List fully reversed: ${values.slice().reverse().join(" → ")}.` });
        return { renderer: "linkedlist", title: "Linked List — Iterative Reversal", steps };
    },
};

// Fallback/aliases for topic name variants that don't exactly match a key above.
const TOPIC_ALIASES = {
    "Strings": "Strings",
};

function resolveDemo(topic) {
    if (Demos[topic]) return Demos[topic];
    const norm = Object.keys(Demos).find((k) => topic && topic.toLowerCase().includes(k.toLowerCase().split(" ")[0]));
    return Demos[norm] || Demos["Arrays"];
}

// ----------------------------------------------------------------------
// Player — mounts into a container, owns play/pause/step state.
// ----------------------------------------------------------------------

export class VisualizerPlayer {
    constructor(root) {
        this.root = root;
        this.steps = [];
        this.index = 0;
        this.playing = false;
        this.timer = null;
        this.speedMs = 900;
    }

    load(topic) {
        this.stop();
        const demoFn = resolveDemo(topic);
        const demo = demoFn();
        this.steps = demo.steps;
        this.title = demo.title;
        this.renderer = demo.renderer;
        this.index = 0;
        this._mountShell();
        this._renderFrame();
    }

    _mountShell() {
        this.root.innerHTML = `
            <div class="viz-header">
                <span class="viz-title">${this.title}</span>
                <span class="viz-step-counter"><span class="viz-step-cur">1</span> / <span class="viz-step-total">${this.steps.length}</span></span>
            </div>
            <div class="viz-stage"></div>
            <p class="viz-description"></p>
            <div class="viz-controls">
                <button type="button" class="btn btn-icon viz-btn-restart" title="Restart"><i class="fa-solid fa-rotate-left"></i></button>
                <button type="button" class="btn btn-icon viz-btn-prev" title="Previous step"><i class="fa-solid fa-backward-step"></i></button>
                <button type="button" class="btn btn-primary-sm viz-btn-play" title="Play / Pause"><i class="fa-solid fa-play"></i> Play</button>
                <button type="button" class="btn btn-icon viz-btn-next" title="Next step"><i class="fa-solid fa-forward-step"></i></button>
                <div class="viz-progress-track"><div class="viz-progress-fill"></div></div>
            </div>
        `;
        this.stageEl = this.root.querySelector(".viz-stage");
        this.descEl = this.root.querySelector(".viz-description");
        this.curEl = this.root.querySelector(".viz-step-cur");
        this.playBtn = this.root.querySelector(".viz-btn-play");
        this.progressFill = this.root.querySelector(".viz-progress-fill");

        this.root.querySelector(".viz-btn-restart").addEventListener("click", () => this.restart());
        this.root.querySelector(".viz-btn-prev").addEventListener("click", () => this.step(-1));
        this.root.querySelector(".viz-btn-next").addEventListener("click", () => this.step(1));
        this.playBtn.addEventListener("click", () => this.togglePlay());
    }

    _renderFrame() {
        const frame = this.steps[this.index];
        if (!frame) return;
        Renderers[this.renderer](this.stageEl, frame);
        this.descEl.textContent = frame.description || "";
        this.curEl.textContent = this.index + 1;
        this.progressFill.style.width = `${((this.index + 1) / this.steps.length) * 100}%`;

        const atEnd = this.index >= this.steps.length - 1;
        if (atEnd) this.pause();
    }

    step(delta) {
        const next = this.index + delta;
        if (next < 0 || next >= this.steps.length) return;
        this.index = next;
        this._renderFrame();
    }

    restart() {
        this.pause();
        this.index = 0;
        this._renderFrame();
    }

    togglePlay() {
        this.playing ? this.pause() : this.play();
    }

    play() {
        if (this.index >= this.steps.length - 1) this.index = 0;
        this.playing = true;
        this.playBtn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
        this.timer = setInterval(() => {
            if (this.index >= this.steps.length - 1) { this.pause(); return; }
            this.index += 1;
            this._renderFrame();
        }, this.speedMs);
    }

    pause() {
        this.playing = false;
        if (this.playBtn) this.playBtn.innerHTML = '<i class="fa-solid fa-play"></i> Play';
        if (this.timer) { clearInterval(this.timer); this.timer = null; }
    }

    stop() {
        this.pause();
    }
}

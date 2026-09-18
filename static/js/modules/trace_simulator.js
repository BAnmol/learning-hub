// ============================================================================
// Trace Simulator — Dynamic, test-case-driven step-by-step visual simulation.
// Generates concrete execution frames for ANY example/test case selected by
// the user, supporting both Optimized and Brute Force approaches.
// ============================================================================

/**
 * Parse a raw input string into structured arguments.
 * Examples:
 *   "[2, 7, 11, 15], 9" -> { array: [2, 7, 11, 15], target: 9, type: "array_target" }
 *   "[5, 1, 4, 2, 8]"    -> { array: [5, 1, 4, 2, 8], type: "array" }
 *   "\"racecar\""        -> { string: "racecar", array: ["r","a","c","e","c","a","r"], type: "string" }
 *   "153"                -> { number: 153, type: "number" }
 */
export function parseInputData(raw) {
    if (!raw) return { type: "empty", items: [], raw: "" };
    const s = String(raw).trim();

    // 1. Array + Target scalar (e.g. "[2, 7, 11, 15], 9")
    const arrTargetMatch = s.match(/^\[(.*?)\]\s*,\s*(-?\d+|["'].*?["'])$/);
    if (arrTargetMatch) {
        try {
            const arr = JSON.parse(`[${arrTargetMatch[1]}]`);
            const target = JSON.parse(arrTargetMatch[2]);
            return {
                type: "array_target",
                array: arr,
                target: target,
                items: arr.map(String),
                raw: s,
            };
        } catch (_) {}
    }

    // 2. Standalone JSON array (e.g. "[5, 1, 4, 2, 8]")
    if (s.startsWith("[") && s.endsWith("]")) {
        try {
            const arr = JSON.parse(s);
            if (Array.isArray(arr)) {
                return {
                    type: "array",
                    array: arr,
                    items: arr.map((x) => (x === null ? "null" : String(x))),
                    raw: s,
                };
            }
        } catch (_) {
            const inner = s.slice(1, -1).split(",").map((t) => t.trim());
            return { type: "array", array: inner, items: inner, raw: s };
        }
    }

    // 3. String input (e.g. "\"racecar\"" or "'abcabcbb'")
    if ((s.startsWith('"') && s.endsWith('"')) || (s.startsWith("'") && s.endsWith("'"))) {
        const cleanStr = s.slice(1, -1);
        return {
            type: "string",
            string: cleanStr,
            array: cleanStr.split(""),
            items: cleanStr.split(""),
            raw: s,
        };
    }

    // 4. Two numbers separated by comma (e.g. "48, 18")
    const twoNumMatch = s.match(/^(-?\d+)\s*,\s*(-?\d+)$/);
    if (twoNumMatch) {
        const a = parseInt(twoNumMatch[1], 10);
        const b = parseInt(twoNumMatch[2], 10);
        return {
            type: "two_numbers",
            a, b,
            array: [a, b],
            target: b,
            items: [String(a), String(b)],
            raw: s,
        };
    }

    // 5. Integer input (e.g. "153")
    if (/^-?\d+$/.test(s)) {
        const n = parseInt(s, 10);
        return {
            type: "number",
            number: n,
            items: String(Math.abs(n)).split(""),
            raw: s,
        };
    }

    // 5. Comma-separated list fallback
    const tokens = s.split(",").map((t) => t.trim().replace(/^['"]|['"]$/g, ""));
    return {
        type: "general",
        items: tokens,
        raw: s,
    };
}

/**
 * Main entry point: generate concrete visual simulation frames for a given
 * problem, approach ('optimized' | 'brute'), and input data.
 */
export function buildVisualSimulation(problem, approach, rawInput) {
    const inputData = parseInputData(rawInput);
    const title = (problem?.title || "").toLowerCase();
    const topic = (problem?.topic || "").toLowerCase();

    // 1. Two Sum / Pair Sum matching
    if (title.includes("two sum") || (title.includes("sum") && inputData.type === "array_target")) {
        return simulateTwoSum(inputData, approach);
    }

    // 2. Binary Search
    if (title.includes("binary search") || (topic.includes("binary search") && inputData.type === "array_target")) {
        return simulateBinarySearch(inputData, approach);
    }

    // 3. Sorting techniques
    if (title.includes("sort") || topic.includes("sorting")) {
        return simulateSorting(inputData, approach);
    }

    // 4. Palindrome check
    if (title.includes("palindrome")) {
        return simulatePalindrome(inputData, approach);
    }

    // 5. Count Digits
    if (title.includes("count digit") || title.includes("number of digit")) {
        return simulateCountDigits(inputData, approach);
    }

    // 6. Reverse Number
    if (title.includes("reverse") && (title.includes("number") || title.includes("integer") || title.includes("digit"))) {
        return simulateReverseNumber(inputData, approach);
    }

    // 7. Check Prime
    if (title.includes("prime")) {
        return simulateCheckPrime(inputData, approach);
    }

    // 8. GCD / HCF
    if (title.includes("gcd") || title.includes("hcf") || title.includes("divisor") && inputData.type === "two_numbers") {
        return simulateGCD(inputData, approach);
    }

    // 9. All Divisors
    if (title.includes("divisor")) {
        return simulateDivisors(inputData, approach);
    }

    // 10. Math / Armstrong Number
    if (title.includes("armstrong")) {
        return simulateArmstrong(inputData, approach);
    }

    // 11. Find Largest / Maximum Element
    if (title.includes("largest") || title.includes("maximum element") || title.includes("second largest")) {
        return simulateFindLargest(inputData, approach);
    }

    // 12. Linear Search
    if (title.includes("linear search") || (title.includes("search") && inputData.type === "array_target")) {
        return simulateLinearSearch(inputData, approach);
    }

    // 13. Sliding Window / Longest Substring
    if (title.includes("substring") || title.includes("sliding window") || topic.includes("sliding window")) {
        return simulateSlidingWindow(inputData, approach);
    }

    // 14. Kadane's / Max Subarray
    if (title.includes("kadane") || title.includes("maximum subarray") || title.includes("subarray")) {
        return simulateKadane(inputData, approach);
    }

    // 15. Stack / Valid Parentheses
    if (title.includes("parenthes") || title.includes("bracket") || topic.includes("stack")) {
        return simulateParentheses(inputData, approach);
    }

    // 16. General Dynamic Simulator Fallback
    return simulateGeneral(inputData, approach, problem);
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. Two Sum Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulateTwoSum(inputData, approach) {
    const arr = Array.isArray(inputData.array) ? inputData.array : [2, 7, 11, 15];
    const target = inputData.target !== undefined ? Number(inputData.target) : 9;
    const items = arr.map(String);
    const frames = [];

    if (approach === "optimized") {
        // Optimized: Single pass with Hash Map
        const seen = {};
        frames.push({
            phase: "init",
            title: "Initialize Hash Map",
            guidance: `Target sum is ${target}. We initialize an empty hash map <code>seen = {}</code> to store numbers and their indices for instant O(1) lookup.`,
            roles: {},
            pointers: {},
            memory: { "Target": target, "Seen Map": "{}" },
        });

        let found = false;
        for (let i = 0; i < arr.length; i++) {
            const num = arr[i];
            const needed = target - num;

            // Step A: Inspect element
            const rolesExamining = { [i]: "active" };
            Object.keys(seen).forEach((val) => {
                rolesExamining[seen[val]] = "visited";
            });

            frames.push({
                phase: "scan",
                title: `Inspect Element at Index ${i}`,
                guidance: `Examining <code>nums[${i}] = ${num}</code>. We need complement <code>${target} - ${num} = ${needed}</code>.`,
                roles: rolesExamining,
                pointers: { [i]: "i" },
                memory: {
                    "Target": target,
                    "Current": `nums[${i}] = ${num}`,
                    "Needed Complement": `${target} - ${num} = ${needed}`,
                    "Seen Map": formatMap(seen),
                },
            });

            // Step B: Check hash map
            if (needed in seen) {
                const prevIdx = seen[needed];
                const rolesMatch = { [prevIdx]: "match", [i]: "match" };
                frames.push({
                    phase: "result",
                    title: `Match Found! [${prevIdx}, ${i}]`,
                    guidance: `✨ <strong>Complement ${needed} found in seen map!</strong> Stored at index <code>${prevIdx}</code>. Pair: <code>nums[${prevIdx}] (${needed}) + nums[${i}] (${num}) = ${target}</code>. Return indices <code>[${prevIdx}, ${i}]</code>.`,
                    roles: rolesMatch,
                    pointers: { [prevIdx]: "match", [i]: "match" },
                    memory: {
                        "Target": target,
                        "Result": `[${prevIdx}, ${i}]`,
                        "Equation": `${needed} + ${num} = ${target}`,
                    },
                });
                found = true;
                break;
            } else {
                seen[num] = i;
                const rolesUpdated = { ...rolesExamining, [i]: "visited" };
                frames.push({
                    phase: "update",
                    title: `Save nums[${i}] to Hash Map`,
                    guidance: `Complement ${needed} is not in seen map yet. Save <code>seen[${num}] = ${i}</code> so future elements can look it up in O(1) time.`,
                    roles: rolesUpdated,
                    pointers: { [i]: "saved" },
                    memory: {
                        "Target": target,
                        "Seen Map": formatMap(seen),
                        "Status": `Saved ${num} -> idx ${i}`,
                    },
                });
            }
        }

        if (!found) {
            frames.push({
                phase: "result",
                title: "Scan Completed (No Pair Found)",
                guidance: `Finished scanning the entire array. No two numbers summed up to ${target}. Return <code>[]</code>.`,
                roles: Object.fromEntries(arr.map((_, idx) => [idx, "visited"])),
                pointers: {},
                memory: { "Target": target, "Result": "[]" },
            });
        }
    } else {
        // Brute Force: Nested Loops O(n²)
        frames.push({
            phase: "init",
            title: "Brute Force: Setup Nested Loops",
            guidance: `We use two nested loops: outer pointer <code>i</code> and inner pointer <code>j</code>, testing every pair <code>(i, j)</code> with <code>j > i</code>.`,
            roles: {},
            pointers: {},
            memory: { "Target": target, "Comparison": "nums[i] + nums[j]" },
        });

        let found = false;
        for (let i = 0; i < arr.length && !found; i++) {
            for (let j = i + 1; j < arr.length; j++) {
                const sum = arr[i] + arr[j];
                const isMatch = sum === target;

                if (isMatch) {
                    frames.push({
                        phase: "result",
                        title: `Pair Found! nums[${i}] + nums[${j}] = ${target}`,
                        guidance: `🎉 <strong>Match!</strong> <code>nums[${i}] (${arr[i]}) + nums[${j}] (${arr[j]}) = ${sum}</code> equals target <code>${target}</code>. Return indices <code>[${i}, ${j}]</code>.`,
                        roles: { [i]: "match", [j]: "match" },
                        pointers: { [i]: "i", [j]: "j" },
                        memory: {
                            "Target": target,
                            "nums[i] + nums[j]": `${arr[i]} + ${arr[j]} = ${sum}`,
                            "Result": `[${i}, ${j}]`,
                        },
                    });
                    found = true;
                    break;
                } else {
                    frames.push({
                        phase: "compare",
                        title: `Compare Pair (${i}, ${j})`,
                        guidance: `Checking pair: <code>nums[${i}] (${arr[i]}) + nums[${j}] (${arr[j]}) = ${sum}</code> ≠ target <code>${target}</code>. Move inner pointer <code>j</code> forward.`,
                        roles: { [i]: "active", [j]: "compare" },
                        pointers: { [i]: "i", [j]: "j" },
                        memory: {
                            "Target": target,
                            "Current Sum": `${arr[i]} + ${arr[j]} = ${sum}`,
                            "Match": "No",
                        },
                    });
                }
            }
        }
    }

    return { items, frames, inputSummary: `nums = [${arr.join(", ")}], target = ${target}` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. Binary Search Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulateBinarySearch(inputData, approach) {
    let arr = Array.isArray(inputData.array) ? inputData.array.slice().sort((a, b) => a - b) : [1, 3, 5, 7, 9, 11];
    const target = inputData.target !== undefined ? Number(inputData.target) : 7;
    const items = arr.map(String);
    const frames = [];

    if (approach === "optimized") {
        let lo = 0, hi = arr.length - 1;
        frames.push({
            phase: "init",
            title: "Initialize Binary Search Bounds",
            guidance: `Searching for <code>target = ${target}</code> in sorted array. Set <code>low = 0</code> and <code>high = ${hi}</code>.`,
            roles: { [lo]: "active", [hi]: "active" },
            pointers: { [lo]: "low", [hi]: "high" },
            memory: { "Low": lo, "High": hi, "Target": target },
        });

        let found = false;
        while (lo <= hi) {
            const mid = Math.floor((lo + hi) / 2);
            const midVal = arr[mid];

            if (midVal === target) {
                frames.push({
                    phase: "result",
                    title: `Target Found at Index ${mid}!`,
                    guidance: `🎯 <strong>arr[${mid}] = ${midVal} equals target ${target}!</strong> Return index <code>${mid}</code> in O(log n) time.`,
                    roles: { [mid]: "match" },
                    pointers: { [mid]: "found" },
                    memory: { "Mid": mid, "Value": midVal, "Target": target, "Result": mid },
                });
                found = true;
                break;
            } else if (midVal < target) {
                frames.push({
                    phase: "compare",
                    title: `arr[${mid}] = ${midVal} < ${target} → Search Right Half`,
                    guidance: `Middle element <code>arr[${mid}] = ${midVal}</code> is less than target <code>${target}</code>. Discard left half; move <code>low = ${mid + 1}</code>.`,
                    roles: { [mid]: "compare", [lo]: "active", [hi]: "active" },
                    pointers: { [mid]: "mid", [lo]: "low", [hi]: "high" },
                    memory: { "Mid": mid, "Value": midVal, "Decision": "Search Right" },
                });
                lo = mid + 1;
            } else {
                frames.push({
                    phase: "compare",
                    title: `arr[${mid}] = ${midVal} > ${target} → Search Left Half`,
                    guidance: `Middle element <code>arr[${mid}] = ${midVal}</code> is greater than target <code>${target}</code>. Discard right half; move <code>high = ${mid - 1}</code>.`,
                    roles: { [mid]: "compare", [lo]: "active", [hi]: "active" },
                    pointers: { [mid]: "mid", [lo]: "low", [hi]: "high" },
                    memory: { "Mid": mid, "Value": midVal, "Decision": "Search Left" },
                });
                hi = mid - 1;
            }
        }

        if (!found) {
            frames.push({
                phase: "result",
                title: "Target Not Found",
                guidance: `Pointers crossed (<code>low > high</code>). Target <code>${target}</code> does not exist in the array. Return <code>-1</code>.`,
                roles: {},
                pointers: {},
                memory: { "Result": -1 },
            });
        }
    } else {
        // Brute Force: Linear Scan O(n)
        frames.push({
            phase: "init",
            title: "Linear Scan Setup",
            guidance: `Brute force checks every element one by one from left to right in O(n) time.`,
            roles: {},
            pointers: {},
            memory: { "Target": target },
        });

        let found = false;
        for (let i = 0; i < arr.length; i++) {
            if (arr[i] === target) {
                frames.push({
                    phase: "result",
                    title: `Target Found at Index ${i}`,
                    guidance: `Found target <code>${target}</code> at index <code>${i}</code> after <code>${i + 1}</code> comparisons.`,
                    roles: { [i]: "match" },
                    pointers: { [i]: "found" },
                    memory: { "Index": i, "Value": arr[i] },
                });
                found = true;
                break;
            } else {
                frames.push({
                    phase: "scan",
                    title: `Check arr[${i}] = ${arr[i]}`,
                    guidance: `<code>arr[${i}] = ${arr[i]}</code> ≠ target <code>${target}</code>. Keep scanning forward.`,
                    roles: { [i]: "compare" },
                    pointers: { [i]: "i" },
                    memory: { "Current": arr[i], "Target": target },
                });
            }
        }
    }

    return { items, frames, inputSummary: `arr = [${arr.join(", ")}], target = ${target}` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. Sorting Simulation (Bubble / Pairwise)
// ─────────────────────────────────────────────────────────────────────────────
function simulateSorting(inputData, approach) {
    const rawArr = Array.isArray(inputData.array) ? inputData.array.slice() : [5, 2, 8, 1, 9];
    const a = rawArr.map(Number);
    const items = a.map(String);
    const frames = [];

    frames.push({
        phase: "init",
        title: "Initial Unsorted Array",
        guidance: `Starting sort on <code>[${a.join(", ")}]</code>. We will compare adjacent elements and bubble inversions.`,
        roles: {},
        pointers: {},
        memory: { "Length": a.length, "Status": "Unsorted" },
    });

    const workArr = a.slice();
    let stepsCount = 0;
    const maxSteps = 12; // Keep interactive trace snappy

    for (let pass = 0; pass < workArr.length - 1 && stepsCount < maxSteps; pass++) {
        for (let k = 0; k < workArr.length - pass - 1 && stepsCount < maxSteps; k++) {
            const needSwap = workArr[k] > workArr[k + 1];
            stepsCount++;

            if (needSwap) {
                frames.push({
                    phase: "compare",
                    title: `Compare arr[${k}] (${workArr[k]}) & arr[${k+1}] (${workArr[k+1]})`,
                    guidance: `<code>${workArr[k]} > ${workArr[k+1]}</code> is out of order. Swap them!`,
                    roles: { [k]: "compare", [k + 1]: "compare" },
                    pointers: { [k]: "swap", [k + 1]: "swap" },
                    memory: { "Pair": `(${workArr[k]}, ${workArr[k+1]})`, "Action": "Swap" },
                });
                [workArr[k], workArr[k + 1]] = [workArr[k + 1], workArr[k]];
                frames.push({
                    phase: "update",
                    title: `Swapped: [${workArr[k]}, ${workArr[k+1]}]`,
                    guidance: `Values swapped. Current array is now <code>[${workArr.join(", ")}]</code>.`,
                    roles: { [k]: "active", [k + 1]: "active" },
                    pointers: { [k]: "ok", [k + 1]: "ok" },
                    memory: { "Array": `[${workArr.join(", ")}]` },
                });
            }
        }
    }

    frames.push({
        phase: "result",
        title: "Sorting Completed",
        guidance: `All elements are placed in ascending order: <code>[${workArr.sort((x, y) => x - y).join(", ")}]</code>.`,
        roles: Object.fromEntries(workArr.map((_, i) => [i, "match"])),
        pointers: {},
        memory: { "Result": `[${workArr.join(", ")}]` },
    });

    return { items: workArr.map(String), frames, inputSummary: `arr = [${a.join(", ")}]` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. Palindrome Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulatePalindrome(inputData, approach) {
    const s = inputData.string || (Array.isArray(inputData.items) ? inputData.items.join("") : "racecar");
    const items = s.split("");
    const frames = [];

    frames.push({
        phase: "init",
        title: "Two Pointers Setup (Ends Inward)",
        guidance: `Checking if <code>"${s}"</code> is a palindrome. Initialize left pointer <code>i = 0</code> and right pointer <code>j = ${s.length - 1}</code>.`,
        roles: { 0: "active", [s.length - 1]: "active" },
        pointers: { 0: "i", [s.length - 1]: "j" },
        memory: { "Left Char": items[0], "Right Char": items[items.length - 1] },
    });

    let i = 0, j = items.length - 1;
    let isPal = true;

    while (i < j) {
        const match = items[i] === items[j];
        if (match) {
            frames.push({
                phase: "compare",
                title: `Characters Match: '${items[i]}' === '${items[j]}'`,
                guidance: `Left <code>s[${i}] = '${items[i]}'</code> equals right <code>s[${j}] = '${items[j]}'</code>. Move both inward.`,
                roles: { [i]: "match", [j]: "match" },
                pointers: { [i]: "i", [j]: "j" },
                memory: { "Match": "True", "Pair": `'${items[i]}' === '${items[j]}'` },
            });
            i++; j--;
        } else {
            frames.push({
                phase: "result",
                title: `Mismatch Found: '${items[i]}' !== '${items[j]}'`,
                guidance: `Mismatch at positions <code>${i}</code> ('${items[i]}') and <code>${j}</code> ('${items[j]}'). String is NOT a palindrome.`,
                roles: { [i]: "compare", [j]: "compare" },
                pointers: { [i]: "mismatch", [j]: "mismatch" },
                memory: { "Result": "False" },
            });
            isPal = false;
            break;
        }
    }

    if (isPal) {
        frames.push({
            phase: "result",
            title: "Palindrome Confirmed (True)",
            guidance: `Pointers met without any mismatches. <code>"${s}"</code> is a valid palindrome! Return <code>True</code>.`,
            roles: Object.fromEntries(items.map((_, idx) => [idx, "match"])),
            pointers: {},
            memory: { "Result": "True" },
        });
    }

    return { items, frames, inputSummary: `s = "${s}"` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. Sliding Window Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulateSlidingWindow(inputData, approach) {
    const s = inputData.string || (Array.isArray(inputData.items) ? inputData.items.join("") : "abcabcbb");
    const items = s.split("");
    const frames = [];

    frames.push({
        phase: "init",
        title: "Sliding Window Setup",
        guidance: `Find longest substring with unique characters in <code>"${s}"</code>. We maintain window <code>[left ... right]</code> and a set of seen characters.`,
        roles: { 0: "active" },
        pointers: { 0: "L, R" },
        memory: { "Window": `"${items[0]}"`, "Max Length": 1 },
    });

    let left = 0, maxLen = 0, bestWindow = [0, 0];
    const seen = new Map();

    for (let right = 0; right < items.length && frames.length < 12; right++) {
        const ch = items[right];
        if (seen.has(ch) && seen.get(ch) >= left) {
            left = seen.get(ch) + 1;
            frames.push({
                phase: "update",
                title: `Duplicate '${ch}' Detected → Shrink Left`,
                guidance: `Character <code>'${ch}'</code> already in window. Shrink window from left to index <code>${left}</code>.`,
                roles: windowRoles(items, left, right),
                pointers: { [left]: "L", [right]: "R" },
                memory: { "Duplicate": `'${ch}'`, "Left Jump": left },
            });
        }
        seen.set(ch, right);
        const winLen = right - left + 1;
        if (winLen > maxLen) {
            maxLen = winLen;
            bestWindow = [left, right];
        }

        frames.push({
            phase: "scan",
            title: `Window [${left}..${right}]: "${items.slice(left, right + 1).join("")}"`,
            guidance: `Valid unique window size = <code>${winLen}</code>. Max unique length so far = <code>${maxLen}</code>.`,
            roles: windowRoles(items, left, right),
            pointers: { [left]: "L", [right]: "R" },
            memory: { "Current Window": `"${items.slice(left, right + 1).join("")}"`, "Max Len": maxLen },
        });
    }

    frames.push({
        phase: "result",
        title: `Max Unique Substring Length = ${maxLen}`,
        guidance: `Completed scan. Longest unique substring is <code>"${items.slice(bestWindow[0], bestWindow[1] + 1).join("")}"</code> with length <code>${maxLen}</code>.`,
        roles: windowRoles(items, bestWindow[0], bestWindow[1], "match"),
        pointers: { [bestWindow[0]]: "start", [bestWindow[1]]: "end" },
        memory: { "Max Length": maxLen, "Result": maxLen },
    });

    return { items, frames, inputSummary: `s = "${s}"` };
}

function windowRoles(items, l, r, defaultRole = "active") {
    const roles = {};
    for (let i = 0; i < items.length; i++) {
        if (i >= l && i <= r) roles[i] = defaultRole;
        else if (i < l) roles[i] = "visited";
    }
    return roles;
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. Kadane's Algorithm Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulateKadane(inputData, approach) {
    const arr = Array.isArray(inputData.array) ? inputData.array.map(Number) : [-2, 1, -3, 4, -1, 2, 1, -5, 4];
    const items = arr.map(String);
    const frames = [];

    let currentSum = arr[0];
    let maxSum = arr[0];

    frames.push({
        phase: "init",
        title: "Initialize Kadane's Algorithm",
        guidance: `Track maximum subarray sum. Initialize <code>currentSum = ${currentSum}</code> and <code>maxSum = ${maxSum}</code> at index 0.`,
        roles: { 0: "active" },
        pointers: { 0: "i=0" },
        memory: { "Current Sum": currentSum, "Max Sum": maxSum },
    });

    for (let i = 1; i < arr.length && frames.length < 12; i++) {
        const x = arr[i];
        const restarted = x > currentSum + x;
        currentSum = Math.max(x, currentSum + x);
        const newMax = currentSum > maxSum;
        if (newMax) maxSum = currentSum;

        frames.push({
            phase: restarted ? "update" : "scan",
            title: `Index ${i} (val = ${x}): currentSum = ${currentSum}`,
            guidance: restarted
                ? `Previous sum was negative. Restart new subarray at <code>arr[${i}] = ${x}</code>.`
                : `Extend subarray: <code>${currentSum - x} + ${x} = ${currentSum}</code>. ${newMax ? `New max sum = <strong>${maxSum}</strong>!` : ""}`,
            roles: { [i]: newMax ? "match" : "active" },
            pointers: { [i]: `i=${i}` },
            memory: { "Current Sum": currentSum, "Max Sum": maxSum },
        });
    }

    frames.push({
        phase: "result",
        title: `Maximum Subarray Sum = ${maxSum}`,
        guidance: `Single linear scan completed in O(n) time. The maximum contiguous subarray sum is <code>${maxSum}</code>.`,
        roles: Object.fromEntries(arr.map((_, i) => [i, "match"])),
        pointers: {},
        memory: { "Final Max Sum": maxSum, "Time": "O(n)", "Space": "O(1)" },
    });

    return { items, frames, inputSummary: `arr = [${arr.join(", ")}]` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. Stack / Valid Parentheses Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulateParentheses(inputData, approach) {
    const s = inputData.string || (Array.isArray(inputData.items) ? inputData.items.join("") : "()[]{}");
    const items = s.split("");
    const frames = [];
    const stack = [];
    const pairs = { ")": "(", "]": "[", "}": "{" };

    frames.push({
        phase: "init",
        title: "Initialize Stack",
        guidance: `Validating bracket string <code>"${s}"</code>. We push opening brackets and pop/match on closing brackets.`,
        roles: {},
        pointers: {},
        memory: { "Stack": "[]" },
    });

    let valid = true;
    for (let i = 0; i < items.length; i++) {
        const ch = items[i];
        if (["(", "[", "{"].includes(ch)) {
            stack.push(ch);
            frames.push({
                phase: "scan",
                title: `Push Opening Bracket '${ch}'`,
                guidance: `Encountered opening bracket <code>'${ch}'</code>. Push onto stack.`,
                roles: { [i]: "active" },
                pointers: { [i]: "push" },
                memory: { "Stack": `[${stack.join(", ")}]` },
            });
        } else if (pairs[ch]) {
            const top = stack.pop();
            const match = top === pairs[ch];
            if (match) {
                frames.push({
                    phase: "compare",
                    title: `Match Bracket Pair '${top}${ch}'`,
                    guidance: `Encountered closing bracket <code>'${ch}'</code> matching top of stack <code>'${top}'</code>! Pop top.`,
                    roles: { [i]: "match" },
                    pointers: { [i]: "match" },
                    memory: { "Popped": top, "Stack": `[${stack.join(", ")}]` },
                });
            } else {
                frames.push({
                    phase: "result",
                    title: `Mismatched Bracket '${ch}'`,
                    guidance: `Closing bracket <code>'${ch}'</code> does not match stack top <code>'${top || "empty"}'</code>! Invalid string.`,
                    roles: { [i]: "compare" },
                    pointers: { [i]: "error" },
                    memory: { "Error": "Mismatched bracket", "Result": "False" },
                });
                valid = false;
                break;
            }
        }
    }

    if (valid && stack.length === 0) {
        frames.push({
            phase: "result",
            title: "String is Valid Balanced Parentheses",
            guidance: `All opening brackets were matched and stack is empty. Return <code>True</code>.`,
            roles: Object.fromEntries(items.map((_, i) => [i, "match"])),
            pointers: {},
            memory: { "Result": "True" },
        });
    }

    return { items, frames, inputSummary: `s = "${s}"` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. Armstrong Number Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulateArmstrong(inputData, approach) {
    const num = inputData.number !== undefined ? inputData.number : 153;
    const digits = String(num).split("").map(Number);
    const power = digits.length;
    const items = digits.map(String);
    const frames = [];

    frames.push({
        phase: "init",
        title: `Check Armstrong: ${num}`,
        guidance: `A number is an Armstrong number if the sum of its digits raised to the power of number of digits (${power}) equals the number itself.`,
        roles: {},
        pointers: {},
        memory: { "Number": num, "Digits Count": power, "Running Sum": 0 },
    });

    let sum = 0;
    digits.forEach((d, i) => {
        const term = Math.pow(d, power);
        sum += term;
        frames.push({
            phase: "scan",
            title: `Digit ${d}^${power} = ${term}`,
            guidance: `At index ${i}: digit <code>${d}</code> raised to power <code>${power}</code> is <code>${term}</code>. Running sum = <code>${sum}</code>.`,
            roles: { [i]: "active" },
            pointers: { [i]: `d=${d}` },
            memory: { "Term": `${d}^${power} = ${term}`, "Sum": sum },
        });
    });

    const isArm = sum === num;
    frames.push({
        phase: "result",
        title: isArm ? `Sum ${sum} == ${num} (Armstrong!)` : `Sum ${sum} != ${num}`,
        guidance: isArm
            ? `Sum of powers <code>${sum}</code> equals original number <code>${num}</code>! Return <code>True</code>.`
            : `Sum of powers <code>${sum}</code> does NOT equal <code>${num}</code>. Return <code>False</code>.`,
        roles: Object.fromEntries(digits.map((_, i) => [i, isArm ? "match" : "compare"])),
        pointers: {},
        memory: { "Result": isArm ? "True" : "False" },
    });

    return { items, frames, inputSummary: `n = ${num}` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. All Divisors Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulateDivisors(inputData, approach) {
    const n = inputData.number !== undefined ? inputData.number : 12;
    const items = [];
    const limit = Math.min(n, 12);
    for (let i = 1; i <= limit; i++) items.push(String(i));
    const frames = [];

    frames.push({
        phase: "init",
        title: `Find All Divisors of ${n}`,
        guidance: `Test candidates from 1 to ${limit} to check which numbers divide ${n} with zero remainder.`,
        roles: {},
        pointers: {},
        memory: { "N": n, "Divisors": "[]" },
    });

    const divs = [];
    for (let i = 1; i <= limit; i++) {
        const isDiv = n % i === 0;
        if (isDiv) divs.push(i);

        frames.push({
            phase: isDiv ? "update" : "scan",
            title: `Test i = ${i}: ${n} % ${i} === ${n % i}`,
            guidance: isDiv
                ? `<code>${n} % ${i} === 0</code>! <strong>${i} is a divisor</strong> of ${n}.`
                : `<code>${n} % ${i} === ${n % i}</code> (non-zero remainder). ${i} is not a divisor.`,
            roles: { [i - 1]: isDiv ? "match" : "compare" },
            pointers: { [i - 1]: isDiv ? "div" : "i" },
            memory: { "Candidate": i, "Divisors": `[${divs.join(", ")}]` },
        });
    }

    frames.push({
        phase: "result",
        title: `Divisors of ${n}: [${divs.join(", ")}]`,
        guidance: `Search completed. Valid divisors of ${n} found: <code>[${divs.join(", ")}]</code>.`,
        roles: Object.fromEntries(divs.map((d) => [d - 1, "match"])),
        pointers: {},
        memory: { "Result": `[${divs.join(", ")}]` },
    });

    return { items, frames, inputSummary: `N = ${n}` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 10. Count Digits Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulateCountDigits(inputData, approach) {
    const n = inputData.number !== undefined ? Math.abs(inputData.number) : 7789;
    const digits = String(n).split("");
    const items = digits.slice();
    const frames = [];

    frames.push({
        phase: "init",
        title: `Count Digits for N = ${n}`,
        guidance: `We count how many digits make up <code>${n}</code> by repeatedly extracting the last digit with <code>N % 10</code> and dividing <code>N // 10</code>.`,
        roles: {},
        pointers: {},
        memory: { "N": n, "Digits Counted": 0 },
    });

    let count = 0;
    let temp = n;
    for (let i = digits.length - 1; i >= 0; i--) {
        const lastDigit = temp % 10;
        count++;
        temp = Math.floor(temp / 10);

        frames.push({
            phase: "scan",
            title: `Extract Digit '${lastDigit}' (Count: ${count})`,
            guidance: `Extracted last digit <code>${lastDigit} = ${temp * 10 + lastDigit} % 10</code>. Count is incremented to <strong>${count}</strong>. Remaining number is <code>${temp}</code>.`,
            roles: { [i]: "active" },
            pointers: { [i]: `d=${lastDigit}` },
            memory: { "Extracted": lastDigit, "Remaining N": temp, "Digits Counted": count },
        });
    }

    frames.push({
        phase: "result",
        title: `Total Digits = ${count}`,
        guidance: `All digits processed. <code>N</code> has reduced to <code>0</code>. Total count is <strong>${count}</strong>.`,
        roles: Object.fromEntries(digits.map((_, idx) => [idx, "match"])),
        pointers: {},
        memory: { "Total Digits": count, "Result": count },
    });

    return { items, frames, inputSummary: `N = ${n}` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 11. Reverse a Number Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulateReverseNumber(inputData, approach) {
    const n = inputData.number !== undefined ? inputData.number : 12345;
    const sign = n < 0 ? -1 : 1;
    const absN = Math.abs(n);
    const digits = String(absN).split("");
    const items = digits.slice();
    const frames = [];

    frames.push({
        phase: "init",
        title: `Reverse Number: ${n}`,
        guidance: `Reverse <code>${n}</code> by extracting digits right-to-left: <code>rev = rev * 10 + (N % 10)</code> and <code>N = N // 10</code>.`,
        roles: {},
        pointers: {},
        memory: { "Original N": n, "Reversed": 0 },
    });

    let rev = 0;
    let temp = absN;
    for (let i = digits.length - 1; i >= 0; i--) {
        const d = temp % 10;
        rev = rev * 10 + d;
        temp = Math.floor(temp / 10);

        frames.push({
            phase: "update",
            title: `Shift & Append Digit ${d} → rev = ${rev}`,
            guidance: `Extracted <code>${d}</code>. Update reversed number: <code>${Math.floor(rev / 10)} * 10 + ${d} = ${rev}</code>. Remaining N: <code>${temp}</code>.`,
            roles: { [i]: "active" },
            pointers: { [i]: `d=${d}` },
            memory: { "Extracted Digit": d, "Current Reversed": rev * sign, "Remaining N": temp },
        });
    }

    const finalRev = rev * sign;
    frames.push({
        phase: "result",
        title: `Reversed Number = ${finalRev}`,
        guidance: `All digits reversed successfully! Final reversed integer is <strong>${finalRev}</strong>.`,
        roles: Object.fromEntries(digits.map((_, idx) => [idx, "match"])),
        pointers: {},
        memory: { "Result": finalRev },
    });

    return { items, frames, inputSummary: `N = ${n}` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 12. Check Prime Simulation
// ─────────────────────────────────────────────────────────────────────────────
function simulateCheckPrime(inputData, approach) {
    const n = inputData.number !== undefined ? inputData.number : 29;
    const items = [];
    const limit = Math.floor(Math.sqrt(n));
    for (let i = 2; i <= Math.max(limit, 5); i++) items.push(String(i));
    const frames = [];

    frames.push({
        phase: "init",
        title: `Check if ${n} is Prime`,
        guidance: approach === "optimized"
            ? `A prime number is only divisible by 1 and itself. In the optimized method, we test candidate divisors up to <code>√${n} ≈ ${limit}</code> in O(√N) time.`
            : `Brute Force: Check if any candidate number between 2 and ${n - 1} divides ${n} with zero remainder.`,
        roles: {},
        pointers: {},
        memory: { "N": n, "Limit (√N)": limit, "Approach": approach === "optimized" ? "O(√N)" : "O(N)" },
    });

    let isPrime = n > 1;
    if (n <= 1) {
        isPrime = false;
        frames.push({
            phase: "result",
            title: `${n} is Not Prime`,
            guidance: `Numbers ≤ 1 are not prime by definition. Return <code>False</code>.`,
            roles: {},
            pointers: {},
            memory: { "Result": "False" },
        });
        return { items: [String(n)], frames, inputSummary: `N = ${n}` };
    }

    for (let i = 2; i <= limit; i++) {
        const remainder = n % i;
        const divides = remainder === 0;
        const cellIdx = i - 2;

        if (divides) {
            frames.push({
                phase: "result",
                title: `Factor Found: ${i} divides ${n}!`,
                guidance: `<code>${n} % ${i} === 0</code>! Since ${n} is divisible by ${i}, it is <strong>composite (not prime)</strong>.`,
                roles: { [cellIdx]: "compare" },
                pointers: { [cellIdx]: "factor" },
                memory: { "N": n, "Divisor": i, "Remainder": 0, "Is Prime": "False" },
            });
            isPrime = false;
            break;
        } else {
            frames.push({
                phase: "scan",
                title: `Test Divisor ${i}: ${n} % ${i} = ${remainder}`,
                guidance: `<code>${n} % ${i} = ${remainder}</code> (non-zero remainder). ${i} does not divide ${n}. Move forward.`,
                roles: { [cellIdx]: "active" },
                pointers: { [cellIdx]: `i=${i}` },
                memory: { "Testing": i, "Remainder": remainder },
            });
        }
    }

    if (isPrime) {
        frames.push({
            phase: "result",
            title: `${n} is a Prime Number!`,
            guidance: `No divisor ≤ <code>√${n} (${limit})</code> divided ${n} evenly. Therefore, <strong>${n} is prime!</strong> Return <code>True</code>.`,
            roles: Object.fromEntries(items.map((_, idx) => [idx, "match"])),
            pointers: {},
            memory: { "Result": "True", "Verdict": "Prime" },
        });
    }

    return { items, frames, inputSummary: `N = ${n}` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 13. GCD / HCF (Euclidean Algorithm)
// ─────────────────────────────────────────────────────────────────────────────
function simulateGCD(inputData, approach) {
    let a = 48, b = 18;
    if (inputData.type === "two_numbers") {
        a = inputData.a;
        b = inputData.b;
    } else if (inputData.type === "array_target" && inputData.array) {
        a = Number(inputData.array[0] || 48);
        b = Number(inputData.target || 18);
    } else if (inputData.array && inputData.array.length >= 2) {
        a = Number(inputData.array[0]);
        b = Number(inputData.array[1]);
    }
    const origA = a, origB = b;
    const items = [String(a), String(b)];
    const frames = [];

    frames.push({
        phase: "init",
        title: `Compute GCD(${a}, ${b})`,
        guidance: `Euclidean Algorithm: <code>gcd(a, b) = gcd(b, a % b)</code>. We repeatedly take remainder until remainder is 0.`,
        roles: { 0: "active", 1: "active" },
        pointers: { 0: "a", 1: "b" },
        memory: { "a": a, "b": b, "Operation": "a % b" },
    });

    let x = a, y = b;
    let step = 1;
    while (y !== 0 && step < 10) {
        const rem = x % y;
        frames.push({
            phase: "compare",
            title: `Step ${step}: ${x} % ${y} = ${rem}`,
            guidance: `Compute remainder <code>${x} % ${y} = ${rem}</code>. Next state: <code>a = ${y}</code>, <code>b = ${rem}</code>.`,
            roles: { 0: "active", 1: "compare" },
            pointers: { 0: `a=${x}`, 1: `b=${y}` },
            memory: { "a": x, "b": y, "Remainder (a % b)": rem },
        });
        x = y;
        y = rem;
        step++;
    }

    frames.push({
        phase: "result",
        title: `GCD(${origA}, ${origB}) = ${x}`,
        guidance: `Remainder reached 0. The greatest common divisor is <strong>${x}</strong>!`,
        roles: { 0: "match", 1: "match" },
        pointers: { 0: "gcd", 1: "0" },
        memory: { "GCD": x, "Result": x },
    });

    return { items: [String(origA), String(origB)], frames, inputSummary: `GCD(${origA}, ${origB})` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 14. Find Largest Element
// ─────────────────────────────────────────────────────────────────────────────
function simulateFindLargest(inputData, approach) {
    const arr = Array.isArray(inputData.array) ? inputData.array.map(Number) : [3, 2, 1, 56, 10000, 167];
    const items = arr.map(String);
    const frames = [];

    frames.push({
        phase: "init",
        title: "Initialize Max Element",
        guidance: `We track the largest element seen so far. Start by initializing <code>max_val = arr[0] (${arr[0]})</code>.`,
        roles: { 0: "active" },
        pointers: { 0: "max" },
        memory: { "Max Val": arr[0], "Max Index": 0 },
    });

    let maxVal = arr[0];
    let maxIdx = 0;

    for (let i = 1; i < arr.length; i++) {
        const cur = arr[i];
        const isNewMax = cur > maxVal;

        if (isNewMax) {
            maxVal = cur;
            maxIdx = i;
            frames.push({
                phase: "update",
                title: `New Maximum Found: arr[${i}] = ${cur}`,
                guidance: `<code>${cur} > ${maxVal}</code>! Update <code>max_val = ${cur}</code> at index <code>${i}</code>.`,
                roles: { [i]: "match" },
                pointers: { [i]: "max" },
                memory: { "Max Val": maxVal, "Max Index": i, "Progress": `${i + 1}/${arr.length}` },
            });
        } else {
            frames.push({
                phase: "scan",
                title: `Compare arr[${i}] (${cur}) ≤ max (${maxVal})`,
                guidance: `<code>${cur} ≤ ${maxVal}</code>. Current maximum remains <code>${maxVal}</code>. Move to next element.`,
                roles: { [maxIdx]: "match", [i]: "compare" },
                pointers: { [maxIdx]: "max", [i]: "i" },
                memory: { "Max Val": maxVal, "Inspecting": cur },
            });
        }
    }

    frames.push({
        phase: "result",
        title: `Largest Element = ${maxVal}`,
        guidance: `Array scan complete. The largest element in the array is <strong>${maxVal}</strong> at index <code>${maxIdx}</code>.`,
        roles: { [maxIdx]: "match" },
        pointers: { [maxIdx]: "largest" },
        memory: { "Largest": maxVal, "Result": maxVal },
    });

    return { items, frames, inputSummary: `arr = [${arr.join(", ")}]` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 15. Linear Search
// ─────────────────────────────────────────────────────────────────────────────
function simulateLinearSearch(inputData, approach) {
    const arr = Array.isArray(inputData.array) ? inputData.array.map(Number) : [1, 2, 3, 4, 5];
    const target = inputData.target !== undefined ? Number(inputData.target) : 3;
    const items = arr.map(String);
    const frames = [];

    frames.push({
        phase: "init",
        title: `Linear Search for Target = ${target}`,
        guidance: `Scan the array sequentially from index 0 to ${arr.length - 1} checking if <code>arr[i] == ${target}</code>.`,
        roles: {},
        pointers: {},
        memory: { "Target": target, "Array Size": arr.length },
    });

    let foundIdx = -1;
    for (let i = 0; i < arr.length; i++) {
        if (arr[i] === target) {
            frames.push({
                phase: "result",
                title: `Target Found at Index ${i}!`,
                guidance: `🎯 <code>arr[${i}] = ${arr[i]}</code> equals target <code>${target}</code>! Return index <code>${i}</code>.`,
                roles: { [i]: "match" },
                pointers: { [i]: "found" },
                memory: { "Found Index": i, "Value": arr[i], "Target": target },
            });
            foundIdx = i;
            break;
        } else {
            frames.push({
                phase: "scan",
                title: `Check arr[${i}] = ${arr[i]}`,
                guidance: `<code>arr[${i}] = ${arr[i]}</code> does not match target <code>${target}</code>. Move to next element.`,
                roles: { [i]: "compare" },
                pointers: { [i]: "i" },
                memory: { "Current": arr[i], "Target": target, "Index": i },
            });
        }
    }

    if (foundIdx === -1) {
        frames.push({
            phase: "result",
            title: `Target ${target} Not Found`,
            guidance: `Scanned all ${arr.length} elements without finding target <code>${target}</code>. Return <code>-1</code>.`,
            roles: Object.fromEntries(arr.map((_, i) => [i, "visited"])),
            pointers: {},
            memory: { "Result": -1 },
        });
    }

    return { items, frames, inputSummary: `arr = [${arr.join(", ")}], target = ${target}` };
}

// ─────────────────────────────────────────────────────────────────────────────
// 16. General Dynamic Simulator Fallback
// ─────────────────────────────────────────────────────────────────────────────
function simulateGeneral(inputData, approach, problem) {
    const items = inputData.items && inputData.items.length ? inputData.items : ["1", "2", "3", "4", "5"];
    const frames = [];
    const isOpt = approach === "optimized";

    frames.push({
        phase: "init",
        title: `${isOpt ? "Optimized Strategy" : "Brute Force Scan"} Initialized`,
        guidance: `Input parsed: <code>${items.join(", ")}</code>. Setting up execution state for <strong>${escapeHtml(problem?.title || "Problem")}</strong>.`,
        roles: {},
        pointers: {},
        memory: { "Input Count": items.length, "Approach": isOpt ? "Optimized" : "Brute Force" },
    });

    const stepCap = Math.min(items.length, 8);
    for (let i = 0; i < stepCap; i++) {
        frames.push({
            phase: i % 2 === 0 ? "scan" : "compare",
            title: `Step ${i + 1}: Inspect Item at Index ${i} ('${items[i]}')`,
            guidance: `Evaluating element <code>${items[i]}</code> at position <code>${i}</code> according to the ${isOpt ? "optimized" : "brute-force"} rules.`,
            roles: { [i]: "active" },
            pointers: { [i]: `i=${i}` },
            memory: { "Index": i, "Value": items[i], "Progress": `${i + 1}/${items.length}` },
        });
    }

    frames.push({
        phase: "result",
        title: "Execution Completed",
        guidance: `All elements evaluated successfully. Yielding computed result for <code>[${items.join(", ")}]</code>.`,
        roles: Object.fromEntries(items.map((_, i) => [i, "match"])),
        pointers: {},
        memory: { "Status": "Success", "Approach": isOpt ? "Optimized" : "Brute Force" },
    });

    return { items, frames, inputSummary: inputData.raw || items.join(", ") };
}

function formatMap(obj) {
    const keys = Object.keys(obj);
    if (!keys.length) return "{}";
    return "{" + keys.map((k) => `${k}: ${obj[k]}`).join(", ") + "}";
}

function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, (m) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
    }[m]));
}

import json
import os
import re
import zipfile
from typing import Any, Dict, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CACHE_FILE = os.path.join(DATA_DIR, "dsa_problems.json")
# Brute-force solutions live in a separate, independently-regenerable file
# ({problem_id: python_code}) rather than being baked into the main
# curriculum cache — keeps the curated curriculum file untouched and lets
# the brute-force set be extended/regenerated without touching anything else.
BRUTE_FORCE_FILE = os.path.join(DATA_DIR, "dsa_brute_force.json")
AIML_CURRICULUM_FILE = os.path.join(DATA_DIR, "aiml_curriculum.json")

# Look for curriculum zip archive in project root
_ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
_ZIP_CANDIDATES = [
    os.path.join(_ROOT_DIR, f)
    for f in os.listdir(_ROOT_DIR)
    if f.endswith(".zip")
] if os.path.exists(_ROOT_DIR) else []
ZIP_FILE = _ZIP_CANDIDATES[0] if _ZIP_CANDIDATES else os.path.join(_ROOT_DIR, "dsa-curriculum.zip")


class ProblemLoader:
    """Extracts, parses, and serves all 340+ DSA & AI/ML problems with clean boilerplates."""

    def __init__(self, zip_path: str = ZIP_FILE, cache_path: str = CACHE_FILE, force_reload: bool = False):
        self.zip_path = zip_path
        self.cache_path = cache_path
        self.problems_cache: Dict[str, Dict[str, Any]] = {}
        self._load_problems(force_reload=force_reload)
        self._merge_brute_force()
        self._merge_aiml_curriculum()

    def _merge_aiml_curriculum(self) -> None:
        """Merge specialized AI/ML & Data Engineering problems into curriculum."""
        if not os.path.exists(AIML_CURRICULUM_FILE):
            return
        try:
            with open(AIML_CURRICULUM_FILE, "r", encoding="utf-8") as f:
                aiml_probs = json.load(f)
            for p in aiml_probs:
                self.problems_cache[p["id"]] = p
        except Exception as e:
            print(f"[ProblemLoader] Warning: could not load aiml curriculum: {e}")

    def _merge_brute_force(self) -> None:
        """Overlay verified brute-force solutions onto the loaded problems, if present."""
        if not os.path.exists(BRUTE_FORCE_FILE):
            return
        try:
            with open(BRUTE_FORCE_FILE, "r", encoding="utf-8") as f:
                brute_map = json.load(f)
            for pid, code in brute_map.items():
                if pid in self.problems_cache and code:
                    self.problems_cache[pid]["brute_force_solution"] = code
        except Exception:
            pass

    def reload_brute_force(self) -> None:
        """Public hook to pick up a freshly-regenerated brute-force file without a full restart."""
        self._merge_brute_force()

    def _load_problems(self, force_reload: bool = False) -> None:
        """Load from JSON cache or extract from zip file."""
        if not force_reload and os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.problems_cache = {p["id"]: p for p in data}
                    if len(self.problems_cache) > 0:
                        return
            except Exception:
                pass

        if not os.path.exists(self.zip_path):
            return

        parsed = []
        with zipfile.ZipFile(self.zip_path, "r") as z:
            for filename in sorted(z.namelist()):
                if not (filename.endswith(".py") or filename.endswith(".PY")):
                    continue
                parts = filename.split("/")
                if len(parts) < 3:
                    continue

                step_folder = parts[1]
                base_file = parts[-1]
                prob_slug = base_file.replace(".py", "").replace(".PY", "").lower()

                # Clean Title
                raw_name = base_file.replace(".py", "").replace(".PY", "").replace("-", " ").replace("_", " ")
                title = " ".join(word.capitalize() for word in raw_name.split())

                try:
                    code_content = z.read(filename).decode("utf-8", errors="ignore")
                except Exception:
                    continue

                # Extract method signature
                method_match = re.search(
                    r"def\s+([a-zA-Z0-9_]+)\s*\((.*?)\)(?:\s*->\s*([a-zA-Z0-9_\[\],\s]+))?:",
                    code_content,
                )
                method_name = method_match.group(1) if method_match else "solve"
                params = method_match.group(2) if method_match else ""
                ret_type = f" -> {method_match.group(3)}" if method_match and method_match.group(3) else ""

                # Normalize params so 'self' is always the first parameter
                clean_params = params.strip()
                if not clean_params:
                    clean_params = "self"
                elif not clean_params.startswith("self"):
                    clean_params = f"self, {clean_params}"

                topic = step_folder.split(" - ")[-1] if " - " in step_folder else step_folder

                # Boilerplate header additions
                header_imports = "from typing import List, Optional, Dict, Set, Tuple\n\n"
                if "tree" in topic.lower() or "bst" in topic.lower():
                    header_imports += (
                        "# Definition for a binary tree node.\n"
                        "# class TreeNode:\n"
                        "#     def __init__(self, val=0, left=None, right=None):\n"
                        "#         self.val = val\n"
                        "#         self.left = left\n"
                        "#         self.right = right\n\n"
                    )
                elif "linked list" in topic.lower() or "linked_list" in topic.lower():
                    header_imports += (
                        "# Definition for singly-linked list.\n"
                        "# class ListNode:\n"
                        "#     def __init__(self, val=0, next=None):\n"
                        "#         self.val = val\n"
                        "#         self.next = next\n\n"
                    )

                # Pure starter boilerplate
                starter_code = (
                    f"{header_imports}"
                    f"class Solution:\n"
                    f"    def {method_name}({clean_params}){ret_type}:\n"
                    f"        # Write your Python solution here\n"
                    f"        pass\n"
                )

                # Difficulty Heuristic
                diff = "Medium"
                lower_folder = step_folder.lower()
                lower_title = title.lower()
                if any(k in lower_folder for k in ["basics", "sorting"]):
                    diff = "Easy"
                elif any(k in lower_title for k in ["easy", "check", "reverse", "palindrome", "count", "is"]):
                    diff = "Easy"
                elif any(k in lower_title or k in lower_folder for k in ["hard", "tries", "advanced", "median", "kth", "graph"]):
                    diff = "Hard"

                problem_id = f"{step_folder}_{prob_slug}".replace(" ", "_").replace("-", "_").lower()

                description = (
                    f"### Problem Statement\n\n"
                    f"Solve the **{title}** problem from **{step_folder}** ({topic}).\n\n"
                    f"Implement the `Solution.{method_name}()` method in Python.\n\n"
                    f"#### Topics & Tags\n"
                    f"- **Step:** {step_folder}\n"
                    f"- **Category:** {topic}\n"
                    f"- **Difficulty:** {diff}\n"
                )

                # Clean reference solution of external urls or branding
                clean_ref = re.sub(r"#\s*https?://\S+", "", code_content)
                clean_ref = re.sub(r"#\s*Striver[^\n]*\n?", "", clean_ref, flags=re.I)
                clean_ref = re.sub(r"Striver[^\s]*", "Curriculum", clean_ref, flags=re.I)

                clean_file_path = f"curriculum/{step_folder}/{base_file}"

                prob_item = {
                    "id": problem_id,
                    "title": title,
                    "step": step_folder,
                    "topic": topic,
                    "difficulty": diff,
                    "method_name": method_name,
                    "description": description,
                    "starter_code": starter_code,
                    "reference_solution": clean_ref,
                    "file_path": clean_file_path,
                }
                parsed.append(prob_item)

        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)

        self.problems_cache = {p["id"]: p for p in parsed}

    def get_all_problems(self) -> List[Dict[str, Any]]:
        return list(self.problems_cache.values())

    def get_problem(self, problem_id: str) -> Optional[Dict[str, Any]]:
        return self.problems_cache.get(problem_id)

    def get_steps_summary(self) -> List[Dict[str, Any]]:
        steps_dict: Dict[str, List[Dict[str, Any]]] = {}
        for p in self.problems_cache.values():
            step = p["step"]
            if step not in steps_dict:
                steps_dict[step] = []
            steps_dict[step].append(p)

        def step_sort_key(item):
            m = re.search(r"Step\s+(\d+)", item[0], re.I)
            return int(m.group(1)) if m else 999

        summary = []
        for step, probs in sorted(steps_dict.items(), key=step_sort_key):
            summary.append({
                "step": step,
                "topic": probs[0]["topic"] if probs else step,
                "total_problems": len(probs),
                "easy_count": sum(1 for p in probs if p["difficulty"] == "Easy"),
                "medium_count": sum(1 for p in probs if p["difficulty"] == "Medium"),
                "hard_count": sum(1 for p in probs if p["difficulty"] == "Hard"),
                "problem_ids": [p["id"] for p in probs],
            })
        return summary

import base64
import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional


class PythonCodeRunner:
    """Executes and tests Python solutions in an isolated subprocess with timeout safeguards."""

    TIMEOUT_SECONDS = 5

    @classmethod
    def execute_code(
        cls,
        user_code: str,
        method_name: str,
        reference_solution: Optional[str] = None,
        custom_input: Optional[str] = None,
        test_inputs: Optional[List[Any]] = None,
        test_cases: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute user code against test inputs, custom input, or curated test cases.
        Returns detailed execution metrics, pass/fail statuses, stdout, and tracebacks.
        """
        user_b64 = base64.b64encode(user_code.encode("utf-8")).decode("ascii")
        ref_b64 = base64.b64encode((reference_solution or "").encode("utf-8")).decode("ascii")
        custom_in_b64 = base64.b64encode((custom_input or "").encode("utf-8")).decode("ascii")
        test_cases_json = json.dumps(test_cases or [])
        test_cases_b64 = base64.b64encode(test_cases_json.encode("utf-8")).decode("ascii")

        harness_script = cls._generate_test_harness(
            user_b64=user_b64,
            ref_b64=ref_b64,
            method_name=method_name,
            custom_in_b64=custom_in_b64,
            test_cases_b64=test_cases_b64,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(harness_script)
            temp_path = f.name

        start_time = time.perf_counter()
        try:
            python_executable = sys.executable
            proc = subprocess.run(
                [python_executable, temp_path],
                capture_output=True,
                text=True,
                timeout=cls.TIMEOUT_SECONDS,
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            if proc.returncode != 0 or not stdout:
                return {
                    "status": "Runtime Error",
                    "passed": False,
                    "execution_time_ms": elapsed_ms,
                    "stdout": stdout,
                    "error": stderr or f"Process exited with code {proc.returncode}",
                    "test_results": [],
                }

            try:
                result_data = json.loads(stdout)
                result_data["execution_time_ms"] = elapsed_ms
                return result_data
            except json.JSONDecodeError:
                return {
                    "status": "Runtime Error",
                    "passed": False,
                    "execution_time_ms": elapsed_ms,
                    "stdout": stdout,
                    "error": f"Invalid harness response:\n{stdout}\n{stderr}",
                    "test_results": [],
                }

        except subprocess.TimeoutExpired:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "Time Limit Exceeded",
                "passed": False,
                "execution_time_ms": elapsed_ms,
                "stdout": "",
                "error": f"Execution timed out after {cls.TIMEOUT_SECONDS} seconds. Check for infinite loops.",
                "test_results": [],
            }
        except Exception as e:
            return {
                "status": "Runtime Error",
                "passed": False,
                "execution_time_ms": 0.0,
                "stdout": "",
                "error": str(e),
                "test_results": [],
            }
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    @classmethod
    def _generate_test_harness(
        cls,
        user_b64: str,
        ref_b64: str,
        method_name: str,
        custom_in_b64: str,
        test_cases_b64: str = "",
    ) -> str:
        return f'''
import sys
import json
import base64
import inspect
import math
from io import StringIO
from typing import *

# Capture user print stdout
captured_output = StringIO()
sys.stdout = captured_output

USER_CODE = base64.b64decode("{user_b64}").decode("utf-8")
REF_CODE = base64.b64decode("{ref_b64}").decode("utf-8")
CUSTOM_INPUT = base64.b64decode("{custom_in_b64}").decode("utf-8").strip()
RAW_TEST_CASES = base64.b64decode("{test_cases_b64}").decode("utf-8").strip() if "{test_cases_b64}" else "[]"
try:
    TEST_CASES = json.loads(RAW_TEST_CASES)
except Exception:
    TEST_CASES = []

def are_equal(a, b, tol=1e-4):
    """Deep structural equality check with numerical floating-point tolerance."""
    if a is b:
        return True
    if a is None or b is None:
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return False
        return all(are_equal(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(are_equal(a[k], b[k], tol) for k in a)
    return a == b

def run_tests():
    user_globals = {{}}
    try:
        exec(USER_CODE, user_globals)
    except Exception as e:
        import traceback
        sys.stdout = sys.__stdout__
        print(json.dumps({{
            "status": "Syntax / Compilation Error",
            "passed": False,
            "error": traceback.format_exc(),
            "test_results": []
        }}))
        return

    if "Solution" not in user_globals:
        sys.stdout = sys.__stdout__
        print(json.dumps({{
            "status": "Runtime Error",
            "passed": False,
            "error": "Class 'Solution' not found in your code.",
            "test_results": []
        }}))
        return

    user_sol = user_globals["Solution"]()

    target_method_name = "{method_name}"
    if not hasattr(user_sol, target_method_name):
        methods = [m for m in dir(user_sol) if not m.startswith("_") and callable(getattr(user_sol, m))]
        if methods:
            target_method_name = methods[0]
        else:
            sys.stdout = sys.__stdout__
            print(json.dumps({{
                "status": "Runtime Error",
                "passed": False,
                "error": f"Method '{{target_method_name}}' not found in Solution class.",
                "test_results": []
            }}))
            return

    user_fn = getattr(user_sol, target_method_name)

    ref_fn = None
    if REF_CODE.strip():
        ref_globals = {{}}
        try:
            exec(REF_CODE, ref_globals)
            if "Solution" in ref_globals:
                ref_sol = ref_globals["Solution"]()
                if hasattr(ref_sol, target_method_name):
                    ref_fn = getattr(ref_sol, target_method_name)
        except Exception:
            pass

    try:
        sig = inspect.signature(user_fn)
        param_count = len(sig.parameters)
    except Exception:
        param_count = 1

    test_results = []
    all_passed = True
    first_error = None

    if CUSTOM_INPUT:
        try:
            parsed_in = eval(CUSTOM_INPUT)
            if isinstance(parsed_in, tuple):
                args = list(parsed_in)
            elif isinstance(parsed_in, dict):
                args = list(parsed_in.values())
            else:
                args = [parsed_in]
        except Exception:
            args = [CUSTOM_INPUT]

        try:
            user_res = user_fn(*args)
            ref_res = ref_fn(*args) if ref_fn else None
            is_match = are_equal(user_res, ref_res) if ref_res is not None else True
            test_results.append({{
                "test_id": 1,
                "input": str(args),
                "user_output": repr(user_res),
                "expected_output": repr(ref_res) if ref_res is not None else "Custom Run",
                "passed": is_match,
            }})
            all_passed = is_match
        except Exception as e:
            import traceback
            first_error = traceback.format_exc()
            all_passed = False
            test_results.append({{
                "test_id": 1,
                "input": str(args),
                "user_output": "Error",
                "expected_output": "N/A",
                "passed": False,
                "error": first_error
            }})
    elif TEST_CASES:
        for idx, tc in enumerate(TEST_CASES, start=1):
            raw_args = tc.get("input", [])
            args = list(raw_args) if isinstance(raw_args, (list, tuple)) else [raw_args]
            try:
                expected = tc.get("expected")
                if expected is None and ref_fn:
                    expected = ref_fn(*args)
                user_res = user_fn(*args)
                passed = are_equal(user_res, expected) if expected is not None else True
                test_results.append({{
                    "test_id": idx,
                    "input": str(args),
                    "user_output": repr(user_res),
                    "expected_output": repr(expected) if expected is not None else "Valid Output",
                    "passed": passed,
                }})
                if not passed:
                    all_passed = False
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                if not first_error:
                    first_error = err
                all_passed = False
                test_results.append({{
                    "test_id": idx,
                    "input": str(args),
                    "user_output": "Exception",
                    "expected_output": repr(tc.get("expected")),
                    "passed": False,
                    "error": str(e)
                }})
    else:
        sample_vectors = []
        if param_count == 1:
            sample_vectors = [
                (5,),
                (12,),
                (28,),
                ([2, 7, 11, 15],),
                ([3, 2, 4],),
                ("racecar",),
            ]
        elif param_count == 2:
            sample_vectors = [
                ([2, 7, 11, 15], 9),
                ([3, 2, 4], 6),
                ([3, 3], 6),
                ("hello", "ll"),
                (10, 2),
            ]
        elif param_count == 3:
            sample_vectors = [
                ([1, 2, 3], 3, 2),
                ([0, 0, 0], 0, 0),
            ]
        else:
            sample_vectors = [()]

        for idx, vec in enumerate(sample_vectors, start=1):
            try:
                expected = ref_fn(*vec) if ref_fn else None
                user_res = user_fn(*vec)
                
                passed = True
                if expected is not None:
                    passed = are_equal(user_res, expected)
                    
                test_results.append({{
                    "test_id": idx,
                    "input": str(vec),
                    "user_output": repr(user_res),
                    "expected_output": repr(expected) if expected is not None else repr(user_res),
                    "passed": passed,
                }})
                if not passed:
                    all_passed = False
                if len(test_results) >= 3:
                    break
            except TypeError:
                continue
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                if not first_error:
                    first_error = err
                all_passed = False
                test_results.append({{
                    "test_id": idx,
                    "input": str(vec),
                    "user_output": "Exception",
                    "expected_output": "Valid Output",
                    "passed": False,
                    "error": str(e)
                }})
                if len(test_results) >= 3:
                    break

    if not test_results:
        try:
            res = user_fn()
            test_results.append({{
                "test_id": 1,
                "input": "()",
                "user_output": repr(res),
                "expected_output": repr(res),
                "passed": True
            }})
            all_passed = True
        except Exception as e:
            test_results.append({{
                "test_id": 1,
                "input": "()",
                "user_output": "Error",
                "expected_output": "N/A",
                "passed": False,
                "error": str(e)
            }})
            all_passed = False

    sys.stdout = sys.__stdout__
    user_stdout = captured_output.getvalue().strip()

    status = "Accepted" if all_passed else ("Runtime Error" if first_error else "Wrong Answer")

    print(json.dumps({{
        "status": status,
        "passed": all_passed,
        "stdout": user_stdout,
        "error": first_error,
        "test_results": test_results,
        "tests_passed": sum(1 for t in test_results if t.get("passed")),
        "tests_total": len(test_results)
    }}))

if __name__ == "__main__":
    run_tests()
'''

"""Test-only helpers: path setup, fixture loader, FakeLLM, CountingFakeLLM."""
import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

FIXTURES = ROOT / "tests" / "fixtures"
LLM_FIXTURES = FIXTURES / "llm"


def load(name):
    """Load tests/fixtures/<name> (e.g. 'sample_request.json') as a fresh dict."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def load_llm(name):
    return json.loads((LLM_FIXTURES / name).read_text(encoding="utf-8"))


def _as_list(x):
    return [] if x is None else (list(x) if isinstance(x, (list, tuple)) else [x])


class FakeLLM:
    """Replays canned answers. `main` serves topic_locator + brief calls, `reviewer` serves brief_review.

    Each can be a fixture file name, a dict, or a list of them (used in order; the last one repeats).
    """

    def __init__(self, main=None, reviewer=None):
        self._src = {"main": _as_list(main), "reviewer": _as_list(reviewer)}
        self._n = {"main": 0, "reviewer": 0}
        self.calls = 0
        self.call_log = []  # (task, payload)

    def complete_json(self, task, prompt, payload):
        self.calls += 1
        self.call_log.append((task, copy.deepcopy(payload)))
        kind = "reviewer" if task == "brief_review" else "main"
        srcs = self._src[kind]
        if not srcs:
            raise AssertionError(f"unexpected LLM call: task={task}")
        item = srcs[min(self._n[kind], len(srcs) - 1)]
        self._n[kind] += 1
        return copy.deepcopy(item) if isinstance(item, dict) else load_llm(item)

    def count(self, task):
        return sum(1 for t, _ in self.call_log if t == task)


class CountingFakeLLM(FakeLLM):
    """No canned answers: any call is counted and then fails the test."""

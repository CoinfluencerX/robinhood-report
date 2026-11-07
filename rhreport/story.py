"""Guardrails for the written story: every number in it must come from the report data.

The story is written by Opus (Claude subscription, `claude -p`) from prompts/story.md. This check runs
before anything is exported, so a model can't slip an invented statistic onto the website.
"""
import re

NUM = re.compile(r"(?<![\w.])[-+]?\$?\d[\d,]*(?:\.\d+)?%?")
SKIP = re.compile(r"`[^`]*`|\]\([^)]*\)|0x[0-9a-fA-F]+|\b\d{4}-\d{2}-\d{2}(?:T[\d:]+Z)?\b")


def _numbers(obj, plain, pct, key=""):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        v = float(obj)
        plain.add(v)
        if key.endswith("_pp"):
            pct.add(v)                # already in percentage points
        elif abs(v) <= 1.5:
            pct.add(v * 100)          # a fraction written as a percent
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _numbers(v, plain, pct, str(k))
    elif isinstance(obj, list):
        for v in obj:
            _numbers(v, plain, pct, key)


def allowed_numbers(report_data):
    """Two sets: numbers that may appear as-is, and numbers that may appear with a % sign."""
    plain, pct = set(), set()
    _numbers(report_data, plain, pct)
    return plain, pct


def _matches(x, decimals, vals):
    tol = 0.5 * 10 ** (-decimals)
    return any(abs(abs(v) - x) <= tol + 1e-9 for v in vals)


def check(markdown, report_data, small_ints=range(0, 11)):
    """Return the list of numbers in the story that the data does not support (empty list = pass)."""
    plain, pct = allowed_numbers(report_data)
    text = SKIP.sub(" ", markdown)
    bad = []
    for m in NUM.finditer(text):
        raw = m.group(0)
        clean = raw.replace("$", "").replace(",", "").rstrip("%")
        try:
            x = float(clean)
        except ValueError:
            continue
        decimals = len(clean.split(".")[1]) if "." in clean else 0
        if decimals == 0 and x.is_integer() and int(x) in small_ints and not raw.endswith("%"):
            continue
        if not _matches(abs(x), decimals, pct if raw.endswith("%") else plain):
            bad.append(raw)
    return bad

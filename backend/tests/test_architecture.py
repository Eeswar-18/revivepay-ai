"""
tests/test_architecture.py — Executable architecture constraints.

Implements held-out environment bans, inward-only model dependencies, and
the monetary-column type ban as AST checks over source text.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[1] / "app"

_HELD_OUT_PREFIXES = ("app.policy", "app.decision", "app.agent", "app.ml")
_ENV_BANNED_MODULES = frozenset(
    {
        "app.core.environment",
        "app.sim.environment",
    }
)
_MODEL_BANNED_PREFIXES = ("app.services", "app.api", "app.repositories")
_FORBIDDEN_COLUMN_TYPES = frozenset({"Float", "Numeric", "Decimal"})


def _is_under(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(module_name == p or module_name.startswith(p + ".") for p in prefixes)


def _module_mentions_environment(dotted: str) -> bool:
    if dotted in _ENV_BANNED_MODULES:
        return True
    parts = dotted.split(".")
    return "environment" in parts


def find_forbidden_imports(source: str, module_name: str) -> list[str]:
    """Parse ``source`` and return human-readable architecture violations."""
    violations: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{module_name}: syntax error: {exc}"]

    held_out = _is_under(module_name, _HELD_OUT_PREFIXES)
    is_model = _is_under(module_name, ("app.models",))

    if held_out and "world_config" in source:
        violations.append(
            f"{module_name}: held-out ban — source references 'world_config'"
        )

    for node in ast.walk(tree):
        imported: list[str] = []
        if isinstance(node, ast.Import):
            imported = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported = [node.module]

        for name in imported:
            if held_out and _module_mentions_environment(name):
                violations.append(
                    f"{module_name}: held-out ban — imports '{name}'"
                )
            if is_model and _is_under(name, _MODEL_BANNED_PREFIXES):
                violations.append(
                    f"{module_name}: models must not import '{name}' (dependencies point inward)"
                )

    return violations


def _mapped_column_type_violations(source: str, module_name: str) -> list[str]:
    """Fail if Float/Numeric/Decimal appear as arguments to mapped_column(...)."""
    violations: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{module_name}: syntax error: {exc}"]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_mapped = (isinstance(func, ast.Name) and func.id == "mapped_column") or (
            isinstance(func, ast.Attribute) and func.attr == "mapped_column"
        )
        if not is_mapped:
            continue
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            for sub in ast.walk(arg):
                if isinstance(sub, ast.Name) and sub.id in _FORBIDDEN_COLUMN_TYPES:
                    violations.append(
                        f"{module_name}: forbidden type {sub.id} inside mapped_column(...)"
                    )
                if isinstance(sub, ast.Attribute) and sub.attr in _FORBIDDEN_COLUMN_TYPES:
                    violations.append(
                        f"{module_name}: forbidden type {sub.attr} inside mapped_column(...)"
                    )
    return violations


def _path_to_module(path: Path) -> str:
    rel = path.relative_to(APP_ROOT)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return "app" + (("." + ".".join(parts)) if parts else "")


def test_find_forbidden_imports_detects_held_out_environment() -> None:
    """Negative test: a synthetic held-out violation must be detected."""
    source = "from app.core.environment import World\n"
    violations = find_forbidden_imports(source, "app.policy.kernel")
    assert violations, "expected at least one held-out import violation"
    assert any("app.core.environment" in v for v in violations)


def test_real_app_tree_has_zero_architecture_violations() -> None:
    """Positive test: walk backend/app and assert zero violations."""
    all_violations: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path.name == ".gitkeep":
            continue
        source = path.read_text(encoding="utf-8")
        module_name = _path_to_module(path)
        all_violations.extend(find_forbidden_imports(source, module_name))
        if _is_under(module_name, ("app.models",)):
            all_violations.extend(_mapped_column_type_violations(source, module_name))

    assert all_violations == [], "architecture violations:\n" + "\n".join(all_violations)


def test_negative_held_out_check_fails_when_inverted() -> None:
    """Prove the negative check is live: inverting the assertion must fail."""
    source = "from app.core.environment import World\n"
    violations = find_forbidden_imports(source, "app.policy.kernel")
    # Correct polarity: violations must be non-empty.
    assert len(violations) > 0
    # Document the inverted form that would fail this session's proof:
    # assert len(violations) == 0  # would fail — confirmed below via pytest.raises path
    with pytest.raises(AssertionError):
        assert len(violations) == 0

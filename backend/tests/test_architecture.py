"""
tests/test_architecture.py — Executable architecture constraints.

Implements the held-out environment ban, inward-only model dependencies, and
the monetary-column type ban as AST checks over source text.

The held-out ban is the most important invariant in this repository.
``app/sim/`` contains the ground-truth outcome environment that grades the
agent.  If any decision-side module could read it — directly, through a
submodule, through a relative import, or by loading ``world_config.yaml`` —
then the agent would be scored by a world it can see, and every uplift number
in the evaluation report would be unfalsifiable.

Two design notes, both the result of holes found by inspection:

1.  The rule is a **universal ban with a tiny allowlist**, not a list of
    "decision-side" packages.  An earlier version enumerated the packages
    that were forbidden to import ``app.sim``; ``app.economics`` and
    ``app.config`` did not exist when that list was written, so they were
    silently exempt until someone noticed.  Enumerating the forbidden set
    fails open every time a package is added.  Enumerating the *permitted*
    set fails closed.

2.  There is exactly ONE import-resolution helper here
    (:func:`_resolved_import_targets`) and every check routes through it.
    An earlier version had two independent AST walkers implementing the same
    rule and they had already drifted: one missed submodule imports, neither
    resolved relative imports.  Do not add a third.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[1] / "app"

# The held-out simulation package.
_SIM_PACKAGE = "app.sim"

# The ONLY modules permitted to import app.sim. Dataset generation and the
# evaluation harness live in scripts/, outside app/, and so are unaffected.
# Adding an entry here punches a hole in the held-out boundary and must be
# justified in an ADR.
_SIM_IMPORT_ALLOWLIST: tuple[str, ...] = (_SIM_PACKAGE,)

# Legacy/renamed environment locations, still banned by name so that a
# revived old path cannot slip through.
_ENV_BANNED_MODULES = frozenset(
    {
        "app.core.environment",
        "app.sim.environment",
    }
)

# Packages that additionally may not name the world config file in code.
_HELD_OUT_PREFIXES = ("app.policy", "app.decision", "app.agent", "app.ml")

_MODEL_BANNED_PREFIXES = ("app.services", "app.api", "app.repositories")
_FORBIDDEN_COLUMN_TYPES = frozenset({"Float", "Numeric", "Decimal"})


# ---------------------------------------------------------------------------
# Module-name helpers
# ---------------------------------------------------------------------------


def _is_under(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(module_name == p or module_name.startswith(p + ".") for p in prefixes)


def _module_mentions_environment(dotted: str) -> bool:
    if dotted in _ENV_BANNED_MODULES:
        return True
    parts = dotted.split(".")
    return "environment" in parts


def _path_to_module(path: Path) -> str:
    rel = path.relative_to(APP_ROOT)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return "app" + (("." + ".".join(parts)) if parts else "")


def _path_to_package(path: Path) -> str:
    """Return the package that relative imports inside *path* resolve against.

    For ``app/economics/net_value.py`` this is ``app.economics``.  For a
    package ``__init__.py`` the module *is* its own package, so
    ``app/economics/__init__.py`` also yields ``app.economics``.  Getting this
    distinction wrong shifts every relative import by one level.
    """
    module = _path_to_module(path)
    if path.name == "__init__.py":
        return module
    return module.rpartition(".")[0] or module


# ---------------------------------------------------------------------------
# Import resolution — the single source of truth for "what does this import?"
# ---------------------------------------------------------------------------


def _resolve_relative(module: str | None, level: int, package: str) -> str | None:
    """Resolve a possibly-relative ``ImportFrom`` target to an absolute name.

    ``level`` follows Python semantics: 0 is absolute, 1 is "current
    package", and each further level walks one package upward.  Returns
    ``None`` if the import escapes the tree (which cannot be checked).
    """
    if level == 0:
        return module
    parts = [p for p in package.split(".") if p]
    drop = level - 1
    if drop > len(parts):
        return None
    base_parts = parts[: len(parts) - drop]
    if module:
        base_parts = base_parts + module.split(".")
    if not base_parts:
        return None
    return ".".join(base_parts)


def _resolved_import_targets(node: ast.AST, package: str) -> list[str]:
    """Every absolute dotted name an import statement could bind.

    Handles three shapes a naive checker misses:

    * ``import app.sim.generators``           → ``['app.sim.generators']``
    * ``from ..sim.environment import World`` → ``['app.sim.environment', ...]``
    * ``from app import sim``                 → ``['app', 'app.sim']``

    The third form matters: ``from app import sim`` followed by
    ``sim.environment.World`` reaches held-out truth without ever spelling
    ``app.sim`` in a single dotted string.

    Emitting ``base.name`` for every alias is deliberately over-broad — for
    ``from app.economics.net_value import net_expected_value`` it yields the
    function's dotted path too.  That is harmless, because these names are
    only ever prefix-matched against banned *packages*.
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    base = _resolve_relative(node.module, node.level, package)
    if base is None:
        return []
    targets = [base]
    for alias in node.names:
        if alias.name != "*":
            targets.append(f"{base}.{alias.name}")
    return targets


# ---------------------------------------------------------------------------
# world_config reference detection
# ---------------------------------------------------------------------------


def _docstring_constant_ids(tree: ast.AST) -> set[int]:
    """Ids of ``Constant`` nodes that are module/class/function docstrings."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


def _references_world_config(tree: ast.AST) -> bool:
    """True if a non-docstring string literal names the world config file.

    Prose mentions in docstrings and ``#`` comments are exempt on purpose.
    The boundary has to be *documented* to be respected, and comments never
    reach the AST anyway.  What this catches is code that actually tries to
    reach the file, e.g. ``Path("app/sim/world_config.yaml")``.  Matching on
    raw source text instead — as an earlier version did — would forbid
    explaining the rule in the very modules that must obey it.
    """
    skip = _docstring_constant_ids(tree)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in skip
            and "world_config" in node.value
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------


def find_forbidden_imports(source: str, module_name: str, package: str | None = None) -> list[str]:
    """Parse ``source`` and return human-readable architecture violations.

    ``package`` is the anchor for relative imports.  When omitted it is
    derived from ``module_name``, which is correct for plain modules; callers
    walking real files should pass :func:`_path_to_package` so that package
    ``__init__`` files anchor correctly.
    """
    violations: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{module_name}: syntax error: {exc}"]

    if package is None:
        package = module_name.rpartition(".")[0] or module_name

    held_out = _is_under(module_name, _HELD_OUT_PREFIXES)
    is_model = _is_under(module_name, ("app.models",))
    may_import_sim = _is_under(module_name, _SIM_IMPORT_ALLOWLIST)

    if held_out and _references_world_config(tree):
        violations.append(f"{module_name}: held-out ban — code references 'world_config'")

    for node in ast.walk(tree):
        for name in _resolved_import_targets(node, package):
            if not may_import_sim and _is_under(name, (_SIM_PACKAGE,)):
                violations.append(
                    f"{module_name}: held-out ban — imports '{name}' "
                    f"('{_SIM_PACKAGE}' is the held-out environment)"
                )
            elif held_out and _module_mentions_environment(name):
                violations.append(f"{module_name}: held-out ban — imports '{name}'")
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


def _iter_app_modules() -> Iterator[tuple[Path, str, str]]:
    """Yield ``(path, module_name, package)`` for every module under app/."""
    for path in sorted(APP_ROOT.rglob("*.py")):
        yield path, _path_to_module(path), _path_to_package(path)


# ---------------------------------------------------------------------------
# Negative tests — prove each enforcement mechanism is live
# ---------------------------------------------------------------------------


def test_find_forbidden_imports_detects_held_out_environment() -> None:
    """A synthetic held-out violation must be detected."""
    source = "from app.core.environment import World\n"
    violations = find_forbidden_imports(source, "app.policy.kernel")
    assert violations, "expected at least one held-out import violation"
    assert any("app.core.environment" in v for v in violations)


def test_find_forbidden_imports_detects_sim_submodule_import() -> None:
    """Importing a NON-environment app.sim submodule must be detected.

    Regression guard: the original checker only flagged dotted names
    containing the word "environment", so ``app.ml.features`` could import
    ``app.sim.generators`` — which knows every ground-truth distribution —
    completely legally.
    """
    source = "from app.sim.generators import generate_population\n"
    violations = find_forbidden_imports(source, "app.ml.features")
    assert violations, "expected app.sim.generators import to be flagged"
    assert any("app.sim.generators" in v for v in violations)


def test_find_forbidden_imports_detects_relative_sim_import() -> None:
    """A relative import that reaches app.sim must be detected.

    Regression guard: ``from ..sim.environment import World`` parses to
    ``ImportFrom(module='sim.environment', level=2)``.  Checkers that read
    only ``node.module`` never see an ``app.sim`` prefix, so this bypassed
    the boundary entirely.
    """
    source = "from ..sim.environment import World\n"
    violations = find_forbidden_imports(source, "app.economics.net_value")
    assert violations, "expected relative app.sim import to be flagged"
    assert any("app.sim.environment" in v for v in violations)


def test_find_forbidden_imports_detects_deep_relative_sim_import() -> None:
    """Three-level relative imports must resolve correctly too."""
    source = "from ...sim import environment\n"
    violations = find_forbidden_imports(source, "app.ml.calibration.fit")
    assert violations, "expected deep relative app.sim import to be flagged"
    assert any("app.sim" in v for v in violations)


def test_find_forbidden_imports_detects_from_package_import_of_sim() -> None:
    """``from app import sim`` must be detected.

    This binds the held-out package to a local name without ever spelling
    ``app.sim`` as a single dotted string.
    """
    source = "from app import sim\n"
    violations = find_forbidden_imports(source, "app.policy.kernel")
    assert violations, "expected 'from app import sim' to be flagged"
    assert any("app.sim" in v for v in violations)


def test_held_out_module_loading_world_config_is_a_violation() -> None:
    """Decision-side code must not name the world config file in code."""
    source = 'CONFIG = Path("app/sim/world_config.yaml")\n'
    violations = find_forbidden_imports(source, "app.agent.planner")
    assert violations, "expected world_config reference to be flagged"
    assert any("world_config" in v for v in violations)


def test_negative_held_out_check_fails_when_inverted() -> None:
    """Prove the negative check is live: inverting the assertion must fail."""
    source = "from app.core.environment import World\n"
    violations = find_forbidden_imports(source, "app.policy.kernel")
    assert len(violations) > 0
    with pytest.raises(AssertionError):
        assert len(violations) == 0


# ---------------------------------------------------------------------------
# Guards against over-broad enforcement (false positives)
# ---------------------------------------------------------------------------


def test_sim_internal_imports_are_permitted() -> None:
    """app.sim may import itself, including relatively.

    Without this the held-out package could not be organised into modules.
    """
    absolute = find_forbidden_imports(
        "from app.sim.environment import World\n", "app.sim.generators"
    )
    relative = find_forbidden_imports("from .environment import World\n", "app.sim.generators")
    assert absolute == [], absolute
    assert relative == [], relative


def test_docstring_prose_about_world_config_is_not_a_violation() -> None:
    """Documenting the boundary must not itself violate the boundary.

    ``app/models/enums.py`` and ``app/core/banding.py`` both explain that
    they mirror values from world_config.yaml.  That prose is how the next
    agent learns the rule, so only real code references count.
    """
    source = '"""This module mirrors keys from world_config.yaml."""\n'
    assert find_forbidden_imports(source, "app.policy.kernel") == []


def test_ordinary_decision_side_imports_are_permitted() -> None:
    """Sanity check that the universal ban is not simply flagging everything."""
    source = "from app.models.enums import ActionType\nimport app.economics.net_value\n"
    assert find_forbidden_imports(source, "app.policy.kernel") == []


# ---------------------------------------------------------------------------
# Positive tests — walk the real tree
# ---------------------------------------------------------------------------


def test_real_app_tree_has_zero_architecture_violations() -> None:
    """Walk backend/app and assert zero violations."""
    all_violations: list[str] = []
    for path, module_name, package in _iter_app_modules():
        source = path.read_text(encoding="utf-8")
        all_violations.extend(find_forbidden_imports(source, module_name, package))
        if _is_under(module_name, ("app.models",)):
            all_violations.extend(_mapped_column_type_violations(source, module_name))

    assert all_violations == [], "architecture violations:\n" + "\n".join(all_violations)


def test_no_app_module_outside_sim_imports_app_sim() -> None:
    """Universal held-out boundary check over every module under app/.

    This subsumes the earlier per-package checks for app.economics and
    app.config: any package added to app/ in future is covered the moment it
    exists, with no test change required.
    """
    violations: list[str] = []
    checked = 0
    for path, module_name, package in _iter_app_modules():
        if _is_under(module_name, _SIM_IMPORT_ALLOWLIST):
            continue
        checked += 1
        source = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            for name in _resolved_import_targets(node, package):
                if _is_under(name, (_SIM_PACKAGE,)):
                    violations.append(
                        f"{module_name}: forbidden import of '{name}' "
                        f"('{_SIM_PACKAGE}' is held-out)"
                    )

    assert violations == [], "modules outside app.sim must not import app.sim:\n" + "\n".join(
        violations
    )
    # Guard against the walk silently covering nothing (e.g. a moved APP_ROOT).
    assert checked > 10, f"expected to check many modules, only saw {checked}"


def test_economics_and_config_do_not_import_app_sim() -> None:
    """Explicit check for the two packages that were previously exempt.

    Retained as a named regression test even though
    :func:`test_no_app_module_outside_sim_imports_app_sim` also covers them —
    these two are where the original hole was found, and a named test makes
    the regression obvious if the universal walk is ever weakened.
    """
    violations: list[str] = []
    for subpackage in ("economics", "config"):
        root = APP_ROOT / subpackage
        assert root.is_dir(), f"expected app/{subpackage}/ to exist"
        for path in sorted(root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            violations.extend(
                find_forbidden_imports(source, _path_to_module(path), _path_to_package(path))
            )
    assert violations == [], "app.economics and app.config must not import app.sim:\n" + "\n".join(
        violations
    )

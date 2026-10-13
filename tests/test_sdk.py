"""Offline checks of the CAPIE script SDK v1 and its demo mod.

The game's own parser is not available offline, so these tests check what can be checked
statically: the generated files are current, braces balance, every SDK name a script calls is
defined, every localisation key exists in every language, the character table matches the
SDK's single definition, the record names fit the contract, and the demo mod follows the
editor grammar of ``plugin/capie/CONTRACT.md``. None of this replaces an in-game test.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

SDK = Path(__file__).resolve().parents[1]
"""SDK folder."""

sys.path.insert(0, str(SDK / "tools"))

import capie_charset  # noqa: E402 - path set up above
import gen_sdk  # noqa: E402 - path set up above

MOD = SDK / "mod"
"""Generated Workshop item."""

DEMO = SDK / "examples" / "capie_demo"
"""Demo mod."""

CONTRACT = SDK.parents[1] / "plugin" / "capie" / "CONTRACT.md"
"""The versioned contract."""

GRAMMAR_ID = r"[a-z0-9]{1,12}"
"""Mod and editor ids of the grammar."""

MODEL = re.compile(rf"^capie_v1_ed__({GRAMMAR_ID})__({GRAMMAR_ID})$")
"""Grammar model name."""

DEFINITION = re.compile(r"^([A-Za-z_][\w]*)\s*=\s*\{", re.MULTILINE)
"""Top-level ``name = {`` at the start of a line."""

CALL = re.compile(r"\b(capie_v1_\w+|mydemo_\w+)\s*=\s*yes\b")
"""A scripted effect or trigger call."""

LOC_LINE = re.compile(r'^ ([\w.]+):0 "(.*)"$')
"""One localisation line."""

RECORD = re.compile(r"temp_var:(capie_(?:cap|ver|epoch|nf|f\d_\w+))")
"""A command record name used by the SDK."""

MAX_RECORD_KEY = 15
"""Longest record name the native transport builds (short-string layout)."""


def strip(text: str) -> str:
    """Remove comments and quoted strings from Paradox script.

    Args:
        text: Script text.

    Returns:
        Text with every quoted string emptied and every comment removed.
    """
    text = re.sub(r'"[^"\n]*"', '""', text)
    return re.sub(r"#[^\n]*", "", text)


def script_files(root: Path) -> list[Path]:
    """Return every script and interface file under a mod folder.

    Args:
        root: Mod folder.

    Returns:
        Sorted ``.txt`` and ``.gui`` files.
    """
    return sorted([*root.rglob("*.txt"), *root.rglob("*.gui")])


def definitions(root: Path) -> set[str]:
    """Return the top-level names defined in scripted effects and triggers.

    Args:
        root: Mod folder.

    Returns:
        Names.
    """
    names: set[str] = set()
    for folder in ("scripted_effects", "scripted_triggers"):
        for path in (root / "common" / folder).glob("*.txt"):
            names |= set(DEFINITION.findall(strip(path.read_text(encoding="utf-8"))))
    return names


def localisation(root: Path, language: str) -> dict[str, str]:
    """Read every localisation file of one language.

    Args:
        root: Mod folder.
        language: Language folder.

    Returns:
        Key to value.
    """
    entries: dict[str, str] = {}
    for path in sorted((root / "localisation" / language).glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
            match = LOC_LINE.match(line)
            if match:
                entries[match.group(1)] = match.group(2)
    return entries


def test_generated_files_are_current() -> None:
    """``mod/`` is exactly what ``gen_sdk.py`` writes."""
    stale = [
        path
        for path, data in gen_sdk.outputs().items()
        if not path.exists() or path.read_bytes() != data
    ]
    assert not stale, f"run gen_sdk.py: {stale}"


@pytest.mark.parametrize("root", [MOD, DEMO], ids=["sdk", "demo"])
def test_braces_balance(root: Path) -> None:
    """Every script and interface file has balanced braces (comments and strings ignored).

    Args:
        root: Mod folder (the SDK or the demo).
    """
    for path in script_files(root):
        depth = 0
        for char in strip(path.read_text(encoding="utf-8")):
            depth += {"{": 1, "}": -1}.get(char, 0)
            assert depth >= 0, f"{path.name}: closing brace without opening"
        assert depth == 0, f"{path.name}: {depth} unclosed braces"


def test_every_call_is_defined() -> None:
    """Every ``capie_v1_* = yes`` and ``mydemo_* = yes`` names a defined effect or trigger."""
    defined = definitions(MOD) | definitions(DEMO)
    for path in script_files(MOD) + script_files(DEMO):
        for name in CALL.findall(strip(path.read_text(encoding="utf-8"))):
            assert name in defined, f"{path.name}: {name} is not defined"


def test_sdk_names_are_reserved() -> None:
    """Every SDK definition starts with ``capie_v1_``; the demo defines none."""
    assert all(name.startswith("capie_v1_") for name in definitions(MOD))
    assert not any(name.startswith("capie_") for name in definitions(DEMO))


def test_localisation_complete() -> None:
    """All ten languages hold the same keys; the character table is identical everywhere."""
    english = localisation(MOD, "english")
    for language in gen_sdk.LANGUAGES:
        entries = localisation(MOD, language)
        assert set(entries) == set(english), language
        for code in range(capie_charset.LAST_CODE + 1):
            assert entries[f"CAPIE_CH_{code}"] == english[f"CAPIE_CH_{code}"], (language, code)
        raw = (MOD / "localisation" / language / f"capie_sdk_v1_l_{language}.yml").read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf" + f"l_{language}:".encode()), language


def test_character_table() -> None:
    """``CAPIE_CH_<code>`` prints the character of the SDK table; no markup can slip in."""
    english = localisation(MOD, "english")
    assert english["CAPIE_CH_0"] == ""
    for code, character in capie_charset.CHARS.items():
        assert english[f"CAPIE_CH_{code}"] == character
    assert capie_charset.encode("Ville-Marie, Québec")[-4] == capie_charset.CODE["é"]
    assert capie_charset.LAST_CODE == 264  # noqa: PLR2004 - contract value


def test_referenced_keys_exist() -> None:
    """Keys used by scripted localisation, GUIs and nested ``$KEY$`` exist in English."""
    sdk_en = localisation(MOD, "english")
    demo_en = sdk_en | localisation(DEMO, "english")
    scripted = (MOD / "common" / "scripted_localisation" / "capie_sdk_v1_text.txt").read_text(
        encoding="utf-8"
    )
    for key in set(re.findall(r"localization_key = (\w+)", scripted)):
        assert key in sdk_en, key
    defined_texts = set(re.findall(r"name = (\w+)", scripted))
    for root, entries in ((MOD, sdk_en), (DEMO, demo_en)):
        texts = [path.read_text(encoding="utf-8") for path in root.rglob("*.gui")]
        texts += list(entries.values())
        for text in texts:
            for key in re.findall(r'(?:text|buttonText|pdx_tooltip) = "([A-Z][A-Z0-9_]+)"', text):
                assert key in entries, key
            for key in re.findall(r"\$([A-Z][A-Z0-9_]+)\$", text):
                assert key in entries, key
            for name in re.findall(r"\[ROOT\.(CAPIE_V1_\w+)\]", text):
                assert name in defined_texts, name


def test_record_names_fit_the_contract() -> None:
    """Command records the SDK reads exist in the contract and fit the 15-byte layout."""
    effects = (MOD / "common" / "scripted_effects" / "capie_sdk_v1_effects.txt").read_text(
        encoding="utf-8"
    )
    records = set(RECORD.findall(effects))
    allowed = {"capie_cap", "capie_ver", "capie_epoch", "capie_nf"}
    for field in range(1, gen_sdk.FIELDS + 1):
        allowed |= {f"capie_f{field}_err", f"capie_f{field}_at", f"capie_f{field}_len"}
        allowed |= {f"capie_f{field}_{slot}" for slot in range(capie_charset.MAX_FIELD_LENGTH)}
    assert records <= allowed, records - allowed
    assert all(len(name) <= MAX_RECORD_KEY for name in allowed)
    assert {"capie_cap", "capie_ver", "capie_epoch"} <= records


def test_error_codes_match_contract() -> None:
    """Every ``capie_err`` code of CONTRACT.md section 10 has a message, and no other code does."""
    section = CONTRACT.read_text(encoding="utf-8").split("## 10.")[1].split("## 11.")[0]
    codes: set[int] = set()
    for first, last in re.findall(r"^\| (\d+)(?:\.\.(\d+))? \|", section, re.MULTILINE):
        codes |= set(range(int(first), int(last or first) + 1))
    codes.discard(0)
    assert set(gen_sdk.ERRORS) == codes


def test_demo_follows_the_grammar() -> None:
    """Demo editors: model names parse, fields are consecutive, carriers and Apply exist."""
    gui = (DEMO / "interface" / "mydemo.gui").read_text(encoding="utf-8")
    sgui = (DEMO / "common" / "scripted_guis" / "mydemo.txt").read_text(encoding="utf-8")
    models = re.findall(r"^\t(capie_v1_ed__\w+) = \{", sgui, re.MULTILINE)
    assert len(models) == 2  # noqa: PLR2004 - motto and name editors
    for model in models:
        match = MODEL.match(model)
        assert match, model
        mod, editor = match.groups()
        assert f'window_name = "{model}"' in sgui
        assert f'name = "{model}"' in gui
        assert f"{model}_apply_click = " in sgui
        assert f'name = "{model}_apply"' in gui
        assert f'name = "capie_v1_ep__{mod}__{editor}"' in gui
        fields = [n for n in range(1, 6) if f'name = "capie_v1_f__{mod}__{editor}__{n}"' in gui]
        assert fields == list(range(1, len(fields) + 1))
        assert 1 <= len(fields) <= gen_sdk.FIELDS
    assert "ignore_enter = yes" in gui
    assert 'shortcut = "RETURN"' in gui


def test_demo_checks_permission_in_the_effect() -> None:
    """Every demo Apply effect begins with the SDK header check and checks the actor."""
    effects = (DEMO / "common" / "scripted_effects" / "mydemo_effects.txt").read_text(
        encoding="utf-8"
    )
    for body in re.findall(r"^mydemo_apply_\w+ = \{(.*?)^\}", effects, re.MULTILINE | re.DOTALL):
        assert body.index("capie_v1_begin = yes") < body.index("capie_v1_field_load = yes")
        assert "capie_v1_actor_ok = yes" in body
        assert "capie_open_epoch" in body


# ---- Checks against the game's own files (PID45148: two parser errors in error.log) ----------

GAME = Path(
    os.environ.get("HOI4_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV")
)
"""HOI4 installation (read only); the tests below are skipped when it is missing."""

TOKEN = re.compile(r'"[^"\n]*"|[{}=]|[^\s{}=#"]+')
"""One token of Paradox script after comments are removed."""

Block = list[tuple[str, "str | Block"]]
"""Parsed script: (key, value or nested block) in file order."""


def parse_blocks(text: str) -> Block:
    """Parse Paradox script into nested ``key = value`` / ``key = { ... }`` pairs.

    Args:
        text: Script text.

    Returns:
        The top-level pairs; bare list items inside braces are ignored.
    """
    tokens = TOKEN.findall(re.sub(r"#[^\n]*", "", text))
    root: Block = []
    stack: list[Block] = [root]
    i = 0
    while i < len(tokens):
        item = tokens[i]
        if item == "}":
            if len(stack) > 1:
                stack.pop()
            i += 1
        elif i + 2 < len(tokens) + 1 and i + 1 < len(tokens) and tokens[i + 1] == "=":
            value = tokens[i + 2] if i + 2 < len(tokens) else ""
            if value == "{":
                child: Block = []
                stack[-1].append((item, child))
                stack.append(child)
            else:
                stack[-1].append((item, value.strip('"')))
            i += 3
        else:
            i += 1
    return root


def vanilla_files(pattern: str) -> list[Path]:
    """Return vanilla files matching a pattern, or skip the test without a game folder.

    Args:
        pattern: Glob relative to the game folder.

    Returns:
        Files.
    """
    files = sorted(GAME.glob(pattern))
    if not files:
        pytest.skip(f"HOI4 not found at {GAME} (set HOI4_DIR)")
    return files


def values_of(block: Block, key: str) -> set[str]:
    """Collect every value of a key anywhere in a parsed block.

    Args:
        block: Parsed script.
        key: Key, compared case-insensitively.

    Returns:
        The values, lower case.
    """
    found: set[str] = set()
    for name, value in block:
        if isinstance(value, list):
            found |= values_of(value, key)
        elif name.lower() == key:
            found.add(value.lower())
    return found


def keys_of(block: Block) -> set[str]:
    """Collect every key anywhere in a parsed block.

    Args:
        block: Parsed script.

    Returns:
        The keys, lower case.
    """
    found: set[str] = set()
    for name, value in block:
        found.add(name.lower())
        if isinstance(value, list):
            found |= keys_of(value)
    return found


def our_guis() -> list[Path]:
    """Return the SDK's and the demo's interface files.

    Returns:
        ``.gui`` files.
    """
    return sorted([*MOD.rglob("*.gui"), *DEMO.rglob("*.gui")])


def test_gui_orientations_are_vanilla() -> None:
    """Every ``orientation`` value is one the game's own interface files use."""
    vanilla: set[str] = set()
    for path in vanilla_files("interface/**/*.gui"):
        vanilla |= values_of(
            parse_blocks(path.read_text(encoding="utf-8", errors="replace")), "orientation"
        )
    for path in our_guis():
        for value in values_of(parse_blocks(path.read_text(encoding="utf-8")), "orientation"):
            assert value in vanilla, f"{path.name}: orientation {value} is not used by the game"


def test_gui_keys_are_vanilla() -> None:
    """Every key in our ``.gui`` files also appears in the game's interface files."""
    vanilla: set[str] = set()
    for path in vanilla_files("interface/**/*.gui"):
        vanilla |= keys_of(parse_blocks(path.read_text(encoding="utf-8", errors="replace")))
    for path in our_guis():
        unknown = keys_of(parse_blocks(path.read_text(encoding="utf-8"))) - vanilla
        assert not unknown, f"{path.name}: {sorted(unknown)}"


def vanilla_rule_shape() -> tuple[set[str], set[str], set[str]]:
    """Collect what vanilla game rules use.

    Returns:
        Rule-level keys, option-level keys and ``group`` values.
    """
    rule_keys: set[str] = set()
    option_keys: set[str] = set()
    groups: set[str] = set()
    for path in vanilla_files("common/game_rules/*.txt"):
        for _, rule in parse_blocks(path.read_text(encoding="utf-8-sig", errors="replace")):
            if not isinstance(rule, list):
                continue
            rule_keys |= {key for key, _ in rule}
            groups |= {value for key, value in rule if key == "group" and isinstance(value, str)}
            for key, value in rule:
                if key in {"option", "default"} and isinstance(value, list):
                    option_keys |= {name for name, _ in value}
    return rule_keys, option_keys, groups


def test_game_rules_match_vanilla() -> None:
    """Rule-level and option-level keys of the SDK rule are those vanilla rules use."""
    rule_keys, option_keys, groups = vanilla_rule_shape()
    ours = parse_blocks(
        (MOD / "common" / "game_rules" / "capie_sdk_v1_rules.txt").read_text(encoding="utf-8")
    )
    for _, rule in ours:
        assert isinstance(rule, list)
        for key, value in rule:
            assert key in rule_keys, f"rule-level key {key} is not used by vanilla rules"
            if key == "group":
                assert value in groups, value
            if isinstance(value, list):
                assert {name for name, _ in value} <= option_keys, key

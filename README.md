# CAPIE script SDK v1

Plain HOI4 script that lets a mod use CAPIE text fields without native code. It is meant to
ship as its own Steam Workshop item ("CAPIE Script SDK") that mods list as a dependency, and to
move into its own repository, `capie-script-sdk`.

The contract it implements is `plugin/capie/CONTRACT.md`: the editor contract of API level 2
(CAPIE 1.1) and the country name layer of API level 4 (CAPIE 1.2). The modder documentation is
in `sites/capie/docs/modders/`.

## Layout

| Path | What it is |
|---|---|
| `mod/` | The Workshop item. Generated; do not edit by hand. |
| `tools/capie_charset.py` | The character code table (single definition, also checked against the native encoder) |
| `tools/messages.toml` | Player-facing texts, English and Polish |
| `tools/gen_sdk.py` | Writes `mod/`; `--check` compares instead of writing |
| `snippets/` | Text to paste into a mod (the "CAPIE missing" indicator) |
| `examples/capie_demo/` | A small mod with two editors built on the SDK |
| `tests/` | Offline checks of the generated files and the demo |
| `MIGRATION.md` | How Rename Anything moves from its private names to the grammar |

## What is in `mod/`

- `capie_v1_begin`: reads the header CAPIE adds to an Apply, notes CAPIE presence for the
  multiplayer handshake and sets `capie_err`.
- `capie_v1_field_load`, `capie_v1_text_trim`, `capie_v1_text_validate`: one field into a work
  buffer, trimmed and checked.
- `capie_v1_text_store` / `_load` / `_equals_slot` / `_clear`: four text slots per country,
  drawn by the localisation keys `CAPIE_V1_TXT1` to `CAPIE_V1_TXT4`.
- Setters: country name and adjective as the country-name layer of API level 4 (country variables;
  flag and colour stay; `capie_v1_clear_country_name` removes it), and through `meta_effect` state,
  character and party names.
- `capie_v1_actor_ok`, `capie_v1_may_edit_country` and the lobby rule `capie_v1_edit_rights`.
- The CAPIE check window of the multiplayer handshake.
- `CAPIE_STATUS`, `CAPIE_API`, `CAPIE_BUILD` fallbacks and every message, in all ten game
  languages (Polish translated, the others in English).

Everything works without CAPIE: Apply effects then end with `capie_err = 10` and change nothing.

## Regenerate and check

```powershell
uv run python sdk/capie-script-sdk/tools/gen_sdk.py           # write mod/
uv run python sdk/capie-script-sdk/tools/gen_sdk.py --check   # exit 1 when mod/ is stale
uv run pytest sdk/capie-script-sdk/tests
```

## Status

Generated and checked offline, and run in the game once on CAPIE 1.1 with the demo mod: the
demo editors work after a fix, and the two parser errors the game reported in the SDK were
removed. Not yet checked in the game: the SDK on CAPIE 1.2 (its country name setter now writes
the name layer), the extended alphabet, the lobby rule and the multiplayer handshake. The full
list is in `CONTRACT.md` section 13 and in the
[in-game test record](../../docs/contributing/in-game-test-record.md).

# Moving Rename Anything onto the public contract

CAPIE 1.1 keeps Rename Anything on its private names (`rn_ip_*` models, `rn_native(b)_*`
records, `rn_ip_cmd_epoch`, `rn_native_cap`, `RN_PLUGIN_STATUS*`, 84-code alphabet). This file
explains why, and the steps of the move.

## Why not in 1.1

- Rename Anything's editors use behaviour that the public contract does not offer: the
  caption refresh of the politics panel after Apply, gated by revision counters; the check
  that `capie_core.dll` is active before a country Apply; focus release when the politics panel
  hides. Moving them means either adding those features to the grammar or dropping them.
- The 1.0 behaviour is accepted in the game (TWENTIETH run, PID50556 and PID25584) and pinned
  by the offline suites and 79 mutants. A move changes the generated mod, the bridge's model
  table and those tests at once, and needs a new in-game run.
- The legacy path costs nothing at run time: grammar names and legacy names are recognised by
  different observers, and a legacy frame never gets `capie_*` records.

## Steps (next release that is tested in the game)

1. Generator (`tools/modgen`, `tools/inline_editor`): rename the three editors to
   `capie_v1_ed__rn__leader`, `capie_v1_ed__rn__party`, `capie_v1_ed__rn__country`, the fields to
   `capie_v1_f__rn__<editor>__<n>`, the carriers to `capie_v1_pf__…` / `capie_v1_ep__…`.
2. Script: replace the payload checks in `rn_inline_payload.txt` and
   `rn_inline_pair_payload.txt` with `capie_v1_begin` and `capie_v1_field_load`; map
   `rn_pair_err` / `rn_ip_status_*` messages to `capie_err`. Keep Rename Anything's own
   cooldowns and target pins; they are not part of the SDK.
3. Decoder: Rename Anything's `RN_CH_*` tables know 84 codes. Either switch its buffers to the
   SDK slots (264 codes) or extend `tools/modgen/charset.py` with the codes 85..264 from
   `capie_charset.py` (codes 1..84 are identical, so saved buffers stay valid).
4. Native: add the caption gate and the country capability gate as optional grammar features
   (for example a model flag derived from a reserved editor id), or keep them for the `rn` mod
   id only. Then remove the legacy model table from `schema.hpp` and its observers.
5. Status line: switch `RN_COUNTRY_PLUGIN` from `$RN_PLUGIN_STATUS_EN/PL$` to `$CAPIE_STATUS$`.
   Keep CAPIE answering `RN_PLUGIN_STATUS*` for one more release so older mod versions still
   show the right text.
6. Keep reading the `RN1|` cosmetic-tag protocol (CAPIE 1.0/1.1 saves contain it); new names are
   written only as the country-name layer of API level 4 (CONTRACT.md section 14).
7. Re-record the mutants of the legacy editor path against the grammar path; run the in-game
   checklist of the twentieth run on the new names.

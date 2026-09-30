# Weather Advisory Support Bot

A LangGraph agent that answers outdoor-activity questions using live Open-Meteo data. Every answer comes from a written SOP in `sops.json`, or the bot says no SOP applies.

## Setup and run
```bash
python -m venv venv
source venv/Scripts/activate      # Git Bash on Windows; use venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env              # then set GROQ_API_KEY (and optionally GROQ_MODEL)
uvicorn app:app --reload
```
- **Frontend (chat UI):** http://127.0.0.1:8000/ (served by the same app; one chat thread = one session)
- **Backend API docs:** http://127.0.0.1:8000/docs, `POST /advice` with `{"question": "...", "session_id": "..."}`

## Graph
```
understand_question -> resolve_location -> get_weather -> match_sop -> respond_with_sop
        |                    |                  |             |
        +---- any error -----+------------------+--> respond_error        match_sop -> respond_no_sop (no SOP)
```
Conditional edges route every failure (unclear question, unknown location, weather API down) to one honest error node, and route "no SOP matched" to a fixed "we don't have guidance" node.

## SOPs
`sops.json` is a list of `{id, activity, description, conditions, severity, advice}`. **Why JSON:** policy is data, so the maintenance team edits it without touching Python. 14 SOPs, categories: any (universal), cycling, walking, picnic, children, travel, elderly, hiking, outdoor. Severities: high, moderate, low.

Condition forms: a list (all must hold), `{"all": [...]}`, `{"any": [...]}`, `{"at_least": n, "of": [...]}` (fuzzy: enough soft signals hold), operators `> < >= <= == in between`.

Adding an SOP (e.g. an 11th): append an object to `sops.json`. A new activity category is picked up automatically (the extraction prompt reads categories from the file). **Honest limit:** a rule on a weather field we don't fetch yet (e.g. humidity) needs a one-line addition to `weather.py`; the graph and model code stay untouched.

### When several SOPs match (decided on purpose)
The answer uses the **single highest-severity** SOP. On equal severity, universal ("any") rules beat activity-specific ones, so a situational rule like heavy rain leads. Other matches are listed by id and severity as "also applicable", and the reply says the highest severity leads.

## What the model does vs. what code does
- **Model:** (1) extracts activity, location and time of day from the question; (2) words the reply. It never picks the SOP and never sees the raw question when writing the reply (limits prompt injection).
- **Code:** geocoding, weather, SOP matching and ranking, the "no SOP" and error replies, and a grounding check: if the model's reply contains a number that isn't from the API data or SOP text, or cites any SOP other than the chosen one, it is discarded and replaced by a fixed template built from the SOP text and API values (`is_grounded` in `graph.py`).

## Session memory
Per `session_id`, the bot remembers the last activity, city and time of day. A follow-up like "what about this evening instead?" fills the missing fields from memory in code. In-process only; resets on restart.

## Weather notes
Uses Open-Meteo. `precipitation_probability` and `uv_index` are hourly-only there, so they are read from the matching hourly slot; "evening" etc. map to fixed local hours (morning 8, afternoon 14, evening 18, night 21) for today only.

## Evals
```bash
python -m unittest discover -s evals -p "test_cases.py" -v
```
Offline tests always run; live tests run only if `GROQ_API_KEY` is set.

| Case | Checks | Pass looks like | Result |
|---|---|---|---|
| test_clear_sop_cycling_wind | SOP clearly applies | SOP-03 cited, real wind value shown | _fill in_ |
| test_picnic_fuzzy_rule_matches | fuzzy, non-numeric rule | SOP-07 selected | _fill in_ |
| test_paraphrase_cycling (live) | paraphrase, no SOP keywords | activity = cycling, cited SOP equals deterministic pick | _fill in_ |
| test_paraphrase_children (live) | paraphrase | activity = children, consistent SOP | _fill in_ |
| test_bhopal_grounded_in_live_numbers (live) | grounding in live data | every number in the reply comes from the API response; cited SOP equals recomputed pick | _fill in_ |
| test_heavy_rain_leads_over_activity_rule | severe conditions, conflict rule | SOP-01 leads, cycling SOPs listed as also applicable | _fill in_ |
| test_no_sop_says_so | no SOP | "don't have" answer, no SOP citation | _fill in_ |
| test_weather_api_unreachable | API down | plain failure message, no SOP, no numbers | _fill in_ |
| test_unresolved_location | geocoding fails | plain "couldn't find" message | _fill in_ |
| test_prompt_injection (live) | adversarial text | no "SOP-99" in reply; SOP equals deterministic pick | _fill in_ |
| test_model_hallucination_is_rejected | model invents number and SOP | both removed, real SOP cited | _fill in_ |
| test_session_followup_reuses_context | session memory | city and activity reused, hour 18 requested, no cross-session leak | _fill in_ |
| test_new_sop_needs_no_code_change | 11th-SOP requirement | new SOP returned with no code edit | _fill in_ |

### Honest notes
- **Severe-weather case depends on the day.** The live Bhopal test passes on any day because it checks consistency (cited SOP equals the deterministic pick, numbers come from the API), not that it is raining. On a calm day it exercises the "no SOP" path instead. Guaranteed severe coverage comes from the mocked `test_heavy_rain_leads_over_activity_rule`. To keep the suite useful after the real system passes, keep this consistency-oracle approach plus mocked severe fixtures.
- **No IMD system detection.** The API has no "low-pressure system" field, so SOP-01 uses heavy-rain/thunderstorm weather codes or high hourly rainfall as a proxy. It can miss a system whose local numbers look mild.
- **Prompt-injection coverage** is one live case plus the offline grounding-guard test. The guard checks numbers and SOP ids, not tone or meaning; a model could still reword advice slightly.
- Unknown operators or missing fields in an SOP silently evaluate to "no match" rather than raising.
- Session memory is in-process and single-server.
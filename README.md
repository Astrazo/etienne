# Etienne
A LLM backed Home Assistant to replace Google Home.

## Debugging API

With the server running, open `/docs` for interactive requests or `/openapi.json`
for the API schema. Device routes call the registered device methods directly,
without involving the GUI or assistant. The assistant endpoint runs the same
service as the chat page.

Use `/api/devices` to find configured device keys. Individual light keys look
like `office.devices.desk`; light groups use their configured ID, such as
`office`. Speaker IDs also come from configuration.

| Method | Route | Input |
| --- | --- | --- |
| GET | `/api/devices` | Current device cards, names, IDs, and observed states |
| GET | `/api/state` | Full observations; optional repeated `device_types` query parameters: `lights`, `speakers`, `tvs` |
| POST | `/lights/{device_key}/on` | Optional query parameters: `colour`, `effect`, `flash` (`short` or `long`); accepts individual lights or groups |
| POST | `/lights/{device_key}/off` | Accepts individual lights or groups |
| GET | `/lights/{device_key}/state` | Full light observation, or observations for each group member |
| POST | `/speakers/{device_id}/play/tracks` | JSON array: `[{"song": "Song name", "artist": "Optional artist"}]` |
| POST | `/speakers/{device_id}/play/album` | Query: `album`, optional `artist` |
| POST | `/speakers/{device_id}/play/artist` | Query: `artist` |
| POST | `/speakers/{device_id}/play/playlist` | Query: `playlist` |
| POST | `/speakers/{device_id}/pause` | No input |
| POST | `/speakers/{device_id}/resume` | No input |
| POST | `/speakers/{device_id}/repeat` | Query: `state` (`track`, `context`, `off`) |
| POST | `/speakers/{device_id}/shuffle` | Query: `state` (`true` or `false`) |
| POST | `/speakers/{device_id}/queue/add` | Same JSON array as track playback |
| POST | `/speakers/{device_id}/queue/navigate` | Query: `direction` (`next` or `previous`) |
| GET | `/speakers/{device_id}/state` | Fresh Spotify playback observation |
| POST | `/speakers/{device_id}/timer` | JSON: `action` (`pause` or `resume`), and exactly one of `timer_minutes` or `trigger_time` |
| GET | `/speakers/{device_id}/timers` | Optional query filters: `action`, `trigger_time` |
| DELETE | `/speakers/{device_id}/timers` | Optional query filters: `action`, `trigger_time`; `cancel_all=true` cancels all matches |
| POST | `/assistant/utterance` | Query: `utterance` |

Timer timestamps must include a timezone; new timers must be in the future.
Cancellation preserves the device method's behaviour: multiple matches require
more specific filters unless `cancel_all=true`. Speaker responses include the
method's message so missing search results and ambiguous timers remain visible.
Light commands report `submitted`; use the state endpoint to check the observed
result. Unknown speaker and light IDs return 404, invalid inputs return 422, and
upstream service failures return 502. Assistant timeouts return 504; an action
may have completed before the timeout.

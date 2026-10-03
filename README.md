# Etienne

## Timer storage

SQLite support comes with Python; no extra dependency or database server is needed.
FastAPI's lifespan handler calls `init_db()` from `src/etienne/db.py` before
initialising devices. It creates `data/etienne.db` relative to the working directory
and runs `CREATE TABLE IF NOT EXISTS timers`, preserving existing rows on restart.
Set `ETIENNE_DB_PATH` in `.env` to use another location. Use an absolute path when
running as a service so changing the working directory cannot select another database.

The `timers` table holds pending speaker pause timers:

| Column | Meaning |
| --- | --- |
| `device_id` | Unique device identifier; one timer per device |
| `pause_at` | UTC Unix timestamp in seconds, such as `datetime.now(UTC).timestamp() + 1800` |

Completed or cancelled timers should be deleted. Timer execution and API endpoints
are not implemented yet; creating the table alone does not restore or run timers.
The resolved database path is available as `request.app.state.db_path`.

Keep database setup in `db.py`. As timer functionality is added, put parameterised
SQL for saving/loading/deleting timers in `repositories/timers.py`, async countdown
and cancellation logic in `services/timers.py`, and HTTP handlers in `api/routes/`.
The lifespan handler wires these pieces together. There is no need for an ORM at
this size. Future schema changes need migrations: `CREATE TABLE IF NOT EXISTS`
does not modify an existing table.

# Etienne

## Scheduling

Startup creates missing tables in `data/etienne.db`. The `speaker_timers` table
stores `id` (automatically assigned), `device_id` (Spotify ID), `action` (`pause`
or `resume`), and `execute_at` (UTC Unix timestamp). Each new sleep timer adds a
row; it does not replace existing timers.

`scheduler.py` checks immediately on startup, then sleeps for 60 seconds between
checks. It executes due actions sequentially in deadline order, including timers
that expired while the server was offline. Successful timers are deleted; failed
actions and unknown devices are logged and retained for retry on the next check.
One failed timer does not stop the others.

`api/app.py` starts the async scheduler after device initialization and cancels
and awaits it on shutdown. SQLite and synchronous Spotify calls use worker
threads. Cancellation cannot stop a synchronous call already running in a thread.
A crash after an action succeeds but before its row is deleted can cause the
action to repeat on restart.

Run one app worker/process so only one scheduler owns the database. Actions can
be late by roughly a minute plus the time spent on earlier actions. Future table
handlers, such as TV scheduling, can be added to the same `run_scheduler` loop,
each with its own error boundary.

`CREATE TABLE IF NOT EXISTS` does not migrate existing tables. Old `timers` and
`speaker_sleep_timers` rows are not read or migrated by this scheduler.

# Course Duplication Logs

_Captured during demo setup simulation_

```
2025-11-19 22:40:33,597 - demo_setup - INFO - Simulating Course Duplication for BIOL-201...
2025-11-19 22:40:33,598 - database_sqlite - INFO - [SQLiteDatabase] Created course 0251dab3-9093-4179-870b-d8514bc76219
2025-11-19 22:40:33,599 - demo_setup - INFO - Successfully duplicated course. New ID: 0251dab3-9093-4179-870b-d8514bc76219
```

_Subsequent run verifies idempotence/existence:_

```
2025-11-19 22:42:23,506 - demo_setup - INFO - Simulating Course Duplication for BIOL-201...
2025-11-19 22:42:23,507 - demo_setup - INFO - Duplicate course BIOL-201-V2 already exists.
```

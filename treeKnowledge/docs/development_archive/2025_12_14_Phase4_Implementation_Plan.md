# Phase 4: Research Data Collection (Backend Focus)

## Goal
Enhance the system to capture distinct behavioral metrics for every practice session, ensuring future research analysis can be performed by simply querying the database. The immediate priority is **data granularity**, specifically **response time**.

## User Review Required
> [!IMPORTANT]
> **Database Schema Change**: This update adds a `duration_seconds` column to the `learning_logs` table.

## Proposed Changes

### Database Layer (`db_utils.py`)
#### [MODIFY] `db_utils.py`
-   **Schema Migration**: Implement a safe check to add `duration_seconds` (REAL) to `learning_logs` table if it doesn't exist.
-   **`log_activity`**: Update generic logging function to accept `duration`.

### Logic Layer (`practice_engine.py`)
#### [MODIFY] `practice_engine.py`
-   **`grade_and_update`**: Accept `duration` parameter and pass it to the logger.

### UI Layer (`pages/2_🎓_Luyen_Tap.py`)
#### [MODIFY] `pages/2_🎓_Luyen_Tap.py`
-   **Timer Logic**: 
    -   Capture `start_time` when question renders.
    -   Capture `end_time` on submission.
    -   Calculate `duration` and submit to engine.

## Verification Plan
### Automated Verification
-   Run a script `verify_logging.py` that simulates a log entry with duration and queries it back to ensure persistence.

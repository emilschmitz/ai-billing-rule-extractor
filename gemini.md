# Gemini Notes

## Database Schema Changes
Since this project is a Proof of Concept (PoC), we do not need to bother with complex database migrations (like alembic or writing ALTER TABLE statements) when the database schema needs to change.

Instead, if you modify the schema in `init.sql`:
1. Use the `reset_db.py` script to instantly drop and recreate the tables.
2. It's completely fine to delete/truncate all existing data.

Run the drop/recreate script with:
```bash
uv run --env-file .env python reset_db.py
```

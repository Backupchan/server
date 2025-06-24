# Backup-chan server

This is the server portion of Backup-chan, an automatic backup system.

## Setting up

1. Install sqlite3
1. Create the database: `touch backupchan.db && sqlite3 backupchan.db < db.sql` (you can choose a different filename for your database)
1. Install requirements for Python: `pip install -r requirements.txt`
1. Copy `config.jsonc.example` to `config.jsonc`. Modify as necessary.
1. Run `main.py` to start the server.

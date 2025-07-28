#!/usr/bin/python3

import database
import serverconfig
import logging
import argparse
import os

def main():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("migration", nargs="?", help="Migration to run. To run all migrations, don't enter anything.", type=str, default="")
    args = parser.parse_args()

    migration = args.migration.strip()

    print("The Backup-chan database will now be migrated.")
    server_config = serverconfig.get_server_config()
    db = database.Database(server_config.get("db"))
    if migration == "":
        db.initialize_database()
    else:
        with open(os.path.join("migrations", migration), "r", encoding="utf-8") as f:
            sql = f.read()
            db.run_migration(migration, sql)
    print("The Backup-chan database has been migrated. Backup-chan is ready to run.")

if __name__ == "__main__":
    main()

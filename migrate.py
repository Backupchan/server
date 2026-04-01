#!/usr/bin/python3

import database
import serverconfig
import logging
import argparse
import os
import glob
import mariadb
from backupchan_server import utility

def get_schema_version(db: database.Database):
    try:
        return db.get_schema_version()
    except mariadb.ProgrammingError:
        return None

def main():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("migration", nargs="?", help="Migration to run. To run all required migrations, don't enter anything.", type=str, default="")
    args = parser.parse_args()

    migration = args.migration.strip()

    print("The Backup-chan database will now be migrated.")
    server_config = serverconfig.get_server_config()
    db = database.Database(server_config.get("db"))
    if migration == "":
        schema_version = get_schema_version(db)
        if schema_version:
            migrations = glob.glob("migrations/???_*.sql")
            for migration in migrations:
                basename = os.path.basename(migration)
                if int(basename.split("_")[0]) > schema_version:
                    with open(migration, "r", encoding="utf-8") as f:
                        sql = f.read()
                        db.run_migration(basename, sql)
        else:
            db.initialize_database()
    else:
        with open(utility.join_path("migrations", migration), "r", encoding="utf-8") as f:
            sql = f.read()
            db.run_migration(migration, sql)
    print("The Backup-chan database has been migrated. Backup-chan is ready to run.")

if __name__ == "__main__":
    main()

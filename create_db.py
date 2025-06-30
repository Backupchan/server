#!/usr/bin/python3

import database
import serverconfig
import logging

def main():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s")
    print("The Backup-chan database will now be created.")
    server_config = serverconfig.get_server_config()
    database.Database(server_config.get("db_path"), server_config.get("db")).initialize_database()
    print("The Backup-chan database has been created. Backup-chan is ready to run.")

if __name__ == "__main__":
    main()

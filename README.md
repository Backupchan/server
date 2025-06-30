# Backup-chan server

This is the server portion of Backup-chan, an automatic backup system.

## Setting up

1. Install MariaDB.
1. Create the Backup-chan database by running the following in the MariaDB shell (replace values depending on your setup):
    ```sql
    CREATE DATABASE dbname CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER 'yourusername'@'localhost' IDENTIFIED BY 'yourpassword';
    GRANT ALL PRIVILEGES ON dbname.* TO 'yourusername'@'localhost';
    FLUSH PRIVILEGES;
    ```
    * Now you can exit the shell by entering `\q`
1. Install program dependencies: `pip install -r requirements.txt`
1. Copy `config.jsonc.example` to `config.jsonc`. Modify as necessary. Make sure to change the options under `db` especially.
1. Run `create_db.py` to create the database.
1. Run `main.py` to start the server.

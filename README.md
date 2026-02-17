# Backup-chan server

This is the server portion of Backup-chan, an automatic backup system.

## Setting up

1. Install MariaDB.
1. Create the Backup-chan database by running the following in the MariaDB shell (replace values depending on your setup):
    ```sql
    CREATE DATABASE dbname CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER 'yourusername'@'localhost' IDENTIFIED BY 'yourpassword'; -- Skip this if you already have a user.
    GRANT ALL PRIVILEGES ON dbname.* TO 'yourusername'@'localhost';
    FLUSH PRIVILEGES;
    ```
    * Now you can exit the shell by entering `\q`
1. Install program dependencies: `pip install -r requirements.txt`
1. Copy `config.jsonc.example` to `config.jsonc`. Modify as necessary. Unless stated otherwise, most options have default values.
1. Run `migrate.py` to create required database tables.

## Running the server

### Development

If you're running for development purposes, simply running `main.py` should be enough.

### Production

If you plan to use this installation in a production environment (with your real backups), you should use a WSGI server. See
[here](https://flask.palletsprojects.com/en/stable/deploying/) on how to set one up. **Remember to start only one worker,
otherwise every job will start multiple times.**

Backup-chan provides `waitress_serve.py` for launching a production server using `waitress`. Configure it using `waitress_config.jsonc` (see `waitress_config.jsonc.example` for an example configuration).

Once it's run, you can access the web UI through the browser or use a dedicated client.

## Running migrations

When updating Backup-chan, the database schema might change. New migrations are added into the `migrations` folder. Run new
migrations like so:

```bash
./migrate.py 002_datetime_created_at.sql
./migrate.py 003_backup_recycled.sql
...
```

## Setting up authentication

1. Enable it in your config
1. Run `passwd.py` and enter the password you'd like to use
1. The password is now saved and can be used to log in.

See `API.md` for details on creating and managing an API key.

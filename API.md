# Backup-chan server API

This is the documentaton for the JSON API for use in client applications and scripts.

If you are using Python for your client application, you should use the API library instead.

## Authentication

Authentication for the API can be done using an API key. Each instance of Backup-chan can
have only one key. To enable authentication, simply create an API key. To disable it, delete
the `apikey.json` file.

**Do not share your API key.** If you accidentally do, then you have to make a new one.

### Creating an API key

To generate a new API key, run `newapikey.py`. Your new key will be stored in `apikey.json`.

If `apikey.json` already exists, it will not be overwritten by default, instead you need to
pass `--overwrite` (or `-o`) to allow overwriting it.

### Authenticating API requests

Pass your API key in the `Bearer` header of your request. If you use the Python client library,
you have to pass the API key through the `API` initializer.

## Target endpoints

### GET `/api/target`

List every target.

Example output:

```json
[
    {
        "id": "00000000-0000-0000-0000-000000000000",
        "name": "My backup",
        "target_type": "multi",
        "recycle_criteria": "count",
        "recycle_value": 10,
        "recycle_action": "recycle",
        "location": "/var/backups/MyBackup",
        "name_template": "backup-$I-$D"
    }
]
```

### POST `/api/target/upload`

Create a new target.

Example payload:

```json
{
    "name": "Name of new target",
    "backup_type": "multi", // multi or single
    "recycle_criteria": "count", // count / age / none
    "recycle_value": 10,
    "recycle_action": "recycle", // recycle or delete
    "location": "/path/to/backups",
    "name_template": "name-template-$I-$D"
}
```

### GET `/api/target/<ID>`

View a target with the specified ID.

Example output:

```json
{
    "id": "00000000-0000-0000-0000-000000000000",
    "name": "My backup",
    "target_type": "multi",
    "recycle_criteria": "count",
    "recycle_value": 10,
    "recycle_action": "recycle",
    "location": "/var/backups/MyBackup",
    "name_template": "backup-$I-$D"
}
```

### PATCH `/api/target/<ID>`

Edit an existing target. A target's type cannot be modified after creaton.

Example payload:

```json
{
    "name": "New name of target",
    "recycle_criteria": "count", // count / age / none
    "recycle_value": 10,
    "recycle_action": "recycle", // recycle or delete
    "location": "/path/to/backups",
    "name_template": "name-template-$I-$D"
}
```

### DELETE `/api/target/<id>`

Delete an existing target. `delete_files` must be supplied in the payload
to indicate whether or not to permanently delete backup files as well.

## Backup endpoints

### DELETE `/api/backup/<id>`

Delete an existing backup. `delete_files` must be supplied in the payload
to indicate whether or not to permanently delete backup files as well.

### PATCH `/api/backup/<id>`

Recycle or restore an existing backup.

Example payload:

```json
{
    "is_recycled": true
}
```

## Miscellaneous endpoints

### GET `/api/recycle_bin`

List contents of the recycle bin.

### DELETE `/api/recycle_bin`

Delete every backup in the recycle bin. `delete_files` must be supplied in
the payload to indicate whether or not to permanently delete backup files
as well.

### POST `/target/<ID>/upload`

Upload a new backup. Requires a `backup_file` to be present as a file
through `multipart/form-data` and `manual` boolean in JSON payload.

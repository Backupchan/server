# Backup-chan server API

This is the documentaton for the JSON API for use in client applications and scripts.

If you are using Python for your client application, you should use the API library instead.

## Testing

The API is tested using `pytest`. Once installed, run `pytest apitest.py` to test the API.

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

Accepts a `page` argument for pagination: `/api/target?page=2`

#### Example output

```json
{
    "success": true,
    "targets": [
        {
            "id": "00000000-0000-0000-0000-000000000000",
            "name": "My backup",
            "target_type": "multi",
            "recycle_criteria": "count",
            "recycle_value": 10,
            "recycle_action": "recycle",
            "location": "/var/backups/MyBackup",
            "name_template": "backup-$I-$D",
            "deduplicate": true,
            "alias": "mybackup",
            "min_backups": 2,
            "tags": ["cool", "beans"]
        }
    ]
}
```

### POST `/api/target`

Create a new target.

#### Example payload

```jsonc
{
    "name": "Name of new target",
    "backup_type": "multi", // multi or single
    "recycle_criteria": "count", // count / age / none
    "recycle_value": 10,
    "recycle_action": "recycle", // recycle or delete
    "location": "/path/to/backups",
    "name_template": "name-template-$I-$D",
    "deduplicate": true,
    "alias": "target-alias", // or null if you don't want one,
    "min_backups": 3,
    "tags": ["cool", "beans"] // optional
}
```

#### Example output

```json
{
    "success": true,
    "id": "00000000-0000-0000-0000-000000000000"
}
```

### GET `/api/target/<ID>`

View a target with the specified ID.

#### Example output

```json
{
    "success": true,
    "target": {
        "id": "00000000-0000-0000-0000-000000000000",
        "name": "My backup",
        "target_type": "multi",
        "recycle_criteria": "count",
        "recycle_value": 10,
        "recycle_action": "recycle",
        "location": "/var/backups/MyBackup",
        "name_template": "backup-$I-$D",
        "deduplicate": true,
        "alias": "mybackup",
        "min_backups": 4,
        "tags": ["cool", "beans"]
    },
    "backups": [
        {
            "id": "00000000-0000-0000-0000-000000000000",
            "target_id": "00000000-0000-0000-0000-001000000000",
            "created_at": "2025-07-11T12:57:17+00:00",
            "manual": false,
            "is_recycled": false,
            "filesize": 123456
        }
    ]
}
```

* Filesize is stored in bytes.

### POST `/target/<ID>/upload`

Upload a new backup.

This endpoint uses the Content-Type `multipart/form-data` for the payload.

#### Example payload

```
backup_file: File you want to upload.
manual: true/false, whether the upload was manual or not.
```

#### Example output

```json
{
    "success": true,
    "job_id": 2
}
```

### PATCH `/api/target/<ID>`

Edit an existing target. A target's type cannot be modified after creaton.

#### Example payload

```jsonc
{
    "name": "New name of target",
    "recycle_criteria": "count", // count / age / none
    "recycle_value": 10,
    "recycle_action": "recycle", // recycle or delete
    "location": "/path/to/backups",
    "name_template": "name-template-$I-$D",
    "deduplicate": false,
    "alias": "new-alias", // or null to clear it,
    "num_backups": 2,
    "tags": ["uncool", "beans"]
}
```

#### Example output

```json
{
    "success": true
}
```

### DELETE `/api/target/<id>`

Delete an existing target. `delete_files` must be supplied in the payload
to indicate whether or not to permanently delete backup files as well.

#### Example payload

```json
{
    "delete_files": true
}
```

#### Example output

```json
{
    "success": true
}
```

### DELETE `/api/target/<id>/all`

Delete every backup from an existing target. `delete_files` must be supplied
to indicate whether or not to permanently delete backup files as well.

#### Example payload

```json
{
    "delete_files": true
}
```

#### Example output

```json
{
    "success": true
}
```

### DELETE `/api/target/<id>/recycled`

Delete every recycled backup from an existing target. `delete_files` must be supplied
to indicate whether or not to permanently delete backup files as well.

#### Example payload

```json
{
    "delete_files": true
}
```

#### Example output

```json
{
    "success": true
}
```

## Backup endpoints

### DELETE `/api/backup/<id>`

Delete an existing backup. `delete_files` must be supplied in the payload
to indicate whether or not to permanently delete backup files as well.

#### Example payload

```json
{
    "delete_files": true
}
```

#### Example output

```json
{
    "success": true
}
```

### PATCH `/api/backup/<id>`

Recycle or restore an existing backup.

#### Example payload

```json
{
    "is_recycled": true
}
```

#### Example output

```json
{
    "success": true
}
```

## Miscellaneous endpoints

### GET `/api/recycle_bin`

List contents of the recycle bin.

#### Example output

```json
{
    "success": true,
    "backups": [
        {
            "id": "00000000-0000-0000-0000-000000000000",
            "target_id": "00000000-0000-0000-0000-001000000000",
            "created_at": "2025-07-11T12:57:17+00:00",
            "manual": false,
            "is_recycled": true,
            "filesize": 123456
        }
    ]
}
```

### DELETE `/api/recycle_bin`

Delete every backup in the recycle bin. `delete_files` must be supplied in
the payload to indicate whether or not to permanently delete backup files
as well.

#### Example payload

```json
{
    "delete_files": true
}
```

#### Example output

```json
{
    "success": true
}
```

### GET `/api/jobs`

List all scheduled and delayed jobs.

#### Example output

```jsonc
{
    "success": true,
    "delayed": [
        {
            "id": 1,
            "name": "upload_job",
            "status": "FINISHED", // see delayed_jobs/manager.py for a list of statuses
            "start_time": "Mon, 11 Aug 2025 17:33:29 GMT",
            "end_time": "Mon, 11 Aug 2025 17:33:31 GMT"
        }
    ],
    "scheduled": [
        {
            "name": "recycle_job",
            "interval": 1800,
            "next_run": 1754915748.9602332 // unix timestamp
        }
    ]
}
```

### GET `/api/jobs/force_run/<job name>`

Force a specific job to run.

#### Example output

```json
{
    "success": true
}
```

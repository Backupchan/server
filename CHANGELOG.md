# Backup-chan server changelog

See what's changed between versions!

## 2.6.0

* Fixed 400 status code when editing or creating target.
* Changed target list to show total filesize and number of backups. Removed recycle criteria and name template columns.

## 2.5.1

* Added API support for minimum backups field.

## 2.5.0

* Added a minimum backups field for targets with age-based recycle criteria.

## 2.4.2

* Fixed recycle job not working.

## 2.4.1

* Fixed force run job web UI crashing.

## 2.4

* Added API endpoint to force run job.
* Added bulk edit mode for backups.

## 2.3.1

* Updated schema version back to 10 as I added the corrseponding migration file.

## 2.3

* Added a better page for force running scheduled jobs.
* Added an option to force run a job from the job list.
* Added a scheduled job to remove temp files older than a day.
* Revert schema version number back to 9 as I forgot to commit the migration code and currently don't have it on me.

## 2.2.1

* Automatically focus on password field on login page.

## 2.2

* Added ability to delete only recycled backups of specific target.
* Fixed checkbox labels in Web UI deletion confirmation pages not working.
* Disable recycle options in Web UI target edit page if recycle criteria set to none.

## 2.1.6

* Fixed crashing when doing a sequential upload.

## 2.1.5

* Fixed age-based recycling not working.

## 2.1.4

* Refactored sequential upload checks.
* Refactored log reading and initialization.
* Handle log read errors.
* Handle database connection error cleanly.

## 2.1.3

* Fixed recycle bin page in Web UI not showing properly.

## 2.1.2

* Fixed recycled backups not showing in a table in Web UI.

## 2.1.1

* Added proper pluralization in target list and target details page.
* Delayed jobs have a proper string representation in job list.
* No longer required to specify recycle value for targets if no criteria set.

## 2.1.0

* Added sequential uploads (upload files one-by-one, for large multi-file backups)

## 2.0.1

* Fixed API uploads not returning a response when error.

## 2.0.0

* **Breaking change**: API endpoint for uploads now returns a job ID instead of backup ID.
* Added delayed job system for one-time tasks to run in the background

## 1.2.1

* Fixed API backup downloads not working.

## 1.2.0

* Added ability to download backups.

## 1.1.5

* Refactored to use external libraries for models and configuration.

## 1.1.4

* Fixed listing backups not working with aliases.

## 1.1.3

* Fixed backups bigger than 2,147,483,647 bytes not working.

## 1.1.2

* Fixed file manager-related errors.

## 1.1.1

* Fixed `total_target_size` statistic being a string value.

## 1.1.0

* Added `$M` syntax to name templates for whether the backup was manual or automatic.
* Added `/api/stats` endpoint.

## 1.0.0

The first stable version.

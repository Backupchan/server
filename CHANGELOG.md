# Backup-chan server changelog

See what's changed between versions!

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

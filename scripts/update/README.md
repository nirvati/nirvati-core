<!--
SPDX-FileCopyrightText: 2020 Umbrel. https://getumbrel.com
SPDX-FileCopyrightText: 2023 Nirvati and contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Over-The-Air (OTA) Updates
How over-the-air updates work on Nirvati.

## Execution Flow

1. New developments across the any/entire fleet of Nirvati's services (dashboard, api, etc) are made, which maintain their own independent version-control and release-schedule. Subsequently, their new docker images are built, tagged and pushed to Docker Hub.

2. The newly built and tagged images are updated in the main repository's (i.e. this repo) [`docker-compose.yml`](https://github.com/nirvati/nirvati-core/blob/main/docker-compose.yml) file.

3. Any new developments to the main repository (i.e. this repo) are made, eg. adding a new directory or a new config file.

4. To prepare a new release of Nirvati, called `vX.Y.Z`, a PR is opened that updates the version in [`README.md`](https://github.com/nirvati/nirvati-core/blob/main/README.md) and [`info.json`](https://github.com/nirvati/nirvati-core/blob/main/info.json) file to:

```json
{
    "version": "X.Y.Z",
    "name": "Nirvati vX.Y.Z",
    "notes": "This release contains a number of bug fixes and new features.",
    "requires": ">=A.B.C"
}
```

5. Once the PR is merged, the main branch is immediately tagged `vX.Y.Z` and released on GitHub.

6. Thus the new `info.json` will automatically be available at `https://raw.githubusercontent.com/nirvati/nirvati-core/main/info.json`. This is what triggers the OTA update.

6. When the user opens his [`dashboard`](https://github.com/nirvati/nirvati-dashboard), it periodically polls [`api`](https://github.com/nirvati/nirvati-api) to check for new updates.

7. `api` fetches the latest `info.json` from Nirvati's main repo's main branch using `GET https://raw.githubusercontent.com/nirvati/nirvati-core/main/info.json`, compares it's `version` with the `version` of the local `$NIRVATI_ROOT/info.json` file, and exits if both the versions are same.

8. If fetched `version` > local `version`, `api` checks if local `version` satisfies the `requires` condition in the fetched `info.json`.

9. If not, `api` computes the minimum satisfactory version, called `L.M.N`, required for update. Eg, for `"requires": ">=1.2.2"` the minimum satisfactory version would be `1.2.2`. `api` then makes a `GET` request to `https://raw.githubusercontent.com/nirvati/nirvati-core/vL.M.N/info.json` and repeats step 8 and 9 until local `version` < fetched `version` **AND** local `version` fulfills the fetched `requires` condition.

10. `api` then returns the satisfying `info.json` to `dashboard`.

11. `dashboard` then alerts the user regarding the available update, and after the user consents, it makes a `POST` request to `api` to start the update process.

12. `api` adds the `updateTo` key to `$NIRVATI_ROOT/statuses/update-status.json` (a file used to continuosly update the user with the update status and progress) with the update release tag.

```json
{
    ...
    "updateTo": "vX.Y.Z"
    ...
}
```

13. `api` then creates an update signal file on the mounted host OS volume (`$NIRVATI_ROOT/events/signals/update`) and returns `OK` to the `dashboard`.

14. [`karen`](https://github.com/nirvati/nirvati-core/blob/main/karen) is triggered (obviously) as soon as `$NIRVATI_ROOT/events/signals/update` is touched/updated, and immediately runs the `update` trigger script [`$NIRVATI_ROOT/events/triggers/update`](https://github.com/nirvati/nirvati-core/blob/main/events/triggers/update) as root.

15. `$NIRVATI_ROOT/events/triggers/update` clones release `vX.Y.Z` from github in `$NIRVATI_ROOT/.nirvati-vX.Y.Z`.

16. `$NIRVATI_ROOT/events/triggers/update` then executes all of the following update scripts from the new release `$NIRVATI_ROOT/.nirvati-vX.Y.Z` one-by-one:

- [`$NIRVATI_ROOT/.nirvati-vX.Y.Z/scripts/update/00-run.sh`](https://github.com/nirvati/nirvati-core/blob/main/scripts/update/00-run.sh): Pre-update preparation script (does things like making a backup)
- [`$NIRVATI_ROOT/.nirvati-vX.Y.Z/scripts/update/01-run.sh`](https://github.com/nirvati/nirvati-core/blob/main/scripts/update/01-run.sh): Install update script (installs the update)
- [`$NIRVATI_ROOT/.nirvati-vX.Y.Z/scripts/update/02-run.sh`](https://github.com/nirvati/nirvati-core/blob/main/scripts/update/02-run.sh): Post-update script (used to run unit-tests to make sure the update was successfully installed)
- [`$NIRVATI_ROOT/.nirvati-vX.Y.Z/scripts/update/03-run.sh`](https://github.com/nirvati/nirvati-core/blob/main/scripts/update/03-run.sh): Success script (runs after the updated has been successfully downloaded and installed)

All of the above scripts continuously update `$NIRVATI_ROOT/statuses/update-status.json` with the progress of update, which the dashboard periodically fetches every 2s via `api` to keep the user updated.

### Further improvements

- OTA updates should not trust GitHub, they should verify signed checksums before installing
- Catch any error during the update and restore from the backup
- Restore from backup on power-failure

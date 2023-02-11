#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2020 Umbrel. https://getumbrel.com
# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
# SPDX-FileCopyrightText: 2023 Nirvati and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail

RELEASE=$1
NIRVATI_ROOT=$2

# Only used on Nirvati OS
SD_CARD_NIRVATI_ROOT="/sd-root${NIRVATI_ROOT}"

echo
echo "======================================="
echo "=============== UPDATE ================"
echo "======================================="
echo "=========== Stage: Install ============"
echo "======================================="
echo

[[ -f "/etc/default/nirvati" ]] && source "/etc/default/nirvati"

# Make Citadel OS specific updates
if [[ ! -z "${NIRVATI_OS:-}" ]]; then
    echo
    echo "============================================="
    echo "Installing on Nirati OS $NIRVATI_OS"
    echo "============================================="
    echo
    
    # Update SD card installation
    if  [[ -f "${SD_CARD_NIRVATI_ROOT}/.nirvati" ]]; then
        echo "Replacing ${SD_CARD_NIRVATI_ROOT} on SD card with the new release"
        rsync --archive \
            --verbose \
            --include-from="${NIRVATI_ROOT}/.nirvati-${RELEASE}/scripts/update/.updateinclude" \
            --exclude-from="${NIRVATI_ROOT}/.nirvati-${RELEASE}/scripts/update/.updateignore" \
            --delete \
            "${NIRVATI_ROOT}/.nirvati-${RELEASE}/" \
            "${SD_CARD_NIRVATI_ROOT}/"

        echo "Fixing permissions"
        chown -R 1000:1000 "${SD_CARD_NIRVATI_ROOT}/"
    else
        echo "ERROR: No Citadel installation found at SD root ${SD_CARD_NIRVATI_ROOT}"
        echo "Skipping updating on SD Card..."
    fi

    # This makes sure systemd services are always updated (and new ones are enabled).
    NIRVATI_SYSTEMD_SERVICES="${NIRVATI_ROOT}/.nirvati-${RELEASE}/scripts/citadel-os/services/*.service"
    for service_path in $NIRVATI_SYSTEMD_SERVICES; do
      service_name=$(basename "${service_path}")
      install -m 644 "${service_path}" "/etc/systemd/system/${service_name}"
      systemctl enable "${service_name}"
    done
fi

cd "$NIRVATI_ROOT"

# Stopping karen
echo "Stopping background daemon"
cat <<EOF > "$NIRVATI_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 55, "description": "Stopping background daemon", "updateTo": "$RELEASE"}
EOF
pkill -f "\./karen" || true

echo "Stopping installed apps"
cat <<EOF > "$NIRVATI_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 60, "description": "Stopping installed apps", "updateTo": "$RELEASE"}
EOF
./scripts/app stop installed || true

# Stop old containers
echo "Stopping old containers"
cat <<EOF > "$NIRVATI_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 67, "description": "Stopping old containers", "updateTo": "$RELEASE"}
EOF
./scripts/stop || true

# Overlay home dir structure with new dir tree
echo "Overlaying $NIRVATI_ROOT/ with new directory tree"
rsync --archive \
    --verbose \
    --include-from="$NIRVATI_ROOT/.nirvati-$RELEASE/scripts/update/.updateinclude" \
    --exclude-from="$NIRVATI_ROOT/.nirvati-$RELEASE/scripts/update/.updateignore" \
    --delete \
    "$NIRVATI_ROOT"/.nirvati-"$RELEASE"/ \
    "$NIRVATI_ROOT"/

# Fix permissions
echo "Fixing permissions"
find "$NIRVATI_ROOT" -path "$NIRVATI_ROOT/app-data" -prune -o -exec chown 1000:1000 {} + || true
chmod -R 700 "$NIRVATI_ROOT"/tor/data/* || true

# Start updated containers
echo "Starting new containers"
cat <<EOF > "$NIRVATI_ROOT"/statuses/update-status.json
{"state": "installing", "progress": 80, "description": "Starting new containers", "updateTo": "$RELEASE"}
EOF
cd "$NIRVATI_ROOT"
./scripts/start || true


cat <<EOF > "$NIRVATI_ROOT"/statuses/update-status.json
{"state": "success", "progress": 100, "description": "Successfully installed Nirvati $RELEASE", "updateTo": ""}
EOF

# Make Nirvati OS specific post-update changes
if [[ ! -z "${NIRVATI_OS:-}" ]]; then
  # Delete unused Docker images on Nirvati OS
  echo "Deleting previous images"
  docker image prune --all --force
fi

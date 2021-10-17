#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2021 Aaron Dewes <aaron.dewes@protonmail.com>
#
# SPDX-License-Identifier: MIT

import yaml
import os
import argparse

# Print an error if user is not root
if os.getuid() != 0:
    print('This script must be run as root!')
    exit(1)

# The directory with this script
scriptDir = os.path.dirname(os.path.realpath(__file__))
nodeRoot = os.path.join(scriptDir, "..")

parser = argparse.ArgumentParser(description="Manage services on your Citadel")
parser.add_argument('action', help='What to do with the service.', choices=["install", "uninstall"])
parser.add_argument('--verbose', '-v', action='store_true')
parser.add_argument(
    'app', help='The service to perform an action on.')
args = parser.parse_args()

# Function to install a service
# To install it, read the service's YAML file (nodeRoot/services/name.yml) and add it to the main compose file (nodeRoot/docker-compose.yml)
def installService(name):
    # Read the YAML file
    with open(os.path.join(nodeRoot, "services", name + ".yml"), 'r') as stream:
        service = yaml.safe_load(stream)

    # Read the main compose file
    with open(os.path.join(nodeRoot, "docker-compose.yml"), 'r') as stream:
        compose = yaml.safe_load(stream)

    # Add the service to the main compose file
    compose['services'].update(service)

    # Write the main compose file
    with open(os.path.join(nodeRoot, "docker-compose.yml"), 'w') as stream:
        yaml.dump(compose, stream, sort_keys=False)

def uninstallService(name):
    # Read the main compose file
    with open(os.path.join(nodeRoot, "docker-compose.yml"), 'r') as stream:
        compose = yaml.safe_load(stream)

    # Remove the service from the main compose file
    del compose['services'][name]

    # Write the main compose file
    with open(os.path.join(nodeRoot, "docker-compose.yml"), 'w') as stream:
        yaml.dump(compose, stream, sort_keys=False)

if args.action == "install":
    installService(args.app)
elif args.action == "uninstall":
    uninstallService(args.app)
    
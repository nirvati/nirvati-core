#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from lib.manage import compose, createDataDir, deleteData, getUserData, setInstalled, setRemoved, update, deriveEntropy, updateRepos, download, getAvailableUpdates
from lib.validate import findAndValidateApps
import os
import argparse

# Print an error if user is not root
if os.getuid() != 0:
    print('This script must be run as root!')
    exit(1)

# The directory with this script
scriptDir = os.path.dirname(os.path.realpath(__file__))
nodeRoot = os.path.join(scriptDir, "..")
appsDir = os.path.join(nodeRoot, "apps")
appDataDir = os.path.join(nodeRoot, "app-data")
userFile = os.path.join(nodeRoot, "db", "user.json")
legacyScript = os.path.join(nodeRoot, "scripts", "app")

parser = argparse.ArgumentParser(description="Manage apps on your Citadel")
parser.add_argument('action', help='What to do with the app database.', choices=[
                    "list", "download", "generate", "update", "list-updates", "ls-installed", "install", "uninstall", "stop", "start", "compose", "restart", "entropy"])
# Add the --invoked-by-configure option, which is hidden from the user in --help
parser.add_argument('--invoked-by-configure',
                    action='store_true', help=argparse.SUPPRESS)
parser.add_argument('--verbose', '-v', action='store_true')
parser.add_argument(
    'app', help='Optional, the app to perform an action on. (For install, uninstall, stop, start and compose)', nargs='?')
parser.add_argument(
    'other', help='Anything else (For compose)', nargs="*")
args = parser.parse_args()

# If no action is specified, the list action is used
if args.action is None:
    args.action = 'list'

if args.action == 'list':
    apps = findAndValidateApps(appsDir)
    for app in apps:
        print(app)
    exit(0)
elif args.action == "list-updates":
    availableUpdates = getAvailableUpdates()
    print(json.dumps(availableUpdates))
    exit(0)
elif args.action == 'download':
    updateRepos()
    exit(0)
elif args.action == 'generate':
    if args.invoked_by_configure:
        update(args.app)
    else:
        os.system(os.path.join(nodeRoot, "scripts", "configure"))
        os.chdir(nodeRoot)
        os.system("docker compose stop app-tor")
        os.system("docker compose start app-tor")
        os.system("docker compose stop app-2-tor")
        os.system("docker compose start app-2-tor")
        os.system("docker compose stop app-3-tor")
        os.system("docker compose start app-3-tor")
    exit(0)
elif args.action == 'update':
    if args.app is None:
        updateRepos()
        print("Downloaded all updates")
    else:
        download(args.app)
        print("Downloaded latest {} version".format(args.app))
    if args.invoked_by_configure:
        update(args.verbose)
    else:
        os.system(os.path.join(nodeRoot, "scripts", "configure"))
        os.chdir(nodeRoot)
        os.system("docker compose stop app-tor")
        os.system("docker compose start app-tor")
        os.system("docker compose stop app-2-tor")
        os.system("docker compose start app-2-tor")
        os.system("docker compose stop app-3-tor")
        os.system("docker compose start app-3-tor")
    exit(0)
elif args.action == 'ls-installed':
    # Load the userFile as JSON, check if installedApps is in it, and if so, print the apps
    with open(userFile, "r") as f:
        userData = json.load(f)
    if "installedApps" in userData:
        print("\n".join(userData["installedApps"]))
    else:
        # To match the behavior of the old script, print a newline if there are no apps installed
        print("\n")
elif args.action == 'install':
    if not args.app:
        print("No app provided")
        exit(1)
    with open(os.path.join(appsDir, "virtual-apps.json"), "r") as f:
        virtual_apps = json.load(f)
    userData = getUserData()
    for virtual_app in virtual_apps.keys():
        implementations = virtual_apps[virtual_app]
        if args.app in implementations:
            for implementation in implementations:
                if "installedApps" in userData and implementation in userData["installedApps"]:
                    print("Another implementation of {} is already installed: {}. Uninstall it first to install this app.".format(virtual_app, implementation))
                    exit(1)
    createDataDir(args.app)
    compose(args.app, "pull")
    compose(args.app, "up --detach")
    setInstalled(args.app)
    registryFile = os.path.join(nodeRoot, "apps", "registry.json")
    registry: list = []
    if os.path.isfile(registryFile):
        with open(registryFile, 'r') as f:
            registry = json.load(f)
    for app in registry:
        if not app.compatible:
            for dependency in app.missing_dependencies:
                # If dependency is a string, check if it's the app we're installing or the app we're installing implements
                if isinstance(dependency, str):
                    if dependency == args.app or args.app in virtual_apps[dependency]:
                        # Delete the app's result.yml file
                        os.remove(os.path.join(nodeRoot, "apps", app.name, "result.yml"))
                # Else, it should be a list, so check if the app we're installing is in it
                else if isinstance(dependency, list):
                    for dep in dependency:
                        if dep == args.app or args.app in virtual_apps[dep]:
                            # Delete the app's result.yml file
                            os.remove(os.path.join(nodeRoot, "apps", app.name, "result.yml"))
    # Reconfigure
    os.system(os.path.join(nodeRoot, "scripts", "configure"))
    os.chdir(nodeRoot)
    os.system("docker compose stop app-tor")
    os.system("docker compose start app-tor")
    os.system("docker compose stop app-2-tor")
    os.system("docker compose start app-2-tor")
    os.system("docker compose stop app-3-tor")
    os.system("docker compose start app-3-tor")

elif args.action == 'uninstall':
    if not args.app:
        print("No app provided")
        exit(1)
    userData = getUserData()
    if not "installedApps" in userData or args.app not in userData["installedApps"]:
        print("App {} is not installed".format(args.app))
        exit(1)
    print("Stopping app {}...".format(args.app))
    try:
        compose(args.app, "rm --force --stop")
        print("Deleting data...")
        deleteData(args.app)
    except:
        pass
    print("Removing from the list of installed apps...")
    setRemoved(args.app)
elif args.action == 'stop':
    if not args.app:
        print("No app provided")
        exit(1)
    userData = getUserData()
    print("Stopping app {}...".format(args.app))
    compose(args.app, "rm --force --stop")
elif args.action == 'start':
    if not args.app:
        print("No app provided")
        exit(1)

    userData = getUserData()
    if not "installedApps" in userData or args.app not in userData["installedApps"]:
        print("App {} is not yet installed".format(args.app))
        exit(1)
    compose(args.app, "up --detach")

elif args.action == 'restart':
    if not args.app:
        print("No app provided")
        exit(1)

    userData = getUserData()
    if not "installedApps" in userData or args.app not in userData["installedApps"]:
        print("App {} is not yet installed".format(args.app))
        exit(1)
    compose(args.app, "rm --force --stop")
    compose(args.app, "up --detach")

elif args.action == 'compose':
    if not args.app:
        print("No app provided")
        exit(1)
    compose(args.app, " ".join(args.other))

elif args.action == "entropy":
    if args.app == "":
        print("Missing identifier for entropy")
        exit(1)
    print(deriveEntropy(args.app))

else:
    print("Error: Unknown action")
    print("See --help for usage")
    exit(1)

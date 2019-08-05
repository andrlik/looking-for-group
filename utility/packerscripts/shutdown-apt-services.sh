#!/usr/bin/env bash

set -e

function killService() {
    service=$1
    systemctl stop $service
    systemctl kill --kill-who=all $service

    # # Wait until the status of the service is either exited or killed.
    # while ! (systemctl status "$service" | grep -q "Main.*code=\(exited\|killed\)")
    # do
    #     sleep 10
    # done
    sleep 10
}

function disableTimers() {
    systemctl disable apt-daily.timer
    systemctl disable apt-daily-upgrade.timer
}

function killServices() {
    killService unattended-upgrades.service
    killService apt-daily.service
    killService apt-daily-upgrade.service
}

function main() {
    disableTimers
    killServices
}

main

exit 0

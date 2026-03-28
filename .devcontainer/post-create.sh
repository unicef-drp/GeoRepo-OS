#!/bin/bash

set -e

# Configure git safe directory and Claude config dir
git config --global --add safe.directory /home/web/project
sudo mkdir -p /home/web/.claude

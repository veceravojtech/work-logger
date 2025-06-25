#!/bin/bash

# Script to easily run the GitLab-Toggl workflow
# This script will run the work_flow.py Python script

# Exit on error
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Path to the work_flow.py script
WORKFLOW_SCRIPT="${SCRIPT_DIR}/work/work_flow.py"

# Check if the workflow script exists
if [ ! -f "$WORKFLOW_SCRIPT" ]; then
    echo "Error: Workflow script not found at $WORKFLOW_SCRIPT"
    echo "Make sure you're running this script from the project root directory."
    exit 1
fi

# Check if the script is executable, if not make it executable
if [ ! -x "$WORKFLOW_SCRIPT" ]; then
    echo "Making workflow script executable..."
    chmod +x "$WORKFLOW_SCRIPT"
fi

# Check if the virtual environment exists
VENV_DIR="$HOME/gitlab_venv"
VENV_PATH="$VENV_DIR/bin/activate"

if [ ! -f "$VENV_PATH" ]; then
    echo "Python virtual environment not found at $VENV_PATH"
    echo "Would you like to create it? (y/n)"
    read -r create_venv

    if [[ "$create_venv" =~ ^[Yy]$ ]]; then
        echo "Creating Python virtual environment..."
        python3 -m venv "$VENV_DIR"

        echo "Activating Python virtual environment..."
        source "$VENV_PATH"

        echo "Installing required packages..."
        pip install python-gitlab requests
    else
        echo "Warning: Continuing without virtual environment. Some dependencies might be missing."
    fi
else
    echo "Activating Python virtual environment..."
    source "$VENV_PATH"

    # Check if the gitlab package is installed
    if ! python3 -c "import gitlab" &>/dev/null; then
        echo "Installing required package: python-gitlab..."
        pip install python-gitlab
    fi

    # Check if the requests package is installed (used by toggle_activity.py)
    if ! python3 -c "import requests" &>/dev/null; then
        echo "Installing required package: requests..."
        pip install requests
    fi
fi

# Run the workflow script
echo "Starting GitLab-Toggl Workflow..."
"$WORKFLOW_SCRIPT"

# Exit with the same status as the workflow script
exit $?

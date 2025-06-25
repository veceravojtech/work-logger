# Toggl Time Tracking Script

This script connects to your Toggl account and provides various time tracking functionalities, including reading activity, adding time entries, and importing data from GitLab.

## Directory Structure

```
toggle/
├── auth.py             # Authentication configuration (API token and workspace ID)
├── auth.py.template    # Template for authentication configuration
├── toggle_activity.py  # Main script for Toggl time tracking
└── README.md           # This file
```

## Prerequisites

- Python 3.6 or higher
- Required Python packages:
  - requests
  - python-dateutil

You can install the required packages using pip:

```bash
pip install requests python-dateutil
```

## Configuration

The script uses authentication details from `auth.py`. This file should contain:

```python
# Toggl authentication configuration
TOGGL_API_TOKEN = "your-toggl-api-token"
TOGGL_WORKSPACE_ID = "your-workspace-id"
```

To set up your authentication:
1. Copy the template file to create your auth.py file:
   ```bash
   cp auth.py.template auth.py
   ```
2. Edit the auth.py file with your Toggl API token and workspace ID.

Note: The auth.py file is excluded from version control in .gitignore to prevent accidentally committing your credentials.

You can override these settings using command-line arguments.

## Usage

The script provides several commands for different operations:

```bash
./toggle_activity.py <command> [options]
```

Available commands:
- `activity`: Get time entries from Toggl
- `add`: Add a new time entry to Toggl
- `import`: Import GitLab activity data into Toggl
- `projects`: List all projects in the Toggl workspace

### Command: activity

Get time entries from Toggl for a specified time period.

```bash
./toggle_activity.py activity [options]
```

Options:
```
  --token TOKEN, -t TOKEN
                        Toggl API token. If not provided, will try to use value from auth.py or TOGGL_API_TOKEN environment variable.
  --workspace WORKSPACE, -w WORKSPACE
                        Toggl workspace ID. If not provided, will try to use value from auth.py or TOGGL_WORKSPACE_ID environment variable.
  --current-month, -c   Show only the current month's activity.
  --previous-month, -p  Show only the previous month's activity.
  --format {text,json,csv}, -f {text,json,csv}
                        Output format. Default: text
  --output OUTPUT, -o OUTPUT
                        Output file path. If not provided, prints to stdout.
```

### Command: add

Add a new time entry to Toggl.

```bash
./toggle_activity.py add [options]
```

Options:
```
  --token TOKEN, -t TOKEN
                        Toggl API token. If not provided, will try to use value from auth.py or TOGGL_API_TOKEN environment variable.
  --workspace WORKSPACE, -w WORKSPACE
                        Toggl workspace ID. If not provided, will try to use value from auth.py or TOGGL_WORKSPACE_ID environment variable.
  --description DESCRIPTION, -d DESCRIPTION
                        Description of the time entry. [required]
  --project PROJECT, -p PROJECT
                        Project ID for the time entry.
  --start START, -s START
                        Start time for the entry (format: YYYY-MM-DD HH:MM:SS). If not provided, uses current time.
  --duration DURATION, -u DURATION
                        Duration in seconds. If not provided, creates a running entry.
  --tags TAGS, -g TAGS  Comma-separated list of tags to apply to the entry.
```

### Command: import

Import GitLab activity data into Toggl.

```bash
./toggle_activity.py import [options]
```

Options:
```
  --token TOKEN, -t TOKEN
                        Toggl API token. If not provided, will try to use value from auth.py or TOGGL_API_TOKEN environment variable.
  --workspace WORKSPACE, -w WORKSPACE
                        Toggl workspace ID. If not provided, will try to use value from auth.py or TOGGL_WORKSPACE_ID environment variable.
  --file FILE, -f FILE  Path to GitLab activity file (JSON format). [required]
  --project PROJECT, -p PROJECT
                        Project ID to use for imported entries.
```

### Command: projects

List all projects in the Toggl workspace.

```bash
./toggle_activity.py projects [options]
```

Options:
```
  --token TOKEN, -t TOKEN
                        Toggl API token. If not provided, will try to use value from auth.py or TOGGL_API_TOKEN environment variable.
  --workspace WORKSPACE, -w WORKSPACE
                        Toggl workspace ID. If not provided, will try to use value from auth.py or TOGGL_WORKSPACE_ID environment variable.
```

## Examples

1. View current month's activity:
   ```bash
   ./toggle_activity.py activity --current-month
   ```

2. View previous month's activity in JSON format:
   ```bash
   ./toggle_activity.py activity --previous-month --format json
   ```

3. Add a new time entry:
   ```bash
   ./toggle_activity.py add --description "Working on project X" --project 123456
   ```

4. Add a time entry with specific start time and duration:
   ```bash
   ./toggle_activity.py add --description "Meeting with client" --start "2023-06-15 14:00:00" --duration 3600 --tags "meeting,client"
   ```

5. Import GitLab activity:
   ```bash
   ./toggle_activity.py import --file gitlab_activity.json --project 123456
   ```

6. List available projects:
   ```bash
   ./toggle_activity.py projects
   ```

## Getting a Toggl API Token

1. Log in to your Toggl account
2. Go to your Profile settings (click on your name in the bottom left corner and select "Profile settings")
3. Scroll down to the "API Token" section
4. Copy your API token

## Getting a Toggl Workspace ID

1. Log in to your Toggl account
2. The workspace ID is visible in the URL when you're in the workspace
   - Example: `https://track.toggl.com/123456/timer` (where 123456 is the workspace ID)
3. Alternatively, you can use the `projects` command to see your workspace ID in the API responses

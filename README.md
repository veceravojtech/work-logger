# Work Logger: GitLab-Toggl Integration

This project provides a set of tools to integrate GitLab activity with Toggl time tracking, making it easier to ensure that all your GitLab activities are properly logged in Toggl.

## Overview

The Work Logger consists of three main components:

1. **GitLab History**: Fetches your activity history from GitLab
2. **Toggl Activity**: Manages your time entries in Toggl
3. **Comparison Tool**: Compares GitLab activities with Toggl entries to identify missing time logs

The project also includes a workflow script that ties these components together, providing a user-friendly interface for the entire process.

## Directory Structure

```
work-logger/
├── gitlab/                  # GitLab integration
│   ├── auth.py             # Authentication configuration (URL and token)
│   ├── auth.py.template    # Template for authentication configuration
│   ├── gitlab_history.py   # Script to fetch and display GitLab activity
│   ├── test_gitlab_api.py  # Test script for GitLab API
│   └── README.md           # GitLab component documentation
├── toggle/                  # Toggl integration
│   ├── auth.py             # Authentication configuration (API token and workspace ID)
│   ├── auth.py.template    # Template for authentication configuration
│   ├── toggle_activity.py  # Script for Toggl time tracking
│   └── README.md           # Toggl component documentation
├── compare/                 # Comparison tool
│   ├── compare_gitlab_toggl.py  # Script to compare GitLab and Toggl data
│   ├── result/             # Directory for comparison results
│   └── README.md           # Comparison tool documentation
├── work/                    # Workflow scripts
│   └── work_flow.py        # Main workflow script
├── run_workflow.sh         # Shell script to run the workflow
└── README.md               # This file
```

## Installation

### Prerequisites

- Python 3.6 or higher
- Required Python packages:
  - python-gitlab
  - python-dateutil
  - requests

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/veceravojtech/work-logger.git
   cd work-logger
   ```

2. Set up authentication for GitLab:
   ```bash
   cd gitlab
   cp auth.py.template auth.py
   # Edit auth.py with your GitLab URL and personal access token
   cd ..
   ```

3. Set up authentication for Toggl:
   ```bash
   cd toggle
   cp auth.py.template auth.py
   # Edit auth.py with your Toggl API token and workspace ID
   cd ..
   ```

4. Make the workflow script executable:
   ```bash
   chmod +x run_workflow.sh
   ```

## Usage

### Running the Workflow

The easiest way to use the Work Logger is through the provided shell script:

```bash
./run_workflow.sh
```

This script will:
1. Check if a Python virtual environment exists and activate it
2. Install required packages if needed
3. Run the workflow script

### Workflow Options

The workflow script provides several options:

1. **Select the month for data processing**:
   - Current month
   - Previous month

2. **Select the script to run**:
   - GitLab history: Fetch your GitLab activity
   - Toggl activity: Fetch your Toggl time entries
   - Both: Run both GitLab and Toggl scripts
   - Compare only: Compare existing GitLab and Toggl data
   - Import JSON: Import missing entries to Toggl
   - Exit: Exit the workflow

### Manual Usage

You can also run each component separately:

#### GitLab History

```bash
cd gitlab
./gitlab_history.py --current-month --format json --output gitlab_current_month.json
```

See [GitLab README](gitlab/README.md) for more options.

#### Toggl Activity

```bash
cd toggle
./toggle_activity.py activity --current-month --format json --output toggl_current_month.json
```

See [Toggl README](toggle/README.md) for more options.

#### Comparison Tool

```bash
cd compare
./compare_gitlab_toggl.py compare ../gitlab/gitlab_current_month.json ../toggle/toggl_current_month.json --generate-import
```

See [Comparison README](compare/README.md) for more options.

## Workflow Process

The typical workflow is as follows:

1. Run the workflow script and select "Both" to fetch both GitLab and Toggl data
2. Run the workflow script again and select "Compare only" to compare the data
3. Review the comparison results in the HTML report
4. If there are missing entries, choose whether to import them to Toggl

## Getting Authentication Tokens

### GitLab Personal Access Token

1. Log in to your GitLab account
2. Go to your user settings (click on your avatar in the top-right corner and select "Preferences")
3. Navigate to "Access Tokens" in the left sidebar
4. Create a new personal access token with the "read_api" scope
5. Copy the token immediately after creation (you won't be able to see it again)

### Toggl API Token

1. Log in to your Toggl account
2. Go to your Profile settings (click on your name in the bottom left corner and select "Profile settings")
3. Scroll down to the "API Token" section
4. Copy your API token

### Toggl Workspace ID

1. Log in to your Toggl account
2. The workspace ID is visible in the URL when you're in the workspace
   - Example: `https://track.toggl.com/123456/timer` (where 123456 is the workspace ID)
3. Alternatively, you can use the `projects` command to see your workspace ID in the API responses

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
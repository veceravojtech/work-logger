# GitLab History Script

This script connects to your GitLab account and prints your activity history for a specified time period.

## Directory Structure

```
gitlab/
├── auth.py             # Authentication configuration (URL and token)
├── auth.py.template    # Template for authentication configuration
├── gitlab_history.py   # Main script to fetch and display GitLab activity
├── test_gitlab_api.py  # Test script for GitLab API
└── README.md           # This file
```

## Prerequisites

- Python 3.6 or higher
- Required Python packages:
  - python-gitlab
  - python-dateutil

You can install the required packages using pip:

```bash
pip install python-gitlab python-dateutil
```

## Configuration

The script uses authentication details from `auth.py`. This file should contain:

```python
# GitLab authentication configuration
GITLAB_URL = "https://your-gitlab-instance.com/"
GITLAB_TOKEN = "your-personal-access-token"
```

To set up your authentication:
1. Copy the template file to create your auth.py file:
   ```bash
   cp auth.py.template auth.py
   ```
2. Edit the auth.py file with your GitLab URL and personal access token.

Note: The auth.py file is excluded from version control in .gitignore to prevent accidentally committing your credentials.

You can override these settings using command-line arguments.

## Usage

### Basic Usage

```bash
./gitlab_history.py [options]
```

### Command-line Options

```
  -h, --help            Show this help message and exit
  --token TOKEN, -t TOKEN
                        GitLab personal access token. If not provided, will try to use value from auth.py or GITLAB_TOKEN environment variable.
  --url URL, -u URL     GitLab instance URL. If not provided, will try to use value from auth.py or default to https://gitlab.com
  --months MONTHS, -m MONTHS
                        Number of months to look back. Default: 1
  --days DAYS, -d DAYS  Additional number of days to look back. Default: 0
  --current-month, -c   Show only the current month's activity.
  --previous-month, -p  Show only the previous month's activity.
  --format {text,json,csv}, -f {text,json,csv}
                        Output format. Default: text
  --output OUTPUT, -o OUTPUT
                        Output file path. If not provided, prints to stdout.
  --event-type EVENT_TYPE, -e EVENT_TYPE
                        Filter by event type (e.g., pushed, commented).
```

The script also supports the original positional arguments for backward compatibility:
```bash
./gitlab_history.py [token] [gitlab_url]
```

### Examples

1. Basic usage (using auth.py configuration):
   ```bash
   ./gitlab_history.py
   ```

2. Basic usage (last month's activity with explicit token):
   ```bash
   ./gitlab_history.py --token your_personal_access_token
   ```

3. Using an environment variable:
   ```bash
   export GITLAB_TOKEN=your_personal_access_token
   ./gitlab_history.py
   ```

4. Using a self-hosted GitLab instance:
   ```bash
   ./gitlab_history.py --url https://gitlab.your-company.com
   ```

5. Custom time range (last 3 months and 15 days):
   ```bash
   ./gitlab_history.py --months 3 --days 15
   ```

6. Filter by event type:
   ```bash
   ./gitlab_history.py --event-type pushed
   ```

7. Output to JSON format:
   ```bash
   ./gitlab_history.py --format json
   ```

8. Save output to a file:
   ```bash
   ./gitlab_history.py --output gitlab_activity.txt
   ```

9. Show only the current month's activity:
   ```bash
   ./gitlab_history.py --current-month
   ```

10. Show only the previous month's activity:
    ```bash
    ./gitlab_history.py --previous-month
    ```

11. Combining multiple options:
    ```bash
    ./gitlab_history.py --months 6 --format csv --output activity.csv --event-type commented
    ```

## Getting a GitLab Personal Access Token

1. Log in to your GitLab account
2. Go to your user settings (click on your avatar in the top-right corner and select "Preferences")
3. Navigate to "Access Tokens" in the left sidebar
4. Create a new personal access token with the "read_api" scope
5. Copy the token immediately after creation (you won't be able to see it again)

## Output

The script will display your GitLab activity for the specified time period, including:
- Commits
- Issues
- Merge requests
- Comments
- Other GitLab activities

Each activity will show the date, action type, project name, and additional details when available.

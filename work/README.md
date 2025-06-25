# GitLab-Toggl Workflow

This script automates the workflow between GitLab and Toggl time tracking, making it easy to synchronize your GitLab activity with your Toggl time entries.

## Directory Structure

```
bin/work/
├── work_flow.py    # Main workflow script
└── README.md       # This file
```

## Prerequisites

- Python 3.6 or higher
- Required Python packages:
  - subprocess
  - json

The script uses the following components:
- GitLab history script (`bin/gitlab/gitlab_history.py`)
- Toggl activity script (`bin/toggle/toggle_activity.py`)
- Comparison script (`bin/compare/compare_gitlab_toggl.py`)

## Usage

```bash
./work_flow.py
```

## Workflow Steps

The script guides you through the following steps:

1. **Select Month**: Choose between current month or previous month for data processing.

2. **Select Script**: Choose which script(s) to run:
   - GitLab history: Fetches your GitLab activity
   - Toggl activity: Fetches your Toggl time entries
   - Both: Runs both scripts

3. **Run Selected Script(s)**: The script runs the selected script(s) with appropriate parameters and saves the output to JSON files.

4. **Run Comparison**: The script compares the GitLab and Toggl data to find missing entries and generates:
   - An HTML report (`bin/compare/result/missing_entries.html`)
   - A JSON file with missing entries ready for import (`bin/compare/result/toggl_import.json`)

5. **Confirmation**: The script asks for confirmation before importing the missing entries to Toggl.

6. **Import Data**: If confirmed, the script imports the missing entries to Toggl.

## Features

- **User-friendly Interface**: Clear prompts and options for each step
- **Error Handling**: Comprehensive error handling with informative messages
- **Output Management**: Truncates long output for better readability
- **Project Selection**: Option to select a specific project for imported entries
- **Confirmation Step**: Asks for confirmation before making changes to Toggl

## Example

```
================================================================================
                             GitLab-Toggl Workflow                              
================================================================================

Select the month for data processing:
1. Current month
2. Previous month

Enter your choice (number): 1

Select the script to run:
1. GitLab history
2. Toggl activity
3. Both

Enter your choice (number): 3

================================================================================
                        Running GitLab History Script                           
================================================================================

Running command: python3 /home/console/PhpstormProjects/previo2/bin/gitlab/gitlab_history.py --current-month --format json --output /home/console/PhpstormProjects/previo2/bin/gitlab/gitlab_current_month.json
--------------------------------------------------------------------------------

✅ GitLab history for current month saved to /home/console/PhpstormProjects/previo2/bin/gitlab/gitlab_current_month.json

================================================================================
                        Running Toggl Activity Script                           
================================================================================

Running command: python3 /home/console/PhpstormProjects/previo2/bin/toggle/toggle_activity.py activity --current-month --format json --output /home/console/PhpstormProjects/previo2/bin/toggle/toggl_current_month.json
--------------------------------------------------------------------------------

✅ Toggl activity for current month saved to /home/console/PhpstormProjects/previo2/bin/toggle/toggl_current_month.json

================================================================================
                          Running Comparison Script                             
================================================================================

Running command: python3 /home/console/PhpstormProjects/previo2/bin/compare/compare_gitlab_toggl.py compare /home/console/PhpstormProjects/previo2/bin/gitlab/gitlab_current_month.json /home/console/PhpstormProjects/previo2/bin/toggle/toggl_current_month.json --generate-import
--------------------------------------------------------------------------------
HTML results written to /home/console/PhpstormProjects/previo2/bin/compare/result/missing_entries.html
Import data written to /home/console/PhpstormProjects/previo2/bin/compare/result/toggl_import.json

✅ Comparison completed successfully

Comparison results are available in the following files:
- HTML report: /home/console/PhpstormProjects/previo2/bin/compare/result/missing_entries.html
- Import data: /home/console/PhpstormProjects/previo2/bin/compare/result/toggl_import.json

Do you want to import the missing entries to Toggl? (y/n): y

================================================================================
                           Importing Data to Toggl                              
================================================================================

Found 16 entries to import.

Available projects:
Running command: python3 /home/console/PhpstormProjects/previo2/bin/toggle/toggle_activity.py projects
--------------------------------------------------------------------------------
Available projects:
--------------------------------------------------------------------------------
ID: 123456 - Name: Previo
ID: 789012 - Name: Personal
--------------------------------------------------------------------------------
Total projects: 2

Enter project ID to use for import (leave empty to use project from import file): 123456

Running command: python3 /home/console/PhpstormProjects/previo2/bin/toggle/toggle_activity.py import --file /home/console/PhpstormProjects/previo2/bin/compare/result/toggl_import.json --project 123456
--------------------------------------------------------------------------------
Successfully imported 16 GitLab events into Toggl.

✅ Data imported to Toggl successfully

🎉 Workflow completed successfully!
```

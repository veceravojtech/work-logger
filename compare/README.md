# GitLab-Toggl Comparison Tool

This tool compares GitLab activity with Toggl time entries to identify GitLab activities that don't have corresponding Toggl entries. It also provides a side-by-side comparison of original and updated Toggl records.

## Usage

The tool now supports two main modes of operation:

### 1. Standard Comparison Mode

```bash
./compare_gitlab_toggl.py compare gitlab_file toggl_file [--output OUTPUT] [--format {json,html}]
```

### 2. Side-by-Side Comparison Mode

```bash
./compare_gitlab_toggl.py side-by-side original_toggl_file updated_toggl_file [--output OUTPUT]
```

### Arguments for Standard Comparison Mode

- `gitlab_file`: Path to the GitLab JSON file (e.g., `/path/to/gitlab_current_month.json`)
- `toggl_file`: Path to the Toggl JSON file (e.g., `/path/to/toggl_current_month.json`)
- `--output`, `-o` (optional): Path to the output file. If not provided, saves to the `bin/compare/result` directory.
- `--format`, `-f` (optional): Output format - 'json' or 'html'. Default: 'html'
- `--generate-import`, `-g` (optional): Generate a clean JSON file with squashed entries ready for import to Toggl.

### Arguments for Side-by-Side Comparison Mode

- `original_toggl_file`: Path to the original Toggl JSON file
- `updated_toggl_file`: Path to the updated Toggl JSON file
- `--output`, `-o` (optional): Path to the output file. If not provided, saves to `bin/compare/result/toggl_comparison.html`

### Backward Compatibility

For backward compatibility, the tool still supports the original command format:

```bash
./compare_gitlab_toggl.py gitlab_file toggl_file [--output OUTPUT] [--format {json,html}]
```

### Examples

Standard comparison with HTML output (default):
```bash
./compare_gitlab_toggl.py compare /path/to/gitlab_current_month.json /path/to/toggl_current_month.json
```

Standard comparison with JSON output:
```bash
./compare_gitlab_toggl.py compare /path/to/gitlab_current_month.json /path/to/toggl_current_month.json --format json
```

Generate a clean JSON file with squashed entries ready for import to Toggl:
```bash
./compare_gitlab_toggl.py compare /path/to/gitlab_current_month.json /path/to/toggl_current_month.json --generate-import
```

Side-by-side comparison of Toggl records:
```bash
./compare_gitlab_toggl.py side-by-side /path/to/original_toggl.json /path/to/updated_toggl.json
```

Backward compatibility mode:
```bash
./compare_gitlab_toggl.py /path/to/gitlab_current_month.json /path/to/toggl_current_month.json
```

## How It Works

1. The script reads both JSON files and extracts the task numbers from each entry.
2. It groups entries by date and compares GitLab activities with Toggl entries for each date.
3. The script identifies three types of entries:
   - **Matched entries**: GitLab activities that have corresponding Toggl entries (with the same task number on the same date)
   - **Missing entries**: GitLab activities that don't have corresponding Toggl entries
   - **Toggl-only entries**: Toggl entries that don't have corresponding GitLab activities (either they don't have a task number or the task number wasn't found in GitLab)
4. The script outputs all three types of entries, with missing entries formatted for Toggl import.

## Import File Generation

When using the `--generate-import` option, the script generates a clean JSON file with squashed entries ready for import to Toggl. This file is saved to `bin/compare/result/toggl_import.json`.

The import file has the following features:

1. Tasks with the same ID on the same day are squashed into one entry
2. Duration is calculated based on the number of occurrences:
   - 1 task = 30 minutes
   - 2 tasks = 60 minutes
   - 3 tasks = 90 minutes
   - etc.
3. The start time is taken from the first occurrence of the task on that day
4. The description is taken from the first occurrence of the task on that day
5. The project name is taken from the first occurrence of the task on that day
6. The tags include 'gitlab-import' and 'squashed'

This makes it easy to import the entries into Toggl without duplicates and with appropriate durations.

## Output Formats

### JSON Output

When using the default JSON format, the output has the following structure:

```json
{
  "summary": {
    "gitlab_period": {
      "start": "2025-06-01",
      "end": "2025-06-24"
    },
    "toggl_period": {
      "start": "2025-06-01",
      "end": "2025-06-24"
    },
    "total_gitlab_events": 114,
    "total_toggl_entries": 38,
    "matched_entries_count": 98,
    "missing_entries_count": 16,
    "toggl_only_entries_count": 12
  },
  "matched_entries": [
    {
      "date": "2025-06-24 15:42:10",
      "description": "#48345",
      "project": "Previo",
      "action": "Pushed",
      "details": {
        "target": "#48345: Fix reservation form validation",
        "commits": 2,
        "branch": "feature/48345-form-validation"
      }
    }
  ],
  "missing_entries": [
    {
      "date": "2025-06-23 20:19:08",
      "description": "#47502",
      "project": "Previo",
      "action": "Opened",
      "details": {
        "target": "#47502: Alfred: fix price multiplier",
        "commits": null,
        "branch": null
      }
    }
  ],
  "toggl_only_entries": [
    {
      "date": "2025-06-24 10:00:00",
      "description": "Team meeting",
      "project": "Previo",
      "duration": 3.0,
      "duration_formatted": "3h 0m",
      "action": "Toggl Entry"
    }
  ],
  "toggl_import_data": [
    {
      "description": "#47502: Alfred: fix price multiplier",
      "start": "2025-06-23 20:19:08",
      "duration": 1800,
      "project_name": "Previo",
      "tags": [
        "gitlab-import",
        "opened"
      ]
    }
  ]
}
```

The `toggl_import_data` section contains entries formatted for import into Toggl. Each entry includes:

- `description`: The task description, including the task number and title
- `start`: The start time of the activity
- `duration`: The duration in seconds (default: 30 minutes)
- `project_name`: The project name
- `tags`: Tags for the entry, including "gitlab-import" and the action type

### HTML Output

When using the HTML format (`--format html`), the output is a well-formatted HTML page that provides a more user-friendly view of both matched and missing entries. The HTML output includes:

- A summary section with period information and counts (including matched, missing, and Toggl-only entries)
- A color-coded legend explaining the status indicators:
  - Green: Matched entries (already logged in Toggl)
  - Yellow: Missing entries (need to be added to Toggl)
  - Blue: Toggl-only entries (logged in Toggl, not in GitLab)
- All entries grouped by date in reverse chronological order
- A table for each date showing:
  - Time of the activity
  - Task description
  - Project name
  - Action type (or duration for Toggl-only entries)
  - Status (Logged, Missing, or Toggl Only)
- Color-coded rows for easy visual identification:
  - Green rows: Entries that are already logged in Toggl
  - Yellow rows: Entries that are missing in Toggl and need to be added
  - Blue rows: Entries that are logged in Toggl but don't have corresponding GitLab activities
- Responsive styling for easy reading on different devices

The HTML output is ideal for reviewing your activity and quickly identifying:
1. Which GitLab activities are already logged in Toggl (matched entries)
2. Which GitLab activities still need to be logged in Toggl (missing entries)
3. Which Toggl entries don't have corresponding GitLab activities (Toggl-only entries)

The color-coding makes it easy to scan the report and see at a glance what work has been tracked, what still needs to be logged, and what has been logged without corresponding GitLab activity.

### Side-by-Side Comparison HTML Output

When using the side-by-side comparison mode, the output is a well-formatted HTML page that provides a visual comparison of original and updated Toggl records. The HTML output includes:

- A summary section with period information and total task count
- A legend explaining the color coding:
  - Green: New entries (added in updated data)
  - Yellow: Modified entries (changed from original data)
- A two-column layout:
  - Left column: Original Toggl records
  - Right column: Updated Toggl records
- Entries organized by date first, then by task (improved organization):
  - Each date appears only once in each column
  - Tasks for each date are grouped together
  - Clear visual hierarchy with distinct date and task headers
- Dates displayed in reverse chronological order with day names (e.g., "2025-06-24 - Tuesday")
- A table for each task showing:
  - Time of the entry
  - Project name
  - Tags
  - Duration
- Color-coded rows in the right column:
  - Green: New entries that don't exist in the original data
  - Yellow: Modified entries that have been changed from the original data
- Responsive styling for easy reading on different devices

The side-by-side comparison is ideal for reviewing changes between two versions of Toggl records, such as before and after importing GitLab activities. The new organization by date first, then by task, makes it easier to see all activities for a specific day, while the color coding helps quickly identify new and modified entries.

## New Features

### Day Captions

All dates in the HTML output now include day names (e.g., "2025-06-24 - Tuesday") for easier reference.

### Output Directory

All output files are now saved to the `bin/compare/result` directory by default. This helps keep the output files organized and prevents cluttering the main directory.

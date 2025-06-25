#!/usr/bin/env python3

import json
import sys
import os
import re
import datetime
import argparse
import calendar
from collections import defaultdict

def extract_task_number(text):
    """Extract task number from text using regex."""
    if not text:
        return None

    # Look for #XXXXX pattern
    match = re.search(r'#(\d+)', text)
    if match:
        return match.group(1)
    return None

def get_date_from_entry(entry_date):
    """Extract just the date part from a datetime string."""
    return entry_date.split()[0]

def get_day_name(date_str):
    """Get the day name (Monday, Tuesday, etc.) from a date string."""
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return calendar.day_name[date_obj.weekday()]
    except ValueError:
        return ""

def load_json_file(file_path):
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {str(e)}")
        sys.exit(1)

def generate_side_by_side_html(original_toggl_data, updated_toggl_data):
    """
    Generate a side-by-side comparison HTML showing original and updated Toggl records.

    Args:
        original_toggl_data (dict): The original Toggl data
        updated_toggl_data (dict): The updated Toggl data

    Returns:
        str: HTML content
    """
    # Extract entries from both datasets
    original_entries = original_toggl_data.get('entries', [])
    updated_entries = updated_toggl_data.get('entries', [])

    # Get date range from both datasets
    start_date_str = min(
        original_toggl_data.get('period', {}).get('start', '9999-12-31'),
        updated_toggl_data.get('period', {}).get('start', '9999-12-31')
    )
    end_date_str = max(
        original_toggl_data.get('period', {}).get('end', '1970-01-01'),
        updated_toggl_data.get('period', {}).get('end', '1970-01-01')
    )

    # Convert to datetime objects
    try:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        # Default to current month if dates are invalid
        now = datetime.datetime.now()
        start_date = now.replace(day=1)
        end_date = now

    # Generate a list of all dates in the range
    all_dates = []
    current_date = start_date
    while current_date <= end_date:
        all_dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += datetime.timedelta(days=1)

    # Group entries by date and task
    original_by_date_task = defaultdict(lambda: defaultdict(list))
    updated_by_date_task = defaultdict(lambda: defaultdict(list))

    # Group original entries by date and task
    for entry in original_entries:
        date = get_date_from_entry(entry.get('date', ''))
        task_number = extract_task_number(entry.get('description', ''))
        if task_number:
            original_by_date_task[date][task_number].append(entry)
        else:
            # For entries without a task number, use the description as the key
            original_by_date_task[date][entry.get('description', 'No description')].append(entry)

    # Group updated entries by date and task
    for entry in updated_entries:
        date = get_date_from_entry(entry.get('date', ''))
        task_number = extract_task_number(entry.get('description', ''))
        if task_number:
            updated_by_date_task[date][task_number].append(entry)
        else:
            # For entries without a task number, use the description as the key
            updated_by_date_task[date][entry.get('description', 'No description')].append(entry)

    # Get all unique task IDs across all dates
    all_task_ids = set()
    for date in all_dates:
        all_task_ids.update(original_by_date_task[date].keys())
        all_task_ids.update(updated_by_date_task[date].keys())

    # Start building HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Toggl Records Comparison</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .summary {{
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            border-left: 5px solid #007bff;
        }}
        .summary-item {{
            margin-bottom: 5px;
        }}
        .comparison-container {{
            display: flex;
            margin-top: 30px;
        }}
        .column {{
            flex: 1;
            padding: 0 15px;
        }}
        .column-header {{
            background-color: #007bff;
            color: white;
            padding: 10px;
            border-radius: 5px 5px 0 0;
            text-align: center;
            font-weight: bold;
        }}
        .date-container {{
            margin-bottom: 30px;
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
        }}
        .date-header {{
            background-color: #e9ecef;
            font-weight: bold;
            padding: 10px;
            border-bottom: 1px solid #ddd;
            font-size: 1.2em;
        }}
        .task-header {{
            background-color: #f8f9fa;
            font-weight: bold;
            padding: 8px 10px;
            border-bottom: 1px solid #ddd;
            margin-top: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .no-entries {{
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-style: italic;
        }}
        .added {{
            background-color: #d4edda;
        }}
        .removed {{
            background-color: #f8d7da;
        }}
        .modified {{
            background-color: #fff3cd;
        }}
        .legend {{
            margin: 20px 0;
            padding: 10px;
            border-radius: 5px;
            background-color: #f8f9fa;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-right: 5px;
            vertical-align: middle;
            border-radius: 3px;
        }}
        .legend-green {{
            background-color: #d4edda;
        }}
        .legend-yellow {{
            background-color: #fff3cd;
        }}
    </style>
</head>
<body>
    <h1>Toggl Records Comparison</h1>

    <div class="summary">
        <h2>Summary</h2>
        <div class="summary-item"><strong>Original Period:</strong> {original_toggl_data.get('period', {}).get('start', 'N/A')} to {original_toggl_data.get('period', {}).get('end', 'N/A')}</div>
        <div class="summary-item"><strong>Updated Period:</strong> {updated_toggl_data.get('period', {}).get('start', 'N/A')} to {updated_toggl_data.get('period', {}).get('end', 'N/A')}</div>
        <div class="summary-item"><strong>Total Tasks:</strong> {len(all_task_ids)}</div>
    </div>

    <div class="legend">
        <div class="legend-item"><span class="legend-color legend-green"></span> New entries (added in updated data)</div>
        <div class="legend-item"><span class="legend-color legend-yellow"></span> Modified entries (changed from original data)</div>
    </div>

    <div class="comparison-container">
        <div class="column">
            <div class="column-header">Original Toggl Records</div>
"""

    # Process each date in reverse chronological order
    for date in sorted(all_dates, reverse=True):
        day_name = get_day_name(date)

        # Skip dates with no entries in either dataset
        if not original_by_date_task[date] and not updated_by_date_task[date]:
            continue

        # Add date container for the left column
        html_content += f"""
        <div class="date-container">
            <div class="date-header">{date} - {day_name}</div>
"""

        # Get all task IDs for this date
        date_task_ids = set(original_by_date_task[date].keys()) | set(updated_by_date_task[date].keys())

        # Process each task for this date
        for task_id in sorted(date_task_ids):
            original_task_entries = original_by_date_task[date].get(task_id, [])

            # Skip if no original entries
            if not original_task_entries:
                continue

            # Get task description
            task_desc = original_task_entries[0].get('description', f'Task #{task_id}')

            # Add task header
            html_content += f'<div class="task-header">Task: {task_desc}</div>'

            # Create a table for the entries
            html_content += '''
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Project</th>
                        <th>Tags</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
            '''

            # Sort entries by time
            sorted_entries = sorted(original_task_entries, key=lambda x: x.get('date', ''))

            # Process each entry
            for entry in sorted_entries:
                # Extract time
                time = entry.get('date', '').split()[1] if ' ' in entry.get('date', '') else ''

                # Get project
                project = entry.get('project', 'No project')

                # Get tags
                tags = entry.get('tags', [])
                tags_str = ', '.join(tags) if tags else 'No tags'

                # Get duration
                duration = entry.get('duration_formatted', '')

                html_content += f'''
                <tr>
                    <td>{time}</td>
                    <td>{project}</td>
                    <td>{tags_str}</td>
                    <td>{duration}</td>
                </tr>
                '''

            html_content += '''
                </tbody>
            </table>
            '''

        html_content += """
        </div>
"""

    # Close left column and start right column
    html_content += """
        </div>
        <div class="column">
            <div class="column-header">Updated Toggl Records</div>
"""

    # Process each date again for the right column
    for date in sorted(all_dates, reverse=True):
        day_name = get_day_name(date)

        # Skip dates with no entries in either dataset
        if not original_by_date_task[date] and not updated_by_date_task[date]:
            continue

        # Add date container for the right column
        html_content += f"""
        <div class="date-container">
            <div class="date-header">{date} - {day_name}</div>
"""

        # Get all task IDs for this date
        date_task_ids = set(original_by_date_task[date].keys()) | set(updated_by_date_task[date].keys())

        # Process each task for this date
        for task_id in sorted(date_task_ids):
            updated_task_entries = updated_by_date_task[date].get(task_id, [])
            original_task_entries = original_by_date_task[date].get(task_id, [])

            # Skip if no updated entries
            if not updated_task_entries:
                continue

            # Get task description
            task_desc = updated_task_entries[0].get('description', f'Task #{task_id}')

            # Add task header
            html_content += f'<div class="task-header">Task: {task_desc}</div>'

            # Create a table for the entries
            html_content += '''
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Project</th>
                        <th>Tags</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
            '''

            # Sort entries by time
            sorted_entries = sorted(updated_task_entries, key=lambda x: x.get('date', ''))

            # Process each entry
            for entry in sorted_entries:
                # Extract time
                time = entry.get('date', '').split()[1] if ' ' in entry.get('date', '') else ''

                # Get project
                project = entry.get('project', 'No project')

                # Get tags
                tags = entry.get('tags', [])
                tags_str = ', '.join(tags) if tags else 'No tags'

                # Get duration
                duration = entry.get('duration_formatted', '')

                # Determine if this entry is new or modified
                row_class = ""

                # Check if this entry exists in the original data for this task and date
                matching_entries = []
                for orig_entry in original_task_entries:
                    if orig_entry.get('date', '') == entry.get('date', ''):
                        matching_entries.append(orig_entry)

                if not matching_entries:
                    # This is a new entry
                    row_class = "added"
                else:
                    # Check if any fields have been modified
                    is_modified = False
                    for orig_entry in matching_entries:
                        # Compare relevant fields
                        if (entry.get('description', '') != orig_entry.get('description', '') or
                            entry.get('project', '') != orig_entry.get('project', '') or
                            entry.get('duration', 0) != orig_entry.get('duration', 0) or
                            entry.get('tags', []) != orig_entry.get('tags', [])):
                            is_modified = True
                            break

                    if is_modified:
                        row_class = "modified"

                html_content += f'''
                <tr class="{row_class}">
                    <td>{time}</td>
                    <td>{project}</td>
                    <td>{tags_str}</td>
                    <td>{duration}</td>
                </tr>
                '''

            html_content += '''
                </tbody>
            </table>
            '''

        html_content += """
        </div>
"""

    # Close right column and HTML
    html_content += """
        </div>
    </div>
</body>
</html>
"""

    return html_content

def generate_html_output(final_output):
    """
    Generate HTML output from the comparison results.

    Args:
        final_output (dict): The comparison results

    Returns:
        str: HTML content
    """
    # Extract data from final_output
    summary = final_output['summary']
    missing_entries = final_output['missing_entries']
    matched_entries = final_output.get('matched_entries', [])
    toggl_only_entries = final_output.get('toggl_only_entries', [])

    # Start building HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitLab-Toggl Comparison Results</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .summary {{
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            border-left: 5px solid #007bff;
        }}
        .summary-item {{
            margin-bottom: 5px;
        }}
        .entries-section {{
            margin-top: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #007bff;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .date-header {{
            background-color: #e9ecef;
            font-weight: bold;
            padding: 10px;
            margin-top: 20px;
            border-radius: 3px;
        }}
        .action-tag {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            background-color: #6c757d;
            color: white;
        }}
        .no-entries {{
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-style: italic;
        }}
        .matched-row {{
            background-color: #d4edda;  /* Light green */
        }}
        .matched-row:hover {{
            background-color: #c3e6cb;  /* Slightly darker green on hover */
        }}
        .missing-row {{
            background-color: #fff3cd;  /* Light yellow */
        }}
        .missing-row:hover {{
            background-color: #ffeeba;  /* Slightly darker yellow on hover */
        }}
        .legend {{
            margin: 20px 0;
            padding: 10px;
            border-radius: 5px;
            background-color: #f8f9fa;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-right: 5px;
            vertical-align: middle;
            border-radius: 3px;
        }}
        .legend-green {{
            background-color: #d4edda;
        }}
        .legend-yellow {{
            background-color: #fff3cd;
        }}
        .toggl-only-row {{
            background-color: #cce5ff;  /* Light blue */
        }}
        .toggl-only-row:hover {{
            background-color: #b8daff;  /* Slightly darker blue on hover */
        }}
        .legend-blue {{
            background-color: #cce5ff;
        }}
    </style>
</head>
<body>
    <h1>GitLab-Toggl Comparison Results</h1>

    <div class="summary">
        <h2>Summary</h2>
        <div class="summary-item"><strong>GitLab Period:</strong> {summary['gitlab_period'].get('start', 'N/A')} to {summary['gitlab_period'].get('end', 'N/A')}</div>
        <div class="summary-item"><strong>Toggl Period:</strong> {summary['toggl_period'].get('start', 'N/A')} to {summary['toggl_period'].get('end', 'N/A')}</div>
        <div class="summary-item"><strong>Total GitLab Events:</strong> {summary['total_gitlab_events']}</div>
        <div class="summary-item"><strong>Total Toggl Entries:</strong> {summary['total_toggl_entries']}</div>
        <div class="summary-item"><strong>Matched Entries:</strong> {summary.get('matched_entries_count', 0)}</div>
        <div class="summary-item"><strong>Missing Entries:</strong> {summary['missing_entries_count']}</div>
        <div class="summary-item"><strong>Toggl-Only Entries:</strong> {summary.get('toggl_only_entries_count', 0)}</div>
    </div>

    <div class="legend">
        <div class="legend-item"><span class="legend-color legend-green"></span> Matched entries (already logged in Toggl)</div>
        <div class="legend-item"><span class="legend-color legend-yellow"></span> Missing entries (need to be added to Toggl)</div>
        <div class="legend-item"><span class="legend-color legend-blue"></span> Toggl-only entries (logged in Toggl, not in GitLab)</div>
    </div>

    <div class="entries-section">
        <h2>GitLab-Toggl Entries</h2>
"""

    # Combine missing, matched, and Toggl-only entries for display, but keep track of their status
    all_entries = []
    for entry in missing_entries:
        entry['status'] = 'missing'
        all_entries.append(entry)

    for entry in matched_entries:
        entry['status'] = 'matched'
        all_entries.append(entry)

    for entry in toggl_only_entries:
        entry['status'] = 'toggl-only'
        all_entries.append(entry)

    if not all_entries:
        html_content += '<div class="no-entries">No entries found!</div>'
    else:
        # Group all entries by date for better organization
        entries_by_date = {}
        for entry in all_entries:
            date = get_date_from_entry(entry['date'])
            if date not in entries_by_date:
                entries_by_date[date] = []
            entries_by_date[date].append(entry)

        # Sort dates in reverse chronological order
        sorted_dates = sorted(entries_by_date.keys(), reverse=True)

        for date in sorted_dates:
            day_name = get_day_name(date)
            html_content += f'<div class="date-header">{date} - {day_name}</div>'
            html_content += '''
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Task</th>
                    <th>Project</th>
                    <th>Action</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
'''

            # Sort entries by time for this date
            date_entries = sorted(entries_by_date[date], key=lambda x: x['date'])

            for entry in date_entries:
                # Extract time from the datetime
                time = entry['date'].split()[1] if ' ' in entry['date'] else ''

                # Get task description
                if 'details' in entry and entry['details'].get('target'):
                    task_desc = entry['details']['target']
                else:
                    task_desc = entry.get('description', 'No description')

                # Determine row class and status text based on status
                if entry['status'] == 'matched':
                    row_class = 'matched-row'
                    status_text = 'Logged'
                elif entry['status'] == 'missing':
                    row_class = 'missing-row'
                    status_text = 'Missing'
                else:  # toggl-only
                    row_class = 'toggl-only-row'
                    status_text = 'Toggl Only'

                # For Toggl-only entries, show duration instead of action
                if entry['status'] == 'toggl-only' and 'duration_formatted' in entry:
                    action_or_duration = f"{entry.get('duration_formatted', '')}"
                    action_html = action_or_duration
                else:
                    action_or_duration = entry.get('action', 'No action')
                    action_html = f'<span class="action-tag">{action_or_duration}</span>'

                html_content += f'''
                <tr class="{row_class}">
                    <td>{time}</td>
                    <td>{task_desc}</td>
                    <td>{entry.get('project', 'No project')}</td>
                    <td>{action_html}</td>
                    <td>{status_text}</td>
                </tr>
'''

            html_content += '''
            </tbody>
        </table>
'''

    # Close HTML tags
    html_content += '''
    </div>
</body>
</html>
'''

    return html_content

def generate_squashed_import_data(missing_entries):
    """
    Generate squashed import data from missing entries.
    Tasks with the same ID on the same day will be squashed into one entry.
    Duration will be calculated based on the number of occurrences:
    - 1 task = 30 minutes
    - 2 tasks = 60 minutes
    - 3 tasks = 90 minutes
    - etc.

    Args:
        missing_entries (list): List of missing entries

    Returns:
        list: List of squashed entries ready for import
    """
    # Group entries by date and task number
    entries_by_date_task = defaultdict(lambda: defaultdict(list))

    for entry in missing_entries:
        date = get_date_from_entry(entry['date'])
        task_number = extract_task_number(entry.get('description', ''))

        if task_number:
            entries_by_date_task[date][task_number].append(entry)

    # Create squashed entries
    squashed_entries = []

    for date, tasks in entries_by_date_task.items():
        for task_number, entries in tasks.items():
            # Skip if no entries (shouldn't happen)
            if not entries:
                continue

            # Get the first entry for this task
            first_entry = entries[0]

            # Calculate duration based on number of occurrences
            # Each occurrence is 30 minutes (1800 seconds)
            duration = len(entries) * 1800

            # Create a description that includes the task number and title
            description = f"#{task_number}"
            if 'details' in first_entry and 'target' in first_entry['details']:
                description = first_entry['details']['target']

            # Create entry for Toggl import
            toggl_entry = {
                'description': description,
                'start': first_entry['date'],  # Use the date of the first entry
                'duration': duration,
                'project_name': first_entry['project'],
                'tags': ['gitlab-import', 'squashed']
            }

            squashed_entries.append(toggl_entry)

    return squashed_entries

def generate_import_json(squashed_entries, period):
    """
    Generate a clean JSON file with squashed entries ready for import to Toggl.

    Args:
        squashed_entries (list): List of squashed entries
        period (dict): Period information

    Returns:
        dict: JSON data ready for import
    """
    return {
        'period': period,
        'entries': squashed_entries
    }

def compare_entries(gitlab_file, toggl_file, output_file=None, output_format='json', comparison_mode=None, original_toggl_file=None, generate_import=False):
    """
    Compare GitLab and Toggl entries to find missing Toggl entries.

    Args:
        gitlab_file (str): Path to GitLab JSON file
        toggl_file (str): Path to Toggl JSON file
        output_file (str, optional): Path to output file. If None, prints to stdout.
        output_format (str): Output format - 'json' or 'html'. Default: 'json'
        comparison_mode (str, optional): Comparison mode - 'side-by-side'. If provided, generates a side-by-side comparison.
        original_toggl_file (str, optional): Path to original Toggl JSON file for side-by-side comparison.
        generate_import (bool): If True, generates a clean JSON file with squashed entries ready for import to Toggl.
    """
    # Ensure the result directory exists
    # Use a path relative to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    result_dir = os.path.join(script_dir, 'result')
    os.makedirs(result_dir, exist_ok=True)

    # Load JSON files
    toggl_data = load_json_file(toggl_file)

    # In side-by-side mode, we don't need GitLab data
    if comparison_mode == 'side-by-side':
        gitlab_data = {"events": [], "period": {}}

        # Check if there's a missing entries JSON file in the result folder
        missing_entries_file = os.path.join(result_dir, 'missing_entries.json')
        if os.path.exists(missing_entries_file):
            try:
                # Load the missing entries JSON file
                missing_entries_data = load_json_file(missing_entries_file)

                # Extract the toggl_import_data from the JSON file
                toggl_import_data = missing_entries_data.get('toggl_import_data', [])

                # Convert the toggl_import_data to Toggl entries format
                for import_entry in toggl_import_data:
                    # Create a new entry in the Toggl data format
                    new_entry = {
                        'id': f"import_{len(toggl_data.get('entries', []))}",
                        'date': import_entry.get('start', ''),
                        'description': import_entry.get('description', ''),
                        'project': import_entry.get('project_name', 'No Project'),
                        'duration': import_entry.get('duration', 0) / 3600,  # Convert seconds to hours
                        'duration_formatted': f"{int(import_entry.get('duration', 0) / 3600)}h {int((import_entry.get('duration', 0) % 3600) / 60)}m",
                        'tags': import_entry.get('tags', [])
                    }

                    # Add the new entry to the Toggl data
                    toggl_data.setdefault('entries', []).append(new_entry)

                print(f"Added {len(toggl_import_data)} missing entries from {missing_entries_file}")
            except Exception as e:
                print(f"Error loading missing entries from {missing_entries_file}: {str(e)}")
    else:
        gitlab_data = load_json_file(gitlab_file)

    # Group GitLab events by date
    gitlab_events_by_date = defaultdict(list)
    for event in gitlab_data.get('events', []):
        date = get_date_from_entry(event.get('date', ''))
        task_number = None

        # Try to extract task number from target field
        if 'details' in event and 'target' in event['details']:
            task_number = extract_task_number(event['details']['target'])

        # If no task number found, skip this event
        if not task_number:
            continue

        gitlab_events_by_date[date].append({
            'date': event.get('date', ''),
            'action': event.get('action', ''),
            'project': event.get('project', ''),
            'task_number': task_number,
            'details': event.get('details', {})
        })

    # Group Toggl entries by date
    toggl_entries_by_date = defaultdict(list)
    all_toggl_entries = []  # Keep track of all Toggl entries

    for entry in toggl_data.get('entries', []):
        date = get_date_from_entry(entry.get('date', ''))
        task_number = extract_task_number(entry.get('description', ''))

        # Create a standardized entry
        toggl_entry = {
            'date': entry.get('date', ''),
            'description': entry.get('description', ''),
            'project': entry.get('project', ''),
            'task_number': task_number,
            'duration': entry.get('duration', 0),
            'duration_formatted': entry.get('duration_formatted', '')
        }

        # Add to all entries list
        all_toggl_entries.append(toggl_entry)

        # If it has a task number, add it to the date-based dictionary for matching
        if task_number:
            toggl_entries_by_date[date].append(toggl_entry)

    # Find missing, matched, and Toggl-only entries
    missing_entries = []
    matched_entries = []
    toggl_only_entries = []

    # Track which Toggl entries have been matched
    matched_toggl_entries = set()

    # First, process GitLab events and find missing/matched entries
    for date, gitlab_events in gitlab_events_by_date.items():
        toggl_entries = toggl_entries_by_date.get(date, [])

        # Get all task numbers logged in Toggl for this date
        toggl_task_numbers = set(entry['task_number'] for entry in toggl_entries)

        # Process each GitLab event
        for event in gitlab_events:
            # Create a base entry
            entry = {
                'date': event['date'],
                'description': f"#{event['task_number']}",
                'project': event['project'],
                'action': event['action'],
                'details': event['details']
            }

            # Check if this task is already logged in Toggl
            if event['task_number'] in toggl_task_numbers:
                # It's a matched entry
                matched_entries.append(entry)

                # Mark this task number as matched for this date
                for toggl_entry in toggl_entries:
                    if toggl_entry['task_number'] == event['task_number']:
                        matched_toggl_entries.add((date, toggl_entry['task_number'], toggl_entry['date']))
            else:
                # It's a missing entry
                missing_entries.append(entry)

    # Now find Toggl-only entries (entries in Toggl that don't have corresponding GitLab activities)
    for toggl_entry in all_toggl_entries:
        date = get_date_from_entry(toggl_entry['date'])

        # If this entry has no task number or its task number wasn't matched with GitLab
        if not toggl_entry['task_number'] or (date, toggl_entry['task_number'], toggl_entry['date']) not in matched_toggl_entries:
            # Create a Toggl-only entry
            entry = {
                'date': toggl_entry['date'],
                'description': toggl_entry['description'],
                'project': toggl_entry['project'],
                'duration': toggl_entry['duration'],
                'duration_formatted': toggl_entry['duration_formatted'],
                'action': 'Toggl Entry'  # To be consistent with GitLab entries that have an action
            }
            toggl_only_entries.append(entry)

    # Prepare output
    output_data = {
        'gitlab_period': gitlab_data.get('period', {}),
        'toggl_period': toggl_data.get('period', {}),
        'missing_entries': missing_entries,
        'matched_entries': matched_entries,
        'toggl_only_entries': toggl_only_entries
    }

    # Format output for Toggl import
    toggl_import_data = []
    for entry in missing_entries:
        # Create a description that includes the task number and action
        description = entry['description']
        if 'target' in entry['details'] and entry['details']['target']:
            description = entry['details']['target']

        # Default duration (30 minutes)
        duration = 30 * 60

        # Create entry for Toggl import
        toggl_entry = {
            'description': description,
            'start': entry['date'],
            'duration': duration,
            'project_name': entry['project'],
            'tags': ['gitlab-import', entry['action'].lower().replace(' ', '-')]
        }
        toggl_import_data.append(toggl_entry)

    # Final output
    final_output = {
        'summary': {
            'gitlab_period': gitlab_data.get('period', {}),
            'toggl_period': toggl_data.get('period', {}),
            'total_gitlab_events': len(gitlab_data.get('events', [])),
            'total_toggl_entries': len(toggl_data.get('entries', [])),
            'matched_entries_count': len(matched_entries),
            'missing_entries_count': len(missing_entries),
            'toggl_only_entries_count': len(toggl_only_entries)
        },
        'matched_entries': matched_entries,
        'missing_entries': missing_entries,
        'toggl_only_entries': toggl_only_entries,
        'toggl_import_data': toggl_import_data
    }

    # Generate import file if requested
    if generate_import:
        # Generate squashed import data
        squashed_entries = generate_squashed_import_data(missing_entries)

        # Generate import JSON
        import_data = generate_import_json(squashed_entries, {
            'start': gitlab_data.get('period', {}).get('start', ''),
            'end': gitlab_data.get('period', {}).get('end', '')
        })

        # Determine output file path for import data
        import_file = os.path.join(result_dir, 'toggl_import.json')

        # Write to file
        with open(import_file, 'w') as f:
            json.dump(import_data, f, indent=2)
        print(f"Import data written to {import_file}")

    # Handle side-by-side comparison mode
    if comparison_mode == 'side-by-side' and original_toggl_file:
        # Load original Toggl data
        original_toggl_data = load_json_file(original_toggl_file)

        # Generate side-by-side HTML
        html_content = generate_side_by_side_html(original_toggl_data, toggl_data)

        # Determine output file path
        if not output_file:
            output_file = os.path.join(result_dir, 'toggl_comparison.html')
        elif not os.path.isabs(output_file):
            # If not an absolute path, save to result directory
            output_file = os.path.join(result_dir, os.path.basename(output_file))

        # Write to file
        with open(output_file, 'w') as f:
            f.write(html_content)
        print(f"Side-by-side comparison written to {output_file}")
        return

    # Standard output handling
    if output_format.lower() == 'html':
        # Generate HTML output
        html_content = generate_html_output(final_output)

        # Determine output file path
        if not output_file:
            output_file = os.path.join(result_dir, 'missing_entries.html')
        elif not os.path.isabs(output_file):
            # If not an absolute path, save to result directory
            output_file = os.path.join(result_dir, os.path.basename(output_file))

        # Write to file
        with open(output_file, 'w') as f:
            f.write(html_content)
        print(f"HTML results written to {output_file}")
    else:
        # Default to JSON output
        if output_file:
            # Determine output file path
            if not os.path.isabs(output_file):
                # If not an absolute path, save to result directory
                output_file = os.path.join(result_dir, os.path.basename(output_file))

            # Write to file
            with open(output_file, 'w') as f:
                json.dump(final_output, f, indent=2)
            print(f"JSON results written to {output_file}")
        else:
            print(json.dumps(final_output, indent=2))

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description='Compare GitLab and Toggl entries to find missing Toggl entries.')

    # Create subparsers for different modes
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')

    # Parser for standard comparison mode
    compare_parser = subparsers.add_parser('compare', help='Compare GitLab and Toggl entries')
    compare_parser.add_argument('gitlab_file',
                        help='Path to GitLab JSON file')
    compare_parser.add_argument('toggl_file',
                        help='Path to Toggl JSON file')
    compare_parser.add_argument('--output', '-o',
                        help='Path to output file. If not provided, saves to compare/result directory.')
    compare_parser.add_argument('--format', '-f',
                        choices=['json', 'html'],
                        default='html',
                        help='Output format. Default: html')
    compare_parser.add_argument('--generate-import', '-g',
                        action='store_true',
                        help='Generate a clean JSON file with squashed entries ready for import to Toggl.')

    # Parser for side-by-side comparison mode
    side_by_side_parser = subparsers.add_parser('side-by-side', help='Generate side-by-side comparison of original and updated Toggl records')
    side_by_side_parser.add_argument('original_toggl_file',
                        help='Path to original Toggl JSON file')
    side_by_side_parser.add_argument('updated_toggl_file',
                        help='Path to updated Toggl JSON file')
    side_by_side_parser.add_argument('--output', '-o',
                        help='Path to output file. If not provided, saves to bin/compare/result/toggl_comparison.html')

    # For backward compatibility, also accept positional arguments directly
    parser.add_argument('gitlab_file_pos', nargs='?',
                        help='Path to GitLab JSON file (for backward compatibility)')
    parser.add_argument('toggl_file_pos', nargs='?',
                        help='Path to Toggl JSON file (for backward compatibility)')
    parser.add_argument('--output-pos', '-op', dest='output_pos',
                        help='Path to output file (for backward compatibility)')
    parser.add_argument('--format-pos', '-fp', dest='format_pos',
                        choices=['json', 'html'],
                        help='Output format (for backward compatibility)')

    args = parser.parse_args()

    # Handle side-by-side comparison mode
    if args.mode == 'side-by-side':
        compare_entries(
            gitlab_file=None,  # Not used in side-by-side mode
            toggl_file=args.updated_toggl_file,
            output_file=args.output,
            output_format='html',
            comparison_mode='side-by-side',
            original_toggl_file=args.original_toggl_file
        )
    # Handle standard comparison mode
    elif args.mode == 'compare':
        compare_entries(
            gitlab_file=args.gitlab_file,
            toggl_file=args.toggl_file,
            output_file=args.output,
            output_format=args.format,
            generate_import=args.generate_import
        )
    # Handle backward compatibility
    elif args.gitlab_file_pos and args.toggl_file_pos:
        compare_entries(
            gitlab_file=args.gitlab_file_pos,
            toggl_file=args.toggl_file_pos,
            output_file=args.output_pos,
            output_format=args.format_pos or 'json'
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

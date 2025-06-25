#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import sys
import csv
import requests
from dateutil.relativedelta import relativedelta
from base64 import b64encode

# Import authentication details from auth.py
try:
    from auth import TOGGL_API_TOKEN, TOGGL_WORKSPACE_ID
except ImportError:
    # If running from a different directory, try with full path
    try:
        from toggle.auth import TOGGL_API_TOKEN, TOGGL_WORKSPACE_ID
    except ImportError:
        # Default values if auth.py cannot be imported
        TOGGL_API_TOKEN = None
        TOGGL_WORKSPACE_ID = None

# Toggl API endpoints
TOGGL_API_URL = "https://api.track.toggl.com/api/v9"

def get_auth_header(api_token):
    """Generate the authorization header for Toggl API."""
    auth_string = f"{api_token}:api_token"
    return {
        "Authorization": f"Basic {b64encode(auth_string.encode()).decode('ascii')}"
    }

def get_toggl_activity(api_token=None, workspace_id=None,
                      current_month=False, previous_month=False,
                      output_format="text", output_file=None):
    """
    Fetch time entries from Toggl for a specified time period.

    Args:
        api_token (str): Toggl API token. If None, will try to use value from auth.py.
        workspace_id (str): Toggl workspace ID. If None, will try to use value from auth.py.
        current_month (bool): If True, show only the current month's activity.
        previous_month (bool): If True, show only the previous month's activity.
        output_format (str): Output format - 'text', 'json', or 'csv'.
        output_file (str): Path to output file. If None, prints to stdout.
    """
    # Use values from auth.py if not provided
    if api_token is None:
        api_token = TOGGL_API_TOKEN or os.environ.get('TOGGL_API_TOKEN')

    if workspace_id is None:
        workspace_id = TOGGL_WORKSPACE_ID or os.environ.get('TOGGL_WORKSPACE_ID')

    if not api_token:
        print("Error: Toggl API token not provided.")
        print("Please provide a token as an argument, set it in auth.py, or set the TOGGL_API_TOKEN environment variable.")
        sys.exit(1)

    if not workspace_id:
        print("Error: Toggl workspace ID not provided.")
        print("Please provide a workspace ID as an argument, set it in auth.py, or set the TOGGL_WORKSPACE_ID environment variable.")
        sys.exit(1)

    # Calculate date range based on input parameters
    now = datetime.datetime.now(datetime.timezone.utc)

    if current_month:
        # Set to the first day of the current month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif previous_month:
        # Set to the first day of the previous month
        start_date = (now.replace(day=1) - relativedelta(months=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        # Set to the last day of the previous month
        end_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - relativedelta(microseconds=1)
    else:
        # Default to current month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now

    # Format dates for Toggl API
    start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    end_date_str = end_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    # Prepare request headers
    headers = get_auth_header(api_token)
    headers["Content-Type"] = "application/json"

    try:
        # Get user info
        user_response = requests.get(f"{TOGGL_API_URL}/me", headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()

        # Get time entries
        entries_url = f"{TOGGL_API_URL}/me/time_entries"
        params = {
            "start_date": start_date_str,
            "end_date": end_date_str
        }

        entries_response = requests.get(entries_url, headers=headers, params=params)
        entries_response.raise_for_status()
        time_entries = entries_response.json()

        # Get projects for reference
        projects_url = f"{TOGGL_API_URL}/workspaces/{workspace_id}/projects"
        projects_response = requests.get(projects_url, headers=headers)
        projects_response.raise_for_status()
        projects = {project["id"]: project["name"] for project in projects_response.json()}

        # Process time entries
        processed_entries = []
        total_duration = 0

        for entry in time_entries:
            start_time = datetime.datetime.fromisoformat(entry["start"].replace('Z', '+00:00'))
            formatted_start = start_time.strftime('%Y-%m-%d %H:%M:%S')

            # Calculate duration in hours
            duration = entry.get("duration", 0)
            if duration < 0:  # Running entry
                duration = (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds()

            duration_hours = duration / 3600
            total_duration += duration

            # Get project name
            project_id = entry.get("project_id")
            project_name = projects.get(project_id, "No Project") if project_id else "No Project"

            # Create entry details
            entry_details = {
                "id": entry.get("id"),
                "date": formatted_start,
                "description": entry.get("description", ""),
                "project": project_name,
                "duration": duration_hours,
                "duration_formatted": f"{int(duration_hours)}h {int((duration_hours % 1) * 60)}m",
                "tags": entry.get("tags", [])
            }

            processed_entries.append(entry_details)

        # Sort entries by date (newest first)
        processed_entries.sort(key=lambda x: x["date"], reverse=True)

        # Calculate total duration in hours and minutes
        total_hours = int(total_duration / 3600)
        total_minutes = int((total_duration % 3600) / 60)

        # Handle output based on format
        if not processed_entries:
            message = f"No time entries found from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

            if output_file:
                with open(output_file, 'w') as f:
                    f.write(message + "\n")
            else:
                print(message)
            return

        # Output handling
        if output_format == "json":
            # JSON output
            json_output = json.dumps({
                "user": user_data.get("fullname", user_data.get("email", "Unknown")),
                "period": {
                    "start": start_date.strftime('%Y-%m-%d'),
                    "end": end_date.strftime('%Y-%m-%d')
                },
                "total_duration": {
                    "hours": total_hours,
                    "minutes": total_minutes,
                    "formatted": f"{total_hours}h {total_minutes}m"
                },
                "entries": processed_entries
            }, indent=2)

            if output_file:
                with open(output_file, 'w') as f:
                    f.write(json_output)
            else:
                print(json_output)

        elif output_format == "csv":
            # CSV output
            if output_file:
                with open(output_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Date", "Description", "Project", "Duration", "Tags"])

                    for entry in processed_entries:
                        writer.writerow([
                            entry["date"],
                            entry["description"],
                            entry["project"],
                            entry["duration_formatted"],
                            ", ".join(entry["tags"])
                        ])
            else:
                writer = csv.writer(sys.stdout)
                writer.writerow(["Date", "Description", "Project", "Duration", "Tags"])

                for entry in processed_entries:
                    writer.writerow([
                        entry["date"],
                        entry["description"],
                        entry["project"],
                        entry["duration_formatted"],
                        ", ".join(entry["tags"])
                    ])

        else:
            # Text output (default)
            header = f"Toggl Time Entries for: {user_data.get('fullname', user_data.get('email', 'Unknown'))}"
            period = f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            summary = f"Total Time: {total_hours}h {total_minutes}m"

            text_output = [header, period, summary, "-" * 80]

            for entry in processed_entries:
                entry_text = f"{entry['date']} - {entry['description']} ({entry['project']})"
                duration_text = f"  Duration: {entry['duration_formatted']}"

                text_output.append(entry_text)
                text_output.append(duration_text)

                if entry["tags"]:
                    tags_text = f"  Tags: {', '.join(entry['tags'])}"
                    text_output.append(tags_text)

                text_output.append("")  # Empty line between entries

            if output_file:
                with open(output_file, 'w') as f:
                    f.write("\n".join(text_output))
            else:
                print("\n".join(text_output))

    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def add_toggl_entry(api_token=None, workspace_id=None, description="", project_id=None,
                   start_time=None, duration=None, tags=None):
    """
    Add a new time entry to Toggl.

    Args:
        api_token (str): Toggl API token. If None, will try to use value from auth.py.
        workspace_id (str): Toggl workspace ID. If None, will try to use value from auth.py.
        description (str): Description of the time entry.
        project_id (int): Project ID for the time entry.
        start_time (datetime): Start time for the entry. If None, uses current time.
        duration (int): Duration in seconds. If None, creates a running entry.
        tags (list): List of tags to apply to the entry.

    Returns:
        dict: The created time entry data.
    """
    # Use values from auth.py if not provided
    if api_token is None:
        api_token = TOGGL_API_TOKEN or os.environ.get('TOGGL_API_TOKEN')

    if workspace_id is None:
        workspace_id = TOGGL_WORKSPACE_ID or os.environ.get('TOGGL_WORKSPACE_ID')

    if not api_token:
        print("Error: Toggl API token not provided.")
        print("Please provide a token as an argument, set it in auth.py, or set the TOGGL_API_TOKEN environment variable.")
        sys.exit(1)

    if not workspace_id:
        print("Error: Toggl workspace ID not provided.")
        print("Please provide a workspace ID as an argument, set it in auth.py, or set the TOGGL_WORKSPACE_ID environment variable.")
        sys.exit(1)

    # Set default start time to now if not provided
    if start_time is None:
        start_time = datetime.datetime.now(datetime.timezone.utc)

    # Format start time for Toggl API
    start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    # Prepare request headers
    headers = get_auth_header(api_token)
    headers["Content-Type"] = "application/json"

    # Prepare request data
    entry_data = {
        "description": description,
        "start": start_time_str,
        "workspace_id": int(workspace_id),
        "created_with": "toggle_activity.py"
    }

    if project_id:
        entry_data["project_id"] = int(project_id)

    if duration:
        entry_data["duration"] = int(duration)

    if tags:
        entry_data["tags"] = tags

    try:
        # Create time entry
        entry_url = f"{TOGGL_API_URL}/workspaces/{workspace_id}/time_entries"
        response = requests.post(entry_url, headers=headers, json=entry_data)
        response.raise_for_status()

        new_entry = response.json()
        print(f"Time entry created: {description}")
        return new_entry

    except requests.exceptions.RequestException as e:
        print(f"Error creating time entry: {str(e)}")
        sys.exit(1)

def import_from_gitlab(api_token=None, workspace_id=None, import_file=None, project_id=None):
    """
    Import GitLab activity data or Toggl import data into Toggl.

    Args:
        api_token (str): Toggl API token. If None, will try to use value from auth.py.
        workspace_id (str): Toggl workspace ID. If None, will try to use value from auth.py.
        gitlab_file (str): Path to GitLab activity file or Toggl import file (JSON format).
        project_id (int): Project ID to use for imported entries.
    """
    # Use values from auth.py if not provided
    if api_token is None:
        api_token = TOGGL_API_TOKEN or os.environ.get('TOGGL_API_TOKEN')

    if workspace_id is None:
        workspace_id = TOGGL_WORKSPACE_ID or os.environ.get('TOGGL_WORKSPACE_ID')

    if not api_token:
        print("Error: Toggl API token not provided.")
        print("Please provide a token as an argument, set it in auth.py, or set the TOGGL_API_TOKEN environment variable.")
        sys.exit(1)

    if not workspace_id:
        print("Error: Toggl workspace ID not provided.")
        print("Please provide a workspace ID as an argument, set it in auth.py, or set the TOGGL_WORKSPACE_ID environment variable.")
        sys.exit(1)

    if not import_file:
        print("Error: Import file not provided.")
        print("Please provide a path to a GitLab activity file or Toggl import file in JSON format.")
        sys.exit(1)

    try:
        # Read import data
        with open(import_file, 'r') as f:
            gitlab_data = json.load(f)

        # Check if the file has the expected structure
        # It could be either GitLab activity data (with "events" key) or Toggl import data (with "entries" key)
        if not isinstance(gitlab_data, dict) or ("events" not in gitlab_data and "entries" not in gitlab_data):
            print("Error: Invalid file format.")
            print("The file should contain either GitLab activity data or Toggl import data in JSON format.")
            sys.exit(1)

        imported_count = 0

        # Check if it's a Toggl import file (has "entries" key)
        if "entries" in gitlab_data:
            entries = gitlab_data.get("entries", [])

            for entry in entries:
                # Get entry details
                description = entry.get("description", "")
                project_name = entry.get("project_name", "")

                # Skip entries without description or project
                if not description:
                    continue

                # Parse date
                start_time_str = entry.get("start", "")
                if not start_time_str:
                    continue

                try:
                    start_time = datetime.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
                    # Add timezone info
                    start_time = start_time.replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    print(f"Warning: Could not parse date: {start_time_str}")
                    continue

                # Get duration
                duration = entry.get("duration", 30 * 60)  # Default to 30 minutes if not specified

                # Get tags
                tags = entry.get("tags", ["toggl-import"])

                # Create Toggl entry
                add_toggl_entry(
                    api_token=api_token,
                    workspace_id=workspace_id,
                    description=description,
                    project_id=project_id,
                    start_time=start_time,
                    duration=duration,
                    tags=tags
                )

                imported_count += 1

        # Otherwise, it's a GitLab activity file (has "events" key)
        else:
            events = gitlab_data.get("events", [])

            for event in events:
                # Create a description based on the event
                action = event.get("action", "")
                project = event.get("project", "")

                # Skip events without action or project
                if not action or not project:
                    continue

                # Create description
                description = f"{action} in {project}"

                # Add details if available
                details = event.get("details", {})
                if "target" in details:
                    description += f" - {details['target']}"

                # Parse date
                event_date_str = event.get("date", "")
                if not event_date_str:
                    continue

                try:
                    event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d %H:%M:%S')
                    # Add timezone info
                    event_date = event_date.replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    print(f"Warning: Could not parse date: {event_date_str}")
                    continue

                # Set a default duration (30 minutes)
                duration = 30 * 60

                # Add tags
                tags = ["gitlab-import", action.lower()]

                # Create Toggl entry
                add_toggl_entry(
                    api_token=api_token,
                    workspace_id=workspace_id,
                    description=description,
                    project_id=project_id,
                    start_time=event_date,
                    duration=duration,
                    tags=tags
                )

                imported_count += 1

        print(f"Successfully imported {imported_count} entries into Toggl.")

    except FileNotFoundError:
        print(f"Error: Import file not found: {import_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in import file: {import_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error importing data: {str(e)}")
        sys.exit(1)

def list_toggl_projects(api_token=None, workspace_id=None):
    """
    List all projects in the Toggl workspace.

    Args:
        api_token (str): Toggl API token. If None, will try to use value from auth.py.
        workspace_id (str): Toggl workspace ID. If None, will try to use value from auth.py.
    """
    # Use values from auth.py if not provided
    if api_token is None:
        api_token = TOGGL_API_TOKEN or os.environ.get('TOGGL_API_TOKEN')

    if workspace_id is None:
        workspace_id = TOGGL_WORKSPACE_ID or os.environ.get('TOGGL_WORKSPACE_ID')

    if not api_token:
        print("Error: Toggl API token not provided.")
        print("Please provide a token as an argument, set it in auth.py, or set the TOGGL_API_TOKEN environment variable.")
        sys.exit(1)

    if not workspace_id:
        print("Error: Toggl workspace ID not provided.")
        print("Please provide a workspace ID as an argument, set it in auth.py, or set the TOGGL_WORKSPACE_ID environment variable.")
        sys.exit(1)

    # Prepare request headers
    headers = get_auth_header(api_token)

    try:
        # Get projects
        projects_url = f"{TOGGL_API_URL}/workspaces/{workspace_id}/projects"
        response = requests.get(projects_url, headers=headers)
        response.raise_for_status()

        projects = response.json()

        if not projects:
            print("No projects found in the workspace.")
            return

        print("Available projects:")
        print("-" * 80)

        for project in projects:
            print(f"ID: {project['id']} - Name: {project['name']}")

        print("-" * 80)
        print(f"Total projects: {len(projects)}")

    except requests.exceptions.RequestException as e:
        print(f"Error listing projects: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description='Toggl time tracking utility.')

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Parser for 'activity' command
    activity_parser = subparsers.add_parser('activity', help='Get time entries from Toggl')
    activity_parser.add_argument('--token', '-t',
                        help='Toggl API token. If not provided, will try to use value from auth.py or TOGGL_API_TOKEN environment variable.')
    activity_parser.add_argument('--workspace', '-w',
                        help='Toggl workspace ID. If not provided, will try to use value from auth.py or TOGGL_WORKSPACE_ID environment variable.')
    activity_parser.add_argument('--current-month', '-c',
                        action='store_true',
                        help='Show only the current month\'s activity.')
    activity_parser.add_argument('--previous-month', '-p',
                        action='store_true',
                        help='Show only the previous month\'s activity.')
    activity_parser.add_argument('--format', '-f',
                        choices=['text', 'json', 'csv'],
                        default='text',
                        help='Output format. Default: text')
    activity_parser.add_argument('--output', '-o',
                        help='Output file path. If not provided, prints to stdout.')

    # Parser for 'add' command
    add_parser = subparsers.add_parser('add', help='Add a new time entry to Toggl')
    add_parser.add_argument('--token', '-t',
                        help='Toggl API token. If not provided, will try to use value from auth.py or TOGGL_API_TOKEN environment variable.')
    add_parser.add_argument('--workspace', '-w',
                        help='Toggl workspace ID. If not provided, will try to use value from auth.py or TOGGL_WORKSPACE_ID environment variable.')
    add_parser.add_argument('--description', '-d',
                        required=True,
                        help='Description of the time entry.')
    add_parser.add_argument('--project', '-p',
                        type=int,
                        help='Project ID for the time entry.')
    add_parser.add_argument('--start', '-s',
                        help='Start time for the entry (format: YYYY-MM-DD HH:MM:SS). If not provided, uses current time.')
    add_parser.add_argument('--duration', '-u',
                        type=int,
                        help='Duration in seconds. If not provided, creates a running entry.')
    add_parser.add_argument('--tags', '-g',
                        help='Comma-separated list of tags to apply to the entry.')

    # Parser for 'import' command
    import_parser = subparsers.add_parser('import', help='Import GitLab activity data or Toggl import data into Toggl')
    import_parser.add_argument('--token', '-t',
                        help='Toggl API token. If not provided, will try to use value from auth.py or TOGGL_API_TOKEN environment variable.')
    import_parser.add_argument('--workspace', '-w',
                        help='Toggl workspace ID. If not provided, will try to use value from auth.py or TOGGL_WORKSPACE_ID environment variable.')
    import_parser.add_argument('--file', '-f',
                        required=True,
                        help='Path to GitLab activity file or Toggl import file (JSON format).')
    import_parser.add_argument('--project', '-p',
                        type=int,
                        help='Project ID to use for imported entries.')

    # Parser for 'projects' command
    projects_parser = subparsers.add_parser('projects', help='List all projects in the Toggl workspace')
    projects_parser.add_argument('--token', '-t',
                        help='Toggl API token. If not provided, will try to use value from auth.py or TOGGL_API_TOKEN environment variable.')
    projects_parser.add_argument('--workspace', '-w',
                        help='Toggl workspace ID. If not provided, will try to use value from auth.py or TOGGL_WORKSPACE_ID environment variable.')

    args = parser.parse_args()

    # Execute the appropriate command
    if args.command == 'activity':
        get_toggl_activity(
            api_token=args.token,
            workspace_id=args.workspace,
            current_month=args.current_month,
            previous_month=args.previous_month,
            output_format=args.format,
            output_file=args.output
        )
    elif args.command == 'add':
        # Parse start time if provided
        start_time = None
        if args.start:
            try:
                start_time = datetime.datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S')
                # Add timezone info
                start_time = start_time.replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                print(f"Error: Invalid start time format. Use YYYY-MM-DD HH:MM:SS")
                sys.exit(1)

        # Parse tags if provided
        tags = None
        if args.tags:
            tags = [tag.strip() for tag in args.tags.split(',')]

        add_toggl_entry(
            api_token=args.token,
            workspace_id=args.workspace,
            description=args.description,
            project_id=args.project,
            start_time=start_time,
            duration=args.duration,
            tags=tags
        )
    elif args.command == 'import':
        import_from_gitlab(
            api_token=args.token,
            workspace_id=args.workspace,
            import_file=args.file,
            project_id=args.project
        )
    elif args.command == 'projects':
        list_toggl_projects(
            api_token=args.token,
            workspace_id=args.workspace
        )
    else:
        parser.print_help()
        sys.exit(1)

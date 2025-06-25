#!/usr/bin/env python3

import gitlab
import datetime
import sys
import os
import argparse
import json
import csv
from dateutil.relativedelta import relativedelta

# Import authentication details from auth.py
try:
    from auth import GITLAB_URL, GITLAB_TOKEN
except ImportError:
    # If running from a different directory, try with full path
    try:
        from gitlab.auth import GITLAB_URL, GITLAB_TOKEN
    except ImportError:
        # Default values if auth.py cannot be imported
        GITLAB_URL = "https://gitlab.com"
        GITLAB_TOKEN = None

def get_gitlab_history(token=None, gitlab_url=None,
                      months=1, days=0, current_month=False, previous_month=False,
                      output_format="text", output_file=None, event_type=None):
    """
    Connect to GitLab and print user activity for a specified time period.

    Args:
        token (str): GitLab personal access token. If None, will try to use values from auth.py or environment variable.
        gitlab_url (str): GitLab instance URL. If None, will try to use value from auth.py.
        months (int): Number of months to look back.
        days (int): Number of days to look back (in addition to months).
        current_month (bool): If True, show only the current month's activity.
        previous_month (bool): If True, show only the previous month's activity.
        output_format (str): Output format - 'text', 'json', or 'csv'.
        output_file (str): Path to output file. If None, prints to stdout.
        event_type (str): Filter by event type (e.g., 'pushed', 'commented').
    """
    # Use values from auth.py if not provided
    if gitlab_url is None:
        gitlab_url = GITLAB_URL

    # Get token from auth.py or environment variable if not provided
    if not token:
        token = GITLAB_TOKEN or os.environ.get('GITLAB_TOKEN')

    if not token:
        print("Error: GitLab token not provided.")
        print("Please provide a token as an argument, set it in auth.py, or set the GITLAB_TOKEN environment variable.")
        print("You can create a personal access token at: {}/profile/personal_access_tokens".format(gitlab_url))
        sys.exit(1)

    try:
        # Connect to GitLab
        gl = gitlab.Gitlab(gitlab_url, private_token=token)
        gl.auth()

        # Get current user
        user = gl.user

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
            # Use the specified months and days
            end_date = now
            start_date = end_date - relativedelta(months=months, days=days)

        # Get events for the current user
        events = gl.events.list(all=True)

        # Filter events by date and event type
        filtered_events = []
        for e in events:
            event_date = datetime.datetime.fromisoformat(e.created_at.replace('Z', '+00:00'))

            # Check if event is within date range
            if start_date <= event_date <= end_date:
                # Check if event matches the event type filter (if provided)
                if event_type is None or event_type.lower() in e.action_name.lower():
                    filtered_events.append(e)

        # Sort events by date (newest first)
        filtered_events.sort(key=lambda x: x.created_at, reverse=True)

        # Prepare output data
        output_data = []

        for event in filtered_events:
            event_date = datetime.datetime.fromisoformat(event.created_at.replace('Z', '+00:00'))
            formatted_date = event_date.strftime('%Y-%m-%d %H:%M:%S')
            action_text = event.action_name.replace('_', ' ').title()

            # Get project name
            project_name = "Unknown Project"
            if hasattr(event, 'project_id'):
                try:
                    project = gl.projects.get(event.project_id)
                    project_name = project.name
                except:
                    project_name = f"Project ID: {event.project_id}"

            # Collect event details
            event_details = {
                "date": formatted_date,
                "action": action_text,
                "project": project_name,
                "details": {}
            }

            # Add additional details
            if hasattr(event, 'target_title'):
                event_details["details"]["target"] = event.target_title

            if hasattr(event, 'push_data') and event.push_data:
                if 'commit_count' in event.push_data and event.push_data['commit_count']:
                    event_details["details"]["commits"] = event.push_data['commit_count']
                if 'ref' in event.push_data:
                    event_details["details"]["branch"] = event.push_data['ref']

            output_data.append(event_details)

        # Handle output based on format
        if not output_data:
            message = f"No activity found from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            if event_type:
                message += f" for event type: {event_type}"

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
                "user": user.username,
                "name": user.name,
                "period": {
                    "start": start_date.strftime('%Y-%m-%d'),
                    "end": end_date.strftime('%Y-%m-%d')
                },
                "events": output_data
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
                    writer.writerow(["Date", "Action", "Project", "Target", "Commits", "Branch"])

                    for event in output_data:
                        writer.writerow([
                            event["date"],
                            event["action"],
                            event["project"],
                            event["details"].get("target", ""),
                            event["details"].get("commits", ""),
                            event["details"].get("branch", "")
                        ])
            else:
                writer = csv.writer(sys.stdout)
                writer.writerow(["Date", "Action", "Project", "Target", "Commits", "Branch"])

                for event in output_data:
                    writer.writerow([
                        event["date"],
                        event["action"],
                        event["project"],
                        event["details"].get("target", ""),
                        event["details"].get("commits", ""),
                        event["details"].get("branch", "")
                    ])

        else:
            # Text output (default)
            header = f"GitLab Activity for: {user.username} ({user.name})"
            period = f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

            if event_type:
                period += f" (Filtered by: {event_type})"

            text_output = [header, period, "-" * 80]

            for event in output_data:
                event_text = f"{event['date']} - {event['action']} - {event['project']}"
                text_output.append(event_text)

                for key, value in event["details"].items():
                    text_output.append(f"  {key.title()}: {value}")

                text_output.append("")  # Empty line between events

            if output_file:
                with open(output_file, 'w') as f:
                    f.write("\n".join(text_output))
            else:
                print("\n".join(text_output))

    except gitlab.exceptions.GitlabAuthenticationError:
        print("Authentication failed. Please check your token.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description='Fetch and display GitLab user activity history.')

    parser.add_argument('--token', '-t',
                        help='GitLab personal access token. If not provided, will try to use value from auth.py or GITLAB_TOKEN environment variable.')

    parser.add_argument('--url', '-u',
                        help='GitLab instance URL. If not provided, will try to use value from auth.py or default to https://gitlab.com')

    parser.add_argument('--months', '-m',
                        type=int,
                        default=1,
                        help='Number of months to look back. Default: 1')

    parser.add_argument('--days', '-d',
                        type=int,
                        default=0,
                        help='Additional number of days to look back. Default: 0')

    parser.add_argument('--format', '-f',
                        choices=['text', 'json', 'csv'],
                        default='text',
                        help='Output format. Default: text')

    parser.add_argument('--output', '-o',
                        help='Output file path. If not provided, prints to stdout.')

    parser.add_argument('--event-type', '-e',
                        help='Filter by event type (e.g., pushed, commented).')

    parser.add_argument('--current-month', '-c',
                        action='store_true',
                        help='Show only the current month\'s activity.')

    parser.add_argument('--previous-month', '-p',
                        action='store_true',
                        help='Show only the previous month\'s activity.')

    # For backward compatibility
    parser.add_argument('token_pos', nargs='?',
                        help='GitLab token (positional argument for backward compatibility)')

    parser.add_argument('url_pos', nargs='?',
                        help='GitLab URL (positional argument for backward compatibility)')

    args = parser.parse_args()

    # Handle backward compatibility with positional arguments
    token = args.token or args.token_pos
    gitlab_url = args.url or args.url_pos

    get_gitlab_history(
        token=token,
        gitlab_url=gitlab_url,
        months=args.months,
        days=args.days,
        current_month=args.current_month,
        previous_month=args.previous_month,
        output_format=args.format,
        output_file=args.output,
        event_type=args.event_type
    )

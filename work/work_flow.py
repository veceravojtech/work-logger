#!/usr/bin/env python3

import os
import sys
import subprocess
import json
import time

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"{title.center(80)}")
    print("=" * 80 + "\n")

def get_user_choice(prompt, options):
    """
    Get user choice from a list of options.

    Args:
        prompt (str): The prompt to display to the user.
        options (list): List of options to choose from.

    Returns:
        int: The index of the selected option.
    """
    print(prompt)
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")

    while True:
        try:
            choice = int(input("\nEnter your choice (number): "))
            if 1 <= choice <= len(options):
                return choice
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(options)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def run_command(command, success_message=None, error_message=None):
    """
    Run a shell command and handle the output.

    Args:
        command (list): The command to run as a list of arguments.
        success_message (str, optional): Message to display on success.
        error_message (str, optional): Message to display on error.

    Returns:
        bool: True if the command succeeded, False otherwise.
        str: The command output.
    """
    print(f"Running command: {' '.join(command)}")
    print("-" * 80)

    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        output = result.stdout

        if output:
            print(output[:500])  # Print first 500 characters of output
            if len(output) > 500:
                print("... (output truncated)")

        if success_message:
            print(f"\n✅ {success_message}")

        return True, output
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stdout:
            print("Output:")
            print(e.stdout)
        if e.stderr:
            print("Error output:")
            print(e.stderr)

        if error_message:
            print(f"\n❌ {error_message}")

        return False, e.stdout if e.stdout else ""

def run_workflow():
    """Run the workflow operations."""
    # Define paths
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gitlab_script = os.path.join(script_dir, "gitlab/gitlab_history.py")
    toggl_script = os.path.join(script_dir, "toggle/toggle_activity.py")
    compare_script = os.path.join(script_dir, "compare/compare_gitlab_toggl.py")
    redmine_script = os.path.join(script_dir, "redmine/redmine_worklogs.py")

    # Step 1: Ask for current or previous month
    month_choice = get_user_choice(
        "Select the month for data processing:",
        ["Current month", "Previous month", "Return to Main Menu"]
    )

    # Return to main menu if requested
    if month_choice == 3:
        return

    month_flag = "--current-month" if month_choice == 1 else "--previous-month"
    month_name = "current" if month_choice == 1 else "previous"

    # Step 2: Ask whether to run GitLab or Toggl script
    script_choice = get_user_choice(
        "Select the script to run:",
        [
            "GitLab history",
            "Toggl activity",
            "All (Redmine + GitLab + Toggl)",
            "Compare only",
            "Import JSON",
            "Assign Previo project to unassigned Toggl entries",
            "Round Toggl time entries to clean intervals",
            "Trim Toggl descriptions (keep only task numbers)",
            "Return to Main Menu"
        ]
    )

    # Return to main menu if requested
    if script_choice == 9:
        return

    gitlab_output_file = os.path.join(script_dir, f"gitlab/gitlab_{month_name}_month.json")
    toggl_output_file = os.path.join(script_dir, f"toggle/toggl_{month_name}_month.json")
    redmine_output_file = os.path.join(script_dir, f"redmine/redmine_{month_name}_month.json")

    # Step 3: Run the selected script(s)
    if script_choice == 5:  # Import JSON
        print_header("Importing JSON Data to Toggl")

        import_file = os.path.join(script_dir, "compare/result/toggl_import.json")

        # Check if the import file exists
        if not os.path.exists(import_file):
            print(f"Error: Import file not found: {import_file}")
            print("Please run the comparison script first to generate the import file.")
            input("\nPress Enter to return to main menu...")
            return

        # Check if the import file has entries
        try:
            with open(import_file, 'r') as f:
                import_data = json.load(f)
                entries = import_data.get('entries', [])

            if not entries:
                print("No entries to import. Returning to main menu.")
                input("\nPress Enter to return to main menu...")
                return
            else:
                print(f"Found {len(entries)} entries to import.")

                # Get project ID (optional)
                print("\nAvailable projects:")
                projects_command = [
                    "python3", toggl_script,
                    "projects"
                ]

                run_command(projects_command)

                project_id = input("\nEnter project ID to use for import (leave empty to use project from import file): ")

                import_command = [
                    "python3", toggl_script,
                    "import",
                    "--file", import_file
                ]

                if project_id:
                    import_command.extend(["--project", project_id])

                success, _ = run_command(
                    import_command,
                    success_message="Data imported to Toggl successfully",
                    error_message="Failed to import data to Toggl"
                )

                if success:
                    print("\n🎉 Workflow completed successfully!")
                else:
                    print("\n❌ Workflow completed with errors during import.")
                
                input("\nPress Enter to return to main menu...")

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading import file: {e}")
            input("\nPress Enter to return to main menu...")
            return

    elif script_choice == 6:  # Assign Previo project to unassigned Toggl entries
        print_header("Assigning Previo Project to Unassigned Toggl Entries")

        # Import required modules
        try:
            import sys
            import datetime
            sys.path.insert(0, os.path.join(script_dir, "toggle"))
            from auth import TOGGL_API_TOKEN, TOGGL_WORKSPACE_ID
            import requests
            from base64 import b64encode
        except ImportError as e:
            print(f"Error: Could not import required modules: {e}")
            input("\nPress Enter to return to main menu...")
            return

        api_token = TOGGL_API_TOKEN
        workspace_id = TOGGL_WORKSPACE_ID
        previo_project_id = 203219153

        # Auth header
        auth_string = f'{api_token}:api_token'
        headers = {
            'Authorization': f'Basic {b64encode(auth_string.encode()).decode("ascii")}',
            'Content-Type': 'application/json'
        }

        try:
            # Get all time entries from selected month
            now = datetime.datetime.now(datetime.timezone.utc)
            if month_choice == 1:  # Current month
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end = now
            else:  # Previous month
                start = (now.replace(day=1) - datetime.timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(microseconds=1)

            params = {
                'start_date': start.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'end_date': end.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            }

            print(f"Fetching time entries from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}...")
            r = requests.get('https://api.track.toggl.com/api/v9/me/time_entries', headers=headers, params=params)
            r.raise_for_status()
            entries = r.json()

            # Find entries without a project
            unassigned = [e for e in entries if not e.get('project_id')]

            print(f'Total entries: {len(entries)}')
            print(f'Unassigned entries: {len(unassigned)}')
            print()

            if unassigned:
                confirm = input(f"Do you want to assign 'Previo' project to {len(unassigned)} unassigned entries? (y/n): ")

                if confirm.lower() == 'y':
                    print('Updating unassigned entries...')
                    updated_count = 0
                    failed_count = 0

                    for entry in unassigned:
                        entry_id = entry['id']
                        description = entry.get('description', 'No description')

                        # Update entry with project
                        update_url = f'https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries/{entry_id}'
                        update_data = {'project_id': previo_project_id}

                        update_r = requests.put(update_url, headers=headers, json=update_data)

                        if update_r.status_code == 200:
                            print(f'  ✓ Updated: {description[:50]}')
                            updated_count += 1
                        else:
                            print(f'  ✗ Failed: {description[:50]} - {update_r.status_code}')
                            failed_count += 1

                    print()
                    if failed_count == 0:
                        print(f'✅ Successfully updated {updated_count} entries with project "Previo"')
                    else:
                        print(f'⚠️  Updated {updated_count} entries, {failed_count} failed')
                else:
                    print("Operation cancelled.")
            else:
                print('✅ All entries already have a project assigned.')

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Toggl API: {e}")
        except Exception as e:
            print(f"Error: {e}")

        input("\nPress Enter to return to main menu...")
        return

    elif script_choice == 7:  # Round Toggl time entries
        print_header("Rounding Toggl Time Entries to Clean Intervals")

        # Import required modules
        try:
            import sys
            import math
            import datetime
            sys.path.insert(0, os.path.join(script_dir, "toggle"))
            from auth import TOGGL_API_TOKEN, TOGGL_WORKSPACE_ID
            import requests
            from base64 import b64encode
        except ImportError as e:
            print(f"Error: Could not import required modules: {e}")
            input("\nPress Enter to return to main menu...")
            return

        def round_duration_seconds(seconds):
            """Round duration to clean intervals."""
            minutes = seconds / 60
            if minutes < 5:
                return 5 * 60
            else:
                rounded_minutes = math.ceil(minutes / 15) * 15
                return int(rounded_minutes * 60)

        def format_duration(seconds):
            """Format duration in hours and minutes."""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"

        api_token = TOGGL_API_TOKEN
        workspace_id = TOGGL_WORKSPACE_ID

        auth_string = f'{api_token}:api_token'
        headers = {
            'Authorization': f'Basic {b64encode(auth_string.encode()).decode("ascii")}',
            'Content-Type': 'application/json'
        }

        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            if month_choice == 1:
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end = now
            else:
                start = (now.replace(day=1) - datetime.timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(microseconds=1)

            params = {
                'start_date': start.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'end_date': end.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            }

            print(f"Fetching time entries from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}...")
            r = requests.get('https://api.track.toggl.com/api/v9/me/time_entries', headers=headers, params=params)
            r.raise_for_status()
            entries = r.json()

            entries_to_round = []
            for entry in entries:
                current_duration = entry.get('duration', 0)
                if current_duration < 0:
                    continue

                rounded_duration = round_duration_seconds(current_duration)
                if current_duration != rounded_duration:
                    entries_to_round.append({
                        'entry': entry,
                        'current_duration': current_duration,
                        'rounded_duration': rounded_duration
                    })

            print(f'Total entries: {len(entries)}')
            print(f'Entries needing rounding: {len(entries_to_round)}')
            print()

            if entries_to_round:
                print("Preview of changes (first 10):")
                for i, item in enumerate(entries_to_round[:10]):
                    entry = item['entry']
                    description = entry.get('description', 'No description')[:40]
                    current = format_duration(item['current_duration'])
                    rounded = format_duration(item['rounded_duration'])
                    print(f"  {description:40} | {current:10} → {rounded:10}")

                if len(entries_to_round) > 10:
                    print(f"  ... and {len(entries_to_round) - 10} more")
                print()

                confirm = input(f"Do you want to round {len(entries_to_round)} entries? (y/n): ")

                if confirm.lower() == 'y':
                    print('Rounding time entries...')
                    updated_count = 0
                    failed_count = 0

                    for item in entries_to_round:
                        entry = item['entry']
                        entry_id = entry['id']

                        update_url = f'https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries/{entry_id}'
                        update_data = {'duration': item['rounded_duration']}

                        update_r = requests.put(update_url, headers=headers, json=update_data)

                        if update_r.status_code == 200:
                            updated_count += 1
                        else:
                            description = entry.get('description', 'No description')[:40]
                            print(f'  ✗ Failed: {description} - {update_r.status_code}')
                            failed_count += 1

                    print()
                    if failed_count == 0:
                        print(f'✅ Successfully rounded {updated_count} entries')
                    else:
                        print(f'⚠️  Rounded {updated_count} entries, {failed_count} failed')
                else:
                    print("Operation cancelled.")
            else:
                print('✅ All entries are already rounded to clean intervals.')

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Toggl API: {e}")
        except Exception as e:
            print(f"Error: {e}")

        input("\nPress Enter to return to main menu...")
        return

    elif script_choice == 8:  # Trim Toggl descriptions
        print_header("Trimming Toggl Descriptions")

        # Import required modules
        try:
            import sys
            import re
            import datetime
            sys.path.insert(0, os.path.join(script_dir, "toggle"))
            from auth import TOGGL_API_TOKEN, TOGGL_WORKSPACE_ID
            import requests
            from base64 import b64encode
        except ImportError as e:
            print(f"Error: Could not import required modules: {e}")
            input("\nPress Enter to return to main menu...")
            return

        def should_trim_description(description):
            """Check if description should be trimmed."""
            if not description:
                return False, description

            # Pattern for task number with optional prefix
            task_pattern = r'^(?:[A-Za-z]+:\s*)?(#\d+)[\s:.-]+'
            match = re.match(task_pattern, description)

            if match:
                task_number = match.group(1)
                remaining = description[len(match.group(0)):]

                if remaining.strip():
                    return True, task_number

            return False, description

        api_token = TOGGL_API_TOKEN
        workspace_id = TOGGL_WORKSPACE_ID

        auth_string = f'{api_token}:api_token'
        headers = {
            'Authorization': f'Basic {b64encode(auth_string.encode()).decode("ascii")}',
            'Content-Type': 'application/json'
        }

        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            if month_choice == 1:
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end = now
            else:
                start = (now.replace(day=1) - datetime.timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(microseconds=1)

            params = {
                'start_date': start.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'end_date': end.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            }

            print(f"Fetching time entries from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}...")
            r = requests.get('https://api.track.toggl.com/api/v9/me/time_entries', headers=headers, params=params)
            r.raise_for_status()
            entries = r.json()

            entries_to_trim = []
            for entry in entries:
                description = entry.get('description', '')
                should_trim, trimmed = should_trim_description(description)

                if should_trim:
                    entries_to_trim.append({
                        'entry': entry,
                        'current_description': description,
                        'trimmed_description': trimmed
                    })

            print(f'Total entries: {len(entries)}')
            print(f'Entries needing trimming: {len(entries_to_trim)}')
            print()

            if entries_to_trim:
                print("Preview of changes (first 15):")
                for i, item in enumerate(entries_to_trim[:15]):
                    current = item['current_description'][:60]
                    trimmed = item['trimmed_description'][:30]
                    print(f"  {current:60} → {trimmed}")

                if len(entries_to_trim) > 15:
                    print(f"  ... and {len(entries_to_trim) - 15} more")
                print()

                confirm = input(f"Do you want to trim {len(entries_to_trim)} descriptions? (y/n): ")

                if confirm.lower() == 'y':
                    print('Trimming descriptions...')
                    updated_count = 0
                    failed_count = 0

                    for item in entries_to_trim:
                        entry = item['entry']
                        entry_id = entry['id']

                        update_url = f'https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries/{entry_id}'
                        update_data = {'description': item['trimmed_description']}

                        update_r = requests.put(update_url, headers=headers, json=update_data)

                        if update_r.status_code == 200:
                            updated_count += 1
                        else:
                            current = item['current_description'][:40]
                            print(f'  ✗ Failed: {current} - {update_r.status_code}')
                            failed_count += 1

                    print()
                    if failed_count == 0:
                        print(f'✅ Successfully trimmed {updated_count} descriptions')
                    else:
                        print(f'⚠️  Trimmed {updated_count} descriptions, {failed_count} failed')
                else:
                    print("Operation cancelled.")
            else:
                print('✅ All descriptions are already clean.')

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Toggl API: {e}")
        except Exception as e:
            print(f"Error: {e}")

        input("\nPress Enter to return to main menu...")
        return

    elif script_choice == 4:  # Compare only
        print_header("Running Comparison Script")

        # Check if both GitLab and Toggl output files exist
        if not os.path.exists(gitlab_output_file):
            print(f"Error: GitLab output file not found: {gitlab_output_file}")
            print("Please run the GitLab history script first to generate the output file.")
            input("\nPress Enter to return to main menu...")
            return

        if not os.path.exists(toggl_output_file):
            print(f"Error: Toggl output file not found: {toggl_output_file}")
            print("Please run the Toggl activity script first to generate the output file.")
            input("\nPress Enter to return to main menu...")
            return

        # Run comparison script
        compare_command = [
            "python3", compare_script,
            "compare",
            gitlab_output_file,
            toggl_output_file,
            "--generate-import"
        ]

        success, _ = run_command(
            compare_command,
            success_message="Comparison completed successfully",
            error_message="Failed to compare GitLab and Toggl data"
        )

        if not success:
            print("Comparison script failed.")
            input("\nPress Enter to return to main menu...")
            return

        # Check for entries to import and wait for confirmation
        print("\nComparison results are available in the following files:")
        print(f"- HTML report: {os.path.join(script_dir, 'compare/result/missing_entries.html')}")
        print(f"- Import data: {os.path.join(script_dir, 'compare/result/toggl_import.json')}")

        import_file = os.path.join(script_dir, "compare/result/toggl_import.json")

        # Check if the import file exists and has entries
        try:
            with open(import_file, 'r') as f:
                import_data = json.load(f)
                entries = import_data.get('entries', [])

            if not entries:
                print("\nNo entries to import. Skipping import step.")
            else:
                print(f"\nFound {len(entries)} entries to import.")

                confirm = input("\nDo you want to import the missing entries to Toggl? (y/n): ")

                if confirm.lower() == 'y':
                    # Import data to Toggl
                    print_header("Importing Data to Toggl")

                    # Get project ID (optional)
                    print("\nAvailable projects:")
                    projects_command = [
                        "python3", toggl_script,
                        "projects"
                    ]

                    run_command(projects_command)

                    project_id = input("\nEnter project ID to use for import (leave empty to use project from import file): ")

                    import_command = [
                        "python3", toggl_script,
                        "import",
                        "--file", import_file
                    ]

                    if project_id:
                        import_command.extend(["--project", project_id])

                    success, _ = run_command(
                        import_command,
                        success_message="Data imported to Toggl successfully",
                        error_message="Failed to import data to Toggl"
                    )

                    if success:
                        print("\n🎉 Workflow completed successfully!")
                    else:
                        print("\n❌ Workflow completed with errors during import.")
                else:
                    print("\nImport cancelled. Workflow completed without importing data.")

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading import file: {e}")
            print("Skipping import step.")
        
        input("\nPress Enter to return to main menu...")

    elif script_choice == 3:  # Run all: Redmine, GitLab, and Toggl
        print_header("Running Redmine Worklog Script")

        redmine_command = [
            "python3", redmine_script,
            month_flag,
            "--format", "json",
            "--output", redmine_output_file,
        ]

        success, _ = run_command(
            redmine_command,
            success_message=(
                f"Redmine worklogs for {month_name} month saved to {redmine_output_file}"
            ),
            error_message="Failed to get Redmine worklogs",
        )

        if not success:
            print("Redmine script failed.")
            input("\nPress Enter to return to main menu...")
            return

        print_header("Running GitLab History Script")

        gitlab_command = [
            "python3", gitlab_script,
            month_flag,
            "--format", "json",
            "--output", gitlab_output_file
        ]

        success, _ = run_command(
            gitlab_command,
            success_message=f"GitLab history for {month_name} month saved to {gitlab_output_file}",
            error_message="Failed to get GitLab history"
        )

        if not success:
            print("GitLab script failed.")
            input("\nPress Enter to return to main menu...")
            return

        print_header("Running Toggl Activity Script")

        toggl_command = [
            "python3", toggl_script,
            "activity",
            month_flag,
            "--format", "json",
            "--output", toggl_output_file
        ]

        success, _ = run_command(
            toggl_command,
            success_message=f"Toggl activity for {month_name} month saved to {toggl_output_file}",
            error_message="Failed to get Toggl activity"
        )

        if not success:
            print("Toggl script failed.")
            input("\nPress Enter to return to main menu...")
            return

        print("\n✅ All data retrieved successfully!")
        print(f"  - Redmine → {redmine_output_file}")
        print(f"  - GitLab → {gitlab_output_file}")
        print(f"  - Toggl → {toggl_output_file}")
        print("\nTo compare the data, run the workflow again and select 'Compare only'.")
        input("\nPress Enter to return to main menu...")
        return

    elif script_choice == 1:  # GitLab only
        print_header("Running GitLab History Script")

        gitlab_command = [
            "python3", gitlab_script,
            month_flag,
            "--format", "json",
            "--output", gitlab_output_file
        ]

        success, _ = run_command(
            gitlab_command,
            success_message=f"GitLab history for {month_name} month saved to {gitlab_output_file}",
            error_message="Failed to get GitLab history"
        )

        if not success:
            print("GitLab script failed.")
            input("\nPress Enter to return to main menu...")
            return

    elif script_choice == 2:  # Toggl only
        print_header("Running Toggl Activity Script")

        toggl_command = [
            "python3", toggl_script,
            "activity",
            month_flag,
            "--format", "json",
            "--output", toggl_output_file
        ]

        success, _ = run_command(
            toggl_command,
            success_message=f"Toggl activity for {month_name} month saved to {toggl_output_file}",
            error_message="Failed to get Toggl activity"
        )

        if not success:
            print("Toggl script failed.")
            input("\nPress Enter to return to main menu...")
            return

    # Inform the user that they can run the comparison manually (for individual script runs)
    if script_choice in [1, 2]:
        print("\nData has been successfully retrieved.")
        if script_choice == 1 and os.path.exists(toggl_output_file):
            print("GitLab and Toggl data are available.")
        elif script_choice == 2 and os.path.exists(gitlab_output_file):
            print("Toggl and GitLab data are available.")

        if os.path.exists(redmine_output_file):
            print(f"Redmine data is also available: {redmine_output_file}")

        print("\nTo compare the data and find missing entries, run the workflow again and select 'Compare only'.")
        print("\nWorkflow completed.")
        input("\nPress Enter to return to main menu...")

def main():
    """Main menu loop function."""
    while True:
        clear_screen()
        print_header("GitLab-Toggl Workflow - Main Menu")
        
        choice = get_user_choice(
            "Select an option:",
            ["Run Workflow", "Exit"]
        )
        
        if choice == 1:
            run_workflow()
        elif choice == 2:
            print("Exiting GitLab-Toggl Workflow. Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    main()

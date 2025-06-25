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

def main():
    """Main function to run the workflow."""
    clear_screen()
    print_header("GitLab-Toggl Workflow")

    # Define paths
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gitlab_script = os.path.join(script_dir, "gitlab/gitlab_history.py")
    toggl_script = os.path.join(script_dir, "toggle/toggle_activity.py")
    compare_script = os.path.join(script_dir, "compare/compare_gitlab_toggl.py")

    # Step 1: Ask for current or previous month
    month_choice = get_user_choice(
        "Select the month for data processing:",
        ["Current month", "Previous month", "Exit"]
    )

    # Exit if requested
    if month_choice == 3:
        print("Exiting workflow.")
        sys.exit(0)

    month_flag = "--current-month" if month_choice == 1 else "--previous-month"
    month_name = "current" if month_choice == 1 else "previous"

    # Step 2: Ask whether to run GitLab or Toggl script
    script_choice = get_user_choice(
        "Select the script to run:",
        ["GitLab history", "Toggl activity", "Both", "Compare only", "Import JSON", "Exit"]
    )

    # Exit if requested
    if script_choice == 6:
        print("Exiting workflow.")
        sys.exit(0)

    gitlab_output_file = os.path.join(script_dir, f"gitlab/gitlab_{month_name}_month.json")
    toggl_output_file = os.path.join(script_dir, f"toggle/toggl_{month_name}_month.json")

    # Step 3: Run the selected script(s)
    if script_choice == 5:  # Import JSON
        print_header("Importing JSON Data to Toggl")

        import_file = os.path.join(script_dir, "compare/result/toggl_import.json")

        # Check if the import file exists
        if not os.path.exists(import_file):
            print(f"Error: Import file not found: {import_file}")
            print("Please run the comparison script first to generate the import file.")
            sys.exit(1)

        # Check if the import file has entries
        try:
            with open(import_file, 'r') as f:
                import_data = json.load(f)
                entries = import_data.get('entries', [])

            if not entries:
                print("No entries to import. Exiting.")
                sys.exit(0)
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

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading import file: {e}")
            sys.exit(1)

    elif script_choice == 4:  # Compare only
        print_header("Running Comparison Script")

        # Check if both GitLab and Toggl output files exist
        if not os.path.exists(gitlab_output_file):
            print(f"Error: GitLab output file not found: {gitlab_output_file}")
            print("Please run the GitLab history script first to generate the output file.")
            sys.exit(1)

        if not os.path.exists(toggl_output_file):
            print(f"Error: Toggl output file not found: {toggl_output_file}")
            print("Please run the Toggl activity script first to generate the output file.")
            sys.exit(1)

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
            print("Exiting due to comparison script error.")
            sys.exit(1)

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

    elif script_choice in [1, 3]:  # GitLab or Both
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
            print("Exiting due to GitLab script error.")
            sys.exit(1)

    if script_choice in [2, 3]:  # Toggl or Both
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
            print("Exiting due to Toggl script error.")
            sys.exit(1)

    # Inform the user that they can run the comparison manually
    if script_choice != 4 and (script_choice == 3 or (script_choice == 1 and os.path.exists(toggl_output_file)) or (script_choice == 2 and os.path.exists(gitlab_output_file))):
        print("\nGitLab and/or Toggl data has been successfully retrieved.")
        print("To compare the data and find missing entries, run the workflow again and select 'Compare only'.")
        print("\nWorkflow completed.")

if __name__ == "__main__":
    main()

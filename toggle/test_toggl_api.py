#!/usr/bin/env python3

import requests
import sys
from base64 import b64encode

# Import authentication details from auth.py
try:
    from auth import TOGGL_API_TOKEN, TOGGL_WORKSPACE_ID
except ImportError:
    # If running from a different directory, try with full path
    try:
        from bin.toggle.auth import TOGGL_API_TOKEN, TOGGL_WORKSPACE_ID
    except ImportError:
        print("Error: Could not import authentication details from auth.py")
        print("Please make sure auth.py exists and contains TOGGL_API_TOKEN and TOGGL_WORKSPACE_ID variables")
        sys.exit(1)

# Toggl API endpoints
TOGGL_API_URL = "https://api.track.toggl.com/api/v9"

def get_auth_header(api_token):
    """Generate the authorization header for Toggl API."""
    auth_string = f"{api_token}:api_token"
    return {
        "Authorization": f"Basic {b64encode(auth_string.encode()).decode('ascii')}"
    }

def main():
    token = TOGGL_API_TOKEN
    workspace_id = TOGGL_WORKSPACE_ID

    if not token:
        print("Error: Toggl API token not provided in auth.py")
        sys.exit(1)

    # We'll list all workspaces, so we don't require workspace_id to be set
    if workspace_id == "your-workspace-id":
        print("Note: Workspace ID is not set in auth.py. We'll list all available workspaces.")

    # Prepare request headers
    headers = get_auth_header(token)

    try:
        # Test 1: Get user info
        print("Test 1: Getting user information...")
        user_response = requests.get(f"{TOGGL_API_URL}/me", headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()

        print(f"Connected as: {user_data.get('fullname', user_data.get('email', 'Unknown'))}")
        print(f"User ID: {user_data.get('id')}")

        # Test 2: List all workspaces
        print("\nTest 2: Listing all available workspaces...")
        workspaces_response = requests.get(f"{TOGGL_API_URL}/workspaces", headers=headers)
        workspaces_response.raise_for_status()
        workspaces = workspaces_response.json()

        if workspaces:
            print(f"Found {len(workspaces)} workspaces:")
            print("-" * 50)
            for workspace in workspaces:
                print(f"Workspace Name: {workspace.get('name')}")
                print(f"Workspace ID: {workspace.get('id')}")
                print(f"Admin: {workspace.get('admin', False)}")
                print("-" * 50)
        else:
            print("No workspaces found")

        # Test 3: Get workspace info (if workspace_id is set)
        if workspace_id != "your-workspace-id":
            print("\nTest 3: Getting workspace information...")
            workspace_response = requests.get(f"{TOGGL_API_URL}/workspaces/{workspace_id}", headers=headers)
            workspace_response.raise_for_status()
            workspace_data = workspace_response.json()

            print(f"Workspace: {workspace_data.get('name')}")
            print(f"Workspace ID: {workspace_data.get('id')}")

            # Test 4: Get projects
            print("\nTest 4: Getting projects...")
            projects_url = f"{TOGGL_API_URL}/workspaces/{workspace_id}/projects"
            projects_response = requests.get(projects_url, headers=headers)
            projects_response.raise_for_status()
            projects = projects_response.json()

            if projects:
                print(f"Found {len(projects)} projects")
                print("First 5 projects:")
                for i, project in enumerate(projects[:5]):
                    print(f"  - {project.get('name')} (ID: {project.get('id')})")
            else:
                print("No projects found in the workspace")

            # Test 5: Get time entries
            print("\nTest 5: Getting recent time entries...")
            # The correct endpoint for time entries in v9 API
            entries_url = f"{TOGGL_API_URL}/me/time_entries"
            entries_response = requests.get(entries_url, headers=headers, params={"limit": 5})
            entries_response.raise_for_status()
            entries = entries_response.json()

            if entries:
                print(f"Found {len(entries)} recent time entries")
                print("Details:")
                for entry in entries:
                    print(f"  - {entry.get('description', 'No description')} (Duration: {entry.get('duration', 0)} seconds)")
            else:
                print("No time entries found")
        else:
            print("\nSkipping Tests 3-5 as no valid workspace ID is set in auth.py")
            print("Please update auth.py with one of the workspace IDs listed above")

        print("\nAll tests completed successfully!")
        print("Your Toggl API configuration is working correctly.")

    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

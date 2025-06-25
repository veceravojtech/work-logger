#!/usr/bin/env python3

import gitlab
import sys

# Import authentication details from auth.py
try:
    from auth import GITLAB_URL, GITLAB_TOKEN
except ImportError:
    # If running from a different directory, try with full path
    try:
        from bin.gitlab.auth import GITLAB_URL, GITLAB_TOKEN
    except ImportError:
        print("Error: Could not import authentication details from auth.py")
        print("Please make sure auth.py exists and contains GITLAB_URL and GITLAB_TOKEN variables")
        sys.exit(1)

def main():
    token = GITLAB_TOKEN
    gitlab_url = GITLAB_URL

    try:
        # Connect to GitLab
        gl = gitlab.Gitlab(gitlab_url, private_token=token)
        gl.auth()

        # Get current user
        user = gl.user
        print(f"Connected as: {user.username} ({user.name})")

        # Print available attributes and methods
        print("\nUser object attributes:")
        for attr in dir(user):
            if not attr.startswith('_'):
                print(f"- {attr}")

        # Try to get events using the current API
        print("\nTrying to get events...")

        # Method 1: Try to get events from the user object
        try:
            print("Method 1: user.events")
            if hasattr(user, 'events'):
                events = user.events.list(all=True)
                print(f"Found {len(events)} events")
            else:
                print("User object does not have 'events' attribute")
        except Exception as e:
            print(f"Error with Method 1: {str(e)}")

        # Method 2: Try to get events from the gitlab object
        try:
            print("\nMethod 2: gl.events.list")
            events = gl.events.list(all=True)
            print(f"Found {len(events)} events")
            if events:
                print(f"First event: {events[0].action_name} at {events[0].created_at}")
        except Exception as e:
            print(f"Error with Method 2: {str(e)}")

        # Method 3: Try to get events using the user ID
        try:
            print("\nMethod 3: gl.user_events.list")
            user_id = user.id
            events = gl.user_events.list(user_id=user_id, all=True)
            print(f"Found {len(events)} events")
            if events:
                print(f"First event: {events[0].action_name} at {events[0].created_at}")
        except Exception as e:
            print(f"Error with Method 3: {str(e)}")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

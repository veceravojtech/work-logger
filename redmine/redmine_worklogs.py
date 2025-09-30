"""Fetch Redmine time entries (worklogs) for the current or previous month."""

import argparse
import csv
import datetime as dt
import json
import os
import sys
import calendar
from typing import Dict, List, Optional, Tuple

import requests

# Attempt to import credentials from auth.py
try:
    from auth import REDMINE_URL, REDMINE_API_KEY
except ImportError:
    try:
        from redmine.auth import REDMINE_URL, REDMINE_API_KEY  # type: ignore
    except ImportError:
        REDMINE_URL = "https://redmine.example.com"
        REDMINE_API_KEY = None

DEFAULT_LIMIT = 100
REQUEST_TIMEOUT = 30  # seconds
DEFAULT_DURATION_HOURS = 0.25  # 15 minutes for activities without time entries


def subtract_months(value: dt.datetime, months: int) -> dt.datetime:
    """Return *value* minus *months* calendar months."""
    if months <= 0:
        return value

    year = value.year
    month = value.month - months
    while month <= 0:
        month += 12
        year -= 1

    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def calculate_date_range(
    *,
    months: int = 1,
    days: int = 0,
    current_month: bool = False,
    previous_month: bool = False,
    now: Optional[dt.datetime] = None,
) -> Tuple[dt.date, dt.date]:
    """Return the inclusive start/end date for the query."""
    now = now or dt.datetime.now(dt.timezone.utc)

    if current_month:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()
        end = now.date()
    elif previous_month:
        first_of_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_month_last = first_of_current - dt.timedelta(days=1)
        start = previous_month_last.replace(day=1).date()
        end = previous_month_last.date()
    else:
        end_dt = now
        start_dt = subtract_months(end_dt, months)
        if days:
            start_dt -= dt.timedelta(days=days)
        start = start_dt.date()
        end = end_dt.date()

    return start, end


def format_hours(hours: float) -> str:
    """Return hours formatted as Hh Mm."""
    total_minutes = int(round(hours * 60))
    h, m = divmod(total_minutes, 60)
    return f"{h}h {m}m"


def create_session(api_key: str) -> requests.Session:
    """Create a configured requests session."""
    session = requests.Session()
    session.headers.update(
        {
            "X-Redmine-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    return session


def fetch_current_user(session: requests.Session, base_url: str) -> Dict:
    """Return the current user information (best effort)."""
    try:
        response = session.get(f"{base_url}/users/current.json", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("user", {})
    except requests.RequestException:
        return {}


def fetch_time_entries(
    session: requests.Session,
    base_url: str,
    start_date: dt.date,
    end_date: dt.date,
    *,
    user_id: str = "me",
) -> List[Dict]:
    """Fetch all Redmine time entries for the given period."""
    entries: List[Dict] = []
    offset = 0
    total = None

    date_params = {
        "user_id": user_id,
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
        "limit": DEFAULT_LIMIT,
    }

    while True:
        params = {**date_params, "offset": offset}
        try:
            response = session.get(
                f"{base_url}/time_entries.json", params=params, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
        except requests.HTTPError as err:
            raise SystemExit(f"Failed to fetch time entries: {err}") from err
        except requests.RequestException as err:
            raise SystemExit(f"Error communicating with Redmine: {err}") from err

        data = response.json()
        batch = data.get("time_entries", [])
        entries.extend(batch)

        total = data.get("total_count", len(entries))
        if len(entries) >= total or not batch:
            break

        offset += data.get("limit", DEFAULT_LIMIT)

    return entries


def fetch_issues_created(
    session: requests.Session,
    base_url: str,
    start_date: dt.date,
    end_date: dt.date,
    *,
    user_id: Optional[int] = None,
) -> List[Dict]:
    """Fetch all issues created by the user in the given period."""
    activities: List[Dict] = []
    offset = 0

    start_datetime = dt.datetime.combine(start_date, dt.time.min)
    end_datetime = dt.datetime.combine(end_date, dt.time.max)

    while True:
        params = {
            "created_on": f"><{start_date.isoformat()}|{end_date.isoformat()}",
            "limit": DEFAULT_LIMIT,
            "offset": offset,
            "status_id": "*",
        }

        if user_id:
            params["author_id"] = user_id

        try:
            response = session.get(
                f"{base_url}/issues.json", params=params, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
        except requests.RequestException as err:
            print(f"Warning: Could not fetch created issues: {err}")
            break

        data = response.json()
        issues = data.get("issues", [])

        if not issues:
            break

        for issue in issues:
            created_on_str = issue.get("created_on")
            if not created_on_str:
                continue

            try:
                created_on = dt.datetime.fromisoformat(created_on_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            if not (start_datetime <= created_on <= end_datetime):
                continue

            activities.append({
                "id": f"issue_created_{issue.get('id')}",
                "type": "Issue Created",
                "date": created_on.date().isoformat(),
                "datetime": created_on_str,
                "project": issue.get("project", {}),
                "issue": {
                    "id": issue.get("id"),
                    "subject": issue.get("subject"),
                },
                "user": issue.get("author", {}),
                "notes": f"Created: {issue.get('subject', '')}",
                "details": [],
            })

        offset += DEFAULT_LIMIT
        total = data.get("total_count", 0)
        if offset >= total:
            break

    return activities


def fetch_user_activities(
    session: requests.Session,
    base_url: str,
    start_date: dt.date,
    end_date: dt.date,
    *,
    user_id: Optional[int] = None,
) -> List[Dict]:
    """Fetch all Redmine activities (comments, updates, etc.) for the given period using activity feed."""
    activities: List[Dict] = []

    start_datetime = dt.datetime.combine(start_date, dt.time.min, tzinfo=dt.timezone.utc)
    end_datetime = dt.datetime.combine(end_date, dt.time.max, tzinfo=dt.timezone.utc)

    # Redmine activity API doesn't support JSON directly in older versions
    # We need to fetch individual issues that were updated and get their journals
    # To optimize, we'll fetch only issues where user is author or assignee

    # Fetch issues where user is author or assigned
    issue_ids_to_check = set()

    for filter_type in ["author_id", "assigned_to_id"]:
        offset = 0
        while offset < 1000:  # Limit to prevent too many API calls
            params = {
                "updated_on": f"><{start_date.isoformat()}|{end_date.isoformat()}",
                filter_type: user_id or "me",
                "limit": 100,
                "offset": offset,
                "status_id": "*",
            }

            try:
                response = session.get(
                    f"{base_url}/issues.json", params=params, timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()
                issues = data.get("issues", [])

                if not issues:
                    break

                for issue in issues:
                    issue_ids_to_check.add(issue.get("id"))

                offset += 100
                if offset >= data.get("total_count", 0):
                    break
            except requests.RequestException:
                break

    # Now fetch each issue with journals
    for issue_id in list(issue_ids_to_check)[:200]:  # Limit to 200 issues to avoid timeout
        try:
            response = session.get(
                f"{base_url}/issues/{issue_id}.json",
                params={"include": "journals"},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            issue_data = response.json().get("issue", {})
            journals = issue_data.get("journals", [])

            for journal in journals:
                created_on_str = journal.get("created_on")
                if not created_on_str:
                    continue

                try:
                    created_on = dt.datetime.fromisoformat(created_on_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    continue

                if not (start_datetime <= created_on <= end_datetime):
                    continue

                journal_user = journal.get("user", {})
                if user_id and journal_user.get("id") != user_id:
                    continue

                notes = journal.get("notes", "")
                details = journal.get("details", [])

                activity_type = "Update"
                if notes:
                    activity_type = "Comment"
                elif details:
                    changes = [d.get("name") for d in details]
                    if "status_id" in changes:
                        activity_type = "Status Change"
                    elif "assigned_to_id" in changes:
                        activity_type = "Assignment"
                    elif "estimated_hours" in changes or "done_ratio" in changes:
                        activity_type = "Progress Update"

                activities.append({
                    "id": f"journal_{journal.get('id')}",
                    "type": activity_type,
                    "date": created_on.date().isoformat(),
                    "datetime": created_on_str,
                    "project": issue_data.get("project", {}),
                    "issue": {
                        "id": issue_data.get("id"),
                        "subject": issue_data.get("subject"),
                    },
                    "user": journal_user,
                    "notes": notes,
                    "details": details,
                })
        except requests.RequestException:
            continue

    return activities


def fetch_changesets(
    session: requests.Session,
    base_url: str,
    start_date: dt.date,
    end_date: dt.date,
    *,
    user_id: Optional[int] = None,
) -> List[Dict]:
    """Fetch all changesets (code commits) by the user in the given period."""
    activities: List[Dict] = []
    offset = 0

    start_datetime = dt.datetime.combine(start_date, dt.time.min)
    end_datetime = dt.datetime.combine(end_date, dt.time.max)

    # Note: Redmine API doesn't have a direct way to filter changesets by user
    # We need to fetch changesets and filter by committer name/email
    # This is a limitation of the Redmine API
    try:
        response = session.get(
            f"{base_url}/users/current.json", timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        current_user = response.json().get("user", {})
        user_email = current_user.get("mail", "").lower()
        user_login = current_user.get("login", "").lower()
        user_firstname = current_user.get("firstname", "").lower()
        user_lastname = current_user.get("lastname", "").lower()
    except requests.RequestException:
        return activities

    # Fetch projects to get their changesets
    try:
        response = session.get(
            f"{base_url}/projects.json", params={"limit": 100}, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        projects = response.json().get("projects", [])
    except requests.RequestException:
        return activities

    for project in projects:
        project_id = project.get("identifier") or project.get("id")
        if not project_id:
            continue

        try:
            response = session.get(
                f"{base_url}/projects/{project_id}/repository/revisions.json",
                params={"limit": 100},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            revisions = response.json().get("changesets", [])
        except requests.RequestException:
            continue

        for changeset in revisions:
            committed_on_str = changeset.get("committed_on")
            if not committed_on_str:
                continue

            try:
                committed_on = dt.datetime.fromisoformat(committed_on_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            if not (start_datetime <= committed_on <= end_datetime):
                continue

            # Filter by user (match email or name)
            user = changeset.get("user", {})
            author = changeset.get("author", "").lower()

            is_user_commit = False
            if user and user_id and user.get("id") == user_id:
                is_user_commit = True
            elif user_email and user_email in author:
                is_user_commit = True
            elif user_login and user_login in author:
                is_user_commit = True
            elif user_firstname and user_firstname in author:
                is_user_commit = True
            elif user_lastname and user_lastname in author:
                is_user_commit = True

            if not is_user_commit:
                continue

            activities.append({
                "id": f"changeset_{changeset.get('revision')}_{project_id}",
                "type": "Code Commit",
                "date": committed_on.date().isoformat(),
                "datetime": committed_on_str,
                "project": project,
                "issue": {
                    "id": None,
                    "subject": None,
                },
                "user": user or {"name": changeset.get("author")},
                "notes": changeset.get("comments", ""),
                "details": [],
            })

    return activities


def fetch_wiki_edits(
    session: requests.Session,
    base_url: str,
    start_date: dt.date,
    end_date: dt.date,
    *,
    user_id: Optional[int] = None,
) -> List[Dict]:
    """Fetch all wiki page edits by the user in the given period."""
    activities: List[Dict] = []

    start_datetime = dt.datetime.combine(start_date, dt.time.min)
    end_datetime = dt.datetime.combine(end_date, dt.time.max)

    # Fetch projects to get their wiki pages
    try:
        response = session.get(
            f"{base_url}/projects.json", params={"limit": 100}, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        projects = response.json().get("projects", [])
    except requests.RequestException:
        return activities

    for project in projects:
        project_id = project.get("identifier") or project.get("id")
        if not project_id:
            continue

        # Get wiki pages for this project
        try:
            response = session.get(
                f"{base_url}/projects/{project_id}/wiki/index.json",
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            wiki_pages = response.json().get("wiki_pages", [])
        except requests.RequestException:
            continue

        for page in wiki_pages:
            page_title = page.get("title")
            if not page_title:
                continue

            # Get the page history
            try:
                response = session.get(
                    f"{base_url}/projects/{project_id}/wiki/{page_title}.json",
                    params={"include": "attachments"},
                    timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()
                page_data = response.json().get("wiki_page", {})
            except requests.RequestException:
                continue

            updated_on_str = page_data.get("updated_on")
            if not updated_on_str:
                continue

            try:
                updated_on = dt.datetime.fromisoformat(updated_on_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            if not (start_datetime <= updated_on <= end_datetime):
                continue

            # Filter by user
            author = page_data.get("author", {})
            if user_id and author.get("id") != user_id:
                continue

            activities.append({
                "id": f"wiki_{project_id}_{page_title}_{updated_on_str}",
                "type": "Wiki Edit",
                "date": updated_on.date().isoformat(),
                "datetime": updated_on_str,
                "project": project,
                "issue": {
                    "id": None,
                    "subject": None,
                },
                "user": author,
                "notes": f"Wiki page: {page_data.get('title', '')}",
                "details": [],
            })

    return activities


def process_time_entries(
    entries: List[Dict],
    base_url: str,
) -> Tuple[List[Dict], float]:
    """Normalise time entries and return processed list and total hours."""
    processed: List[Dict] = []
    total_hours = 0.0

    for entry in entries:
        hours = float(entry.get("hours", 0.0))
        total_hours += hours

        project = entry.get("project", {})
        issue = entry.get("issue", {})
        activity = entry.get("activity", {})

        issue_id = issue.get("id")
        issue_url = f"{base_url}/issues/{issue_id}" if issue_id else None

        processed.append(
            {
                "id": entry.get("id"),
                "date": entry.get("spent_on"),
                "hours": hours,
                "hours_formatted": format_hours(hours),
                "project": project.get("name", "Unknown Project"),
                "project_id": project.get("id"),
                "issue_id": issue_id,
                "issue_url": issue_url,
                "activity": activity.get("name"),
                "activity_id": activity.get("id"),
                "comments": entry.get("comments", ""),
                "created_on": entry.get("created_on"),
                "updated_on": entry.get("updated_on"),
            }
        )

    processed.sort(key=lambda item: (item["date"] or "", item["id"] or 0), reverse=True)
    return processed, total_hours


def merge_activities_with_time_entries(
    time_entries: List[Dict],
    activities: List[Dict],
    base_url: str,
) -> Tuple[List[Dict], float]:
    """Merge activities with time entries, adding default duration for all activities."""
    # Convert all activities to synthetic entries with default duration
    synthetic_entries = []
    for activity in activities:
        date = activity.get("date")
        issue_id = activity["issue"].get("id")

        # Create synthetic time entry with default duration for EVERY activity
        issue_url = f"{base_url}/issues/{issue_id}" if issue_id else None
        project = activity.get("project", {})

        synthetic_entries.append({
            "id": activity.get("id"),
            "date": date,
            "hours": DEFAULT_DURATION_HOURS,
            "hours_formatted": format_hours(DEFAULT_DURATION_HOURS),
            "project": project.get("name", "Unknown Project"),
            "project_id": project.get("id"),
            "issue_id": issue_id,
            "issue_url": issue_url,
            "activity": activity.get("type"),
            "activity_id": None,
            "comments": activity.get("notes", ""),
            "created_on": activity.get("datetime"),
            "updated_on": activity.get("datetime"),
            "is_synthetic": True,  # Flag to indicate this is not a logged time entry
        })

    # Merge and calculate total hours
    all_entries = time_entries + synthetic_entries
    total_hours = sum(entry.get("hours", 0.0) for entry in all_entries)

    # Sort by date and id
    all_entries.sort(key=lambda item: (item["date"] or "", str(item["id"]) or ""), reverse=True)

    return all_entries, total_hours


def output_json(
    *,
    user: Dict,
    period: Tuple[dt.date, dt.date],
    entries: List[Dict],
    total_hours: float,
    destination: Optional[str] = None,
) -> None:
    # Calculate statistics
    logged_entries = [e for e in entries if not e.get("is_synthetic")]
    synthetic_entries = [e for e in entries if e.get("is_synthetic")]

    logged_hours = sum(e.get("hours", 0) for e in logged_entries)
    synthetic_hours = sum(e.get("hours", 0) for e in synthetic_entries)

    content = json.dumps(
        {
            "user": {
                "id": user.get("id"),
                "login": user.get("login"),
                "name": " ".join(
                    [
                        item
                        for item in [user.get("firstname"), user.get("lastname")]
                        if item
                    ]
                )
                or user.get("name"),
                "mail": user.get("mail"),
            },
            "period": {
                "start": period[0].isoformat(),
                "end": period[1].isoformat(),
            },
            "total_hours": {
                "value": round(total_hours, 2),
                "formatted": format_hours(total_hours),
            },
            "statistics": {
                "logged_entries": len(logged_entries),
                "logged_hours": round(logged_hours, 2),
                "activity_entries": len(synthetic_entries),
                "activity_hours": round(synthetic_hours, 2),
            },
            "entries": entries,
        },
        indent=2,
    )

    if destination:
        with open(destination, "w", encoding="utf-8") as handle:
            handle.write(content)
    else:
        print(content)


def output_csv(
    *,
    entries: List[Dict],
    destination: Optional[str] = None,
) -> None:
    fieldnames = [
        "date",
        "hours",
        "hours_formatted",
        "project",
        "project_id",
        "issue_id",
        "activity",
        "comments",
    ]

    if destination:
        outfile = open(destination, "w", newline="", encoding="utf-8")
        close_after = True
    else:
        outfile = sys.stdout
        close_after = False

    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    for entry in entries:
        writer.writerow({key: entry.get(key, "") for key in fieldnames})

    if close_after:
        outfile.close()


def output_text(
    *,
    user: Dict,
    period: Tuple[dt.date, dt.date],
    entries: List[Dict],
    total_hours: float,
) -> None:
    name = " ".join(
        [item for item in [user.get("firstname"), user.get("lastname")] if item]
    ) or user.get("login", "Unknown User")

    # Separate logged and synthetic entries
    logged_entries = [e for e in entries if not e.get("is_synthetic")]
    synthetic_entries = [e for e in entries if e.get("is_synthetic")]

    logged_hours = sum(e.get("hours", 0) for e in logged_entries)
    synthetic_hours = sum(e.get("hours", 0) for e in synthetic_entries)

    header = f"Redmine Worklogs for: {name}"
    period_line = f"Period: {period[0].isoformat()} to {period[1].isoformat()}"
    summary = f"Total Hours: {format_hours(total_hours)} ({round(total_hours, 2)}h)"
    breakdown = f"  - Logged: {format_hours(logged_hours)} ({round(logged_hours, 2)}h)"
    breakdown2 = f"  - Activities (auto): {format_hours(synthetic_hours)} ({round(synthetic_hours, 2)}h)"

    lines = [header, period_line, summary, breakdown, breakdown2, "-" * 80]

    if not entries:
        lines.append("No time entries found for the selected period.")
    else:
        for entry in entries:
            is_synthetic = entry.get("is_synthetic", False)
            prefix = "[AUTO] " if is_synthetic else ""

            base = f"{prefix}{entry['date']} - {entry['project']}"
            if entry.get("issue_id"):
                base += f" (Issue #{entry['issue_id']})"

            lines.append(base)
            lines.append(f"  Hours: {entry['hours_formatted']} ({entry['hours']}h)")

            if entry.get("activity"):
                lines.append(f"  Activity: {entry['activity']}")

            if entry.get("comments"):
                lines.append(f"  Comments: {entry['comments']}")

            lines.append("")

    print("\n".join(lines))


def get_redmine_worklogs(
    *,
    api_key: Optional[str] = None,
    redmine_url: Optional[str] = None,
    user_id: str = "me",
    months: int = 1,
    days: int = 0,
    current_month: bool = False,
    previous_month: bool = False,
    output_format: str = "text",
    output_file: Optional[str] = None,
) -> None:
    """High-level workflow for fetching and displaying Redmine worklogs."""
    base_url = (redmine_url or REDMINE_URL or "").rstrip("/")
    if not base_url:
        print("Error: Redmine URL not provided.")
        print("Please set it via auth.py, --url argument, or REDMINE_URL environment variable.")
        sys.exit(1)

    api_key = api_key or REDMINE_API_KEY or os.environ.get("REDMINE_API_KEY")
    if not api_key:
        print("Error: Redmine API key not provided.")
        print("Please set it via auth.py, --api-key argument, or REDMINE_API_KEY environment variable.")
        sys.exit(1)

    start_date, end_date = calculate_date_range(
        months=months,
        days=days,
        current_month=current_month,
        previous_month=previous_month,
    )

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    session = create_session(api_key)
    user = fetch_current_user(session, base_url)

    # Fetch logged time entries
    entries = fetch_time_entries(session, base_url, start_date, end_date, user_id=user_id)
    processed_entries, _ = process_time_entries(entries, base_url)

    # Fetch all activities
    user_numeric_id = user.get("id") if user else None

    print("Fetching activities from Redmine...")

    # 1. Issues created by the user
    created_issues = fetch_issues_created(session, base_url, start_date, end_date, user_id=user_numeric_id)
    print(f"  - Issues created: {len(created_issues)}")

    # 2. Issue updates/comments by the user
    update_activities = fetch_user_activities(session, base_url, start_date, end_date, user_id=user_numeric_id)
    print(f"  - Issue updates/comments: {len(update_activities)}")

    # 3. Code commits (changesets)
    changesets = fetch_changesets(session, base_url, start_date, end_date, user_id=user_numeric_id)
    print(f"  - Code commits: {len(changesets)}")

    # 4. Wiki edits
    wiki_edits = fetch_wiki_edits(session, base_url, start_date, end_date, user_id=user_numeric_id)
    print(f"  - Wiki edits: {len(wiki_edits)}")

    # Combine all activities
    all_activities = created_issues + update_activities + changesets + wiki_edits
    print(f"  - Total activities: {len(all_activities)}\n")

    # Merge activities with time entries, adding default duration for unlogged activities
    processed_entries, total_hours = merge_activities_with_time_entries(
        processed_entries, all_activities, base_url
    )

    if output_format == "json":
        output_json(
            user=user,
            period=(start_date, end_date),
            entries=processed_entries,
            total_hours=total_hours,
            destination=output_file,
        )
    elif output_format == "csv":
        output_csv(entries=processed_entries, destination=output_file)
    else:
        output_text(
            user=user,
            period=(start_date, end_date),
            entries=processed_entries,
            total_hours=total_hours,
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Redmine worklogs for a specified time period.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--api-key",
        "-k",
        help="Redmine API key. Overrides value from auth.py or environment variable.",
    )
    parser.add_argument(
        "--url",
        "-u",
        help="Redmine base URL. Overrides value from auth.py.",
    )
    parser.add_argument(
        "--user-id",
        default="me",
        help="User identifier for filtering time entries (e.g., 'me' or numeric ID).",
    )
    parser.add_argument(
        "--months",
        "-m",
        type=int,
        default=1,
        help="Number of months to look back (ignored if --current-month or --previous-month).",
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=0,
        help="Additional days to include when looking back (ignored if --current-month or --previous-month).",
    )
    parser.add_argument(
        "--current-month",
        action="store_true",
        help="Restrict results to the current calendar month.",
    )
    parser.add_argument(
        "--previous-month",
        action="store_true",
        help="Restrict results to the previous calendar month.",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Path to an output file. Prints to stdout if omitted.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    get_redmine_worklogs(
        api_key=args.api_key,
        redmine_url=args.url,
        user_id=args.user_id,
        months=args.months,
        days=args.days,
        current_month=args.current_month,
        previous_month=args.previous_month,
        output_format=args.format,
        output_file=args.output,
    )

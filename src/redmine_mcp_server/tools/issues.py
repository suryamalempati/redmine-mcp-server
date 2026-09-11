"""Issue-related MCP tools for Redmine."""

from __future__ import annotations

from fastmcp import FastMCP

from ..client import RedmineClient
from ..exceptions import RedmineError


def register_issue_tools(mcp: FastMCP, client: RedmineClient) -> None:
    """Register all issue-related tools with the MCP server."""

    @mcp.tool()
    async def list_issues(
        project_id: int | None = None,
        status_id: str | None = None,
        assigned_to_id: int | None = None,
        tracker_id: int | None = None,
        fixed_version_id: int | None = None,
        issue_ids: str | None = None,
        sort: str | None = None,
        offset: int = 0,
        limit: int = 100,
        fetch_all: bool = False,
    ) -> dict:
        """List issues with optional filters and pagination.

        Args:
            project_id: Filter by project ID.
            status_id: Filter by status (e.g. "open", "closed", "*", or a numeric ID).
            assigned_to_id: Filter by assignee user ID.
            tracker_id: Filter by tracker ID.
            fixed_version_id: Filter by target version ID.
            issue_ids: Comma-separated list of issue IDs to fetch (e.g. "1,2,3").
            sort: Sort field and direction (e.g. "updated_on:desc").
            offset: Pagination offset (ignored when fetch_all=True).
            limit: Maximum number of results per page (max 100).
            fetch_all: If True, automatically paginates and returns all matching
                issues in a single response.
        """
        params: dict = {}
        if project_id is not None:
            params["project_id"] = project_id
        if status_id is not None:
            params["status_id"] = status_id
        if assigned_to_id is not None:
            params["assigned_to_id"] = assigned_to_id
        if tracker_id is not None:
            params["tracker_id"] = tracker_id
        if fixed_version_id is not None:
            params["fixed_version_id"] = fixed_version_id
        if issue_ids is not None:
            params["issue_id"] = issue_ids
        if sort is not None:
            params["sort"] = sort

        page_limit = min(limit, 100)

        if fetch_all:
            all_issues: list[dict] = []
            current_offset = 0

            while True:
                params["offset"] = current_offset
                params["limit"] = page_limit

                try:
                    data = await client.get("/issues.json", params=params)
                except RedmineError as e:
                    return e.to_dict()

                issues = data.get("issues", [])
                all_issues.extend(issues)

                total_count = data.get("total_count", 0)
                current_offset += len(issues)

                if not issues or current_offset >= total_count:
                    break

            return {
                "total_count": len(all_issues),
                "issues": all_issues,
            }

        # Standard single-page request
        params["offset"] = offset
        params["limit"] = page_limit

        try:
            data = await client.get("/issues.json", params=params)
        except RedmineError as e:
            return e.to_dict()

        return {
            "total_count": data.get("total_count", 0),
            "offset": data.get("offset", offset),
            "limit": data.get("limit", page_limit),
            "issues": data.get("issues", []),
        }

    @mcp.tool()
    async def get_issue(
        issue_id: int,
        include: str | None = None,
    ) -> dict:
        """Get detailed information about a specific issue."""
        if not isinstance(issue_id, int) or issue_id <= 0:
            return {"error": "issue_id must be a positive integer", "details": []}

        supported_includes = {
            "children",
            "attachments",
            "relations",
            "changesets",
            "journals",
            "watchers",
            "allowed_statuses",
        }

        params: dict = {}
        if include is not None:
            requested = {v.strip() for v in include.split(",")}
            invalid = requested - supported_includes
            if invalid:
                return {
                    "error": f"Unsupported include values: {sorted(invalid)}. "
                    f"Supported: {sorted(supported_includes)}",
                    "details": [],
                }
            params["include"] = include

        try:
            data = await client.get(f"/issues/{issue_id}.json", params=params)
        except RedmineError as e:
            return e.to_dict()

        return data.get("issue", data)

    @mcp.tool()
    async def create_issue(
        project_id: int,
        subject: str,
        tracker_id: int | None = None,
        status_id: int | None = None,
        priority_id: int | None = None,
        description: str | None = None,
        category_id: int | None = None,
        fixed_version_id: int | None = None,
        assigned_to_id: int | None = None,
        parent_issue_id: int | None = None,
        custom_fields: list[dict] | None = None,
        watcher_user_ids: list[int] | None = None,
        is_private: bool | None = None,
        estimated_hours: float | None = None,
        start_date: str | None = None,
        due_date: str | None = None,
        done_ratio: int | None = None,
    ) -> dict:
        """Create a new issue in a project.

        Args:
            start_date: Issue start date (YYYY-MM-DD).
            due_date: Issue due date (YYYY-MM-DD).
            done_ratio: Percentage of completion (integer 0-100).
        """
        if not subject or not subject.strip():
            return {"error": "subject is required and cannot be empty", "details": []}

        if done_ratio is not None and (
            not isinstance(done_ratio, int)
            or isinstance(done_ratio, bool)
            or not 0 <= done_ratio <= 100
        ):
            return {
                "error": "done_ratio must be an integer between 0 and 100",
                "details": [],
            }

        issue_data: dict = {
            "project_id": project_id,
            "subject": subject,
        }

        optional_fields = {
            "tracker_id": tracker_id,
            "status_id": status_id,
            "priority_id": priority_id,
            "description": description,
            "category_id": category_id,
            "fixed_version_id": fixed_version_id,
            "assigned_to_id": assigned_to_id,
            "parent_issue_id": parent_issue_id,
            "custom_fields": custom_fields,
            "watcher_user_ids": watcher_user_ids,
            "is_private": is_private,
            "estimated_hours": estimated_hours,
            "start_date": start_date,
            "due_date": due_date,
            "done_ratio": done_ratio,
        }

        for key, value in optional_fields.items():
            if value is not None:
                issue_data[key] = value

        try:
            data = await client.post("/issues.json", {"issue": issue_data})
        except RedmineError as e:
            return e.to_dict()

        return data.get("issue", data)

    @mcp.tool()
    async def update_issue(
        issue_id: int,
        subject: str | None = None,
        project_id: int | None = None,
        tracker_id: int | None = None,
        status_id: int | None = None,
        priority_id: int | None = None,
        description: str | None = None,
        category_id: int | None = None,
        fixed_version_id: int | None = None,
        assigned_to_id: int | None = None,
        parent_issue_id: int | None = None,
        custom_fields: list[dict] | None = None,
        is_private: bool | None = None,
        estimated_hours: float | None = None,
        start_date: str | None = None,
        due_date: str | None = None,
        notes: str | None = None,
        private_notes: bool | None = None,
        done_ratio: int | None = None,
    ) -> dict:
        """Update an existing issue.

        Args:
            done_ratio: Percentage of completion (integer 0-100).
        """
        if not isinstance(issue_id, int) or issue_id <= 0:
            return {"error": "issue_id must be a positive integer", "details": []}

        if done_ratio is not None and (
            not isinstance(done_ratio, int)
            or isinstance(done_ratio, bool)
            or not 0 <= done_ratio <= 100
        ):
            return {
                "error": "done_ratio must be an integer between 0 and 100",
                "details": [],
            }

        issue_data: dict = {}

        optional_fields = {
            "subject": subject,
            "project_id": project_id,
            "tracker_id": tracker_id,
            "status_id": status_id,
            "priority_id": priority_id,
            "description": description,
            "category_id": category_id,
            "fixed_version_id": fixed_version_id,
            "assigned_to_id": assigned_to_id,
            "parent_issue_id": parent_issue_id,
            "custom_fields": custom_fields,
            "is_private": is_private,
            "estimated_hours": estimated_hours,
            "start_date": start_date,
            "due_date": due_date,
            "notes": notes,
            "private_notes": private_notes,
            "done_ratio": done_ratio,
        }

        for key, value in optional_fields.items():
            if value is not None:
                issue_data[key] = value

        try:
            await client.put(f"/issues/{issue_id}.json", {"issue": issue_data})
        except RedmineError as e:
            return e.to_dict()

        return {"status": "success", "issue_id": issue_id}

    @mcp.tool()
    async def delete_issue(issue_id: int) -> dict:
        """Delete an issue permanently."""
        if not isinstance(issue_id, int) or issue_id <= 0:
            return {"error": "issue_id must be a positive integer", "details": []}

        try:
            await client.delete(f"/issues/{issue_id}.json")
        except RedmineError as e:
            return e.to_dict()

        return {"status": "success", "deleted_issue_id": issue_id}

    @mcp.tool()
    async def add_watcher(issue_id: int, user_id: int) -> dict:
        """Add a watcher to an issue."""
        if not isinstance(issue_id, int) or issue_id <= 0:
            return {"error": "issue_id must be a positive integer", "details": []}
        if not isinstance(user_id, int) or user_id <= 0:
            return {"error": "user_id must be a positive integer", "details": []}

        try:
            await client.post(
                f"/issues/{issue_id}/watchers.json", {"user_id": user_id}
            )
        except RedmineError as e:
            return e.to_dict()

        return {"status": "success", "issue_id": issue_id, "user_id": user_id}

    @mcp.tool()
    async def remove_watcher(issue_id: int, user_id: int) -> dict:
        """Remove a watcher from an issue."""
        if not isinstance(issue_id, int) or issue_id <= 0:
            return {"error": "issue_id must be a positive integer", "details": []}
        if not isinstance(user_id, int) or user_id <= 0:
            return {"error": "user_id must be a positive integer", "details": []}

        try:
            await client.delete(f"/issues/{issue_id}/watchers/{user_id}.json")
        except RedmineError as e:
            return e.to_dict()

        return {"status": "success", "issue_id": issue_id, "user_id": user_id}

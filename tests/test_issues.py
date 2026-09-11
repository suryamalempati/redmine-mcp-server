"""Unit tests for issue tool handlers."""

from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import FastMCP

from redmine_mcp_server.client import RedmineClient
from redmine_mcp_server.tools.issues import register_issue_tools


@pytest.fixture
def setup():
    """Create MCP server and client for testing."""
    mcp = FastMCP("test")
    client = RedmineClient(base_url="http://redmine.example.com", api_key="test-key")
    register_issue_tools(mcp, client)
    return mcp, client


@pytest.fixture
def call_tool(setup):
    """Helper to call a tool by name."""
    mcp, _ = setup

    async def _call(name: str, **kwargs):
        tool = await mcp.get_tool(name)
        return await tool.fn(**kwargs)

    return _call


class TestListIssues:
    @respx.mock
    async def test_default_pagination(self, call_tool):
        route = respx.get("http://redmine.example.com/issues.json").mock(
            return_value=httpx.Response(
                200,
                json={"issues": [], "total_count": 0, "offset": 0, "limit": 25},
            )
        )
        result = await call_tool("list_issues")
        assert result["offset"] == 0
        assert result["limit"] == 25
        assert result["total_count"] == 0
        assert result["issues"] == []

    @respx.mock
    async def test_limit_capped_at_100(self, call_tool):
        route = respx.get("http://redmine.example.com/issues.json").mock(
            return_value=httpx.Response(
                200,
                json={"issues": [], "total_count": 0, "offset": 0, "limit": 100},
            )
        )
        await call_tool("list_issues", limit=500)
        request = route.calls[0].request
        assert "limit=100" in str(request.url)

    @respx.mock
    async def test_filters_passed_as_query_params(self, call_tool):
        route = respx.get("http://redmine.example.com/issues.json").mock(
            return_value=httpx.Response(
                200,
                json={"issues": [], "total_count": 0, "offset": 0, "limit": 25},
            )
        )
        await call_tool(
            "list_issues", project_id=5, status_id="open", tracker_id=2, sort="updated_on:desc"
        )
        url = str(route.calls[0].request.url)
        assert "project_id=5" in url
        assert "status_id=open" in url
        assert "tracker_id=2" in url
        assert "sort=updated_on" in url


class TestGetIssue:
    @respx.mock
    async def test_returns_issue_detail(self, call_tool):
        respx.get("http://redmine.example.com/issues/42.json").mock(
            return_value=httpx.Response(
                200,
                json={
                    "issue": {
                        "id": 42,
                        "subject": "Test issue",
                        "project": {"id": 1, "name": "Test"},
                        "tracker": {"id": 1, "name": "Bug"},
                        "status": {"id": 1, "name": "New"},
                        "priority": {"id": 2, "name": "Normal"},
                    }
                },
            )
        )
        result = await call_tool("get_issue", issue_id=42)
        assert result["id"] == 42
        assert result["subject"] == "Test issue"

    async def test_rejects_non_positive_id(self, call_tool):
        result = await call_tool("get_issue", issue_id=0)
        assert "error" in result
        assert "positive integer" in result["error"]

    async def test_rejects_negative_id(self, call_tool):
        result = await call_tool("get_issue", issue_id=-1)
        assert "error" in result

    @respx.mock
    async def test_valid_include_parameter(self, call_tool):
        route = respx.get("http://redmine.example.com/issues/1.json").mock(
            return_value=httpx.Response(200, json={"issue": {"id": 1}})
        )
        await call_tool("get_issue", issue_id=1, include="journals,watchers")
        assert "include=journals" in str(route.calls[0].request.url)

    async def test_rejects_invalid_include(self, call_tool):
        result = await call_tool("get_issue", issue_id=1, include="invalid_value")
        assert "error" in result
        assert "Unsupported" in result["error"]


class TestCreateIssue:
    @respx.mock
    async def test_creates_issue_with_required_fields(self, call_tool):
        route = respx.post("http://redmine.example.com/issues.json").mock(
            return_value=httpx.Response(
                201, json={"issue": {"id": 99, "subject": "New issue", "project": {"id": 1}}}
            )
        )
        result = await call_tool("create_issue", project_id=1, subject="New issue")
        assert result["id"] == 99

    async def test_rejects_empty_subject(self, call_tool):
        result = await call_tool("create_issue", project_id=1, subject="")
        assert "error" in result
        assert "subject" in result["error"]

    async def test_rejects_whitespace_subject(self, call_tool):
        result = await call_tool("create_issue", project_id=1, subject="   ")
        assert "error" in result

    @respx.mock
    async def test_optional_fields_included_in_body(self, call_tool):
        import json

        route = respx.post("http://redmine.example.com/issues.json").mock(
            return_value=httpx.Response(201, json={"issue": {"id": 1}})
        )
        await call_tool(
            "create_issue",
            project_id=1,
            subject="Test",
            description="A description",
            priority_id=3,
            estimated_hours=5.0,
        )
        body = json.loads(route.calls[0].request.content)
        assert body["issue"]["description"] == "A description"
        assert body["issue"]["priority_id"] == 3
        assert body["issue"]["estimated_hours"] == 5.0

    @respx.mock
    async def test_start_and_due_date_included_in_body(self, call_tool):
        import json

        route = respx.post("http://redmine.example.com/issues.json").mock(
            return_value=httpx.Response(201, json={"issue": {"id": 1}})
        )
        await call_tool(
            "create_issue",
            project_id=1,
            subject="Test",
            start_date="2026-01-01",
            due_date="2026-01-31",
        )
        body = json.loads(route.calls[0].request.content)
        assert body["issue"]["start_date"] == "2026-01-01"
        assert body["issue"]["due_date"] == "2026-01-31"

    @respx.mock
    async def test_returns_validation_error_from_redmine(self, call_tool):
        respx.post("http://redmine.example.com/issues.json").mock(
            return_value=httpx.Response(
                422, json={"errors": ["Subject cannot be blank"]}
            )
        )
        result = await call_tool("create_issue", project_id=1, subject="x")
        assert "error" in result
        assert result["status_code"] == 422

    @respx.mock
    async def test_done_ratio_included_in_body(self, call_tool):
        import json

        route = respx.post("http://redmine.example.com/issues.json").mock(
            return_value=httpx.Response(201, json={"issue": {"id": 1}})
        )
        await call_tool("create_issue", project_id=1, subject="Test", done_ratio=50)
        body = json.loads(route.calls[0].request.content)
        assert body["issue"]["done_ratio"] == 50

    async def test_rejects_done_ratio_above_100(self, call_tool):
        result = await call_tool(
            "create_issue", project_id=1, subject="Test", done_ratio=150
        )
        assert "error" in result
        assert "done_ratio" in result["error"]

    async def test_rejects_negative_done_ratio(self, call_tool):
        result = await call_tool(
            "create_issue", project_id=1, subject="Test", done_ratio=-10
        )
        assert "error" in result
        assert "done_ratio" in result["error"]


class TestUpdateIssue:
    @respx.mock
    async def test_updates_successfully(self, call_tool):
        respx.put("http://redmine.example.com/issues/1.json").mock(
            return_value=httpx.Response(204)
        )
        result = await call_tool("update_issue", issue_id=1, subject="Updated")
        assert result["status"] == "success"
        assert result["issue_id"] == 1

    @respx.mock
    async def test_notes_included_in_body(self, call_tool):
        import json

        route = respx.put("http://redmine.example.com/issues/1.json").mock(
            return_value=httpx.Response(204)
        )
        await call_tool("update_issue", issue_id=1, notes="Added a comment")
        body = json.loads(route.calls[0].request.content)
        assert body["issue"]["notes"] == "Added a comment"

    async def test_rejects_invalid_id(self, call_tool):
        result = await call_tool("update_issue", issue_id=-5)
        assert "error" in result

    @respx.mock
    async def test_done_ratio_included_in_body(self, call_tool):
        import json

        route = respx.put("http://redmine.example.com/issues/1.json").mock(
            return_value=httpx.Response(204)
        )
        await call_tool("update_issue", issue_id=1, done_ratio=75)
        body = json.loads(route.calls[0].request.content)
        assert body["issue"]["done_ratio"] == 75

    @respx.mock
    async def test_done_ratio_zero_included_in_body(self, call_tool):
        import json

        route = respx.put("http://redmine.example.com/issues/1.json").mock(
            return_value=httpx.Response(204)
        )
        await call_tool("update_issue", issue_id=1, done_ratio=0)
        body = json.loads(route.calls[0].request.content)
        assert body["issue"]["done_ratio"] == 0

    async def test_rejects_done_ratio_above_100(self, call_tool):
        result = await call_tool("update_issue", issue_id=1, done_ratio=101)
        assert "error" in result
        assert "done_ratio" in result["error"]

    async def test_rejects_negative_done_ratio(self, call_tool):
        result = await call_tool("update_issue", issue_id=1, done_ratio=-1)
        assert "error" in result
        assert "done_ratio" in result["error"]


class TestDeleteIssue:
    @respx.mock
    async def test_deletes_successfully(self, call_tool):
        respx.delete("http://redmine.example.com/issues/42.json").mock(
            return_value=httpx.Response(200)
        )
        result = await call_tool("delete_issue", issue_id=42)
        assert result["status"] == "success"
        assert result["deleted_issue_id"] == 42

    async def test_rejects_non_positive_id(self, call_tool):
        result = await call_tool("delete_issue", issue_id=0)
        assert "error" in result


class TestWatchers:
    @respx.mock
    async def test_add_watcher_correct_path(self, call_tool):
        route = respx.post("http://redmine.example.com/issues/10/watchers.json").mock(
            return_value=httpx.Response(201)
        )
        result = await call_tool("add_watcher", issue_id=10, user_id=5)
        assert result["status"] == "success"
        assert route.called

    @respx.mock
    async def test_remove_watcher_correct_path(self, call_tool):
        route = respx.delete(
            "http://redmine.example.com/issues/10/watchers/5.json"
        ).mock(return_value=httpx.Response(200))
        result = await call_tool("remove_watcher", issue_id=10, user_id=5)
        assert result["status"] == "success"
        assert route.called

    async def test_add_watcher_rejects_invalid_issue_id(self, call_tool):
        result = await call_tool("add_watcher", issue_id=-1, user_id=5)
        assert "error" in result

    async def test_add_watcher_rejects_invalid_user_id(self, call_tool):
        result = await call_tool("add_watcher", issue_id=1, user_id=0)
        assert "error" in result

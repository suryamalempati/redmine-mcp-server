# Redmine MCP Server

An MCP (Model Context Protocol) server that connects AI assistants like [Kiro](https://kiro.dev) to your Redmine instance. It exposes 18 tools covering Issues, Projects, Time Entries, and Search — allowing your AI assistant to create issues, update projects, search across resources, and more, all through natural conversation.

## What it does

Once configured, you can ask your AI assistant things like:

- "List all open issues assigned to me"
- "Create a bug report for the login page crash"
- "Search for issues related to database migration"
- "Archive the old-website project"
- "Add John as a watcher on issue #42"

The server handles authentication, pagination, input validation, and error handling automatically.

## Available tools

| Domain | Tools |
|--------|-------|
| Issues | list, get, create, update, update note, delete, add watcher, remove watcher |
| Projects | list, get, create, update, delete, archive, unarchive |
| Search | full-text search across all Redmine resources |

## Prerequisites

1. **Python 3.10+** installed on your machine
2. **uv** — a fast Python package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
3. **Redmine API key** — get yours from your Redmine instance:
   - Log in to Redmine
   - Go to **My Account** (top-right menu)
   - In the right sidebar, find **API access key** and click **Show**
   - Copy the key

## Setup with Kiro

### Step 1: Add the MCP server config to Kiro

Create or edit `~/.kiro/settings/mcp.json` (this makes it available across all your projects):

```json
{
  "mcpServers": {
    "redmine": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/bizcloud-experts/redmine-mcp-server.git", "redmine-mcp-server"],
      "env": {
        "REDMINE_URL": "https://your-redmine-instance.com",
        "REDMINE_API_KEY": "your-api-key-here"
      },
      "disabled": false
    }
  }
}
```

Replace:
- `https://your-redmine-instance.com` with your Redmine URL
- `your-api-key-here` with your Redmine API key

You can also place this in `.kiro/settings/mcp.json` within a specific workspace if you only want it available there.

### Step 2: Open Kiro

The MCP server will start automatically when Kiro launches. You can verify it's working by asking: "List my Redmine projects."

### Alternative: If git is not installed

If you get a "Git executable not found" error, you can use a zip-based install that doesn't require git on your machine:

```json
{
  "mcpServers": {
    "redmine": {
      "command": "uvx",
      "args": ["--from", "redmine-mcp-server @ https://github.com/bizcloud-experts/redmine-mcp-server/archive/refs/heads/main.zip", "redmine-mcp-server"],
      "env": {
        "REDMINE_URL": "https://your-redmine-instance.com",
        "REDMINE_API_KEY": "your-api-key-here"
      },
      "disabled": false
    }
  }
}
```

## Alternative setup: Local install

If you prefer to run from a local clone instead of `uvx`:

```bash
git clone https://github.com/bizcloud-experts/redmine-mcp-server.git
cd redmine-mcp-server
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install .
```

Then use this MCP config instead:

```json
{
  "mcpServers": {
    "redmine": {
      "command": "/absolute/path/to/redmine-mcp/.venv/bin/redmine-mcp-server",
      "args": [],
      "env": {
        "REDMINE_URL": "https://your-redmine-instance.com",
        "REDMINE_API_KEY": "your-api-key-here"
      },
      "disabled": false
    }
  }
}
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "REDMINE_URL environment variable is missing" | Make sure `REDMINE_URL` is set in the MCP config's `env` block |
| "REDMINE_API_KEY environment variable is missing" | Ensure `REDMINE_API_KEY` is set in the MCP config's `env` block |
| "Authentication failed: invalid or expired API key" | Verify your API key is correct in Redmine → My Account → API access key |
| "Connection failed" | Check that the `REDMINE_URL` is reachable from your machine |
| Tools not appearing in Kiro | Confirm the `mcp.json` file is in the right location and `"disabled"` is `false` |
| "Git executable not found" | Git is not installed or not on PATH. Use the [zip-based install](#alternative-if-git-is-not-installed) instead, or install git and restart your terminal |

## Development

```bash
git clone https://github.com/bizcloud-experts/redmine-mcp-server.git
cd redmine-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

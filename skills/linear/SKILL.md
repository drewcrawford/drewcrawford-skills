---
name: linear
description: Interact with Linear.app using the linearis CLI tool. Use when the user wants to work with Linear issues, comments, projects, labels, or download embedded files. This tool provides JSON output for all operations.
triggers:
  - "linear"
  - "linearis"
  - "linear issue"
  - "linear ticket"
  - "linear comment"
  - "linear project"
  - "linear label"
  - "create issue in linear"
  - "update linear issue"
  - "search linear"
  - "list linear issues"
  - "linear attachments"
  - "linear embeds"
  - "download from linear"
---

You are an expert at using the linearis CLI tool to interact with Linear.app. The linearis tool provides JSON output for all operations, making it easy to parse and work with the data programmatically.

**Prerequisite:** this skill requires the [linearis](https://github.com/linearis-oss/linearis) CLI — install it with `npm i -g linearis`.

## Key Capabilities

The linearis CLI can:
1. **Issues**: Create, list, read, search, and update issues
2. **Comments**: Create comments on issues
3. **Labels**: List and manage labels
4. **Projects**: List projects
5. **Embeds**: Download embedded files from Linear storage

## Important Notes

- **Issue IDs**: Both UUID and identifiers like ABC-123 are supported when passing issue IDs
- **API Token**: The tool requires a Linear API token. Check if it's configured with `--api-token` option or as an environment variable
- **JSON Output**: All commands return JSON output for easy parsing

## Common Tasks

### Working with Issues

#### Create a new issue
```bash
linearis issues create "Issue Title" \
  --description "Detailed description" \
  --team "team-key" \
  --assignee "user-id" \
  --priority 2 \
  --project "project-name" \
  --labels "bug,urgent" \
  --status "In Progress"
```

#### List issues
```bash
linearis issues list --limit 25
```

#### Search issues
```bash
linearis issues search "search query" \
  --team "team-key" \
  --assignee "user-id" \
  --project "project-name" \
  --states "In Progress,Todo" \
  --limit 10
```

#### Get issue details
```bash
linearis issues read ABC-123
# or
linearis issues read "uuid-here"
```

#### Update an issue
```bash
linearis issues update ABC-123 \
  --title "New Title" \
  --description "Updated description" \
  --state "Done" \
  --priority 1 \
  --assignee "new-user-id" \
  --project "new-project"
```

#### Managing issue labels
```bash
# Add labels (default behavior)
linearis issues update ABC-123 --labels "bug,feature"

# Replace all labels
linearis issues update ABC-123 --labels "new-label" --label-by overwriting

# Clear all labels
linearis issues update ABC-123 --clear-labels
```

#### Managing parent-child relationships
```bash
# Set parent ticket
linearis issues update ABC-123 --parent-ticket DEF-456

# Clear parent relationship
linearis issues update ABC-123 --clear-parent-ticket
```

### Working with Comments

```bash
linearis comments create ABC-123 --body "This is a comment on the issue"
```

### Working with Labels

```bash
# List all labels
linearis labels list

# List labels for a specific team
linearis labels list --team "team-key"
```

### Working with Projects

```bash
linearis projects list --limit 100
```

### Downloading Embedded Files

```bash
# Download with default filename
linearis embeds download "linear-storage-url"

# Download to specific path
linearis embeds download "linear-storage-url" --output ./downloads/file.pdf

# Overwrite if exists
linearis embeds download "linear-storage-url" --output ./file.pdf --overwrite
```

## Parsing JSON Output

Since linearis returns JSON, you can easily parse the output:

```bash
# Get issue titles from search
linearis issues search "bug" | jq -r '.[] | .title'

# Count issues in a project
linearis issues search "" --project "my-project" | jq '. | length'

# Get assignee names
linearis issues list | jq -r '.[] | .assignee.name // "Unassigned"'
```

## Authentication

Make sure the Linear API token is configured either:
1. As an environment variable: `LINEARIS_API_TOKEN`
2. Passed directly: `linearis --api-token YOUR_TOKEN_HERE <command>`

You can verify authentication by running a simple command like:
```bash
linearis projects list
```

## Error Handling

Always check the exit code and parse any error messages from the JSON output. The tool will return non-zero exit codes on failure.

## Tips

1. Use `linearis usage` to see all available commands and their options
2. Most commands support both names and IDs for entities (teams, projects, users)
3. Priority levels are 1-4 (1 being highest priority)
4. When creating issues with milestones, you must also specify the project
5. The search functionality is quite powerful - use it to filter issues efficiently

When users ask you to work with Linear, use these commands to help them manage their issues, projects, and workflow efficiently. Always parse the JSON output to provide clear, formatted responses to the user.
# Skill Writer Technical Reference

## YAML Frontmatter Specification

### Required Fields

#### name
- **Type**: string
- **Pattern**: `^[a-z0-9-]+$`
- **Max Length**: 64 characters
- **Description**: Unique identifier for the skill
- **Examples**: `pdf-processor`, `api-client`, `data-analyzer`

#### description
- **Type**: string
- **Max Length**: 1024 characters
- **Purpose**: Discovery and activation trigger
- **Must Include**:
  - Primary functionality
  - Trigger keywords
  - Use case scenarios

### Optional Fields

#### allowed-tools
- **Type**: string (comma-separated list)
- **Claude Code Only**: Not supported in browser version
- **Valid Tools**:
  - `Read` - Read files
  - `Write` - Create/overwrite files
  - `Edit` - Modify files
  - `Glob` - Search file patterns
  - `Grep` - Search file contents
  - `Bash` - Execute commands
  - `WebFetch` - Fetch web content
  - `WebSearch` - Search the web
  - `Task` - Launch subagents
  - `TodoWrite` - Manage tasks
  - `NotebookEdit` - Edit Jupyter notebooks
  - `BashOutput` - Read background process output
  - `KillShell` - Terminate processes
  - `AskUserQuestion` - Query user for input
  - `Skill` - Invoke other skills
  - `SlashCommand` - Execute slash commands

## File System Structure

### Directory Layout
```
.claude/skills/           # Project skills (version controlled)
├── skill-one/
│   ├── SKILL.md
│   ├── reference.md
│   └── scripts/
└── skill-two/
    └── SKILL.md

~/.claude/skills/         # Personal skills (user-specific)
├── personal-skill/
│   └── SKILL.md
└── another-skill/
    ├── SKILL.md
    └── templates/
```

### Installation Methods

#### Personal Skills Installation

**Direct Copy Method:**
```bash
# Create skill directory
mkdir -p ~/.claude/skills/my-skill

# Copy all skill files
cp -r /source/path/my-skill/* ~/.claude/skills/my-skill/

# Set permissions if needed
chmod +x ~/.claude/skills/my-skill/scripts/*.sh
```

**Symbolic Link Method (Recommended):**
```bash
# Link from development directory
ln -s ~/Code/skills/my-skill ~/.claude/skills/my-skill

# Example for this skill-writer skill
ln -s ~/Code/skills/write-skills ~/.claude/skills/write-skills

# Verify symlink
readlink ~/.claude/skills/my-skill
```

**Benefits of Symlinks:**
- Immediate updates when editing source
- Easy version control integration
- Shared development across machines
- No duplication of files

#### Project Skills Installation

```bash
# From project root
mkdir -p .claude/skills/project-skill
cp -r /source/skill/* .claude/skills/project-skill/

# Or use symlink for development
ln -s ../../shared-skills/my-skill .claude/skills/my-skill
```

#### Managing Multiple Skills

```bash
# Install multiple skills at once
for skill in skill1 skill2 skill3; do
    ln -s ~/Code/skills/$skill ~/.claude/skills/$skill
done

# List installed skills
ls -la ~/.claude/skills/

# Remove a skill
rm ~/.claude/skills/skill-name  # If symlink
rm -rf ~/.claude/skills/skill-name  # If directory
```

### File Loading Order
1. SKILL.md - Always loaded when skill activates
2. Additional .md files - Loaded on demand via explicit reference
3. Scripts/templates - Never auto-loaded, must be explicitly read

## Activation Logic

### Discovery Process
1. Claude scans all skill locations
2. Reads name and description from frontmatter
3. Builds activation index

### Matching Algorithm
1. User request analyzed for keywords
2. Description fields searched for matches
3. Best matching skill(s) selected
4. SKILL.md content loaded into context

### Priority Resolution
When multiple skills have same name:
1. Project skills (`.claude/skills/`)
2. Personal skills (`~/.claude/skills/`)
3. Plugin skills (bundled with plugins)

## Progressive Disclosure Pattern

### Initial Load
Only SKILL.md is loaded initially to minimize context usage.

### Reference Loading
Additional files loaded when explicitly referenced:
```markdown
For detailed API documentation, see reference.md
For usage examples, see examples.md
```

### Script Execution
Scripts must be explicitly invoked:
```markdown
Run the validation script:
`scripts/validate.py --input data.json`
```

## Error Handling

### Common Errors

#### Invalid YAML
```yaml
---
name: my skill  # ERROR: spaces not allowed
description: Test
---
```

#### Missing Frontmatter
```markdown
# My Skill  # ERROR: no YAML frontmatter
Content here
```

#### Malformed Frontmatter
```yaml
--  # ERROR: must be three dashes
name: test
---
```

### Validation Rules

1. **Frontmatter Delimiters**: Must use exactly `---`
2. **Indentation**: Use spaces, not tabs
3. **String Values**: Quote if containing special characters
4. **Field Names**: Case-sensitive, lowercase
5. **Line Endings**: LF or CRLF acceptable

## Performance Considerations

### Context Efficiency
- Keep SKILL.md under 500 lines
- Use reference files for detailed documentation
- Avoid redundant information
- Structure content hierarchically

### Activation Speed
- Specific descriptions activate faster
- Avoid generic terms that match many contexts
- Include unique trigger phrases
- Balance specificity with discoverability

## Security Considerations

### Tool Restrictions
Use `allowed-tools` to enforce security boundaries:

```yaml
# Read-only skill
allowed-tools: Read, Grep, Glob

# No file system access
allowed-tools: WebFetch, WebSearch

# No external access
allowed-tools: Read, Write, Edit
```

### Script Security
- Never auto-execute scripts
- Require explicit user confirmation
- Validate inputs before processing
- Use absolute paths for file operations

## Advanced Patterns

### Multi-Mode Skills
Support different operational modes:
```yaml
---
name: database-manager
description: Manage databases - backup, restore, migrate, query. Handles PostgreSQL, MySQL, SQLite operations and maintenance tasks.
---

# Database Manager

## Mode Selection
Based on your request, I'll operate in:
- **Backup Mode**: Creating database backups
- **Restore Mode**: Restoring from backups
- **Migration Mode**: Schema migrations
- **Query Mode**: Running SQL queries
```

### Conditional Activation
Include activation conditions in description:
```yaml
description: Process AWS Lambda functions. Use when working with Lambda, serverless functions, or when AWS CLI is configured.
```

### Skill Composition
Reference other skills for complex workflows:
```markdown
For API authentication, I'll use the auth-manager skill first.
For data visualization, I'll invoke the chart-generator skill.
```

## Testing Checklist

### Pre-deployment
- [ ] YAML syntax valid
- [ ] Name follows convention
- [ ] Description includes triggers
- [ ] Content well-structured
- [ ] Examples provided
- [ ] Scripts executable
- [ ] Tool restrictions appropriate

### Post-deployment
- [ ] Skill discoverable
- [ ] Activates on expected queries
- [ ] Doesn't activate incorrectly
- [ ] All features functional
- [ ] Error handling works
- [ ] Performance acceptable

## Version Compatibility

### Claude Code CLI
- Full skill support
- All tools available
- Script execution enabled
- Background processes supported

### Claude Browser
- Basic skill support
- Limited tool access
- No script execution
- No background processes

## Debugging

### Enable Debug Mode
```bash
claude --debug
```

### Check Skill Loading
```bash
# List discovered skills
claude --list-skills

# Verify specific skill
claude --check-skill skill-name
```

### Common Issues

1. **Skill not found**: Check file location and naming
2. **YAML parse error**: Validate syntax with online tool
3. **Not activating**: Review description triggers
4. **Tool restrictions ignored**: Verify Claude Code version
5. **Scripts failing**: Check permissions and dependencies
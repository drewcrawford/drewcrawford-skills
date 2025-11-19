---
name: skill-writer
description: Create and write Claude Code skills. Use when the user asks to write a skill, create a new skill, design a skill for a specific task (like using bash scripts, web services, APIs), or needs help structuring skill files. Also use when discussing skill best practices, metadata format, or troubleshooting skill activation.
---

# Skill Writer

Expert guidance for creating Claude Code skills that extend functionality through modular, discoverable capabilities.

## Core Concepts

Skills are model-invoked capabilities that Claude autonomously activates based on context. Unlike slash commands requiring explicit invocation, skills trigger automatically when Claude recognizes relevant scenarios.

## Skill Structure

Every skill requires this directory structure:
```
skill-name/
├── SKILL.md (required - main instructions)
├── reference.md (optional - detailed technical docs)
├── examples.md (optional - usage demonstrations)
├── scripts/ (optional - utility scripts)
└── templates/ (optional - reusable templates)
```

## Writing SKILL.md

### Required Frontmatter
```yaml
---
name: lowercase-with-hyphens  # Max 64 chars, no spaces
description: What it does and when to use it  # Max 1024 chars
allowed-tools: Optional tool restrictions  # Claude Code only
---
```

### Name Requirements
- Lowercase letters, numbers, hyphens only
- No spaces or underscores
- Maximum 64 characters
- Must be unique within scope

### Description Best Practices
Write descriptions that are **specific** and include:
1. **Capabilities**: What the skill does
2. **Trigger terms**: Keywords users would mention
3. **Use cases**: When to activate

**Good Example:**
> "Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction."

**Bad Example:**
> "Helps with documents"

### Tool Restrictions (Optional)
Control which tools Claude can use:
```yaml
allowed-tools: Read, Grep, Glob  # Read-only operations
allowed-tools: Read, Write, Edit  # File operations only
```

## Content Guidelines

### Keep Focused Scope
- One capability per skill
- Split broad functionality across multiple skills
- Clear boundaries prevent activation conflicts

### Structure Content Progressively
1. **Overview**: Brief capability summary
2. **Instructions**: Step-by-step guidance
3. **Examples**: Concrete demonstrations
4. **Reference**: Link to detailed docs if needed

### Writing Clear Instructions
- Use imperative mood ("Create", "Check", "Validate")
- Number sequential steps
- Include error handling guidance
- Specify output formats
- Note dependencies or prerequisites

## Skill Locations

Skills can exist in three locations:
- **Personal**: `~/.claude/skills/skill-name/`
- **Project**: `.claude/skills/skill-name/`
- **Plugin**: Bundled with installed plugins

Priority: Project > Personal > Plugin (when names conflict)

## Installing Skills

### Installing Personal Skills

Personal skills are available across all projects. To install a personal skill, copy the skill directory to `~/.claude/skills/`:

```bash
# Create personal skills directory if it doesn't exist
mkdir -p ~/.claude/skills

# Copy the entire skill folder
cp -r /path/to/skill-name ~/.claude/skills/
```

Example:
```bash
# Install the write-skills skill
cp -r ~/Code/skills/write-skills ~/.claude/skills/
```

To update an existing skill, simply copy it again to overwrite:
```bash
# Update a skill by copying again
cp -r /path/to/skill-name ~/.claude/skills/
```

### Installing Project Skills

Project skills are specific to a single project:
```bash
# Navigate to project root
cd /path/to/project

# Create project skills directory
mkdir -p .claude/skills

# Copy the entire skill folder
cp -r /path/to/skill-name .claude/skills/
```

### Verifying Installation

After installing, verify the skill is discoverable:
1. Ask Claude: "What skills are available?"
2. Test activation with a relevant query
3. Check for error messages in debug mode: `claude --debug`

## Common Skill Patterns

### API Integration Skill
```yaml
---
name: api-client
description: Interact with XYZ API for data retrieval and submission. Use when user mentions XYZ service, API operations, or needs to fetch/post data.
allowed-tools: WebFetch, Read, Write
---
```

### Data Processing Skill
```yaml
---
name: data-analyzer
description: Analyze CSV, JSON, and Excel files for patterns, statistics, and visualizations. Use for data analysis, statistical operations, or when user mentions spreadsheets.
---
```

### Automation Skill
```yaml
---
name: build-automator
description: Automate build processes, CI/CD pipelines, and deployment workflows. Use when setting up automation, build scripts, or continuous integration.
---
```

## Testing Skills

### Verification Steps
1. Check skill discovery: Ask "What skills are available?"
2. Test activation with matching queries
3. Verify tool restrictions work correctly
4. Validate script execution permissions

### Debug Mode
Run Claude Code with debug flag for detailed logs:
```bash
claude --debug
```

## Troubleshooting

### Skill Not Activating
- Verify description includes specific trigger terms
- Check YAML syntax (proper `---` markers, no tabs)
- Ensure file path is correct
- Validate name follows requirements

### Multiple Skills Conflicting
- Use distinct, specific trigger terms
- Narrow scope of each skill
- Consider combining if overlap is unavoidable

### Scripts Not Working
- Set execute permissions: `chmod +x scripts/*.py`
- Use forward slashes in paths
- Verify required packages installed
- Test scripts independently first

## Best Practices Summary

1. **Be Specific**: Clear descriptions with trigger keywords
2. **Stay Focused**: One capability per skill
3. **Progressive Disclosure**: Load reference files only when needed
4. **Test Thoroughly**: Verify activation and functionality
5. **Document Well**: Include examples and edge cases
6. **Version Control**: Track project skills in git
7. **Tool Restrictions**: Limit permissions when appropriate

## Creating Your Skill

When asked to create a skill:
1. Identify the core capability and use cases
2. Choose a descriptive, lowercase-hyphenated name
3. Write a specific description with trigger terms
4. Structure content progressively in SKILL.md
5. Add examples if behavior is complex
6. Include scripts/templates for reusable components
7. Test activation with relevant queries
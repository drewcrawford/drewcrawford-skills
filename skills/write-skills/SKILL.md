---
name: write-skills
description: Create and write portable Agent Skills. Use when the user asks to write a skill, create a new skill, design a skill for a specific task such as scripts or APIs, structure SKILL.md files, improve skill metadata, or troubleshoot skill activation across compatible agents.
---

# Skill Writer

Expert guidance for creating portable Agent Skills that extend compatible agents through modular, discoverable capabilities.

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

### Leave permissions to the client

Omit the experimental `allowed-tools` field. Tool names and permission
semantics differ between clients, and modern clients can classify each tool
call using the full execution context. Describe the required operations and
dependencies in the instructions and `compatibility` metadata instead.

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

The Agent Skills specification defines the contents of a skill, not where it
must be installed. The cross-client convention is:

- **Personal**: `~/.agents/skills/skill-name/`
- **Project**: `.agents/skills/skill-name/`

Clients may also scan native locations such as `~/.claude/skills/` or bundle
skills in plugins. Project skills normally override personal skills when names
conflict, but exact precedence is client-specific.

## Installing Skills

### Installing Personal Skills

Personal skills are available across all projects. Install portable personal
skills in `~/.agents/skills/`:

```bash
mkdir -p ~/.agents/skills
cp -R /path/to/skill-name ~/.agents/skills/
```

If a client does not scan the shared directory, link the canonical copy into
its native directory. For Claude Code:

```bash
mkdir -p ~/.claude/skills
ln -s ~/.agents/skills/skill-name ~/.claude/skills/skill-name
```

### Installing Project Skills

Project skills are specific to a single project:
```bash
mkdir -p .agents/skills
cp -R /path/to/skill-name .agents/skills/
```

### Verifying Installation

After installing, verify the skill is discoverable:
1. Ask the agent: "What skills are available?"
2. Test activation with a relevant query
3. Use the client's skill listing or debug mode to check discovery errors

## Common Skill Patterns

### API Integration Skill
```yaml
---
name: api-client
description: Interact with XYZ API for data retrieval and submission. Use when user mentions XYZ service, API operations, or needs to fetch/post data.
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

### Claude Code Debug Mode

For Claude Code specifically, use its debug flag for detailed logs:
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

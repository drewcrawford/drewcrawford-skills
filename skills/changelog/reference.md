# Changelog Skill - Technical Reference

## Overview

The changelog skill generates and maintains CHANGELOG files with personality, transforming git commits and project updates into engaging release notes inspired by Slack's delightfully human approach.

## Core Components

### 1. Changelog Generation Engine

#### Git History Analysis
```python
def analyze_commits(since_tag=None, until_tag="HEAD", limit=None):
    """
    Extract and categorize commits from git history

    Parameters:
    - since_tag: Starting point (tag, commit hash, or date)
    - until_tag: Ending point (default: HEAD)
    - limit: Maximum number of commits to analyze

    Returns categorized commit data:
    - features: New functionality
    - fixes: Bug fixes
    - enhancements: Improvements to existing features
    - breaking: Breaking changes (detected via keywords)
    - docs: Documentation updates
    - internal: Refactoring, tests, build changes
    """
```

#### Commit Categorization Rules
- **Features**: `feat:`, `feature:`, `add:`, `new:`
- **Fixes**: `fix:`, `bugfix:`, `patch:`, `resolve:`
- **Enhancements**: `enhance:`, `improve:`, `update:`, `optimize:`
- **Breaking**: `BREAKING CHANGE:`, `breaking:`, `!:` (conventional commits)
- **Documentation**: `docs:`, `doc:`, changes to .md files
- **Internal**: `refactor:`, `test:`, `build:`, `ci:`, `chore:`

### 2. Voice Translation System

#### Tone Mapping
```python
TONE_TRANSFORMS = {
    "technical": "friendly",
    "past_tense": "present_active",
    "passive": "active",
    "complex": "simple"
}
```

#### Humor Injection Points
1. **Metaphors**: Technical concepts → relatable imagery
2. **Personification**: The app "does things" sparingly
3. **Wordplay**: Gentle puns that enhance, not distract
4. **Sign-offs**: Occasional British charm ("Cheerio!")

#### Voice Rules
- **Lead with clarity**: Information first, charm second
- **One breath per item**: 1-2 sentences max
- **Scannable structure**: Bullets, clear categories
- **Inclusive language**: Avoid jargon, memes, or dated references

### 3. Format Templates

#### Keep a Changelog Format (Default)
```markdown
# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2025-11-06
### Added
- Feature descriptions with personality

### Changed
- Enhancement descriptions that delight

### Fixed
- Bug fix explanations that reassure

### Removed
- Deprecation notices that don't sting
```

#### GitHub Release Format
```markdown
## What's New 🎉
- Major features that'll make your day

## Improvements 🚀
- Enhancements to existing goodness

## Bug Fixes 🐛
- Things that work properly now

## Under the Hood 🔧
- Technical stuff we sorted out
```

#### Conventional Changelog Format
```markdown
## Version 1.2.0 (2025-11-06)

### Features
* **component**: Description of new capability
* **area**: Another delightful addition

### Bug Fixes
* **module**: What we fixed and why you'll love it
```

### 4. Semantic Versioning Logic

#### Version Bump Rules
```python
def suggest_version_bump(changes, current_version):
    """
    Determine appropriate version bump based on changes

    MAJOR (x.0.0): Breaking changes detected
    MINOR (0.x.0): New features without breaking changes
    PATCH (0.0.x): Only fixes and minor improvements
    """
    if has_breaking_changes(changes):
        return bump_major(current_version)
    elif has_features(changes):
        return bump_minor(current_version)
    else:
        return bump_patch(current_version)
```

### 5. Integration Patterns

#### Existing Changelog Updates
```python
def update_changelog(file_path, new_entries, version=None):
    """
    Merge new entries into existing CHANGELOG.md

    1. Parse existing structure
    2. Detect format (Keep a Changelog, GitHub, custom)
    3. Insert new version section
    4. Preserve existing content
    5. Maintain consistent formatting
    """
```

#### Multi-Repository Support
```python
def aggregate_changes(repos, since_date):
    """
    Collect changes across multiple repositories
    Useful for monorepos or multi-package releases
    """
```

## Command Interface

### Basic Commands
```bash
# Generate from recent commits
changelog generate

# Update existing file
changelog update --version 2.0.0

# Generate for specific range
changelog generate --since v1.0.0 --until HEAD

# Different output formats
changelog generate --format github
changelog generate --format json
```

### Advanced Options
```bash
# Custom voice level (1-5, where 5 is maximum Slack-style)
changelog generate --voice-level 4

# Include commit hashes
changelog generate --include-hashes

# Group by component/area
changelog generate --group-by component

# Draft mode (marks as unreleased)
changelog generate --draft
```

## Git Integration

### Commit Message Parsing
```python
COMMIT_PATTERNS = {
    "conventional": r"^(\w+)(?:\(([^)]+)\))?: (.+)$",
    "github": r"^(\w+): (.+) \(#(\d+)\)$",
    "jira": r"^(\[[\w-]+\]) (.+)$"
}
```

### Tag Detection
```python
def find_release_tags():
    """
    Identify version tags using multiple patterns:
    - Semantic: v1.2.3, 1.2.3
    - Date-based: 2025.11.06
    - Custom: release-*, prod-*
    """
```

### Branch Analysis
```python
def analyze_branch_history(branch="main"):
    """
    Understand release patterns from branch history
    - Detect release cadence
    - Identify feature branches
    - Recognize hotfix patterns
    """
```

## Voice Examples

### Technical → Friendly Transformations

| Original | Transformed |
|----------|-------------|
| "Fixed null pointer exception in auth module" | "Login no longer gets confused when you're in a hurry" |
| "Optimized database queries" | "Everything loads a bit snappier now—you're welcome" |
| "Updated dependency versions" | "Freshened up the ingredients under the hood" |
| "Refactored payment processing" | "Gave the payment system a spa day—same features, better foundation" |
| "Added retry logic to API calls" | "API calls now try harder when the internet hiccups" |

### Category Introductions

| Category | Introduction |
|----------|--------------|
| Features | "Fresh out of the oven:" |
| Fixes | "Squashed some bugs:" |
| Improvements | "Made these things even better:" |
| Breaking | "Heads up—these changes need your attention:" |
| Security | "Keeping you safe with:" |

## Error Handling

### Common Issues
1. **No git repository**: Offer to initialize or work with provided commit list
2. **No commits found**: Suggest checking date ranges or tags
3. **Existing changelog conflict**: Prompt for merge strategy
4. **Unknown format**: Ask for example or use default

### Recovery Strategies
```python
ERROR_RESPONSES = {
    "no_commits": "No changes found—must be perfect already! Try a wider date range?",
    "parse_error": "Hmm, this commit message is cryptic. I'll do my best to summarize.",
    "file_exists": "Found existing CHANGELOG. Should I update it or create a fresh one?",
    "no_version": "What version should this be? I can suggest one based on the changes."
}
```

## Configuration

### Settings Schema
```yaml
changelog:
  format: keep-a-changelog  # or github, conventional, custom
  voice_level: 3            # 1-5, personality intensity
  include_commits: false    # Show commit hashes
  include_authors: false    # Credit contributors
  group_by: type           # type, scope, or component
  date_format: YYYY-MM-DD  # Date formatting
  file_name: CHANGELOG.md  # Output filename
  sections:               # Section customization
    - title: Added
      types: [feat, feature]
    - title: Changed
      types: [enhance, update]
```

### Project-Specific Overrides
```yaml
# .changelog.yml in project root
voice_snippets:
  features: "Shiny new things:"
  fixes: "Tidied up:"

exclude_patterns:
  - "^WIP"
  - "^Merge"

custom_categories:
  - name: Security
    patterns: ["security", "CVE", "vulnerability"]
```

## Testing

### Voice Consistency Tests
```python
def test_voice_consistency():
    """
    Ensure generated text maintains appropriate tone:
    - No snark or negativity
    - Consistent personality level
    - Information clarity preserved
    """
```

### Format Validation
```python
def validate_changelog_format(content, format_type):
    """
    Verify output matches expected format:
    - Proper markdown structure
    - Valid version numbers
    - Correct section headers
    - Appropriate linking
    """
```

## Performance Considerations

- **Commit batching**: Process in chunks for large histories
- **Caching**: Store analyzed commits to avoid re-parsing
- **Incremental updates**: Only process new commits when updating
- **Parallel processing**: Analyze multiple repos concurrently

## Extension Points

### Custom Voice Providers
```python
class VoiceProvider:
    def transform(self, text, category):
        """Override to implement custom voice"""
        pass
```

### Format Plugins
```python
class ChangelogFormat:
    def render(self, changes, metadata):
        """Override to implement custom format"""
        pass
```

### Integration Hooks
- Pre-generation: Validate repository state
- Post-generation: Trigger notifications
- On-update: Sync with issue trackers

## Best Practices

1. **Run regularly**: Don't let changes pile up
2. **Review generated text**: AI suggestions need human touch
3. **Maintain commit quality**: Good commits = great changelogs
4. **Version strategically**: Follow semantic versioning
5. **Test voice changes**: Ensure consistency across releases

Remember: The goal is release notes that inform *and* delight. When in doubt, prioritize clarity—then add the sparkle.
# Changelog Skill

Transform your git commits into delightful release notes with Slack-style personality. Because "bug fixes and performance improvements" is so yesterday.

## Quick Start

Ask Claude to:
- "Create a CHANGELOG for this project"
- "Update the changelog with recent changes"
- "Generate release notes for version 2.0"
- "What changed since the last release?"

## Features

### 🎨 Personality Levels
Choose your voice from professional to playful:
- **Level 1**: Just the facts
- **Level 2**: Friendly but professional
- **Level 3**: Warm and approachable (default)
- **Level 4**: Playfully witty
- **Level 5**: Maximum Slack-style charm

### 📝 Format Support
- Keep a Changelog (default)
- GitHub Releases
- Conventional Commits
- Custom team formats

### 🤖 Smart Categorization
Automatically organizes changes into:
- Features (the new shiny things)
- Fixes (bugs we showed the door)
- Improvements (making good things better)
- Breaking Changes (heads up!)
- Security (keeping you safe)

## How It Works

1. **Analyzes git history**: Reads your commits and understands what changed
2. **Categorizes intelligently**: Groups related changes together
3. **Adds personality**: Transforms technical jargon into friendly prose
4. **Suggests versions**: Follows semantic versioning rules
5. **Updates or creates**: Works with existing CHANGELOGs or starts fresh

## Examples

### Basic Generation
```bash
# Generate from all commits
python3 scripts/changelog_generator.py generate

# Generate with maximum personality
python3 scripts/changelog_generator.py generate --voice-level 5

# Generate for specific range
python3 scripts/changelog_generator.py generate --since v1.0.0 --until HEAD
```

### Update Existing File
```bash
# Update CHANGELOG.md with new version
python3 scripts/changelog_generator.py update --version 2.0.0

# Let it suggest the version
python3 scripts/changelog_generator.py suggest-version
```

## Voice Transformations

| Technical | Friendly |
|-----------|----------|
| "Fixed null pointer exception" | "No more confusion when things get busy" |
| "Optimized database queries" | "Everything loads snappier now" |
| "Refactored authentication" | "Gave login a spa day" |
| "Added retry logic" | "Now tries harder when the internet hiccups" |

## Configuration

Create `.changelog.yml` in your project root for custom settings:

```yaml
changelog:
  voice_level: 3
  format: keep-a-changelog
  sections:
    - title: "Fresh Features"
      types: [feat, feature]
    - title: "Bug Squashing"
      types: [fix, bugfix]
```

## Templates

Find starter templates in `templates/`:
- `keep-a-changelog.md` - Standard format with personality
- `github-release.md` - GitHub-friendly release notes
- `simple.md` - Straightforward and clean
- `conventional.md` - Conventional commits style

## Tips for Best Results

1. **Write clear commit messages**: Good commits make great changelogs
2. **Use conventional commits**: `feat:`, `fix:`, `docs:` help categorization
3. **Review and adjust**: AI suggestions benefit from human touch
4. **Maintain consistency**: Pick a voice level and stick with it

## Requirements

- Python 3.6+
- Git repository
- A sense of humor (optional but recommended)

## Installation

The skill is automatically available when you ask Claude about changelogs, release notes, or version history.

## Contributing

Love the voice? Want to add more personality? Contributions welcome!

## License

Part of the Claude Code Skills collection.

---

*Don't mind us—just making your release notes a joy to read. Cheerio!*
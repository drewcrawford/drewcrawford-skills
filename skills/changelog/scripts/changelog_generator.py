#!/usr/bin/env python3
"""
Changelog Generator - Create delightful release notes with Slack-style voice
"""

import subprocess
import json
import re
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import argparse
from collections import defaultdict

class VoiceTransformer:
    """Transform technical commit messages into friendly, Slack-style release notes"""

    # Voice transformation mappings
    FRIENDLY_TERMS = {
        # Technical -> Friendly
        "null pointer": "confusion",
        "exception": "hiccup",
        "segfault": "crash",
        "memory leak": "memory hungry bug",
        "race condition": "timing issue",
        "undefined": "mystery",
        "deprecated": "retiring",
        "refactor": "spa day",
        "optimize": "speed boost",
        "implement": "add",
        "resolve": "fix",
        "bug": "gremlin",
        "error": "oops",
        "fail": "stumble",
        "timeout": "took too long",
        "async": "background magic",
        "sync": "immediate",
        "database": "data home",
        "api": "connection point",
        "endpoint": "door",
        "authentication": "login",
        "authorization": "permissions",
    }

    # Category-specific voice templates
    VOICE_TEMPLATES = {
        "features": [
            "{feature}—because you asked so nicely",
            "Introducing {feature}",
            "Say hello to {feature}",
            "Brand new: {feature}",
            "{feature} has entered the chat"
        ],
        "fixes": [
            "Fixed that thing where {issue}",
            "{component} no longer {problem}",
            "Squashed the bug where {issue}",
            "{component} behaves properly now",
            "No more {problem}"
        ],
        "improvements": [
            "{component} is now {improvement}",
            "Made {component} {improvement}",
            "{component} got a {improvement}",
            "Gave {component} some love—it's {improvement} now",
            "{action} is about {improvement}"
        ],
        "breaking": [
            "Heads up: {change}",
            "Important: {change}",
            "Action required: {change}",
            "Breaking change: {change} (but you'll love it)"
        ]
    }

    # Sign-offs and flavor text
    SIGN_OFFS = [
        "More to come soon!",
        "Thanks for staying up to date!",
        "Cheerio!",
        "Happy coding!",
        "Enjoy the updates!"
    ]

    @staticmethod
    def transform_technical(text: str, voice_level: int = 3) -> str:
        """Transform technical text to friendly voice

        Args:
            text: Original technical text
            voice_level: 1-5, where 5 is maximum Slack-style

        Returns:
            Transformed friendly text
        """
        if voice_level == 1:
            return text  # Professional, minimal changes

        result = text.lower()

        # Apply friendly term replacements based on voice level
        if voice_level >= 2:
            for technical, friendly in VoiceTransformer.FRIENDLY_TERMS.items():
                if technical in result:
                    # Only replace if voice level is high enough
                    if voice_level >= 3 or technical in ["bug", "error", "fail"]:
                        result = result.replace(technical, friendly)

        # Add personality based on voice level
        if voice_level >= 4:
            # Add light humor
            if "performance" in result:
                result += " (zoom zoom)"
            elif "faster" in result:
                result += " (we asked nicely)"
            elif "fixed" in result:
                result = result.replace("fixed", "fixed").replace(".", "—it works now!")

        if voice_level == 5:
            # Maximum personality
            if "update" in result:
                result += " (you're welcome)"
            elif "new" in result:
                result += " ✨"

        # Capitalize first letter
        return result[0].upper() + result[1:] if result else text

    @staticmethod
    def add_category_flavor(category: str, items: List[str], voice_level: int = 3) -> str:
        """Add category-appropriate introduction"""

        intros = {
            "Added": ["Fresh out of the oven:", "New goodies:", "Shiny new things:"],
            "Fixed": ["Squashed some bugs:", "Made these behave:", "Fixed these quirks:"],
            "Changed": ["Improvements all around:", "Made better:", "Polished up:"],
            "Security": ["Keeping you safe:", "Security updates:", "Protected against:"],
            "Removed": ["Spring cleaning:", "Said goodbye to:", "Retired:"],
            "Deprecated": ["Preparing to retire:", "On the way out:", "Getting ready to sunset:"]
        }

        if voice_level >= 3 and category in intros:
            intro_options = intros[category]
            return intro_options[len(items) % len(intro_options)]

        return ""


class ChangelogGenerator:
    """Generate and manage CHANGELOG files"""

    # Commit categorization patterns
    COMMIT_PATTERNS = {
        "conventional": re.compile(r"^(\w+)(?:\(([^)]+)\))?!?: (.+)$"),
        "github": re.compile(r"^(\w+): (.+) \(#(\d+)\)$"),
        "basic": re.compile(r"^(\w+): (.+)$")
    }

    # Category mappings
    CATEGORY_MAP = {
        "feat": "Added",
        "feature": "Added",
        "add": "Added",
        "new": "Added",
        "fix": "Fixed",
        "bugfix": "Fixed",
        "patch": "Fixed",
        "resolve": "Fixed",
        "enhance": "Changed",
        "improve": "Changed",
        "update": "Changed",
        "optimize": "Changed",
        "perf": "Changed",
        "breaking": "BREAKING",
        "remove": "Removed",
        "delete": "Removed",
        "deprecate": "Deprecated",
        "docs": "Documentation",
        "doc": "Documentation",
        "refactor": "Internal",
        "test": "Internal",
        "build": "Internal",
        "ci": "Internal",
        "chore": "Internal",
        "style": "Internal",
        "security": "Security",
        "sec": "Security",
        "vuln": "Security"
    }

    def __init__(self, repo_path: str = ".", voice_level: int = 3):
        self.repo_path = repo_path
        self.voice_level = voice_level
        self.transformer = VoiceTransformer()

    def run_git_command(self, command: str) -> str:
        """Execute git command and return output"""
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e.stderr}", file=sys.stderr)
            return ""

    def get_commits(self, since: Optional[str] = None, until: str = "HEAD", limit: Optional[int] = None) -> List[Dict]:
        """Fetch and parse git commits"""
        cmd = f"git log --pretty=format:%H|%an|%ae|%at|%s"

        if since:
            cmd += f" {since}..{until}"
        else:
            cmd += f" {until}"

        if limit:
            cmd += f" -n {limit}"

        output = self.run_git_command(cmd)
        if not output:
            return []

        commits = []
        for line in output.split('\n'):
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 5:
                commits.append({
                    'hash': parts[0][:7],  # Short hash
                    'author': parts[1],
                    'email': parts[2],
                    'date': datetime.fromtimestamp(int(parts[3])),
                    'message': '|'.join(parts[4:])  # Handle pipes in message
                })

        return commits

    def categorize_commit(self, message: str) -> Tuple[str, str, str]:
        """Categorize a commit message

        Returns:
            Tuple of (category, scope, description)
        """
        # Check for breaking change indicator
        is_breaking = "BREAKING" in message.upper() or "!" in message

        # Try conventional commit format first
        for pattern_name, pattern in self.COMMIT_PATTERNS.items():
            match = pattern.match(message)
            if match:
                if pattern_name == "conventional":
                    type_str = match.group(1).lower()
                    scope = match.group(2) or ""
                    desc = match.group(3)
                elif pattern_name == "github":
                    type_str = match.group(1).lower()
                    desc = match.group(2)
                    scope = f"#{match.group(3)}"
                else:
                    type_str = match.group(1).lower()
                    desc = match.group(2)
                    scope = ""

                category = "BREAKING" if is_breaking else self.CATEGORY_MAP.get(type_str, "Changed")
                return category, scope, desc

        # Fallback: try to guess from keywords
        lower_msg = message.lower()
        if is_breaking:
            return "BREAKING", "", message
        elif any(word in lower_msg for word in ["fix", "bug", "issue", "problem", "error"]):
            return "Fixed", "", message
        elif any(word in lower_msg for word in ["add", "new", "feat", "implement"]):
            return "Added", "", message
        elif any(word in lower_msg for word in ["remove", "delete"]):
            return "Removed", "", message
        elif any(word in lower_msg for word in ["deprecat"]):
            return "Deprecated", "", message
        elif any(word in lower_msg for word in ["security", "vulnerability", "cve"]):
            return "Security", "", message
        elif any(word in lower_msg for word in ["doc", "readme"]):
            return "Documentation", "", message
        else:
            return "Changed", "", message

    def group_commits(self, commits: List[Dict]) -> Dict[str, List[Dict]]:
        """Group commits by category"""
        grouped = defaultdict(list)

        for commit in commits:
            category, scope, description = self.categorize_commit(commit['message'])

            # Skip internal changes unless verbose
            if category == "Internal" and self.voice_level < 4:
                continue

            # Transform the description based on voice level
            friendly_desc = self.transformer.transform_technical(description, self.voice_level)

            # Add scope if present
            if scope:
                if scope.startswith('#'):
                    friendly_desc = f"{friendly_desc} ({scope})"
                else:
                    friendly_desc = f"**{scope}**: {friendly_desc}"

            grouped[category].append({
                **commit,
                'description': friendly_desc,
                'original_description': description
            })

        return dict(grouped)

    def format_changelog_section(self, version: str, date: str, grouped_commits: Dict[str, List[Dict]]) -> str:
        """Format a changelog section"""
        lines = [f"## [{version}] - {date}"]

        # Order categories
        category_order = ["BREAKING", "Security", "Added", "Changed", "Fixed", "Deprecated", "Removed", "Documentation", "Internal"]

        for category in category_order:
            if category not in grouped_commits:
                continue

            commits = grouped_commits[category]
            if not commits:
                continue

            lines.append("")

            # Add category header with emoji
            emoji_map = {
                "BREAKING": "⚠️ ",
                "Security": "🔒 ",
                "Added": "✨ ",
                "Changed": "🚀 ",
                "Fixed": "🐛 ",
                "Deprecated": "⏳ ",
                "Removed": "🗑️ ",
                "Documentation": "📝 ",
                "Internal": "🔧 "
            }

            emoji = emoji_map.get(category, "") if self.voice_level >= 2 else ""

            # Add category flavor if voice level is high enough
            flavor = self.transformer.add_category_flavor(category, commits, self.voice_level)
            if flavor:
                lines.append(f"### {emoji}{category}")
                lines.append(f"*{flavor}*")
            else:
                lines.append(f"### {emoji}{category}")

            # Add commits as bullet points
            for commit in commits:
                lines.append(f"- {commit['description']}")

        # Add sign-off for high voice levels
        if self.voice_level >= 4 and len(lines) > 2:
            lines.append("")
            lines.append(f"---")
            lines.append(f"*{self.transformer.SIGN_OFFS[len(version) % len(self.transformer.SIGN_OFFS)]}*")

        return '\n'.join(lines)

    def suggest_version(self, current_version: str, grouped_commits: Dict[str, List[Dict]]) -> str:
        """Suggest next version based on changes"""
        if not current_version:
            return "0.1.0"

        parts = current_version.split('.')
        if len(parts) != 3:
            return current_version  # Can't parse, return as is

        try:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            return current_version

        # Determine version bump
        if "BREAKING" in grouped_commits:
            return f"{major + 1}.0.0"
        elif "Added" in grouped_commits or "Security" in grouped_commits:
            return f"{major}.{minor + 1}.0"
        else:
            return f"{major}.{minor}.{patch + 1}"

    def generate(self, since: Optional[str] = None, until: str = "HEAD",
                 version: Optional[str] = None, output_format: str = "markdown") -> str:
        """Generate changelog content"""

        # Get commits
        commits = self.get_commits(since, until)
        if not commits:
            return "No changes found in the specified range."

        # Group commits
        grouped = self.group_commits(commits)
        if not grouped:
            return "No significant changes to report (internal changes hidden)."

        # Get or suggest version
        if not version:
            current_version = self.get_latest_tag()
            version = self.suggest_version(current_version, grouped)

        # Format based on requested format
        date = datetime.now().strftime("%Y-%m-%d")

        if output_format == "markdown":
            return self.format_changelog_section(version, date, grouped)
        elif output_format == "json":
            return json.dumps({
                "version": version,
                "date": date,
                "changes": {k: [c['description'] for c in v] for k, v in grouped.items()}
            }, indent=2)
        else:
            return self.format_changelog_section(version, date, grouped)

    def get_latest_tag(self) -> str:
        """Get the latest git tag"""
        output = self.run_git_command("git describe --tags --abbrev=0")
        return output.strip() if output else "0.0.0"

    def update_file(self, file_path: str, new_content: str, version: str) -> bool:
        """Update existing CHANGELOG file"""
        try:
            # Read existing content
            try:
                with open(file_path, 'r') as f:
                    existing = f.read()
            except FileNotFoundError:
                # Create new file with header
                existing = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
"""

            # Find insertion point (after [Unreleased] or at top)
            lines = existing.split('\n')
            insert_index = 0

            for i, line in enumerate(lines):
                if '[Unreleased]' in line:
                    insert_index = i + 1
                    # Skip empty lines after [Unreleased]
                    while insert_index < len(lines) and not lines[insert_index].strip():
                        insert_index += 1
                    break
                elif line.startswith('## ['):
                    insert_index = i
                    break

            # Insert new content
            if insert_index == 0:
                # No existing versions, append after header
                result = existing + '\n\n' + new_content
            else:
                # Insert before first version or after [Unreleased]
                lines.insert(insert_index, '')
                lines.insert(insert_index + 1, new_content)
                result = '\n'.join(lines)

            # Write back
            with open(file_path, 'w') as f:
                f.write(result)

            return True

        except Exception as e:
            print(f"Error updating file: {e}", file=sys.stderr)
            return False


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Generate delightful changelogs")
    parser.add_argument('action', choices=['generate', 'update', 'suggest-version'],
                       help="Action to perform")
    parser.add_argument('--since', help="Starting point (tag, commit, or date)")
    parser.add_argument('--until', default='HEAD', help="Ending point (default: HEAD)")
    parser.add_argument('--version', help="Version number for this release")
    parser.add_argument('--voice-level', type=int, default=3, choices=range(1, 6),
                       help="Voice personality level (1=professional, 5=maximum fun)")
    parser.add_argument('--format', choices=['markdown', 'json'], default='markdown',
                       help="Output format")
    parser.add_argument('--file', default='CHANGELOG.md',
                       help="Changelog file path (for update action)")
    parser.add_argument('--limit', type=int, help="Limit number of commits")

    args = parser.parse_args()

    generator = ChangelogGenerator(voice_level=args.voice_level)

    if args.action == 'generate':
        content = generator.generate(args.since, args.until, args.version, args.format)
        print(content)

    elif args.action == 'update':
        content = generator.generate(args.since, args.until, args.version)
        if generator.update_file(args.file, content, args.version or generator.get_latest_tag()):
            print(f"Successfully updated {args.file}")
        else:
            print("Failed to update changelog", file=sys.stderr)
            sys.exit(1)

    elif args.action == 'suggest-version':
        commits = generator.get_commits(args.since, args.until, args.limit)
        grouped = generator.group_commits(commits)
        current = generator.get_latest_tag()
        suggested = generator.suggest_version(current, grouped)
        print(f"Current version: {current}")
        print(f"Suggested version: {suggested}")

        # Explain why
        if "BREAKING" in grouped:
            print("Reason: Breaking changes detected")
        elif "Added" in grouped:
            print("Reason: New features added")
        elif "Security" in grouped:
            print("Reason: Security fixes (recommend minor bump)")
        else:
            print("Reason: Bug fixes and minor changes only")


if __name__ == "__main__":
    main()
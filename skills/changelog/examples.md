# Changelog Skill - Usage Examples

## Basic Usage

### Generate Initial Changelog

**User Request:**
```
"Create a CHANGELOG for this project"
```

**Skill Response:**
```markdown
I'll analyze your git history and create a delightful CHANGELOG. Let me see what treasures are hiding in those commits...

Found 47 commits since the initial commit. Here's your sparkly new CHANGELOG.md:

# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added 🎉
- Authentication now remembers who you are after coffee breaks—no more surprise logouts
- Dark mode for those late-night coding sessions (your eyes will thank us)
- Export functionality that actually exports things where you want them

### Fixed 🐛
- The save button now saves things—revolutionary, we know
- Fixed that thing where clicking sometimes didn't click
- Database connections no longer ghost you after 5 minutes

### Changed 🚀
- Settings page got a makeover—same features, friendlier face
- API responses arrive 50% faster (we asked them nicely to hurry up)

Would you like me to add this to your project?
```

### Update Existing Changelog

**User Request:**
```
"Update the CHANGELOG with the last week's changes"
```

**Skill Response:**
```markdown
Let me check what's been cooking since last week...

Found 12 commits with some lovely improvements! I'll add these to your existing CHANGELOG:

## [1.3.0] - 2025-11-06

### Added 🎨
- Color picker that actually picks colors (and remembers your favorites)
- Keyboard shortcuts for the keyboard shortcut enthusiasts
- Beta feature toggle—live dangerously if you dare

### Fixed 🔧
- Search no longer searches for things you didn't search for
- Notifications now notify at the right time, not randomly at 3 AM
- That weird spacing issue on mobile? Gone. Poof.

### Under the Hood 🛠️
- Upgraded our dependencies (they were feeling a bit dusty)
- Refactored the widget engine—same widgets, better engine

I've updated your CHANGELOG.md. The new version section has been added right after [Unreleased].
```

## Advanced Scenarios

### Generate Release Notes for Specific Version

**User Request:**
```
"Create release notes for v2.0.0 covering all changes since v1.8.0"
```

**Skill Response:**
```markdown
Ooh, a major version! This must be something special. Let me gather all the exciting changes since v1.8.0...

✨ Found 89 commits across 3 months of hard work. Here's your v2.0.0 release summary:

## Version 2.0.0 - The One Where Everything Gets Better
*Released: 2025-11-06*

### 🎉 The Headliners

**Completely Redesigned Dashboard**
The dashboard got a full makeover—it's like it went to design school and came back with a degree. Everything's where you'd expect it to be, plus some delightful surprises.

**Real-time Collaboration**
See your teammates' cursors dancing around the screen. It's like Google Docs met your app and they became best friends.

**Plugin System**
Your app can now wear accessories! Install plugins to add superpowers we haven't even thought of yet.

### 💔 Breaking Changes (We're Sorry, But You'll Love These)

- **API Authentication**: We've switched to OAuth 2.0. Your old tokens need to retire, but the new ones are much more secure
- **Config Format**: JSON is out, YAML is in. It's friendlier to humans and machines alike
- **Minimum Node Version**: Now requires Node 16+. Time to upgrade if you haven't already!

### 🚀 Improvements That'll Make You Smile

- **Performance**: Everything's about 40% faster. We fed the hamsters extra coffee
- **Mobile Experience**: Touch targets that your thumbs can actually hit
- **Error Messages**: They now tell you what went wrong AND how to fix it
- **Auto-save**: Saves your work every 30 seconds because we know you forget

### 🐛 Bugs We Showed the Door

- Fixed 47 edge cases that were more "cliff cases" if we're being honest
- The memory leak is plugged—your RAM can breathe again
- Printing actually prints things on paper now, not just to the void

### 🏗️ For the Developers

- TypeScript everywhere—because any is not a type
- New testing framework that actually enjoys running tests
- Docker support for those who like their apps containerized
- API documentation that documents actual APIs

### 📦 Dependency Updates

Bumped 23 dependencies to their latest versions. They're all playing nicely together now.

### 🙏 Thank You

Big thanks to our 15 contributors who made this release possible. You're all stars! ⭐

---

*Migration Guide*: Check out our [migration guide](./MIGRATION.md) for smooth sailing from 1.x to 2.0.

*Questions?* We're here to help!
```

### Generate Changelog with Custom Voice Level

**User Request:**
```
"Create a changelog but keep it more professional, less playful"
```

**Skill Response:**
```markdown
Adjusting voice to business casual. Here's your CHANGELOG with a lighter touch of personality:

# Changelog

## [1.1.0] - 2025-11-06

### Added
- User authentication system with session management
- Dark mode support across all interfaces
- CSV export functionality for data reports

### Changed
- Improved dashboard performance by optimizing database queries
- Updated settings interface for better usability
- Enhanced error handling with more descriptive messages

### Fixed
- Resolved issue with save functionality not persisting data
- Corrected timeout behavior in database connections
- Fixed responsive layout issues on mobile devices

### Security
- Updated dependencies to address security vulnerabilities
- Implemented rate limiting on API endpoints

Still friendly, but wearing a tie now. Would you like me to adjust the tone further?
```

## Complex Workflows

### Monorepo Changelog Generation

**User Request:**
```
"Generate a unified changelog for all packages in our monorepo"
```

**Skill Response:**
```markdown
Exploring your monorepo structure... Found 5 packages! Let me create a unified changelog that shows the full picture:

# Monorepo Changelog

## [2025.11.06] - Today's Bundle of Joy

### 📦 @myapp/core (v3.1.0)
- **New**: Event system that actually emits events when things happen
- **Fixed**: Memory leak that was eating RAM like it was at a buffet
- **Improved**: 30% faster initialization (we taught it to wake up quicker)

### 📦 @myapp/ui (v2.5.0)
- **New**: Button component that loves being clicked
- **New**: Toast notifications that pop up politely
- **Fixed**: Modal no longer plays hide and seek with your content
- **Changed**: All components now support dark mode (welcome to the dark side)

### 📦 @myapp/api (v4.0.0) ⚠️ BREAKING
- **Breaking**: REST endpoints now follow RESTful conventions (finally!)
- **New**: WebSocket support for real-time updates
- **Improved**: Response times cut in half (zoom zoom)
- **Fixed**: That one endpoint that returned 418 I'm a teapot

### 📦 @myapp/cli (v1.2.0)
- **New**: Interactive mode for those who like conversations
- **Improved**: Better error messages that actually help
- **Fixed**: Commands no longer require a PhD to understand

### 📦 @myapp/docs (v1.0.1)
- **Updated**: All examples now actually work
- **Added**: Troubleshooting guide for common "oops" moments
- **Fixed**: Broken links now lead somewhere useful

### 🔄 Cross-Package Changes
- Upgraded TypeScript to 5.0 across all packages
- Standardized error handling—errors now speak the same language
- Consistent styling tokens—everything looks like it belongs together

Generated from 156 commits across 5 packages. Want me to create package-specific changelogs too?
```

### PR-Specific Release Notes

**User Request:**
```
"Generate release notes for PR #234 that's about to merge"
```

**Skill Response:**
```markdown
Fetching PR #234 details... Oh, this is the payment processing update! Let me craft release notes for this:

## Pull Request #234 - Payment Processing Upgrade

### What's Changing
We're giving the payment system a tune-up. It's like taking your car to the mechanic, but for money handling.

### For Users 🎯
- **Faster Checkouts**: Payment processing is now 2x faster—less waiting, more doing
- **Better Error Messages**: If something goes wrong, we'll tell you exactly what (no more cryptic error codes)
- **Retry Logic**: If your payment hiccups, we'll automatically try again (just once, we're not pushy)

### For Developers 🔧
- New `PaymentProcessor` class that's actually processor-agnostic
- Webhook handlers that handle webhooks properly
- Comprehensive logging for debugging payment mysteries

### What to Test
1. Try a successful payment (it should succeed)
2. Try with insufficient funds (should fail gracefully)
3. Check that receipts arrive in your inbox
4. Verify refund flow still works

### Migration Notes
- No action required for end users
- Developers: Update your `.env` with the new `PAYMENT_RETRY_ENABLED` flag
- Old payment logs will be archived after 30 days

This PR touches 18 files and includes 47 new tests. Ready to merge?
```

## Specialized Formats

### GitHub Release Format

**User Request:**
```
"Create GitHub release notes for v1.5.0"
```

**Skill Response:**
```markdown
Here's your GitHub release ready to copy and paste:

# 🚀 Version 1.5.0 - The Performance Update

## What's New ✨

### Lightning Fast Loading
Pages now load 50% faster. We convinced the electrons to move quicker.

### Batch Operations
Select multiple items and operate on them all at once. Efficiency lovers, rejoice!

### Smart Caching
The app now remembers things it's seen before. Like a very focused elephant.

## Improvements 🎯

- Search is now instant (seriously, try it)
- Sidebar stays where you put it
- Tooltips that actually help
- Keyboard navigation for power users

## Bug Fixes 🐛

- Fixed the Tuesday-only bug (yes, it was real)
- Uploads no longer pretend to fail when they succeed
- The back button goes back, not forward

## Contributors 🙌

Thanks to @alice, @bob, and @charlie for making this release awesome!

## Installation

```bash
npm install @myapp/core@1.5.0
```

**Full Changelog**: https://github.com/myorg/myapp/compare/v1.4.0...v1.5.0
```

### Semantic Commit Style

**User Request:**
```
"Parse these commits and create a conventional changelog"
```

**Skill Response:**
```markdown
I see you're using conventional commits. Let me create a properly formatted changelog:

# Changelog

## [1.2.0] (2025-11-06)

### Features
* **auth:** add OAuth integration for Google and GitHub
* **api:** implement rate limiting with configurable thresholds
* **ui:** add theme switcher with 5 preset themes

### Bug Fixes
* **auth:** resolve token refresh race condition
* **ui:** correct modal z-index stacking issues
* **api:** handle null values in user preferences

### Performance Improvements
* **db:** optimize queries with proper indexing
* **api:** implement response caching for static resources

### BREAKING CHANGES
* **api:** rename endpoint from `/user/profile` to `/users/me`

### Commits
* feat(auth): add OAuth integration (a1b2c3d)
* fix(auth): resolve token refresh race condition (d4e5f6g)
* feat(api): implement rate limiting (h7i8j9k)
* fix(ui): correct modal z-index (l0m1n2o)
* perf(db): optimize queries (p3q4r5s)
```

## Interactive Scenarios

### Suggesting Version Numbers

**User Request:**
```
"What version number should the next release be?"
```

**Skill Response:**
```markdown
Let me analyze the changes since your last release (v1.3.2)...

Found:
- 3 new features (minor version bump material)
- 5 bug fixes (patch version material)
- 0 breaking changes (no major version bump needed)

📊 My recommendation: **v1.4.0**

Here's why:
- New features warrant a minor version bump (1.3.x → 1.4.x)
- No breaking changes, so major version stays at 1
- Starting fresh at .0 for the patch number

Want to go with v1.4.0, or would you prefer something else? I can also do a pre-release version like v1.4.0-beta.1 if you're feeling cautious.
```

### Handling Missing Information

**User Request:**
```
"Create a changelog but I'm not sure what changed"
```

**Skill Response:**
```markdown
No worries! Let me investigate what's been happening in your project...

Here's what I can check:
1. Git commits since the last tag/release
2. Merged pull requests
3. Closed issues
4. Modified files

Checking git history... Found 23 commits since the last tag (v0.9.0 on Oct 15).

Here's what I discovered:
- 8 commits touching authentication code
- 5 commits updating the UI components
- 7 commits fixing various bugs
- 3 commits updating documentation

Should I generate a changelog from these commits, or would you like to provide more specific guidance?
```

## Error Handling Examples

### No Git Repository

**User Request:**
```
"Generate a changelog"
```

**Skill Response:**
```markdown
Hmm, I don't see a git repository here. No worries though! I have options:

1. **Initialize git**: Want me to set up git and start tracking changes from here?

2. **Manual changelog**: I can create a template CHANGELOG.md that you can fill in manually

3. **From commits list**: If you have a list of changes, I can transform them into a nice changelog

4. **From PR/issue list**: Got GitHub issues or PRs? I can work with those

What would work best for you?
```

### Unclear Commit Messages

**User Request:**
```
"Create release notes from our commits"
```

**Skill Response:**
```markdown
I found your commits, but some are speaking in code (literally). Let me do my best to translate:

## Original Commits → Friendly Translations

- "fix stuff" → Fixed various UI inconsistencies
- "asdfasdf" → (I'll skip this one—even I have limits)
- "FINALLY!!!" → Resolved a long-standing issue (probably that bug everyone knew about)
- "WIP" → Ongoing improvements to the codebase
- "update" → Enhanced existing functionality

Would you like to:
1. Use my translated versions
2. Provide more context for the cryptic commits
3. Skip the mysterious ones and focus on the clear commits

For future releases, commit messages like "fix: resolve login timeout issue" make much prettier changelogs!
```

## Integration Examples

### With CI/CD Pipeline

```yaml
# .github/workflows/release.yml
- name: Generate Changelog
  run: |
    # The skill would generate this changelog
    echo "Creating release notes..."
    changelog generate --since ${{ github.event.before }} --until ${{ github.sha }}
```

### With Package.json Scripts

```json
{
  "scripts": {
    "version": "changelog update && git add CHANGELOG.md",
    "postversion": "git push && git push --tags"
  }
}
```

### With Git Hooks

```bash
# .git/hooks/pre-push
#!/bin/sh
# Remind to update changelog before pushing tags
if git diff HEAD^ HEAD --name-only | grep -q "package.json"; then
  echo "Version changed! Did you update the CHANGELOG? 📝"
fi
```

## Tips for Best Results

### Good Commit Messages = Great Changelogs

**Instead of:**
```
fixed bug
updated code
changes
```

**Write:**
```
fix: prevent logout when switching tabs
feat: add bulk operations to user management
refactor: simplify authentication flow
```

### Grouping Related Changes

**User Request:**
```
"Group the changelog by feature area"
```

**Skill Response:**
```markdown
Organizing your changes by feature area for better readability:

## [2.0.0] - 2025-11-06

### Authentication & Security 🔐
- Added two-factor authentication (because one factor was lonely)
- Improved password strength requirements
- Fixed session timeout issues

### User Interface 🎨
- New dashboard layout with customizable widgets
- Dark mode that actually looks good
- Responsive design that responds properly

### API & Performance ⚡
- GraphQL endpoint for flexible queries
- 50% faster data loading
- Proper error codes (no more 418 I'm a teapot)

### Developer Experience 🛠️
- TypeScript migrations complete
- Comprehensive test coverage
- Docker development environment
```

Remember: The best changelog is one that makes both developers and users smile while staying informed!
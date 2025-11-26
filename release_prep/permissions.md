You will need approximately these permissions

"allow": [
  "Skill(release_prep)",
  "Bash(./scripts/check_all)",
  "Read(~/.claude/skills/release_prep/**)",
  "WebFetch(domain:crates.io)",
  "Bash(grep:*)",
  "Bash(~/.claude/skills/release_prep/scripts/line_count)",
  "Bash(~/.claude/skills/release_prep/scripts/compare_api.sh)",
  "Bash(~/.claude/skills/release_prep/scripts/compare_docs.sh)",
  "Bash(ln -s AGENTS.md CLAUDE.md)",
  "Bash(cargo:*)"
],

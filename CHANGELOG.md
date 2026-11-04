# Changelog

All notable changes to the live-view-agents marketplace are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The plan: [PLAN.md](PLAN.md) (stages S0–S9).
- S0, skeleton: the marketplace catalog (`.claude-plugin/marketplace.json`, name `live-view-agents`) with six
  plugins (live-view-mcp, usecase-runner, log-triage, code-fix, build-push, fix-loop), each with its
  manifest and a README of what it will hold; `scripts/validate.py` and the CI that runs it; install
  docs for Claude Code and VS Code.

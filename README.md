# skill-master

A collection of agent skills for Claude Code, Cursor, and Google Antigravity — reusable procedures for engineering workflows (git/PR flow, Fizzy/Basecamp project management, code review, release notes, and more).

Skills live in `.agent/skills/<skill-name>/SKILL.md`, one directory per skill. `.cursor/skills/` and `.claude/skills/` are symlinks to the same directory, so every skill works across all three IDEs without duplication.

## Install

**Fastest — pull one or two skills into an existing repo:**

```bash
npx skills@latest add tobilafinhangit/skill-master --skill=<skill-name>
npx skills@latest add tobilafinhangit/skill-master --list   # browse what's available
```

**Full clone — if you want to edit skills locally or use many of them:**

```bash
git clone https://github.com/tobilafinhangit/skill-master.git
cd skill-master
./scripts/setup-multi-ide-skills.sh
```

Full instructions, per-IDE setup, and troubleshooting: [docs/installation-multi-ide.md](docs/installation-multi-ide.md).

## Notes for adopters

Some skills were originally written against one team's internal setup (a specific Fizzy/Basecamp account, board names, git-author identity for automated commits). Where that applies, the skill says so and uses a `{PLACEHOLDER}` you should swap for your own — see the **Setup** section at the top of the `fizzy` skill for the pattern.

A few skills also reference optional `.claude/rules/*.md` deep-dive files from the original author's private repos. Those are supplementary, not required — the skills work from their own inline instructions if those files aren't present in your repo.

## Docs

- [Multi-IDE installation guide](docs/installation-multi-ide.md)
- [Multi-IDE compatibility notes](docs/MULTI-IDE-COMPATIBILITY.md)
- [Skill frontmatter template](docs/skill-frontmatter-template.md)
- [Multi-model AI guidance](docs/multi-model-ai-guidance.md)

## Writing a new skill

See the `creating-skills` and `writing-great-skills` skills in `.agent/skills/` for the conventions this repo follows.

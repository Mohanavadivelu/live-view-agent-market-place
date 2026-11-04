"""Checks the marketplace: the catalog, each plugin's manifest, and its agents, skills and commands.

    python scripts/validate.py            exit 1 if anything is wrong (CI runs this)

What it checks (the parts every tool relies on):
- .claude-plugin/marketplace.json parses; every plugin it lists exists at its source, with
  .claude-plugin/plugin.json whose name and version match the catalog's
- every plugin folder under plugins/ is in the catalog
- skills/<name>/SKILL.md: frontmatter with name (= the folder name, kebab-case) and description
- agents/*.md and commands/*.md: frontmatter with a description (agents: a name = the file name)
- .mcp.json, if present, parses and has mcpServers
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
problems: list[str] = []


def bad(where: Path | str, what: str) -> None:
    problems.append(f"{Path(where).relative_to(ROOT) if isinstance(where, Path) else where}: {what}")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        bad(path, f"not valid JSON ({e})")
        return None


def frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        bad(path, "no frontmatter (--- … ---) at the top")
        return None
    fields, key = {}, None
    for line in m.group(1).splitlines():
        if re.match(r"^[A-Za-z][\w-]*:", line):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def check_plugin(folder: Path, listed: dict) -> None:
    manifest = folder / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        return bad(folder, "no .claude-plugin/plugin.json")
    data = load_json(manifest)
    if data is None:
        return
    for field in ("name", "version", "description"):
        if not data.get(field):
            bad(manifest, f"no {field}")
    if data.get("name") != listed.get("name"):
        bad(manifest, f"name {data.get('name')!r} isn't the catalog's {listed.get('name')!r}")
    if listed.get("version") and data.get("version") != listed["version"]:
        bad(manifest, f"version {data.get('version')} isn't the catalog's {listed['version']}")
    for extra in (folder / ".claude-plugin").iterdir():
        if extra.name != "plugin.json":
            bad(extra, "only plugin.json belongs in .claude-plugin/")
    for skill in sorted((folder / "skills").glob("*/")) if (folder / "skills").is_dir() else []:
        md = skill / "SKILL.md"
        if not md.is_file():
            bad(skill, "no SKILL.md")
            continue
        fm = frontmatter(md) or {}
        if fm.get("name") != skill.name:
            bad(md, f"name {fm.get('name')!r} must be the folder name {skill.name!r}")
        if not KEBAB.match(skill.name):
            bad(skill, "skill folder names are kebab-case")
        if not fm.get("description"):
            bad(md, "no description (it is what the agent matches requests against)")
    for kind in ("agents", "commands"):
        for md in sorted((folder / kind).glob("*.md")) if (folder / kind).is_dir() else []:
            fm = frontmatter(md) or {}
            if not fm.get("description"):
                bad(md, "no description")
            if kind == "agents" and fm.get("name") != md.stem:
                bad(md, f"name {fm.get('name')!r} must be the file name {md.stem!r}")
    skills = {s.name for s in (folder / "skills").glob("*/")} if (folder / "skills").is_dir() else set()
    for md in sorted((folder / "commands").glob("*.md")) if (folder / "commands").is_dir() else []:
        if md.stem in skills:
            bad(md, f"a command and a skill are both called {md.stem!r} (commands are skills too)")
    mcp = folder / ".mcp.json"
    if mcp.is_file():
        data = load_json(mcp)
        if data is not None and not isinstance(data.get("mcpServers"), dict):
            bad(mcp, "no mcpServers object")


def main() -> int:
    catalog_path = ROOT / ".claude-plugin" / "marketplace.json"
    catalog = load_json(catalog_path)
    if catalog is None:
        return report()
    for field in ("name", "owner", "plugins"):
        if not catalog.get(field):
            bad(catalog_path, f"no {field}")
    seen = set()
    for entry in catalog.get("plugins", []):
        name, source = entry.get("name"), entry.get("source", "")
        if not name or not KEBAB.match(name):
            bad(catalog_path, f"plugin name {name!r} must be kebab-case")
        if name in seen:
            bad(catalog_path, f"plugin {name!r} listed twice")
        seen.add(name)
        folder = (ROOT / source).resolve()
        if not folder.is_dir():
            bad(catalog_path, f"{name}: source {source!r} isn't a folder")
            continue
        check_plugin(folder, entry)
    for folder in sorted((ROOT / "plugins").glob("*/")):
        if folder.name not in seen:
            bad(folder, "not in .claude-plugin/marketplace.json")
    return report(len(seen))


def report(plugins: int = 0) -> int:
    for p in problems:
        print(f"FAIL {p}")
    if problems:
        print(f"\n{len(problems)} problem{'s' if len(problems) != 1 else ''}")
        return 1
    print(f"OK marketplace: {plugins} plugins")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""MarketplaceService: reads pre-built skill files from the marketplace catalog."""
from __future__ import annotations

import os
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

MARKETPLACE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "marketplace"
)


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from a markdown file."""
    if not content.startswith("---"):
        return {}, content
    try:
        import yaml  # type: ignore
    except ImportError:
        # Minimal parser without pyyaml
        end = content.index("---", 3)
        fm_raw = content[3:end].strip()
        meta: dict = {}
        for line in fm_raw.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                raw_v = v.strip().strip('"').strip("'")
                if raw_v.startswith("[") and raw_v.endswith("]"):
                    raw_v = [x.strip() for x in raw_v[1:-1].split(",")]  # type: ignore[assignment]
                meta[k.strip()] = raw_v
        return meta, content[end + 3:].strip()

    end = content.index("---", 3)
    fm_raw = content[3:end].strip()
    import yaml
    meta = yaml.safe_load(fm_raw) or {}
    return meta, content[end + 3:].strip()


class MarketplaceService:
    """Loads and serves pre-built skills from the marketplace catalog directory."""

    def list_skills(self) -> list[dict[str, Any]]:
        """Return metadata for all marketplace skills."""
        skills = []
        if not os.path.isdir(MARKETPLACE_DIR):
            return skills
        for filename in sorted(os.listdir(MARKETPLACE_DIR)):
            if not filename.endswith(".md"):
                continue
            path = os.path.join(MARKETPLACE_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                meta, body = _parse_frontmatter(content)
                skills.append({
                    "id": filename[:-3],  # strip .md
                    "name": meta.get("name", filename[:-3]),
                    "description": meta.get("description", ""),
                    "version": meta.get("version", "1.0"),
                    "author": meta.get("author", ""),
                    "tags": meta.get("tags", []),
                    "instructions": body,
                })
            except Exception as exc:
                logger.warning("Failed to parse marketplace skill %s: %s", filename, exc)
        return skills

    def get_skill(self, skill_id: str) -> dict[str, Any] | None:
        """Return full skill data for a single marketplace skill."""
        path = os.path.join(MARKETPLACE_DIR, f"{skill_id}.md")
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        meta, body = _parse_frontmatter(content)
        return {
            "id": skill_id,
            "name": meta.get("name", skill_id),
            "description": meta.get("description", ""),
            "version": meta.get("version", "1.0"),
            "author": meta.get("author", ""),
            "tags": meta.get("tags", []),
            "instructions": body,
        }

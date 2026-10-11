from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

EXCLUDED_TOP_LEVEL_DIRS = {".git", ".github", ".build"}
SrdPathEnv = "DAGGERHEART_SRD_PATH"


def resolve_srd_root() -> Path:
    env_value = os.getenv(SrdPathEnv)
    if env_value:
        candidate = Path(env_value).expanduser()
        if candidate.exists():
            return candidate.resolve()

    candidates = [
        Path(__file__).resolve().parent.parent / "daggerheart-srd",
        Path(__file__).resolve().parent / "daggerheart-srd",
        Path.cwd() / "daggerheart-srd",
        Path(r"c:\Users\betto\Documents\repos\daggerheart-srd"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        "Daggerheart SRD repo not found. Clone it adjacent to this project or set the DAGGERHEART_SRD_PATH environment variable."
    )


def _category_from_path(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    if len(relative.parts) <= 1:
        return "rules"
    return relative.parts[0]


def _document_type(category: str) -> str:
    mapping = {
        "abilities": "domain_card",
        "adversaries": "adversary",
        "ancestries": "ancestry",
        "armor": "armor",
        "beastforms": "beastform",
        "classes": "class",
        "communities": "community",
        "consumables": "consumable",
        "domains": "domain",
        "environments": "environment",
        "items": "item",
        "subclasses": "subclass",
        "weapons": "weapon",
        "rules": "rule",
    }
    return mapping.get(category, "document")


def _clean_markdown_text(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text.strip()


def _extract_title(path: Path, markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ").strip() or path.name


def _extract_summary(markdown: str) -> str:
    cleaned = _clean_markdown_text(markdown)
    for line in cleaned.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("#"):
            continue
        if candidate.startswith("---"):
            continue
        if candidate.startswith("|"):
            continue
        if candidate.startswith("- ") and "**" not in candidate:
            continue
        return candidate[:220]
    return "No summary available."


def _extract_headings(markdown: str) -> List[Dict[str, Any]]:
    headings: List[Dict[str, Any]] = []
    for line in markdown.splitlines():
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            headings.append({
                "level": len(match.group(1)),
                "title": match.group(2).strip(),
            })
    return headings


def load_quickstart_characters() -> List[Dict[str, Any]]:
    data_path = Path(__file__).resolve().parent / "data" / "quickstart_characters.json"
    if not data_path.exists():
        return []
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    characters: List[Dict[str, Any]] = []
    for item in payload:
        entry = {
            "name": item["name"],
            "slug": item["slug"],
            "path": f"quickstart/{item['slug']}.json",
            "kind": item["kind"],
            "category": "characters",
            "summary": item["description"],
            "source": item["source"],
            "class_name": item["class_name"],
            "subclass": item["subclass"],
            "heritage": item["heritage"],
            "pronouns": item["pronouns"],
            "story": item["story"],
            "question": item["question"],
            "experiences": item["experiences"],
            "settings": item["settings"],
        }
        characters.append(entry)
    return characters


def _flatten_document_entry(path: Path, root: Path) -> Dict[str, Any]:
    relative = path.relative_to(root)
    markdown = path.read_text(encoding="utf-8")
    category = _category_from_path(path, root)
    title = _extract_title(path, markdown)
    slug = path.stem.lower().replace(" ", "-")
    return {
        "category": category,
        "kind": _document_type(category),
        "name": title,
        "slug": slug,
        "path": relative.as_posix(),
        "file_name": path.name,
        "summary": _extract_summary(markdown),
        "headings": _extract_headings(markdown),
        "markdown": markdown,
    }


@lru_cache(maxsize=1)
def build_catalog() -> Dict[str, Any]:
    root = resolve_srd_root()
    documents: List[Dict[str, Any]] = []

    for path in sorted(root.rglob("*.md"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        top_level = relative.parts[0] if relative.parts else ""
        if top_level in EXCLUDED_TOP_LEVEL_DIRS:
            continue
        if relative.name.lower() == "readme.md" and relative.parts == ("README.md",):
            pass
        documents.append(_flatten_document_entry(path, root))

    categories: Dict[str, Dict[str, Any]] = {}
    for document in documents:
        category = document["category"]
        if category not in categories:
            label = category.replace("_", " ").title()
            if category == "abilities":
                label = "Domain Cards"
            categories[category] = {
                "category": category,
                "label": label,
                "type": _document_type(category),
                "count": 0,
                "entries": [],
            }
        categories[category]["entries"].append({
            "name": document["name"],
            "slug": document["slug"],
            "path": document["path"],
            "kind": document["kind"],
            "summary": document["summary"],
            "headings": document["headings"],
            "markdown": document["markdown"],
        })
        categories[category]["count"] += 1

    quickstart_characters = load_quickstart_characters()
    characters_category = {
        "category": "characters",
        "label": "Characters",
        "type": "character",
        "count": len(quickstart_characters),
        "entries": quickstart_characters,
    }
    categories["characters"] = characters_category

    catalog = {
        "source_repo": str(root),
        "generated_from": "markdown",
        "categories": {},
        "total_documents": len(documents) + len(quickstart_characters),
    }

    for key in sorted(categories):
        catalog["categories"][key] = categories[key]

    catalog["aliases"] = {
        "origins": ["ancestries", "communities"],
        "rules": ["rules"],
        "domain_cards": ["abilities"],
        "classes": ["classes"],
        "items": ["items"],
        "weapons": ["weapons"],
        "armor": ["armor"],
        "characters": ["characters", "quickstart_characters", "prebuilt_characters"],
    }
    return catalog


def get_category(category: str) -> Dict[str, Any]:
    catalog = build_catalog()
    if category not in catalog["categories"]:
        raise KeyError(f"Unknown category: {category}")
    return catalog["categories"][category]


def get_entry(category: str, item_name_or_slug: str) -> Dict[str, Any]:
    category_data = get_category(category)
    normalized = item_name_or_slug.strip().lower()
    for entry in category_data["entries"]:
        if entry["slug"].lower() == normalized or entry["name"].lower() == normalized:
            return entry
    for entry in category_data["entries"]:
        if normalized in entry["name"].lower() or normalized in entry["slug"].lower():
            return entry
    raise KeyError(f"No entry found in category '{category}' for '{item_name_or_slug}'")


def search_catalog(query: str, limit: int = 100) -> List[Dict[str, Any]]:
    text = (query or "").strip().lower()
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    for category_name, category in build_catalog()["categories"].items():
        for entry in category["entries"]:
            haystack = " ".join(
                [
                    category_name,
                    entry.get("name", ""),
                    entry.get("slug", ""),
                    entry.get("path", ""),
                    entry.get("summary", ""),
                ]
            ).lower()
            if text in haystack:
                results.append({
                    "category": category_name,
                    "name": entry["name"],
                    "slug": entry["slug"],
                    "path": entry["path"],
                    "kind": entry["kind"],
                    "summary": entry["summary"],
                })
                if len(results) >= limit:
                    return results
    return results


def export_catalog_json(output_path: str | None = None) -> str:
    catalog = build_catalog()
    destination = Path(output_path) if output_path else Path(__file__).resolve().parent / "data" / "daggerheart_catalog.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(destination)


if __name__ == "__main__":
    print(json.dumps({
        "categories": sorted(build_catalog()["categories"].keys()),
        "total_documents": build_catalog()["total_documents"],
    }, ensure_ascii=False, indent=2))

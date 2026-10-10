from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from daggerheart_api import build_catalog, get_category, get_entry, search_catalog

app = FastAPI(
    title="Daggerheart SRD API",
    description="A JSON/markdown API for the Daggerheart System Reference Document.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def index() -> Dict[str, Any]:
    catalog = build_catalog()
    return {
        "title": "Daggerheart SRD API",
        "source_repo": catalog["source_repo"],
        "total_documents": catalog["total_documents"],
        "categories": sorted(catalog["categories"].keys()),
        "endpoints": [
            "/api/summary",
            "/api/categories",
            "/api/all",
            "/api/search?q=arcana",
            "/api/classes",
            "/api/domains",
            "/api/ancestries",
            "/api/items",
            "/api/abilities",
            "/api/file/classes/Bard.md",
        ],
    }


@app.get("/api/summary")
def summary() -> Dict[str, Any]:
    catalog = build_catalog()
    return {
        "source_repo": catalog["source_repo"],
        "total_documents": catalog["total_documents"],
        "categories": [
            {
                "name": category_name,
                "count": category["count"],
                "label": category["label"],
            }
            for category_name, category in catalog["categories"].items()
        ],
    }


@app.get("/api/categories")
def categories() -> Dict[str, Any]:
    return {"categories": sorted(build_catalog()["categories"].keys())}


@app.get("/api/origins")
def origins() -> Dict[str, Any]:
    catalog = build_catalog()
    merged: List[Dict[str, Any]] = []
    for key in ["ancestries", "communities"]:
        if key in catalog["categories"]:
            merged.extend(catalog["categories"][key]["entries"])
    return {"category": "origins", "count": len(merged), "entries": merged}


@app.get("/api/domain_cards")
def domain_cards() -> Dict[str, Any]:
    catalog = build_catalog()
    if "abilities" not in catalog["categories"]:
        return {"category": "domain_cards", "count": 0, "entries": []}
    return {"category": "domain_cards", "count": catalog["categories"]["abilities"]["count"], "entries": catalog["categories"]["abilities"]["entries"]}


@app.get("/api/all")
def all_documents() -> Dict[str, Any]:
    catalog = build_catalog()
    flattened: List[Dict[str, Any]] = []
    for category_name, category in catalog["categories"].items():
        for entry in category["entries"]:
            flattened.append({
                "category": category_name,
                "name": entry["name"],
                "slug": entry["slug"],
                "path": entry["path"],
                "kind": entry["kind"],
                "summary": entry["summary"],
            })
    return {"count": len(flattened), "items": flattened}


@app.get("/api/search")
def search(q: str = Query(..., min_length=1)) -> Dict[str, Any]:
    return {"query": q, "results": search_catalog(q)}


@app.get("/api/characters")
@app.get("/api/quickstart-characters")
@app.get("/api/prebuilt-characters")
def characters() -> Dict[str, Any]:
    return get_category("characters")


@app.get("/api/{category}")
def category_data(category: str) -> Dict[str, Any]:
    try:
        return get_category(category)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/file/{category}/{file_name:path}")
def file_content(category: str, file_name: str) -> Dict[str, Any]:
    catalog = build_catalog()
    category_entries = catalog["categories"].get(category)
    if category_entries is None:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    normalized = file_name.lower().replace("%20", " ")
    for entry in category_entries["entries"]:
        if entry["slug"].lower() == normalized.replace(".md", "") or entry["path"].lower().endswith(normalized.lower()):
            return {
                "category": category,
                "name": entry["name"],
                "slug": entry["slug"],
                "path": entry["path"],
                "markdown": entry["markdown"],
                "summary": entry["summary"],
                "headings": entry["headings"],
            }

    raise HTTPException(status_code=404, detail=f"No document found for category '{category}' named '{file_name}'")


@app.get("/api/{category}/{name}")
def entry_detail(category: str, name: str) -> Dict[str, Any]:
    try:
        entry = get_entry(category, name)
        return {
            "category": category,
            "name": entry["name"],
            "slug": entry["slug"],
            "path": entry["path"],
            "kind": entry["kind"],
            "summary": entry["summary"],
            "headings": entry["headings"],
            "markdown": entry["markdown"],
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)

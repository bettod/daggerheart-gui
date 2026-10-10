from daggerheart_api import build_catalog, search_catalog


def test_catalog_includes_core_categories():
    catalog = build_catalog()

    assert "classes" in catalog["categories"]
    assert "domains" in catalog["categories"]
    assert "items" in catalog["categories"]
    assert "abilities" in catalog["categories"]
    assert "ancestries" in catalog["categories"]


def test_catalog_contains_expected_entries():
    catalog = build_catalog()
    classes = catalog["categories"]["classes"]["entries"]
    domains = catalog["categories"]["domains"]["entries"]
    items = catalog["categories"]["items"]["entries"]

    assert any(item["name"] == "Bard" for item in classes)
    assert any(item["name"] == "Arcana" for item in domains)
    assert any(item["name"] == "Airblade Charm" for item in items)


def test_search_is_case_insensitive():
    results = search_catalog("arcana")
    assert any(result["category"] == "domains" for result in results)


def test_catalog_includes_aliases_for_origin_and_domain_cards():
    catalog = build_catalog()
    assert "origins" in catalog["aliases"]
    assert "domain_cards" in catalog["aliases"]


def test_quickstart_characters_are_available():
    catalog = build_catalog()
    characters = catalog["categories"]["characters"]["entries"]
    names = {entry["name"] for entry in characters}

    assert {"Marlowe Fairwind", "Barnacle", "Garrick Reed", "Khari Nix", "Varian Soto"}.issubset(names)
    assert any(entry["class_name"] == "Sorcerer" for entry in characters)

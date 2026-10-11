from daggerheart_api import build_catalog, search_catalog
from main import DaggerheartViewer


def test_adventure_section_titles_use_italian_appendix_names():
    viewer = DaggerheartViewer.__new__(DaggerheartViewer)
    sample = """APPENDICE A
	GUIDA RAPIDA DEL GM
	Testo iniziale.

ATTO I
	LA VEGLIA DELLA PIRA
	Descrizione del primo atto.

APPENDICE B
	PERSONAGGI NON GIOCANTI
	Lista NPC.
"""

    sections = viewer.parse_adventure_text_sections(sample)
    titles = [section["title"] for section in sections]

    assert "APPENDICE A" in titles
    assert "ATTO I" in titles
    assert "APPENDICE B" in titles
    assert any(section["title"] == "APPENDICE A" and "GUIDA RAPIDA DEL GM" in section["text"] for section in sections)


def test_adventure_sections_keep_same_indent_together():
    viewer = DaggerheartViewer.__new__(DaggerheartViewer)
    sample = """ATTO I
	Scopo dell'Atto
		Questo atto introduce:
		· Ashgrove Hollow
		· la Pira Sacra
	Arrivo ad Ashgrove Hollow
		Leggi ai giocatori
APPENDICE A
	GUIDA RAPIDA DEL GM
"""

    sections = viewer.parse_adventure_text_sections(sample)

    assert sections[0]["title"] == "ATTO I"
    assert sections[0]["children"][0]["title"] == "Scopo dell'Atto"
    assert "Questo atto introduce:" in sections[0]["children"][0]["text"]
    assert "· Ashgrove Hollow" in sections[0]["children"][0]["text"]
    assert sections[0]["children"][1]["title"] == "Arrivo ad Ashgrove Hollow"
    assert "Leggi ai giocatori" in sections[0]["children"][1]["text"]
    assert "Scopo dell'Atto" in sections[0]["text"]
    assert sections[1]["title"] == "APPENDICE A"
    assert "GUIDA RAPIDA DEL GM" in sections[1]["text"]


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

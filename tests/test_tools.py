import tools
from agent import run_agent
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def test_search_returns_relevant_results():
    results = search_listings("vintage graphic tee", size=None, max_price=30)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(item["price"] <= 30 for item in results)


def test_search_returns_empty_list_when_no_match():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_suggest_outfit_handles_empty_wardrobe(monkeypatch):
    monkeypatch.setattr(tools, "_call_groq_text", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("no api")))
    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    result = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert result.strip()


def test_create_fit_card_rejects_empty_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    result = create_fit_card("", item)
    assert result == "I need an outfit suggestion before I can create a fit card."


def test_run_agent_returns_error_on_no_results():
    session = run_agent("designer ballgown size XXS under $5", get_example_wardrobe())
    assert session["error"] is not None
    assert session["selected_item"] is None
    assert session["fit_card"] is None

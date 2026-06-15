"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import random
import re
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)

def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _tokenize(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", _normalize_text(value)) if token]


def _listing_search_text(listing: dict) -> str:
    parts = [
        listing.get("title", ""),
        listing.get("description", ""),
        listing.get("category", ""),
        " ".join(listing.get("style_tags", []) or []),
        " ".join(listing.get("colors", []) or []),
        listing.get("brand", "") or "",
        listing.get("platform", ""),
        listing.get("condition", ""),
    ]
    return _normalize_text(" ".join(parts))


def _size_matches(requested_size: str | None, listing_size: Any) -> bool:
    if not requested_size:
        return True

    requested = _normalize_text(requested_size)
    candidate = _normalize_text(listing_size)
    if not candidate:
        return False

    requested_tokens = re.findall(r"[a-z0-9]+", requested)
    candidate_tokens = re.findall(r"[a-z0-9]+", candidate)
    if requested in candidate:
        return True
    return any(token and token in candidate_tokens for token in requested_tokens)


def _score_listing(listing: dict, description: str) -> int:
    query_tokens = [
        token
        for token in _tokenize(description)
        if token
        not in {
            "the",
            "a",
            "an",
            "for",
            "and",
            "or",
            "with",
            "under",
            "size",
            "in",
            "on",
            "of",
            "to",
            "my",
            "i",
            "im",
            "looking",
            "want",
            "get",
            "need",
        }
    ]
    if not query_tokens:
        query_tokens = _tokenize(description)

    title_text = _normalize_text(listing.get("title", ""))
    description_text = _normalize_text(listing.get("description", ""))
    category_text = _normalize_text(listing.get("category", ""))
    style_text = _normalize_text(" ".join(listing.get("style_tags", []) or []))
    color_text = _normalize_text(" ".join(listing.get("colors", []) or []))
    brand_text = _normalize_text(listing.get("brand", "") or "")
    search_text = _listing_search_text(listing)

    score = 0
    if description.strip() and description.strip().lower() in search_text:
        score += 3

    for token in query_tokens:
        if token in title_text:
            score += 4
        if token in style_text:
            score += 3
        if token in description_text:
            score += 2
        if token in category_text:
            score += 2
        if token in color_text:
            score += 1
        if token in brand_text:
            score += 1

    return score


def _extract_wardrobe_items(wardrobe: dict) -> list[dict]:
    if not isinstance(wardrobe, dict):
        return []
    items = wardrobe.get("items", [])
    return items if isinstance(items, list) else []


def _summarize_item(item: dict) -> str:
    if not isinstance(item, dict):
        return "unknown item"

    pieces = [
        item.get("name"),
        item.get("category"),
        ", ".join(item.get("colors", []) or []),
        ", ".join(item.get("style_tags", []) or []),
    ]
    notes = item.get("notes")
    if notes:
        pieces.append(str(notes))
    summary = " | ".join(part for part in pieces if part)
    return summary or "unknown item"


def _fallback_style_advice(new_item: dict, empty_wardrobe: bool = False) -> str:
    title = new_item.get("title", "this piece")
    category = _normalize_text(new_item.get("category", ""))
    style_tags = ", ".join(new_item.get("style_tags", []) or [])
    colors = ", ".join(new_item.get("colors", []) or [])

    base = f"Try styling {title} with a clean base layer, simple shoes, and one accent piece that repeats a color from the item."
    if empty_wardrobe:
        return (
            f"Your wardrobe is empty right now, so start with a versatile foundation: a neutral bottom, clean sneakers or boots, and one layer that echoes the vibe of {title}."
        )

    if "outerwear" in category:
        return (
            f"Pair {title} over a fitted top and your favorite jeans or trousers so it stays the statement piece. Keep accessories minimal and let the {style_tags or 'overall vibe'} do the work."
        )
    if "shoes" in category:
        return (
            f"Build the outfit around {title} by repeating its color palette with your top or bag. Keep the rest of the look simple so the shoes read intentional, not crowded."
        )
    if "bottoms" in category:
        return (
            f"Style {title} with a tucked-in tee or fitted top, then add shoes that echo its vibe. Use {colors or 'the color palette'} to choose one matching layer or accessory."
        )
    if "accessories" in category:
        return (
            f"Use {title} as the finishing touch on a simple outfit. It will work best with clean lines, one strong base color, and a small detail that repeats its tone or texture."
        )

    return base


def _call_groq_text(messages: list[dict], temperature: float = 0.8, max_tokens: int = 220) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def _pick_caption_option(text: str) -> str:
    options = []
    for line in re.split(r"[\n\r]+|\s*\|\|\s*", text):
        cleaned = re.sub(r"^[-*\d\.\)\s]+", "", line).strip()
        if cleaned:
            options.append(cleaned)
    if not options:
        return text.strip()
    return random.choice(options)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    try:
        listings = load_listings()
    except Exception:
        return []

    matches: list[tuple[int, dict]] = []
    for listing in listings:
        price = listing.get("price")
        if max_price is not None and price is not None and float(price) > float(max_price):
            continue
        if not _size_matches(size, listing.get("size")):
            continue

        score = _score_listing(listing, description)
        if score <= 0:
            continue

        matches.append((score, listing))

    matches.sort(
        key=lambda pair: (
            -pair[0],
            float(pair[1].get("price", 0) or 0),
            _normalize_text(pair[1].get("title", "")),
        )
    )
    return [dict(listing) for score, listing in matches]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    wardrobe_items = _extract_wardrobe_items(wardrobe)
    item_summary = _summarize_item(new_item)

    if not wardrobe_items:
        prompt = (
            "You are FitFindr, a styling assistant for secondhand fashion. "
            "The user has an empty wardrobe, so give general styling advice for the new item. "
            "Return 2 concise sentences. Be specific about layers, silhouettes, shoes, accessories, or color pairing. "
            f"New item: {item_summary}"
        )
    else:
        wardrobe_lines = "\n".join(f"- {_summarize_item(item)}" for item in wardrobe_items)
        prompt = (
            "You are FitFindr, a styling assistant for secondhand fashion. "
            "Suggest 1-2 complete outfits using the new thrifted item and pieces from the user's wardrobe. "
            "Return a single short paragraph with practical styling advice. Mention specific wardrobe items when they fit. "
            f"New item: {item_summary}\n"
            f"Wardrobe items:\n{wardrobe_lines}"
        )

    try:
        response = _call_groq_text(
            [
                {"role": "system", "content": "You write concise, wearable outfit advice."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.85,
            max_tokens=180,
        )
        if response:
            return response
    except Exception:
        pass

    return _fallback_style_advice(new_item, empty_wardrobe=not wardrobe_items)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "I need an outfit suggestion before I can create a fit card."

    prompt = (
        "You are FitFindr, and you write short, shareable outfit captions. "
        "Write 3 different caption options, each 1-2 sentences, casual and Instagram-ready. "
        "Each caption should mention the thrifted item, the price, and the platform naturally once. "
        "Avoid sounding like a product listing. Separate the three options with blank lines. "
        f"Item details: title={new_item.get('title', 'unknown')}; price={new_item.get('price', 'unknown')}; platform={new_item.get('platform', 'unknown')}; colors={', '.join(new_item.get('colors', []) or [])}; style_tags={', '.join(new_item.get('style_tags', []) or [])}. "
        f"Outfit suggestion: {outfit}"
    )

    try:
        response = _call_groq_text(
            [
                {"role": "system", "content": "You write concise social captions for fashion posts."},
                {"role": "user", "content": prompt},
            ],
            temperature=1.1,
            max_tokens=220,
        )
        if response:
            return _pick_caption_option(response)
    except Exception:
        pass

    title = new_item.get("title", "this find")
    platform = new_item.get("platform", "the app")
    price = new_item.get("price", "?")
    return f"found {title} on {platform} for ${price} and built the whole look around it"

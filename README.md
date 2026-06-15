# FitFindr

FitFindr is a small multi-tool agent that helps users find secondhand listings, turn one item into a full outfit idea, and generate a shareable fit caption.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```bash
GROQ_API_KEY=your_key_here
```

Run the tests:

```bash
pytest -q
```

Run the app:

```bash
python app.py
```

## Tool Inventory

### `search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]`

Searches the mock listings dataset for items that match the query. It filters by budget and size when those values are present, scores listings by keyword overlap, and returns the best matches first.

Returns a list of listing dictionaries. Each item includes fields such as `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

If nothing matches, it returns `[]`.

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

Takes a selected listing and the user's wardrobe and returns one styling suggestion string. If the wardrobe is empty, it falls back to broad styling advice instead of failing.

The `wardrobe` input should look like the schema in `data/wardrobe_schema.json`, especially `wardrobe["items"]`.

### `create_fit_card(outfit: str, new_item: dict) -> str`

Turns the outfit suggestion into a short caption-style fit card. It returns a casual, shareable line that mentions the thrifted item, price, and platform.

If `outfit` is blank, it returns the message `I need an outfit suggestion before I can create a fit card.`

## Planning Loop

The agent does not call all tools blindly. It follows a conditional sequence:

1. Parse the user query into `description`, `size`, and `max_price`.
2. Call `search_listings(description, size, max_price)`.
3. If the result list is empty, store an error message in the session and return immediately.
4. Store `search_results[0]` as `selected_item`.
5. Call `suggest_outfit(selected_item, wardrobe)`.
6. If the returned outfit string is empty, store an error message and stop.
7. Call `create_fit_card(outfit_suggestion, selected_item)`.
8. Return the completed session.

This is implemented in [agent.py](agent.py).

## State Management

The agent keeps a single session dictionary for one run. It stores:

- `query`: the original user text
- `parsed`: the extracted search constraints
- `search_results`: the full list from `search_listings`
- `selected_item`: the first match used in later steps
- `wardrobe`: the wardrobe passed into the agent
- `outfit_suggestion`: the string returned by `suggest_outfit`
- `fit_card`: the string returned by `create_fit_card`
- `error`: a human-readable error message if the run stops early

The selected listing flows directly from search into styling and then into caption generation, so the user never has to re-enter it.

## Error Handling

Each tool handles its own failure mode.

- `search_listings`: returns `[]` when no listings match, and the agent stops with a helpful message about broadening the search.
- `suggest_outfit`: if the wardrobe is empty or the LLM call fails, the tool returns fallback styling advice instead of raising.
- `create_fit_card`: if `outfit` is empty, the tool returns a descriptive error string; if the LLM call fails, it falls back to a simple template caption.

Example no-results response:

> I couldn't find any listings matching that description, size, and price. Try raising your max price, removing the size filter, or using a broader description.

## AI Usage

I used AI as a drafting assistant for implementation and spec-writing, then verified and adjusted the output manually.

1. For the three tools, I supplied the matching tool spec blocks from `planning.md` and asked for code that matched the exact signatures in `tools.py`. I kept the dataset filtering and fallback behavior, but I simplified the prompt and retry logic so the implementation stayed deterministic enough for testing.
2. For the planning loop, I supplied the Planning Loop, State Management, Error Handling, and Architecture sections from `planning.md`. I kept the conditional branching structure, but I implemented the query parsing with local regexes instead of an AI parser so the agent would be easier to test and reproduce.

## What To Look For In The Demo

The demo should show one complete path from user query to final fit card, plus at least one failure case. The important behavior is that state passes from search to styling to caption generation without re-entry from the user.

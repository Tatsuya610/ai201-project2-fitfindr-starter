# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
`search_listings` searches the mock secondhand listings dataset for items that match the user's requested description, size, and maximum price. It helps the agent find candidate thrift listings before any styling or fit card generation happens.

**Input parameters:**
- `description` (str): A natural language description of the item the user is looking for, such as `"vintage graphic tee"`, `"black leather jacket"`, or `"baggy jeans"`.
- `size` (str): The requested clothing size, such as `"XS"`, `"S"`, `"M"`, `"L"`, or `"XL"`. If the user does not specify a size, this can be `None`.
- `max_price` (float): The highest price the user is willing to pay. If the user does not specify a budget, this can be `None`.

**What it returns:**
It returns a list of listing dictionaries sorted by relevance, with the best match first. Each listing dictionary may contain the following fields from the mock dataset:

- `id`
- `title`
- `description`
- `category`
- `style_tags`
- `size`
- `condition`
- `price`
- `colors`
- `brand`
- `platform`

For example, one result might look like:

```python
{
    "id": "item_001",
    "title": "Faded Band Tee",
    "description": "Vintage-style graphic tee",
    "category": "tops",
    "style_tags": ["vintage", "graphic", "grunge"],
    "size": "M",
    "condition": "Good",
    "price": 22,
    "colors": ["black", "gray"],
    "brand": "Unknown",
    "platform": "Depop"
}
```

**What happens if it fails or returns nothing:**
If no listings match the user's request, the tool returns an empty list `[]` instead of raising an exception. The agent then stores a helpful message in `session["error"]` and returns early. It does not call `suggest_outfit` or `create_fit_card` without a selected item.

Example agent response:

`"I couldn't find any listings matching that description, size, and price. Try raising your max price, removing the size filter, or using a broader description like 'graphic tee'."`

---

### Tool 2: suggest_outfit

**What it does:**
`suggest_outfit` takes a selected secondhand listing and the user's wardrobe, then suggests a complete outfit using the new item and existing wardrobe pieces. It should provide practical styling advice rather than only listing item names.

**Input parameters:**
- `new_item` (dict): The selected listing returned by `search_listings`. It contains item details such as title, description, category, style tags, colors, size, condition, price, brand, and platform.
- `wardrobe` (dict): The user's wardrobe data. It contains existing wardrobe items that can be used to build a full outfit.

**What it returns:**
It returns a string containing one or more outfit suggestions. The suggestion should include:

- how to wear the selected thrift item
- which wardrobe pieces to pair with it
- the overall style or aesthetic
- practical styling details such as layering, tucking, shoes, accessories, or color matching

Example return value:

`"Pair this faded band tee with your wide-leg jeans and chunky sneakers for a relaxed 90s-inspired look. Roll the sleeves once and do a small front tuck to give the outfit more shape."`

**What happens if it fails or returns nothing:**
If the wardrobe is empty or minimal, the tool should not crash. Instead, it should return general styling advice based on the selected item.

Example fallback response:

`"Your wardrobe is pretty minimal, so I would style this item with a neutral bottom, clean sneakers, and one simple accessory to keep the focus on the thrifted piece."`

If the LLM call fails, the tool should return a simple fallback suggestion using the selected item's category, colors, and style tags.

---

### Tool 3: create_fit_card

**What it does:**
`create_fit_card` turns the outfit suggestion into a short, shareable caption-style description. The result should sound like something someone might post on Instagram or send to a friend, not like a formal product description.

**Input parameters:**
- `outfit` (str): The outfit suggestion returned by `suggest_outfit`.
- `new_item` (dict): The selected listing returned by `search_listings`. It provides details such as title, price, platform, colors, and style tags.

**What it returns:**
It returns a short caption-like string that describes the completed outfit in a casual, shareable way. The caption should mention the thrifted item and the outfit vibe.

Example return value:

`"thrifted this faded band tee for $22 and it instantly found its place with my wide-leg jeans and chunky sneakers 🖤 easy 90s energy"`

**What happens if it fails or returns nothing:**
If the `outfit` input is empty or missing, the tool returns a clear error message string instead of crashing.

Example error message:

`"I need an outfit suggestion before I can create a fit card."`

If the LLM call fails, the tool should return a simple template-based caption using the selected item's title, platform, and price.

Example fallback caption:

`"found this Faded Band Tee on Depop for $22 — easy thrifted outfit energy."`

---

### Additional Tools (if any)

No additional tools are planned for the required version of this project. If I add a stretch feature later, such as price comparison or retry logic with fallback search, I will update this section before implementing it.

---

## Planning Loop

**How does your agent decide which tool to call next?**

The agent uses a planning loop that checks the current session state after each tool call. It does not call all tools unconditionally. Each step only happens if the previous step returned usable information.

The logic is:

1. Start a new `session` dictionary with these keys:

    - `query`
   - `wardrobe`
   - `search_results`
   - `selected_item`
   - `outfit_suggestion`
   - `fit_card`
   - `error`

2. Read or extract the search constraints from the user query:

   - `description`
   - `size`
   - `max_price`

    I will parse these with simple regular expressions in `agent.py`: one pattern for `size`, one for price phrases like `under $30` or `budget 40`, and a cleanup pass to strip the size/price text out of the description.

3. Call:

   `search_listings(description, size, max_price)`

4. Store the returned list in:

   `session["search_results"]`

5. Check whether `search_results` is empty.

   If `search_results == []`:

   - Set `session["error"]` to a helpful no-results message.
   - Return the session immediately.
   - Do not call `suggest_outfit`.
   - Do not call `create_fit_card`.

   If `search_results` contains one or more items:

   - Select the first item as the best match.
   - Store it in `session["selected_item"]`.
   - Continue to the outfit suggestion step.

6. Call:

   `suggest_outfit(session["selected_item"], session["wardrobe"])`

7. Store the result in:

   `session["outfit_suggestion"]`

8. Check whether `session["outfit_suggestion"]` is usable.

   If the outfit suggestion is empty:

   - Store a helpful error message in `session["error"]`.
   - Return the session without calling `create_fit_card`.

   If the outfit suggestion is a usable string:

   - Continue to the fit card step.

9. Call:

   `create_fit_card(session["outfit_suggestion"], session["selected_item"])`

10. Store the result in:

   `session["fit_card"]`

11. Return the completed session to the user.

The planning loop knows it is done when one of two things happens: either an error branch returns the session early, or the agent successfully stores a final caption in `session["fit_card"]`.

---

## State Management

**How does information from one tool get passed to the next?**

The agent stores session information in a dictionary. This lets information from one tool call become available to later tool calls without asking the user to repeat it.

The session tracks:

- `session["query"]`: The original user request.
- `session["wardrobe"]`: The user's wardrobe data.
- `session["search_results"]`: The full list returned by `search_listings`.
- `session["selected_item"]`: The first and best listing selected from the search results.
- `session["outfit_suggestion"]`: The styling suggestion returned by `suggest_outfit`.
- `session["fit_card"]`: The final caption returned by `create_fit_card`.
- `session["error"]`: A helpful error message if the workflow cannot continue.

The main data flow is:

1. `search_listings` returns `search_results`.
2. The agent stores `search_results` in `session["search_results"]`.
3. The agent selects `search_results[0]` and stores it in `session["selected_item"]`.
4. `session["selected_item"]` is passed into `suggest_outfit`.
5. The returned outfit string is stored in `session["outfit_suggestion"]`.
6. `session["outfit_suggestion"]` and `session["selected_item"]` are passed into `create_fit_card`.
7. The caption is stored in `session["fit_card"]`.

This state management is important because the selected listing found by the search tool flows into both later tools.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | The agent stores a clear message in `session["error"]`, such as `"I couldn't find any listings matching that description, size, and price. Try raising your max price, removing the size filter, or using a broader description."` Then it returns early and does not call `suggest_outfit` or `create_fit_card`. |
| suggest_outfit | Wardrobe is empty | The tool returns a general styling suggestion based on the selected item, such as pairing it with a neutral bottom, simple shoes, and one accessory. The agent stores this in `session["outfit_suggestion"]` and continues to `create_fit_card` if the suggestion is usable. |
| create_fit_card | Outfit input is missing or incomplete | The tool returns a clear error message string, such as `"I need an outfit suggestion before I can create a fit card."` The agent displays the message instead of crashing. |

Additional error cases:

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | Dataset cannot be loaded | The tool returns `[]` or a controlled error result. The agent tells the user that listings could not be loaded and suggests trying again later. |
| suggest_outfit | LLM call fails | The tool returns a fallback outfit suggestion based on the selected item's category, colors, and style tags. The agent stores that fallback suggestion and continues if possible. |
| create_fit_card | LLM call fails | The tool returns a template-based caption using the item title, platform, and price. The agent stores that fallback caption in `session["fit_card"]`. |

---

## Architecture

```text
User input
    │
    ▼
Planning Loop
    │
    ├─ Extract or receive search constraints:
    │     description, size, max_price
    │
    ├─ Load wardrobe:
    │     example wardrobe or empty wardrobe for testing
    │
    ▼
search_listings(description, size, max_price)
    │
    ├─ results = []
    │      │
    │      ▼
    │   session["error"] =
    │   "No listings found. Try a broader description,
    │    higher budget, or removing the size filter."
    │      │
    │      ▼
    │   Return session early
    │
    └─ results = [item, item, ...]
           │
           ▼
       session["search_results"] = results
       session["selected_item"] = results[0]
           │
           ▼
suggest_outfit(session["selected_item"], session["wardrobe"])
    │
    ├─ wardrobe is empty or minimal
    │      │
    │      ▼
    │   Return general styling advice
    │
    └─ wardrobe has usable items
           │
           ▼
       Return outfit suggestion using wardrobe pieces
           │
           ▼
       session["outfit_suggestion"] = outfit_suggestion
           │
           ▼
create_fit_card(session["outfit_suggestion"], session["selected_item"])
    │
    ├─ outfit_suggestion is empty
    │      │
    │      ▼
    │   Return error message string
    │
    └─ outfit_suggestion is valid
           │
           ▼
       Return shareable caption
           │
           ▼
       session["fit_card"] = fit_card
           │
           ▼
       Return completed session
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

I will use ChatGPT or Claude to help implement each tool one at a time. For `search_listings`, I will give the AI tool the Tool 1 section of this planning document and ask it to implement `search_listings(description, size, max_price)` in `tools.py` using `load_listings()` from `utils/data_loader.py`. I expect it to produce a function that filters by description, size, and maximum price, sorts results by relevance, and returns an empty list `[]` when nothing matches. I will verify the output by checking the code manually and running test queries such as `"vintage graphic tee"`, `"jacket"`, and `"designer ballgown"`.

For `suggest_outfit`, I will give the AI tool the Tool 2 section of this planning document. I will ask it to implement `suggest_outfit(new_item, wardrobe)` using Groq's `llama-3.3-70b-versatile` model and the `GROQ_API_KEY` stored in `.env`. I expect it to produce a function that returns a styling suggestion string and handles an empty wardrobe without crashing. I will verify it by testing the function with `get_example_wardrobe()` and `get_empty_wardrobe()`.

For `create_fit_card`, I will give the AI tool the Tool 3 section of this planning document. I will ask it to implement `create_fit_card(outfit, new_item)` using the same Groq model. I expect it to produce a short caption-like string and return a clear error message when the outfit string is empty. I will verify it by running the same input multiple times to check that the captions vary and by testing the empty outfit case.

**Milestone 4 — Planning loop and state management:**

I will use ChatGPT or Claude to help implement `run_agent()` in `agent.py`. I will give it the Planning Loop, State Management, Error Handling, and Architecture sections of this planning document. I expect it to produce code that creates a session dictionary, calls `search_listings` first, branches based on whether results are empty, stores `selected_item`, passes that item into `suggest_outfit`, and then passes the outfit suggestion and selected item into `create_fit_card`.

Before trusting the generated planning loop, I will verify that it does not call all three tools unconditionally. I will test a happy-path query where search returns results and a failure-path query where search returns `[]`. In the failure path, I will confirm that `session["error"]` is set and `session["fit_card"]` remains `None`.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent receives the user query and identifies the search inputs. For this example, it uses:

- `description = "vintage graphic tee"`
- `size = None`
- `max_price = 30.0`

The user also provides wardrobe context: baggy jeans and chunky sneakers. The agent stores the original query and wardrobe information in the session.

The agent calls:

```python
search_listings("vintage graphic tee", size=None, max_price=30.0)
```

**Step 2:**
`search_listings` returns a list of matching listings. For example, it may return a result like:

```python
[
    {
        "id": "item_001",
        "title": "Faded Band Tee",
        "description": "Vintage-style graphic tee",
        "category": "tops",
        "style_tags": ["vintage", "graphic", "grunge"],
        "size": "M",
        "condition": "Good",
        "price": 22,
        "colors": ["black", "gray"],
        "brand": "Unknown",
        "platform": "Depop"
    }
]
```

The agent stores:

```python
session["search_results"] = results
session["selected_item"] = results[0]
```

Because the result list is not empty, the agent continues to the next tool.

The agent calls:

```python
suggest_outfit(session["selected_item"], session["wardrobe"])
```

**Step 3:**
`suggest_outfit` returns an outfit suggestion using the selected item and the user's wardrobe. For example:

```text
Pair this faded band tee with your baggy jeans and chunky sneakers for a relaxed 90s-inspired look. Roll the sleeves once and do a small front tuck to give the outfit more shape.
```

The agent stores:

```python
session["outfit_suggestion"] = outfit_suggestion
```

Because the outfit suggestion is usable, the agent continues to the fit card tool.

The agent calls:

```python
create_fit_card(session["outfit_suggestion"], session["selected_item"])
```

**Step 4:**
`create_fit_card` returns a short shareable caption. For example:

```text
thrifted this faded band tee for $22 and it instantly found its place with my baggy jeans + chunky sneakers 🖤 easy 90s energy
```

The agent stores:

```python
session["fit_card"] = fit_card
```

**Final output to user:**
The user sees three pieces of information:

1. Selected listing:

```text
Faded Band Tee — $22 on Depop, Good condition
```

2. Outfit suggestion:

```text
Pair this faded band tee with your baggy jeans and chunky sneakers for a relaxed 90s-inspired look. Roll the sleeves once and do a small front tuck to give the outfit more shape.
```

3. Fit card:

```text
thrifted this faded band tee for $22 and it instantly found its place with my baggy jeans + chunky sneakers 🖤 easy 90s energy
```

Error path example:

If the user asks:

```text
I'm looking for a designer ballgown under $5, size XXS.
```

The agent calls:

```python
search_listings("designer ballgown", size="XXS", max_price=5.0)
```

If the tool returns:

```python
[]
```

The agent stores:

```python
session["error"] = "I couldn't find any listings matching that description, size, and price. Try raising your max price, removing the size filter, or using a broader description."
```

The agent returns immediately. It does not call `suggest_outfit` or `create_fit_card`.
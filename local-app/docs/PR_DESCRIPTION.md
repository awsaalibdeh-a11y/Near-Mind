# Fix read tools failing output validation (list_chats, list_messages, +4 more)

With a current `mcp` (>=1.10, structured output), several read tools fail with
`1 validation error for <tool>Output ... Input should be a valid dictionary/list`.

## Bug 1: list_messages returned text, not records
`whatsapp.py` `list_messages` ended with `return format_messages_list(...)`, a `str`, while
`main.py` declares `List[Dict[str, Any]]` (`input_type=str`). `format_message` and
`format_messages_list` were also annotated `-> None` but return `str`.
Fix: `list_messages` returns `List[Message]`; both formatters are annotated `-> str` and are
presentation-only. `main.py` serialises at the edge.

## Bug 2: list_chats returned dataclasses, not dicts
`list_chats` returns `List[Chat]`, while `main.py` declares `List[Dict[str, Any]]`
(`input_type=Chat`). The same mismatch affected `search_contacts`, `get_chat`,
`get_direct_chat_by_contact`, `get_contact_chats` and `get_message_context`.
Fix: one set of serialisers in `whatsapp.py` (`message_to_dict`, `chat_to_dict`,
`contact_to_dict`, `context_to_dict`), applied in `main.py`. `get_last_interaction` now returns a
`Message` from the data layer and `main.py` renders it (output still text, now `Optional[str]`).

## Also
- `get_chat` / `get_direct_chat_by_contact` returned `None` for "not found" against a `Dict`
  return type; they now raise a clear `ValueError`.
- A missing `store/messages.db` used to create an empty DB file and fail with "no such table"
  (swallowed into `[]`). `_connect()` now raises `StoreNotFoundError` with an actionable message
  and never creates the file.

## Behaviour change
`list_messages` and `get_message_context` output is now structured JSON instead of formatted text.

## Tests
`whatsapp-mcp-server/tests/test_tools.py`: calls each tool through FastMCP (so output validation is real)
against a temp SQLite DB and a fake bridge. Before: 11 failed / 7 passed. After: 18 passed.
No send touched a real bridge. The Go bridge and `/api/send` shape are unchanged.

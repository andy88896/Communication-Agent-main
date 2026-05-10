import anthropic

_client: anthropic.Anthropic | None = None


def get() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client
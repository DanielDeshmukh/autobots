from __future__ import annotations


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def count_tokens(text: str) -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except (ImportError, Exception):
        return estimate_tokens(text)

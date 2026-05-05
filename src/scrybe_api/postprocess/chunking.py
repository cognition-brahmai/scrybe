from __future__ import annotations

from scrybe_api.schemas.common import ChunkStrategy


def build_chunks(markdown: str, strategy: ChunkStrategy, max_chunk_tokens: int) -> list[str]:
    lines = [line.rstrip() for line in markdown.splitlines()]
    blocks = []
    current: list[str] = []
    if strategy == ChunkStrategy.semantic:
        for line in lines:
            if line.startswith("#") and current:
                blocks.append("\n".join(current).strip())
                current = [line]
            else:
                current.append(line)
        if current:
            blocks.append("\n".join(current).strip())
    elif strategy == ChunkStrategy.paragraph:
        blocks = [block.strip() for block in markdown.split("\n\n") if block.strip()]
    else:
        words = markdown.split()
        chunk_size = max(1, max_chunk_tokens)
        return [
            " ".join(words[index:index + chunk_size])
            for index in range(0, len(words), chunk_size)
        ]

    result: list[str] = []
    current_words: list[str] = []
    for block in blocks:
        words = block.split()
        if len(current_words) + len(words) > max_chunk_tokens and current_words:
            result.append(" ".join(current_words).strip())
            current_words = words.copy()
        else:
            current_words.extend(words)
    if current_words:
        result.append(" ".join(current_words).strip())
    return result


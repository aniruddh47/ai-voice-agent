import json
import os
import re
from typing import Any, Dict, List


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("_", " ").replace("-", " ")).strip()


def _value_to_text(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).strip()


def _collect_sentences(section: str, obj: Any, path: str = "") -> List[str]:
    sentences: List[str] = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            key = _clean(k)
            next_path = f"{path} {key}".strip()
            sentences.extend(_collect_sentences(section, v, next_path))
        return sentences

    if isinstance(obj, list):
        if not obj:
            return sentences
        if all(not isinstance(x, (dict, list)) for x in obj):
            joined = ", ".join(_value_to_text(x) for x in obj)
            sentences.append(f"For {_clean(section)}, {_clean(path)} includes {joined}.")
            return sentences
        for item in obj:
            sentences.extend(_collect_sentences(section, item, path))
        return sentences

    text = _value_to_text(obj)
    if text:
        if path:
            sentences.append(f"For {_clean(section)}, {_clean(path)} is {text}.")
        else:
            sentences.append(f"About {_clean(section)}, {text}.")
    return sentences


def load_knowledge_sentences(data_dir: str) -> List[str]:
    all_sentences: List[str] = []

    if not os.path.isdir(data_dir):
        return all_sentences

    for file_name in sorted(os.listdir(data_dir)):
        if not file_name.lower().endswith(".json"):
            continue
        path = os.path.join(data_dir, file_name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        for section, value in data.items():
            all_sentences.extend(_collect_sentences(section, value))

    seen = set()
    deduped: List[str] = []
    for sentence in all_sentences:
        key = sentence.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(sentence)

    return deduped


def build_meaningful_chunks(sentences: List[str], min_sentences: int = 2, max_sentences: int = 4) -> List[str]:
    chunks: List[str] = []
    buf: List[str] = []

    for sentence in sentences:
        buf.append(sentence)
        if len(buf) >= max_sentences:
            chunks.append(" ".join(buf).strip())
            buf = []

    if buf:
        if chunks and len(buf) < min_sentences:
            chunks[-1] = f"{chunks[-1]} {' '.join(buf)}".strip()
        else:
            chunks.append(" ".join(buf).strip())

    return [c for c in chunks if c]


def load_and_chunk_knowledge(data_dir: str) -> List[str]:
    sentences = load_knowledge_sentences(data_dir)
    return build_meaningful_chunks(sentences, min_sentences=2, max_sentences=4)

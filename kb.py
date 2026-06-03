import json
import re
from typing import Optional, Dict, Tuple

def normalize(text: str):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return set(text.split())

def load_kb(file_path="knowledge_base.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def search_kb(user_query: str, kb_data: list) -> Tuple[Optional[Dict], float]:
    query_tokens = normalize(user_query)
    best_item = None
    best_score = 0.0

    for item in kb_data:
        text = f"{item.get('question', '')} {item.get('keywords', '')}"
        item_tokens = normalize(text)

        if not item_tokens:
            continue

        common = len(query_tokens.intersection(item_tokens))
        score = common / max(len(item_tokens), 1)

        if score > best_score:
            best_score = score
            best_item = item

    return best_item, best_score

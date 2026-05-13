"""ShopAgent — Claude structured output with Pydantic (Day 1, Prompt 10)."""

import json
import logging
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class ReviewAnalysis(BaseModel):
    total_reviews: int
    average_rating: float
    sentiment_distribution: dict[str, int]
    top_complaints: list[str]
    top_praises: list[str]


def load_reviews(path: str, limit: int = 10) -> list[dict]:
    reviews = []
    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                reviews.append(record)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed line %d: %s", line_number, exc)
            if len(reviews) >= limit:
                break
    return reviews


def _extract_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines[1:] if line.strip() != "```"]
        text = "\n".join(lines)
    return text.strip()


def analyze_reviews(reviews: list[dict]) -> ReviewAnalysis:
    client = anthropic.Anthropic()
    reviews_text = json.dumps(reviews, indent=2, ensure_ascii=False)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Analyze these e-commerce reviews and return a structured analysis.\n\n"
                        f"Reviews:\n{reviews_text}\n\n"
                        "Return a JSON object with these exact fields:\n"
                        "- total_reviews: number of reviews analyzed\n"
                        "- average_rating: average rating (float)\n"
                        '- sentiment_distribution: {"positive": N, "neutral": N, "negative": N}\n'
                        "- top_complaints: list of main complaints found\n"
                        "- top_praises: list of main praises found\n\n"
                        "Return ONLY the JSON object, no other text."
                    ),
                }
            ],
        )
    except anthropic.APIError as exc:
        logger.error("Anthropic API call failed: %s", exc)
        raise RuntimeError("LLM call failed") from exc

    if not response.content:
        raise RuntimeError("Empty response from LLM")

    raw = response.content[0].text
    try:
        data = json.loads(_extract_json(raw))
        return ReviewAnalysis(**data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error("Failed to parse LLM output: %s | raw=%s", exc, raw[:200])
        raise RuntimeError("LLM output did not match expected schema") from exc


if __name__ == "__main__":
    reviews_path = Path(__file__).resolve().parents[2] / "gen" / "data" / "reviews" / "reviews.jsonl"

    if not reviews_path.exists():
        print(f"Reviews file not found: {reviews_path}")
        raise SystemExit(1)

    reviews = load_reviews(str(reviews_path))
    print(f"Loaded {len(reviews)} reviews from {reviews_path.name}")

    analysis = analyze_reviews(reviews)
    print("\n" + "=" * 50)
    print("ShopAgent — Review Analysis (Structured Output)")
    print("=" * 50)
    print(f"Total reviews: {analysis.total_reviews}")
    print(f"Average rating: {analysis.average_rating:.1f}")
    print(f"Sentiment: {analysis.sentiment_distribution}")
    print(f"Top complaints: {analysis.top_complaints}")
    print(f"Top praises: {analysis.top_praises}")

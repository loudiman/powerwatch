"""Tier 2: natural-language -> SQL over the PowerWatch warehouse, via Vertex AI Gemini.

GSD scope: the dumbest thing that works. Paste the schema into the prompt, one
Gemini call, run the generated SQL on BigQuery, print the rows. Minimal guardrails.

Requires:
- A billing-enabled GCP project with the Vertex AI API on (`aiplatform.googleapis.com`)
- Application Default Credentials (`gcloud auth application-default login`)

Run: `python ai_assistant/nl_to_sql.py`  then type a question.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.cloud import bigquery

# Load .env from the repo root, regardless of the current working directory.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

PROJECT = os.environ.get("GCP_PROJECT_ID")
if not PROJECT:
    raise SystemExit(
        "GCP_PROJECT_ID is not set. Create your .env from the template first:\n"
        "    cp .env.example .env\n"
        "(or export GCP_PROJECT_ID and GCP_REGION in your shell)."
    )
BQ_LOCATION = os.environ.get("GCP_REGION", "US")                    # where the data lives
VERTEX_LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")  # where Gemini runs
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
SCHEMA_PROMPT = (Path(__file__).parent / "prompts" / "schema_prompt.md").read_text()


def to_sql(question: str) -> str:
    """Ask Gemini for a BigQuery SQL query answering the question."""
    client = genai.Client(vertexai=True, project=PROJECT, location=VERTEX_LOCATION)
    prompt = f"{SCHEMA_PROMPT}\n\nQuestion: {question}\nReturn ONLY a BigQuery SQL query, no prose."
    sql = client.models.generate_content(model=MODEL, contents=prompt).text.strip()
    # strip ```sql fences if the model adds them
    return sql.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()


def main() -> None:
    question = input("Ask PowerWatch: ")
    sql = to_sql(question)
    print(f"\n--- generated SQL ---\n{sql}\n\n--- results ---")
    for row in bigquery.Client(project=PROJECT).query(sql, location=BQ_LOCATION).result():
        print(dict(row))


if __name__ == "__main__":
    main()

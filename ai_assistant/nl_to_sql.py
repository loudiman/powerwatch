"""Stretch goal (Tier 2): natural-language -> SQL over the PowerWatch warehouse.

GSD scope: the dumbest possible version. Schema pasted into the prompt, ONE Vertex
AI (Gemini) call, run the SQL on BigQuery, print rows. No error handling, no
retries, no guardrails. This is the FIRST thing to cut if time runs short — and it
stays in the README only if it actually runs.
"""
import os
from pathlib import Path

import vertexai
from dotenv import load_dotenv
from google.cloud import bigquery
from vertexai.generative_models import GenerativeModel

load_dotenv()

PROJECT = os.environ["GCP_PROJECT_ID"]
REGION = os.environ.get("GCP_REGION", "us-central1")
SCHEMA_PROMPT = Path(__file__).parent / "prompts" / "schema_prompt.md"


def ask(question: str) -> str:
    vertexai.init(project=PROJECT, location=REGION)
    model = GenerativeModel("gemini-1.5-pro")
    prompt = (
        SCHEMA_PROMPT.read_text()
        + f"\n\nQuestion: {question}\nReturn ONLY a BigQuery SQL query, no prose."
    )
    raw = model.generate_content(prompt).text.strip()
    # strip ```sql fences if the model adds them
    return raw.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()


def main() -> None:
    question = input("Ask PowerWatch: ")
    sql = ask(question)
    print("\n--- generated SQL ---\n" + sql + "\n")
    for row in bigquery.Client(project=PROJECT).query(sql).result():
        print(dict(row))


if __name__ == "__main__":
    main()

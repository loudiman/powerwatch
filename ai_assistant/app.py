"""Streamlit web UI for the PowerWatch NL->SQL assistant.

Run (from the repo root, with .env in place):
    streamlit run ai_assistant/app.py
Then open the URL it prints (default http://localhost:8501).
"""
import streamlit as st
from google.cloud import bigquery

from nl_to_sql import to_sql, PROJECT, BQ_LOCATION

st.set_page_config(page_title="PowerWatch — Ask your energy data", page_icon="⚡")
st.title("⚡ PowerWatch")
st.caption("Ask your household-energy warehouse in plain English — Gemini writes the SQL, BigQuery runs it.")

EXAMPLES = [
    "Which zone used the most energy overall?",
    "Which hour has the highest average active power?",
    "What was the average voltage by season?",
    "Which day of week has the highest average household load?",
]

question = st.text_input("Your question", value=EXAMPLES[0])
st.caption("Try:  " + "   |   ".join(EXAMPLES[1:]))

if st.button("Ask", type="primary") and question:
    with st.spinner("Gemini is writing SQL and querying BigQuery..."):
        sql = to_sql(question)
        rows = [dict(r) for r in bigquery.Client(project=PROJECT).query(sql, location=BQ_LOCATION).result()]
    st.subheader("Generated SQL")
    st.code(sql, language="sql")
    st.subheader("Results")
    if rows:
        st.dataframe(rows, width="stretch")
    else:
        st.info("No rows returned.")

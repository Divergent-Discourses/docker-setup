import streamlit as st
import requests
import pandas as pd
import json
import time
import io
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from datetime import datetime

API_URL = "https://tibetcorpus.uni-leipzig.de/corpus_api"
MAX_FILE_SIZE_MB = 2000


st.set_page_config(page_title="Diachronic Analysis", layout="wide")
st.title("Diachronic Analysis Over Time")

# --- Session state ---
for key in ["diachronic_job_id", "is_button_disabled", "last_uploaded_file_name"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "is_button_disabled" else False

uploaded_file = st.file_uploader("Upload subcorpus CSV", type="csv")

if uploaded_file and uploaded_file.name != st.session_state["last_uploaded_file_name"]:
    st.session_state["diachronic_job_id"] = None
    st.session_state["is_button_disabled"] = False
    st.session_state["last_uploaded_file_name"] = uploaded_file.name

if uploaded_file:
    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        st.error(f"File too large (> {MAX_FILE_SIZE_MB} MB)")
        st.stop()

    # --- Inputs for keywords/phrases ---
    single_words_input = st.text_area("Single Words (Token Matches, comma-separated)")
    exact_phrases_input = st.text_area("Exact Phrases (Substring Matches, comma-separated)")

    with st.form("diachronic_form"):
        submit = st.form_submit_button("Run Analysis", disabled=st.session_state["is_button_disabled"])
        if submit:
            if not single_words_input.strip() and not exact_phrases_input.strip():
                st.warning("Enter at least one keyword or phrase")
            else:
                with st.spinner("Submitting job..."):
                    files = {"file": uploaded_file}
                    params = {"single_words": single_words_input, "exact_phrases": exact_phrases_input}
                    try:
                        res = requests.post(f"{API_URL}/diachronic", files=files, params=params)
                        res.raise_for_status()
                        job_id = res.json()["job_id"]
                        st.session_state["diachronic_job_id"] = job_id
                        st.session_state["is_button_disabled"] = True
                        st.success("Job submitted. Please wait...")
                    except Exception as e:
                        st.error(f"Submission failed: {e}")
                        st.session_state["is_button_disabled"] = False

# --- Poll job ---
if st.session_state.get("diachronic_job_id"):
    job_id = st.session_state["diachronic_job_id"]
    status = None
    with st.spinner("Checking job status..."):
        for _ in range(300):
            try:
                res = requests.get(f"{API_URL}/status/{job_id}")
                res.raise_for_status()
                status = res.json()["state"]
                if status == "SUCCESS":
                    break
                elif status in ["FAILURE", "REVOKED"]:
                    st.error(f"Job failed: {status}")
                    st.session_state["diachronic_job_id"] = None
                    st.session_state["is_button_disabled"] = False
                    break
            except Exception as e:
                st.error(f"Status check failed: {e}")
                st.session_state["is_button_disabled"] = False
                break
            time.sleep(2)

    # --- Display results ---
    if status == "SUCCESS":
        st.success("Analysis ready!")
        preview_url = f"{API_URL}/preview_result/{job_id}"
        try:
            results = requests.get(preview_url).json()
            words_percent_df = pd.DataFrame.from_dict(results["words_percent"], orient="index").fillna(0)
            words_raw_df = pd.DataFrame.from_dict(results["words_raw"], orient="index").fillna(0)
            phrases_percent_df = pd.DataFrame.from_dict(results["phrases_percent"], orient="index").fillna(0)
            phrases_raw_df = pd.DataFrame.from_dict(results["phrases_raw"], orient="index").fillna(0)

            st.dataframe(phrases_raw_df)
            st.dataframe(words_raw_df)
            st.dataframe(phrases_percent_df)
            st.dataframe(words_percent_df)

            # --- Plot words ---
            if not words_percent_df.empty:
                st.subheader("Single Word Frequencies (%)")
                fig, ax = plt.subplots(figsize=(12,6))
                for col in words_percent_df.columns:
                    ax.plot(words_percent_df.index, words_percent_df[col], marker='o', label=col)
                ax.set_ylabel("Frequency (%)")
                ax.set_xlabel("Year")
                ax.yaxis.set_major_formatter(PercentFormatter())
                ax.grid(True, linestyle="--", alpha=0.5)
                ax.legend()
                st.pyplot(fig)
                plt.close(fig)

            # --- Plot phrases ---
            if not phrases_percent_df.empty:
                st.subheader("Exact Phrase Frequencies (%)")
                fig2, ax2 = plt.subplots(figsize=(12,6))
                for col in phrases_percent_df.columns:
                    ax2.plot(phrases_percent_df.index, phrases_percent_df[col], marker='o', label=col)
                ax2.set_ylabel("Frequency (%)")
                ax2.set_xlabel("Year")
                ax2.yaxis.set_major_formatter(PercentFormatter())
                ax2.grid(True, linestyle="--", alpha=0.5)
                ax2.legend()
                st.pyplot(fig2)
                plt.close(fig2)

            # --- Download JSON ---
            download_url = f"{API_URL}/download/{job_id}"
            filename_input = st.text_input("Filename for download:", f"diachronic_{datetime.now().strftime('%Y%m%d')}")
            st.download_button(
                label="📥 Download Analysis JSON",
                data=requests.get(download_url).content,
                file_name=f"{filename_input.strip()}.json",
                mime="application/json"
            )

        except Exception as e:
            st.error(f"Failed to fetch results: {e}")

        st.session_state["is_button_disabled"] = False

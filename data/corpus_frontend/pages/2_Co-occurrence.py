import streamlit as st
import requests
import json
import time
import pandas as pd
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Co-occurrence Analysis", layout="wide")
st.title("Co-occurrence Analysis")

st.markdown("Upload your subcorpus to perform an analysis on a chosen key term.")

st.header("🤝 Words That Keep Company")

st.markdown("""
This tool helps you discover which words frequently appear **near** a specific keyword in your text. Think of it as finding the 'company' your chosen word keeps.
""")

st.subheader("How it helps your research:")
st.markdown("""
* It reveals common associations and typical contexts for a word.
* It suggests how a concept or idea was discussed or "framed" in the newspapers.
""")

st.subheader("Some Considerations (Limitations):")
st.markdown("""
* **Association, Not Causation:** Just because words appear together doesn't mean one causes the other, or that they are always directly related in meaning. It shows **patterns of usage**.
* **Window Size Matters:** The 'window size' you choose (how many words we consider around your keyword) will affect the results. Experiment!
* **Common Words Excluded:** Very common words (like 'དང་,' 'དེ་,' 'ཁོང་') are automatically removed to focus on more meaningful associations.
* **Unit of Analysis = Newspaper Page:** We look for words appearing near your search term anywhere on the same newspaper page. To find words that appear very close, like within the same paragraph or article, **reduce the 'window size'** setting. 
* **OCR Impact:** Errors from the original text scanning (OCR) might occasionally affect the accuracy of word counts.
* **Rare Words:** If your keyword appears very rarely, there might not be enough data to find significant co-occurrences.
* **Search Term Limit:** This tool works best for single words (like "ཆོས་ལུགས" or "མི་དམངས") - terms that you would expect to find entries for in a dictionary. If you enter a longer phrase, the tool may not find any results as it only looks for individual words or 'token matches'.
""")

st.markdown("""
**Important Note:** We designed this analysis for whole newspaper pages. It works best on your entire corpus, or a subcorpus filtered by date or newspaper name (which keeps pages complete). Avoid using it on text already filtered by a specific keyword, as this breaks the essential page context for co-occurrence.
""")


st.markdown("""
Use these insights as clues to guide your deeper analysis.
""")


API_URL = "https://tibetcorpus.uni-leipzig.de/corpus_api"

# -----------------------------
# Session state initialisation
# -----------------------------
for key in ["docs_path", "prep_job_id", "coocc_job_id", "last_preview", "is_disabled"]:
    if key not in st.session_state:
        st.session_state[key] = None

uploaded_file = st.file_uploader("Upload your subcorpus CSV", type=["csv"])


# -----------------------------
# Prepare doc object
# -----------------------------


if uploaded_file and (st.session_state.get("docs_path") is None or uploaded_file.name != st.session_state.get("last_file_name")):
    st.session_state["docs_path"] = None
    st.session_state["prep_job_id"] = None
    st.session_state["last_file_name"] = uploaded_file.name
    st.session_state["last_preview"] = None

    if st.button("📄 Prepare Docs"):
        with st.spinner("Submitting doc preparation job…"):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
            try:
                res = requests.post(f"{API_URL}/prepare_docs", files=files, timeout=3000)
                res.raise_for_status()
                prep_job_id = res.json()["job_id"]
                st.session_state["prep_job_id"] = prep_job_id
                st.info(f"Doc preparation job submitted: {prep_job_id}")

                # Poll doc prep
                for _ in range(600):
                    status_res = requests.get(f"{API_URL}/status/{prep_job_id}", timeout=3000)
                    status_res.raise_for_status()
                    state = status_res.json()["state"]
                    if state == "SUCCESS":
                        result_res = requests.get(f"{API_URL}/result/{prep_job_id}", timeout=3000)
                        result_res.raise_for_status()
                        st.session_state["docs_path"] = result_res.json()["result_path"]
                        st.success("Doc preparation complete! Ready for keyword search.")
                        break
                    elif state in ["FAILURE", "REVOKED"]:
                        st.error(f"Doc preparation failed: {state}")
                        break
                    time.sleep(2)
            except Exception as e:
                st.error(f"Doc preparation submission failed: {e}")

search_token = st.text_input("Enter search token:", value="")


# Add a slider for window size (default 100, range 5–200)
if "window_size" not in st.session_state:
    st.session_state["window_size"] = 100

window_size = st.slider(
    "Select window size:",
    min_value=5,
    max_value=200,
    value=st.session_state["window_size"],
    step=5,
    help="Number of tokens to the left/right considered for co-occurrence"
)

# Update session state with current slider value
st.session_state["window_size"] = window_size


# -----------------------------
# Keyword search & co-occurrence
# -----------------------------
if st.session_state.get("docs_path") and search_token.strip():
    if st.button("🔎 Compute Co-occurrences"):
        with st.spinner("Submitting co-occurrence job…"):
            try:
                st.session_state["search_token"] = search_token.strip()

                params = {
                    "docs_path": st.session_state["docs_path"],
                    "search_token": search_token.strip(),
                    "window_size": st.session_state["window_size"],
                    "top_n": 100
                }
                coocc_res = requests.post(f"{API_URL}/cooccurrence", params=params, timeout=3000)
                coocc_res.raise_for_status()
                st.session_state["coocc_job_id"] = coocc_res.json()["job_id"]
                st.session_state["is_disabled"] = True
                st.success("Co-occurrence job submitted!")
            except Exception as e:
                st.error(f"Job submission failed: {e}")


# -----------------------------
# Poll & display results
# -----------------------------
if st.session_state.get("coocc_job_id"):
    job_id = st.session_state["coocc_job_id"]

    with st.spinner("Checking co-occurrence job status…"):
        for _ in range(1500):  # ~50 minutes max
            try:
                # Check job status
                resp = requests.get(f"{API_URL}/status/{job_id}", timeout=30)
                resp.raise_for_status()
                status_json = resp.json()
                status = status_json.get("state")

                if status == "SUCCESS":
                    # Fetch results JSON directly
                    result_res = requests.get(f"{API_URL}/preview_result/{job_id}", timeout=30)
                    result_res.raise_for_status()
                    results = result_res.json()

                    st.session_state["last_preview"] = results
                    st.success(
                        f"Co-occurrence computation complete for "
                        f"'{st.session_state.get('search_token', '')}'!"
                    )
                    st.session_state["coocc_job_id"] = None
                    break

                elif status in ["FAILURE", "REVOKED"]:
                    st.error(f"Co-occurrence job failed: {status}")
                    st.session_state["coocc_job_id"] = None
                    break

            except Exception as e:
                st.error(f"Status check failed: {e}")
                st.session_state["coocc_job_id"] = None
                break

            time.sleep(2)

# -----------------------------
# Display results
# -----------------------------
if st.session_state.get("last_preview"):
    window_size = 50  # or read from session_state if you want
    st.markdown(
        f"### Top co-occurrences for "
        f"'{st.session_state.get('search_token', '')}' "
        f"(window size {st.session_state['window_size']})"
    )


    # Turn results into a DataFrame
    df = pd.DataFrame(st.session_state["last_preview"], columns=["token", "count"])

    # Display nicely as a table
    st.dataframe(df)

    # Offer CSV download
    csv = df.to_csv(index=False).encode("utf-8-sig")

    if 'co_occurrence_download_filename_base' not in st.session_state:
        st.session_state.co_occurrence_download_filename_base = f"co_occurrence_{datetime.now().strftime('%Y%m%d')}"
    user_entered_filename_base = st.text_input(
        "Enter desired filename:",
        value = st.session_state.co_occurrence_download_filename_base,
        key = "collocation_filename_input"
    )

    st.session_state.co_occurrence_download_filename_base = user_entered_filename_base

    final_co_occurrence_filename = user_entered_filename_base.strip().replace('.csv', '')
    if not final_co_occurrence_filename:
        final_co_occurrence_filename = f"co_occurrence_{datetime.now().strftime('%Y%m%d')}"
    final_co_occurrence_filename += ".csv"

    st.download_button(
        label="📥 Download results as CSV",
        data=csv,
        file_name=final_co_occurrence_filename,
        mime="text/csv",
    )
   # for word, count in st.session_state["last_preview"]:
    #    st.write(f"- **{word}**: {count}")

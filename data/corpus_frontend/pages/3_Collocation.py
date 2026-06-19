import streamlit as st
import requests
import time
import pandas as pd
from io import BytesIO
from datetime import datetime, date

# -----------------------------
# Config
# -----------------------------
API_URL = "https://tibetcorpus.uni-leipzig.de/corpus_api"

st.set_page_config(page_title="Collocation Analysis", layout="wide")
st.title("Collocation Analysis")

st.markdown("Upload your subcorpus to perform an analysis on a chosen key term.")

st.header("✨ Uncovering \'Natural\' Word Partners")

st.markdown("""
While Co-occurrence Analysis shows words that appear *near* each other, **Collocation Analysis** identifies words that appear right next to each other *more often th>
These are often words that sound "natural" together to a native speaker.
""")

st.subheader("How it Helps your Research:")
st.markdown("""
* It helps you pinpoint strong, meaningful relationships between words.
* It can highlight common expressions that characterise a particular discourse.
* By showing "negative collocations," it can also reveal words that are *unlikely* to appear with your keyword, which can be just as insightful.
""")

st.subheader("Important Considerations (Limitations):")
st.markdown("""
* **Statistical Significance:** This analysis uses a statistical measure (PMI) to find truly "sticky" word pairs. A higher positive score means a stronger, non-rando>
* **Common Words Excluded:** Where stated, we filter out very common words (e.g. 'དང་,' 'ང་', 'དེ་') to focus on more significant associations.
* **OCR Impact:** Errors from the original text scanning (OCR) might occasionally affect the accuracy of word counts.
* **Rare Words:** If your keyword is very rarely found, there might not be enough data to identify statistically significant collocations.
* **Context is Key:** A collocation is a pattern, not always a fixed idiom. Its exact meaning can still depend on the broader context.
* **Unit of Analysis = Paragraph:** We look for words which appear right next to each other within paragraphs/'text regions'. This means you can upload a corpus filt>
* **Search Term Limit:** This tool works best for single words (like "ཆོས་ལུགས" or "མི་དམངས") - terms that you would expect to find entries for in a dictionary. If you >
""")

st.markdown("""
This tool helps you uncover the ingrained linguistic habits and expressive choices within the different newspaper texts.
""")

# state
if "coll_job_id" not in st.session_state:
    st.session_state["coll_job_id"] = None
if "is_disabled" not in st.session_state:
    st.session_state["is_disabled"] = False
if "last_file_name" not in st.session_state:
    st.session_state["last_file_name"] = None
if "last_preview" not in st.session_state:
    st.session_state["last_preview"] = None

uploaded = st.file_uploader("Upload your subcorpus", type=["csv"])

if uploaded and uploaded.name != st.session_state["last_file_name"]:
    st.session_state["coll_job_id"] = None
    st.session_state["is_disabled"] = False
    st.session_state["last_file_name"] = uploaded.name
    st.session_state["last_preview"] = None

search_term = st.text_input("Optional search term (for focused collocations):", value="")
col1, col2 = st.columns(2)

# -----------------------------
# Preview
# -----------------------------
with col1:
    if st.button("🔎 Preview matches", disabled=not uploaded):
        if not uploaded:
            st.warning("Upload a CSV first.")
        elif not search_term.strip():
            st.warning("Enter a search term to preview.")
        else:
            with st.spinner("Previewing…"):
                files = {"file": (uploaded.name, uploaded.getvalue(), "text/csv")}
                try:
                    res = requests.post(
                        f"{API_URL}/preview",
                        params={"search_term": search_term, "limit": 5},
                        files=files,
                        timeout=3000,
                    )
                    res.raise_for_status()
                    job_id = res.json()["job_id"]
                    st.session_state["preview_job_id"] = job_id
                    st.info(f"Preview job submitted: {job_id}")
                except Exception as e:
                    st.error(f"Submit failed: {e}")


# Poll and fetch preview results
if "preview_job_id" in st.session_state and st.session_state["preview_job_id"]:
    job_id = st.session_state["preview_job_id"]
    status = None

    with st.spinner("Checking preview job status..."):
        for _ in range(1500):  # 240s max wait
            try:
                res = requests.get(f"{API_URL}/status/{job_id}")
                res.raise_for_status()
                status = res.json()["state"]
                if status == "SUCCESS":
                    break
                elif status in ["FAILURE", "REVOKED"]:
                    st.error(f"Preview job failed: {status}")
                    st.session_state.pop("preview_job_id", None)
                    break
            except Exception as e:
                st.error(f"Status check failed: {e}")
                break
            time.sleep(5)

    if status == "SUCCESS":
        try:
            res = requests.get(f"{API_URL}/preview_result/{job_id}", timeout=3000)
            res.raise_for_status()
            preview = res.json()
            st.session_state["last_preview"] = preview
            st.success(f"Found {preview['total_matches']} matches (scanned {preview['scanned_rows']} rows).")
        except Exception as e:
            st.error(f"Fetch failed: {e}")
        st.session_state.pop("preview_job_id", None)

# Display preview excerpts
if st.session_state.get("last_preview"):
    st.markdown("### Preview excerpts")
    for i, p in enumerate(st.session_state["last_preview"]["previews"], start=1):
        st.write(f"**{i}.** {p}")


# -----------------------------
# Run full collocations (Celery)
# -----------------------------
with col2:
    if st.button("🚀 Run full collocation analysis", disabled=(not uploaded or st.session_state["is_disabled"])):
        if not uploaded:
            st.warning("Upload a CSV first.")
        else:
            with st.spinner("Submitting job…"):
                files = {"file": (uploaded.name, uploaded.getvalue(), "text/csv")}
                try:
                    res = requests.post(
                        f"{API_URL}/collocations",
                        params={"search_term": search_term if search_term.strip() else None, "top_n": 50},
                        files=files,
                        timeout=3000,
                    )
                    res.raise_for_status()
                    job_id = res.json()["job_id"]
                    st.session_state["coll_job_id"] = job_id
                    st.session_state["is_disabled"] = True
                    st.success("Job submitted.")
                except Exception as e:
                    st.error(f"Submit failed: {e}")

# -----------------------------
# Polling
# -----------------------------
if st.session_state["coll_job_id"]:
    job_id = st.session_state["coll_job_id"]
    status = None
    with st.spinner("Checking status…"):
        for _ in range(1500):  # up to ~120×2s = 240s = 4 min
            try:
                res = requests.get(f"{API_URL}/status/{job_id}", timeout=3000)
                res.raise_for_status()
                status = res.json()["state"]
                if status == "SUCCESS":
                    break
                elif status in ["FAILURE", "REVOKED"]:
                    st.error(f"Job failed: {status}")
                    st.session_state["coll_job_id"] = None
                    st.session_state["is_disabled"] = False
                    break
            except Exception as e:
                st.error(f"Status check failed: {e}")
                st.session_state["is_disabled"] = False
                break
            time.sleep(2)

    if status == "SUCCESS":
        st.success("Collocation CSV ready!")
        download_url = f"{API_URL}/download/{job_id}"

        # fetch CSV bytes
        try:
            csv_bytes = requests.get(download_url, timeout=3000).content
            df = pd.read_csv(BytesIO(csv_bytes))

            # Show grouped sections as separate tables
            st.markdown("---")
            st.markdown("### Results")
            for section in df["section"].unique():
                if section == "overall_trigram_positive":
                    st.markdown(f"<h3>📊 Collocation (PMI) Results: Corpus-Wide</h3>", unsafe_allow_html=True)
                    st.markdown(f"**{section}**")
                    st.markdown("This analysis presents sticky **three-word** terms (or 'trigrams').")
                    st.markdown("We do not omit results which contain very common words ('stopwords') here because common words may occur within sticky phrases.")
                    st.markdown("See the section below this one to find two-word and three-word results containing a term of your choice.")

                elif section == "overall_trigram_negative":
                    st.markdown(f"**{section}**")

                elif section == "bigram_positive":
                    st.markdown(f"<h3>Two-Word Results: {section}</h3>", unsafe_allow_html=True)
                    st.markdown("We omit results which contain very common words ('stopwords') here.")

                elif section == "bigram_negative":
                    st.markdown(f"<h3>Two-Word Results: {section}</h3>", unsafe_allow_html=True)
                    st.markdown("We omit results which contain very common words ('stopwords') here.")

                elif section == "trigram_positive":
                    st.markdown(f"<h3>Three-Word Results: {section}</h3>", unsafe_allow_html=True)
                    st.markdown("We do not omit results which contain very common words ('stopwords') here because common words may occur within sticky phrases.")

                elif section == "trigram_negative":
                    st.markdown(f"<h3>Three-Word Results: {section}</h3>", unsafe_allow_html=True)
                    st.markdown("We do not omit results which contain very common words ('stopwords') here because common words may occur within sticky phrases.")

                else:
                    st.markdown(f"**{section}**")

                sub = df[df["section"] == section].reset_index(drop=True)
                st.dataframe(sub)

            # Download button offering same CSV
            if 'collocation_download_filename_base' not in st.session_state:
                st.session_state.collocation_download_filename_base = f"collocations_{datetime.now().strftime('%Y%m%d')}"

            user_entered_filename_base = st.text_input(
                "Enter desired filename:",
                value = st.session_state.collocation_download_filename_base,
                key="download_filename_input"
            )

            st.session_state.collocation_download_filename_base = user_entered_filename_base

            final_collocation_filename = user_entered_filename_base.strip().replace('.csv', '')
            if not final_collocation_filename:
                final_collocation_filename = f"collocations_{datetime.now().strftime('%Y%m%d')}"
            final_collocation_filename += ".csv"

            st.download_button(
                label="📥 Download collocations CSV",
                data=csv_bytes,
                file_name=final_collocation_filename,
                mime="text/csv",
            )
        except Exception as e:
            st.error(f"Failed to fetch/display results: {e}")

        st.session_state["is_disabled"] = False


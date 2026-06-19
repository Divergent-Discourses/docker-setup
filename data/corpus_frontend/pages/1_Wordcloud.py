import streamlit as st
import requests
import time
from datetime import datetime, date

API_URL = "https://tibetcorpus.uni-leipzig.de/corpus_api"

st.set_page_config(page_title="Wordcloud Generator", layout="wide")
st.title("Create a Wordcloud")

st.write('Upload your subcorpus to create a summary wordcloud.')

st.subheader("☁️ What's a Wordcloud?")
st.markdown("""
It's a visual way to see which words appear most frequently in your text.
""")

st.markdown("""
**How to read it:**
* **Bigger words** appear more often in the text.
* **Smaller words** appear less often.
""")

st.markdown("""
Use it to quickly spot the main topics and key terms discussed in your corpus.
""")

MAX_FILE_SIZE_MB = 2000

# Initialise session state variables if they don't exist
if "wordcloud_job_id" not in st.session_state:
    st.session_state["wordcloud_job_id"] = None
if "is_button_disabled" not in st.session_state:
    st.session_state["is_button_disabled"] = False
if "last_uploaded_file_name" not in st.session_state:
    st.session_state["last_uploaded_file_name"] = None

prev_file = st.session_state.get("last_uploaded_file_name")
uploaded_file = st.file_uploader("Upload your subcorpus", type="csv")

if uploaded_file and uploaded_file.name != prev_file:
    st.session_state["wordcloud_job_id"] = None
    st.session_state["is_button_disabled"] = False
    st.session_state["last_uploaded_file_name"] = uploaded_file.name

# Control button's state by st.session_state["is_button_disabled"]
# Disable button if True to avoid multiple job submissions = server overload
if uploaded_file:
    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        st.error(f"File is too large. Max size is {MAX_FILE_SIZE_MB} MB.")
        st.stop()

    with st.form(key="wordcloud_form"):
        submit = st.form_submit_button(
            "Generate Wordcloud",
            disabled=st.session_state["is_button_disabled"]
        )

        if submit:
            with st.spinner("Submitting job..."):
                files = {"file": uploaded_file}
                try:
                    res = requests.post(f"{API_URL}/wordcloud", files=files)
                    res.raise_for_status()
                    job_id = res.json()["job_id"]
                    st.session_state["wordcloud_job_id"] = job_id

                    # Disable button immediately
                    st.session_state["is_button_disabled"] = True
                    st.success("Job submitted. Please await results.")
                except Exception as e:
                    st.error(f"Upload failed: {e}")
                    st.session_state["is_button_disabled"] = False
                    st.session_state["wordcloud_job_id"] = None

# Poll status and display SVG
if "wordcloud_job_id" in st.session_state and st.session_state["wordcloud_job_id"] != None:
    job_id = st.session_state["wordcloud_job_id"]
    status = None

    with st.spinner("Checking status..."):
        for _ in range(30):  # wait max 30 × 2s = 60s
            try:
                res = requests.get(f"{API_URL}/status/{job_id}")
                res.raise_for_status()
                status = res.json()["state"]
                if status == "SUCCESS":
                    break
                elif status in ["FAILURE", "REVOKED"]:
                    st.error(f"Job failed: {status}")
                    st.session_state.pop("wordcloud_job_id", None)
                    st.session_state["is_button_disabled"] = False
                    break
            except Exception as e:
                st.error(f"Status check failed: {e}")
                st.error(f"Response status code: {res.status_code}")
                st.session_state["is_button_disabled"] = False
                break
            time.sleep(2)

    if status == "SUCCESS":
        st.success("Wordcloud ready!")
        download_url = f"{API_URL}/download/{job_id}"
        st.markdown("---")
        st.markdown("### 🔍 Wordcloud Preview")
        st.markdown(
            f'<img src="{download_url}" style="width:100%;" alt="Wordcloud" />',
            unsafe_allow_html=True
        )

        st.session_state["is_button_disabled"] = False

        if 'wordcloud_download_filename_base' not in st.session_state:
            st.session_state.wordcloud_download_filename_base = f"wordcloud_{datetime.now().strftime('%Y%m%d')}"

        user_entered_filename_base = st.text_input(
            "Enter desired filename:",
            value=st.session_state.wordcloud_download_filename_base,
            key="wordcloud_filename_input"
        )
        st.session_state.wordcloud_download_filename_base = user_entered_filename_base

        final_wordcloud_filename = user_entered_filename_base.strip().replace('.svg', '')
        if not final_wordcloud_filename:
            final_wordcloud_filename = f"wordcloud_{datetime.now().strftime('%Y%m%d')}"
        final_wordcloud_filename += ".svg"

        st.download_button(
            label="📥 Download Wordcloud",
            data=requests.get(download_url).content,
            file_name=final_wordcloud_filename,
            mime="image/svg+xml",
            key="download_wordcloud_button"
        )

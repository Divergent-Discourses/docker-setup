import streamlit as st
import pandas as pd
import re
import requests
import time
from datetime import datetime, date
import io

# --- Streamlit Config ---
st.set_page_config(page_title="Corpus Tool", layout="wide")
st.title("Corpus Filtering Tool")
st.sidebar.success("Select an analysis tool.")
st.write("Create a subcorpus for further analysis below or move to a page in the sidebar to inspect a subcorpus further.")

API_URL = "https://tibetcorpus.uni-leipzig.de/corpus_api"

#corpus_path = './new_file_name.csv'
corpus_path = './divergent_discourses_corpus.csv'

# --- Initial Load for Filter Options ---
@st.cache_data
def load_metadata_options():
    # Load metadata from a local copy of the CSV to extract dropdown options
    #df = pd.read_csv('./master.csv')
    #df = pd.read_csv('./subcorpus_20250803_utf8_syntheticlarge.csv')
    df = pd.read_csv(corpus_path)
    master_df_len = len(df)
    return sorted(df["region_type"].dropna().unique()), sorted(df["newspaper"].dropna().unique()), master_df_len

region_options, newspaper_options, master_df_len = load_metadata_options()

# --- Filter Widgets ---
region_filter = st.multiselect("Region Type", region_options, help=(
    "Region type/text region type: A layout element containing specific textual "
    "information.\nE.g.:\n"
    "- **HEADING** → headlines or subheadings of articles\n"
    "- **CREDIT** → names of authors, photographers, or institutions that created content\n"
    "- **PARAGRAPH** → the main body text of an article"))

with st.expander("Click for **region type** explanations"):
    st.markdown("""
    The corpus distinguishes different kinds of text regions within newspapers.  
    Most region codes follow a clear pattern with prefixes:

    - **No prefix** → Tibetan text  
    - **`CNH_`** → Chinese (horizontal)  
    - **`CNV_`** → Chinese (vertical)  
    - **`ENG_`** → English (Latin script)  

    For details on these codes, see p167+:  
    [Erhard, F.X. (2025). *Text and Layout Recognition for Tibetan Newspapers with Transkribus.* RET 74, pp.128–171 (esp. p.167).](https://d1i1jdw69xsqx0.cloudfront.net/digitalhimalaya/collections/journals/ret/pdf/ret_74_04.pdf)


    ---

    **Examples of structural region tags:**

    | Tag | Explanation |
    |-----|-------------|
    | NEWSPAPER-TITLE | [Tibetan] Main newspaper title |
    | CNH_NEWSPAPER-TITLE | Newspaper title in horizontal Chinese |
    | ENG_NEWSPAPER-TITLE | Newspaper title in English |
    | HEADER | [Tibetan] Top line with page/date info |
    | CNH_HEADER | Header in horizontal Chinese |
    | ENG_HEADER | Header in English |
    | PARAGRAPH | [Tibetan] Main body of text |
    | CNH_PARAGRAPH | Paragraph in horizontal Chinese |
    | CNV_PARAGRAPH | Paragraph in vertical Chinese |
    | ENG_PARAGRAPH | Paragraph in English |
    | CAPTION | [Tibetan] Captions under images/maps |
    | CNH_CAPTION | Caption in horizontal Chinese |
    | ENG_CAPTION | Caption in English |
    | SECTION-HEADING | [Tibetan] Section title (e.g. news column) |
    | CNH_SECTION-HEADING | Section heading in horizontal Chinese |
    | ENG_SECTION-HEADING | Section heading in English |
    | CREDIT | [Tibetan] Author/agency attribution |
    | CNH_CREDIT | Credit in horizontal Chinese |
    | ENG_CREDIT | Credit in English |
    | MARGINALIA | [Tibetan] Notes printed in the margin |
    | CNV_MARGINALIA | Marginalia in vertical Chinese |
    | ENG_MARGINALIA | Marginalia in English |
    | CONTINUED | [All langs] Marks continuation across pages |
    | OTHER | [Tibetan] Publishing info, announcements, etc. |
    | CNH_OTHER | Other info in horizontal Chinese |
    | CNV_OTHER | Other info in vertical Chinese |
    | ENG_OTHER | Other info in English |

    ---
    """)

newspaper_filter = st.multiselect("Newspaper", newspaper_options)

with st.expander("Click for **newspaper code** explanations"):
    st.markdown("""
    Below is the list of newspapers included in the corpus, along with their short codes, Tibetan titles, 
    and donor shelfmarks.  
    For full details, see the article appendix:  
    [Erhard, F.X. (2025). *The Divergent Discourses Corpus.* RET 74, pp. 44–80.](https://d1i1jdw69xsqx0.cloudfront.net/digitalhimalaya/collections/journals/ret/pdf/ret_74_02.pdf)

    ---

    | Code | Newspaper Title (English)      | Tibetan Title | Donors (Shelfmark) |
    |------|--------------------------------|---------------|---------------------|
    | CWN  | Central Weekly News            | krung dbyang gsar 'gyur | IT (AC16810977); UW (99133499060001452) |
    | DTF  | Defend Tibet's Freedom         | rang dbang srung skyob gsar shog | IT (AC16810250); CU (AN6.T6 .R36); BL |
    | FRD  | Freedom                        | rang dbang gsar shog | IT (AC16809715); BD |
    | GDN  | Ganze Daily                    | dkar mdzes nyin re'i gsar 'gyur | OI (XIV 92/1959); RB |
    | GOT  | Understanding (not in corpus)  | go rtogs | TS |
    | GTN  | Gyantse News                   | rgyal rtse gsar ‘gyur | LT |
    | KDN  | Kangding News                  | dar mdo’i gsar ‘gyur | MV (As Z Ag 10) |
    | MJN  | Minjiang News                  | min kyang tshags dpar | MV (As Z Ag 8); OI (XIV 93/1959) |
    | NIB  | News in Brief                  | Gsar ‘gyur mdor bsdus | TL; MV (As Z Ag 9); CU (AN6.T6 G76) |
    | QTN  | Qinghai Tibetan News           | Mtsho sngon bod yig gsar ‘gyur | CU (AN6.T6M4); SB (Zsn 128163 MR); MV (As Z Ag 12); OI (XIV 85/1959) |
    | SGN  | South Gansu News               | kan lho gsar 'gyur | OI (XIV 90/1959) |
    | TDP  | Tibet Daily Pictorial          | bod ljongs nyin re'i gsar 'gyur par ris | OI (XV 86/1959) |
    | TID  | Tibet Daily                    | bod ljongs nyin re'i gsar 'gyur | OI (XIV 91/1959); SB (Zsn 128162 MR); IT (AC16863326) |
    | TIF  | Tibetan Freedom                | bod mi'i rang dbang | IT (AC16810977) |
    | TIM  | Tibet Mirror                   | yul phyog so so’i gsar ‘gyur me long | MV (As Z Ag 11); IT (AC16810250); CU (DS786.A1 Y85); CF (3 IET PER 1-28) |
    | XNX  | South-West Inst. for Nat.      | Lho nub mi rigs slob grwa chen po | OI (XIV 89/1959); MV (As Z Ag 7) |
    | ZYX  | Central Inst. for Nationalities| Krung dbyang mi rigs slob grwa | OI (XIV 88/1959) |

    ---
    """)


use_date_filter = st.checkbox("Filter by date range", value=False)
start = end = None
if use_date_filter:
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Start Date", value=None, min_value=date(1945, 1, 1), max_value=date(1970, 12, 31))
    with col2:
        end = st.date_input("End Date", value=None, min_value=date(1945, 1, 1), max_value=date(1970, 12, 31))

# --- Keyword Search ---
st.subheader("Keyword Search")
st.markdown("""
Use the boxes below to search for words or phrases in the text.
- **"ALL of these words"** acts like an `AND` search. All words you enter must be present.
- **"ANY of these words"** acts like an `OR` search. At least one of the words you enter must be present.
- **"NONE of these words"** acts like a `NOT` search. The text will be excluded if it contains any of these words.
""")

# An expander providing extra help
with st.expander("Confused? Click here for examples"):
    st.markdown("""

    * **ALL of these words (`AND`):**
        * **Purpose:** Find paragraphs where *every* word you list is present.
        * **Example:** If you enter `བོད་ ལྷ་ས་` ("Tibet" + "Lhasa"), you will only get paragraphs that contain *both* `བོད་` AND `ལྷ་ས་`.

    * **ANY of these words (`OR`):**
        * **Purpose:** Find paragraphs where *at least one* of the words you list is present.
        * **Example:** If you enter `ཆོས་ལུགས རིག་གནས་` ("religion" + "culture"), you will see paragraphs that contain `ཆོས་ལུགས` OR `རིག་གནས་` OR both.

    * **NONE of these words (`NOT`):**
        * **Purpose:** Exclude paragraphs that contain *any* of the words you list.
        * **Example:** If you enter `དགོན་པ` ("monastery"), you will see paragraphs that do NOT contain `དགོན་པ`.

    **Tip:** You can combine these! For example, you could find paragraphs with which mention `དགོན་པ་` (AND) alongside either `གཞིས་ཀ་རྩེ་` (OR) or `ལྷ་ས་` (OR). 

    **Phrases:** Use quotes for exact phrases. E.g., "`སྤྱི་ལོ་༡༩༥༧སྤྱི་ཟླ་༥ཚེས་༡༤་`" will only match the exact phrase.
    """)

col1, col2, col3 = st.columns(3)
with col1:
    all_words = st.text_input("`AND` Find paragraphs containing ALL of these words:", help="Enter words or \"phrases in quotes\". Separate by spaces.")
with col2:
    any_words = st.text_input("`OR` Find paragraphs containing ANY of these words:", help="Enter words or \"phrases in quotes\". Separate by spaces.")
with col3:
    none_words = st.text_input("`NOT` Find paragraphs that DO NOT contain these words:", help="Enter words or \"phrases in quotes\". Separate by spaces.")

# --- Helper Function ---
def get_terms(text_input):
    raw_terms = re.findall(r'"[^"]+"|\S+', text_input)
    return [term.strip().strip('"') for term in raw_terms]

# --- Session States ---
if "job_id" not in st.session_state:
    st.session_state.job_id = None
if "filtered_data" not in st.session_state:
    st.session_state.filtered_data = None

# --- Apply Button ---
if st.button("Apply Filter", type="primary"):
    payload = {
        "region_filter": region_filter,
        "newspaper_filter": newspaper_filter,
        "start_date": str(start) if start else None,
        "end_date": str(end) if end else None,
        "all_words": all_words,
        "any_words": any_words,
        "none_words": none_words
    }

    try:
        response = requests.post(f"{API_URL}/filter", json=payload)
        response.raise_for_status()
        new_job_id = response.json()["job_id"]
        
        # Only reset if new job_id differs from current
        if new_job_id != st.session_state.get("job_id"):
            st.session_state.job_id = new_job_id
            st.session_state.filtered_data = None  # Clear old data immediately

        st.info(f"Submitted filter job (task ID: {st.session_state.job_id})")

    except Exception as e:
        st.error(f"Error submitting filter job: {e}")
        st.stop()


# --- Polling for Results ---
if st.session_state.job_id and st.session_state.filtered_data is None:
    with st.spinner("Filtering corpus... this may take a minute."):
        for _ in range(120):
            r = requests.get(f"{API_URL}/status/{st.session_state.job_id}")
            status_data = r.json()
            if status_data["state"] == "SUCCESS":
                csv_resp = requests.get(f"{API_URL}/download/{st.session_state.job_id}")
                csv_resp.raise_for_status()
                df = pd.read_csv(io.StringIO(csv_resp.text))
                st.session_state.filtered_data = df
                break
            elif status_data["state"] == "FAILURE":
                st.error("❌ Backend failed to process your request.")
                break
            time.sleep(2)

# --- Display Result ---
if st.session_state.filtered_data is not None:
    df = st.session_state.filtered_data
    st.success(f"🎉 Filtered from {master_df_len} entries down to {len(df)} matching paragraphs.")
    st.subheader("Subcorpus Preview")
    st.markdown("See a preview of up to 50 results below - download your file to see full results.")
    st.dataframe(df.head(50), use_container_width=True)

    # Download Section
    st.markdown("### Download Filtered Corpus")

    if 'csv_download_filename_base' not in st.session_state:
        st.session_state.csv_download_filename_base = f"subcorpus_{datetime.now().strftime('%Y%m%d')}"

    user_entered_filename_base = st.text_input(
        "Enter desired filename:",
        value=st.session_state.csv_download_filename_base,
        key="csv_filename_input"
    )
    st.session_state.csv_download_filename_base = user_entered_filename_base

    final_csv_filename = user_entered_filename_base.strip().replace('.csv', '')
    if not final_csv_filename:
        final_csv_filename = f"subcorpus_{datetime.now().strftime('%Y%m%d')}"
    final_csv_filename += ".csv"

    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 Download Filtered CSV",
        data=csv_data,
        file_name=final_csv_filename,
        mime="text/csv",
        key="download_csv_button"
    )
elif st.session_state.job_id and st.session_state.filtered_data is None:
    st.info("Still waiting for results. Try again in a few seconds.")

# --- Show Corpus Preview (before filtering) ---
if st.session_state.filtered_data is None and st.session_state.job_id is None:
    try:
        st.subheader("Corpus Preview")
        preview_df = pd.read_csv(corpus_path)
        st.write(f"Previewing 25 out of {len(preview_df)} total paragraphs.")
        st.dataframe(preview_df.head(25), use_container_width=True)
    except Exception as e:
        st.error(f"Error loading corpus preview: {e}")

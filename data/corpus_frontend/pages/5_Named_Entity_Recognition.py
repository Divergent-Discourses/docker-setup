import streamlit as st
import spacy
from spacy import displacy
import sys
from pathlib import Path
from collections import Counter
import pandas as pd
from utils import create_spacy_tokenizer_factory
import io

# ── Tag definitions ───────────────────────────────────────────────────────────
TAG_INFO = {
    "PER": {
        "label": "Person",
        "color": "#4A90D9",
        "bg": "#E8F2FC",
        "description": (
            "Names of individual people, including first, middle, and last names. "
            "Honorific titles or position designations appearing with a personal name "
            "are tagged separately as POSITION."
        ),
        "example": "བསྟན་འཛིན་རྒྱ་མཚོ་",
    },
    "ORG": {
        "label": "Organisation",
        "color": "#E07B39",
        "bg": "#FDF0E8",
        "description": (
            "Names of companies, government agencies, institutions, associations, "
            "and place names used as a metonym for organisations "
            "(e.g., ལྷ་ས་གྲོང་ཁྱེར་, རང་ལྗོངས་, བོད་རང་སྐྱོང་ལྗོངས་), "
            "and other formally structured groups."
        ),
        "example": "བོད་མི་མང་སྤྱི་འཐུས་ལྷན་ཚོགས་",
    },
    "SOC": {
        "label": "Social Group",
        "color": "#7B5EA7",
        "bg": "#F3EEF9",
        "description": (
            "Names of unstructured social groups, including workers, ethnic groups, "
            "soldiers, academics, youth, and officials."
        ),
        "example": "བོད་རིགས་",
    },
    "TIME": {
        "label": "Time",
        "color": "#3BAF7E",
        "bg": "#E8F7F2",
        "description": (
            "Temporal expressions including dates, times, epochs, durations, "
            "and periods."
        ),
        "example": "ཕྱི་ལོ་ ༢༠༢༣ ལོ་",
    },
    "LOC": {
        "label": "Location",
        "color": "#C0392B",
        "bg": "#FAEAEA",
        "description": (
            "Geographic locations including countries, cities, addresses, "
            "landmarks, regions, and natural features."
        ),
        "example": "ལྷ་ས་",
    },
    "POSITION": {
        "label": "Position",
        "color": "#B7860B",
        "bg": "#FDF6E3",
        "description": (
            "Religious, political, or job titles, roles, positions of authority, "
            "and honorifics. Titles are categorised separately from any associated "
            "personal names, which belong in PER."
        ),
        "example": "༧གོང་ས་ཏཱ་ལའི་བླ་མ་",
    },
    "TITLE": {
        "label": "Title",
        "color": "#2E86AB",
        "bg": "#E6F3F8",
        "description": (
            "Names of published works, including books, articles, reports, films, "
            "songs, and other creative or published/unpublished documents."
        ),
        "example": "བོད་ཀྱི་དུས་བབ་",
    },
    "SLOGAN": {
        "label": "Slogan",
        "color": "#C0392B",
        "bg": "#FAF0F0",
        "description": (
            "Names of policies, political ideologies, campaigns and drives. "
            "Catchphrases, mottos, proverbs, slogans, names of theories, or memorable "
            "phrases associated with political, commercial, or cultural entities. "
            "May appear without explicit quotation markers."
        ),
        "example": "བོད་རང་དབང་རང་བཙན",
    },
    "EVENT": {
        "label": "Event",
        "color": "#16A085",
        "bg": "#E8F8F5",
        "description": (
            "Named occasions including conferences, festivals, anniversaries, "
            "ceremonies, disasters, and historical events."
        ),
        "example": "ལོ་གསར་",
    },
}

# displacy colour map (background / border colour per label)
DISPLACY_COLORS = {tag: info["color"] for tag, info in TAG_INFO.items()}

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Google Fonts ─────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=Source+Sans+3:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Source Sans 3', sans-serif;
    }

    /* ── Title ────────────────────────────────────────── */
    h1 { font-family: 'Playfair Display', serif !important; letter-spacing: -0.5px; }

    /* ── Tag legend cards ─────────────────────────────── */
    .tag-card {
        border-radius 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
        border-left: 5px solid;
        font-size: 0.93rem;
        line-height: 1.55;
    }
    .tag-badge {
        display: inline-block;
        font-family: 'Source Code Pro', monospace;
        font-weight: 700;
        font-size: 0.82rem;
        letter-spacing: 0.06em;
        padding: 2px 9px;
        border-radius: 4px;
        color: #fff;
        margin-right: 8px;
        vertical-align: middle;
    }
    .tag-label {
        font-family: 'Playfair Display', serif;
        font-size: 1.05rem;
        font-weight: 500;
        vertical-align: middle;
    }
    .tag-desc { margin-top: 7px; color: #444; }
    .tag-example {
        margin-top: 5px;
        font-size: 0.85rem;
        color: #777;
        font-style: italic;
    }

    /* ── displaCy wrapper ─────────────────────────────── */
    .displacy-wrapper {
        background: #FAFAF8;
        border: 1px solid #E8E4DC;
        border-radius: 12px;
        padding: 28px 24px;
        font-size: 1.15rem;
        line-height: 2.8;
        font-family: 'Source Sans 3', sans-serif;
        overflow-x: auto;
    }

    /* ── Section divider ──────────────────────────────── */
    .section-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.25rem;
        font-weight: 700;
        margin: 28px 0 12px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid #E8E4DC;
        color: #1A1A1A;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏷️ Tibetn Named Entity Recognition")
st.markdown(
    "Visualize named entities in Tibetan newspaper text using a trained spaCy model. "
    "The tag set was developed for the study of Tibetan-language newspapers of the "
    "**1950s and 1960s**."
)

# ── Tag legend ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">NER Tag Reference</div>', unsafe_allow_html=True)

_cards = []
for _tag, _info in TAG_INFO.items():
    _cards.append(
        "<div class=\"tag-card\" style=\"background:" + _info["bg"] + ";"
        "border-left-color:" + _info["color"] + ";"
        "flex:1 1 auto;min-width:170px;max-width:260px;box-sizing:border-box;\">"
        "<span class=\"tag-badge\" style=\"background:" + _info["color"] + ";\">" + _tag + "</span>"
        "<span class=\"tag-label\">" + _info["label"] + "</span>"
        "<div class=\"tag-desc\">" + _info["description"] + "</div>"
        "<div class=\"tag-example\">e.g. " + _info["example"] + "</div>"
        "</div>"
    )
_legend_html = (
    "<div style=\"display:flex;flex-direction:row;flex-wrap:wrap;gap:10px;margin-bottom:8px;\">"
    + "".join(_cards)
    + "</div>"
)
st.markdown(_legend_html, unsafe_allow_html=True)

# ── Shared helpers ────────────────────────────────────────────────────────────
DISPLACY_OPTIONS = {"ents": list(TAG_INFO.keys()), "colors": DISPLACY_COLORS}
 
 
def render_displacy(doc) -> str:
    html = displacy.render(doc, style="ent", options=DISPLACY_OPTIONS, page=False)
    return '<div class="displacy-wrapper">' + html + "</div>"
 
 
def entity_badge_bar(label_counts: Counter) -> str:
    parts = []
    for lbl, cnt in sorted(label_counts.items()):
        color = TAG_INFO.get(lbl, {}).get("color", "#888")
        parts.append(
            "<span class=\"tag-badge\" style=\"background:" + color + ";\">"
            + lbl + "&nbsp;<strong>" + str(cnt) + "</strong></span>"
        )
    return "<p style=\"margin-bottom:14px;\">" + " &nbsp; ".join(parts) + "</p>"
 
# ── Load model (cached) ──────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading SpaCy model...")
def load_spacy_model():
    nlp_model = spacy.load("bo_core_news_lg")
    # Model strips trailing tshegs to count tokens without strange duplications
    nlp_model.tokenizer = create_spacy_tokenizer_factory(force_split_tsheg=True)(nlp_model)
    # trailing_tsheg_stripper = lambda token: str(token.text).rstrip("་")
    # Token.set_extension("tsheg_stripped", getter=trailing_tsheg_stripper, force=True)
    return nlp_model

nlp = load_spacy_model()
 
# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_text, tab_csv = st.tabs(["📝 Single Text", "📄 CSV Batch"])
 
# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Single text
# ══════════════════════════════════════════════════════════════════════════════
with tab_text:
    st.markdown('<div class="section-title">Input Text</div>', unsafe_allow_html=True)
 
    default_text = (
        "༡༩༥༩ལོར་བོད་ལྷ་སར་ཆིང་གིས་དམར་དམག་གིས་བཙན་འཛུལ་བྱས་སོང་། "
        "དེའི་རྗེས་སུ་བོད་མི་མང་གི་ཐོག་ནས་གཞུང་འབྲེལ་ལས་དོན་མང་པོ་ཞིག་བྱུང་།"
    )
    input_text = st.text_area(
        "Paste Tibetan text here:",
        value=default_text,
        height=130,
        label_visibility="collapsed",
    )
    run_btn = st.button("▶  Analyse", type="primary", key="btn_single")
 
    st.markdown('<div class="section-title">Entity Visualization</div>', unsafe_allow_html=True)
 
    if run_btn or input_text == default_text:
        if not nlp:
            st.info("Enter a valid model name in the sidebar to run NER.")
        elif not input_text.strip():
            st.warning("Please enter some text.")
        else:
            with st.spinner("Running NER…"):
                with nlp.select_pipes(enable=["ner"]):
                    doc = nlp(input_text.strip())
 
            st.markdown(render_displacy(doc), unsafe_allow_html=True)
 
            ents = doc.ents
            if ents:
                st.markdown('<div class="section-title">Extracted Entities</div>', unsafe_allow_html=True)
                label_counts = Counter(e.label_ for e in ents)
                st.markdown(entity_badge_bar(label_counts), unsafe_allow_html=True)
 
                rows = [
                    {
                        "Text":  ent.text,
                        "Label": ent.label_,
                        "Type":  TAG_INFO.get(ent.label_, {}).get("label", ent.label_),
                        "Start": ent.start_char,
                        "End":   ent.end_char,
                    }
                    for ent in ents
                ]
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Label": st.column_config.TextColumn(width="small"),
                        "Start": st.column_config.NumberColumn(width="small"),
                        "End":   st.column_config.NumberColumn(width="small"),
                    },
                )
            else:
                st.info("No entities detected in the input text.")
    else:
        st.info("Enter text above and click **▶ Analyse** to see entity highlights.")
 
# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CSV batch
# ══════════════════════════════════════════════════════════════════════════════
with tab_csv:
    st.markdown('<div class="section-title">Upload CSV</div>', unsafe_allow_html=True)
    st.markdown(
        "Upload a corpus CSV. NER will be run on the `normalised_paragraph` column. "
        "All original columns are preserved in the export."
    )
 
    # ── Session state ─────────────────────────────────────────────────────────
    if "csv_ner_results" not in st.session_state:
        st.session_state.csv_ner_results = None   # flat DataFrame of entities
    if "csv_last_file" not in st.session_state:
        st.session_state.csv_last_file = None
 
    uploaded = st.file_uploader("Upload CSV file", type=["csv"], key="csv_uploader")
 
    # Reset results when a new file is uploaded
    if uploaded is not None and uploaded.name != st.session_state.csv_last_file:
        st.session_state.csv_ner_results = None
        st.session_state.csv_last_file = uploaded.name
 
    batch_size = st.number_input(
        "Batch size", min_value=1, max_value=512, value=64,
        help="Number of texts processed in parallel. Larger = faster but uses more memory.",
        key="csv_batch_size",
    )
 
    run_csv_btn = st.button("▶  Run NER on CSV", type="primary", key="btn_csv")
 
    # ── Run ───────────────────────────────────────────────────────────────────
    if run_csv_btn:
        if not nlp:
            st.warning("Please enter a valid model name in the sidebar first.")
        elif uploaded is None:
            st.warning("Please upload a CSV file first.")
        else:
            # Read CSV
            try:
                df = pd.read_csv(uploaded)
            except Exception as exc:
                st.error(f"Could not read CSV: {exc}")
                df = None
 
            if df is not None:
                required = {"normalised_paragraph", "paragraph_idx", "filename"}
                missing = required - set(df.columns)
                if missing:
                    st.error(f"CSV is missing required columns: {', '.join(missing)}")
                else:
                    df["normalised_paragraph"] = df["normalised_paragraph"].fillna("").astype(str)
 
                    texts = df["normalised_paragraph"].tolist()
                    progress_bar = st.progress(0, text="Running NER…")
 
                    flat_rows = []
                    with nlp.select_pipes(enable=["ner"]):
                        docs = list(nlp.pipe(texts, batch_size=int(batch_size)))
 
                    for i, (doc, (_, csv_row)) in enumerate(zip(docs, df.iterrows())):
                        # Metadata columns to carry through
                        meta = {
                            "paragraph_idx":    csv_row.get("paragraph_idx", ""),
                            "filename":         csv_row.get("filename", ""),
                            "newspaper":        csv_row.get("newspaper", ""),
                            "year":             csv_row.get("year", ""),
                            "month":            csv_row.get("month", ""),
                            "day":              csv_row.get("day", ""),
                            "page_num":         csv_row.get("page_num", ""),
                            "full_date":        csv_row.get("full_date", ""),
                            "region_type":      csv_row.get("region_type", ""),
                            "readingorder_idx": csv_row.get("readingorder_idx", ""),
                            "normalised_paragraph": doc.text,
                        }
 
                        if doc.ents:
                            for ent in doc.ents:
                                flat_rows.append({
                                    **meta,
                                    "ent_text":  ent.text,
                                    "ent_label": ent.label_,
                                    "ent_type":  TAG_INFO.get(ent.label_, {}).get("label", ent.label_),
                                    "ent_start": ent.start_char,
                                    "ent_end":   ent.end_char,
                                })
                        else:
                            # Keep rows with no entities so no paragraph is lost
                            flat_rows.append({
                                **meta,
                                "ent_text":  "",
                                "ent_label": "",
                                "ent_type":  "",
                                "ent_start": "",
                                "ent_end":   "",
                            })
 
                        pct = int((i + 1) / len(docs) * 100)
                        progress_bar.progress(min(pct, 100), text=f"Running NER… {pct}%")
 
                    progress_bar.empty()
                    st.session_state.csv_ner_results = pd.DataFrame(flat_rows)
                    st.success(f"Done — processed {len(docs):,} paragraphs.")
 
    # ── Display & download results ────────────────────────────────────────────
    if st.session_state.csv_ner_results is not None:
        results_df = st.session_state.csv_ner_results
 
        st.markdown('<div class="section-title">Results</div>', unsafe_allow_html=True)
 
        # Summary metrics
        total_paras   = results_df["paragraph_idx"].nunique()
        paras_with    = results_df.loc[results_df["ent_label"] != "", "paragraph_idx"].nunique()
        total_ents    = (results_df["ent_label"] != "").sum()
 
        c1, c2, c3 = st.columns(3)
        c1.metric("Paragraphs processed", f"{total_paras:,}")
        c2.metric("Paragraphs with entities", f"{paras_with:,}")
        c3.metric("Total entities found", f"{int(total_ents):,}")
 
        # Entity frequency by label
        label_series = results_df.loc[results_df["ent_label"] != "", "ent_label"]
        if not label_series.empty:
            label_counts = Counter(label_series.tolist())
            st.markdown(entity_badge_bar(label_counts), unsafe_allow_html=True)
 
        # Filter by label
        all_labels = sorted(label_series.unique().tolist()) if not label_series.empty else []
        if all_labels:
            selected_labels = st.multiselect(
                "Filter by entity label:",
                options=all_labels,
                default=all_labels,
                key="csv_label_filter",
            )
            display_df = results_df[
                results_df["ent_label"].isin(selected_labels) | (results_df["ent_label"] == "")
            ]
        else:
            display_df = results_df
 
        # Table — show entity-bearing rows first, then empty rows
        show_empty = st.checkbox("Include paragraphs with no entities", value=False, key="show_empty")
        if not show_empty:
            display_df = display_df[display_df["ent_label"] != ""]
 
        st.markdown(f"**Showing {len(display_df):,} rows**")
 
        # Column order: metadata first, then entity columns
        col_order = [
            "paragraph_idx", "filename", "newspaper", "full_date",
            "year", "month", "day", "page_num", "readingorder_idx", "region_type",
            "normalised_paragraph",
            "ent_text", "ent_label", "ent_type", "ent_start", "ent_end",
        ]
        col_order = [c for c in col_order if c in display_df.columns]
        st.dataframe(
            display_df[col_order].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            column_config={
                "ent_label":            st.column_config.TextColumn("Label",     width="small"),
                "ent_type":             st.column_config.TextColumn("Type",      width="small"),
                "ent_text":             st.column_config.TextColumn("Entity",    width="medium"),
                "ent_start":            st.column_config.NumberColumn("Start",   width="small"),
                "ent_end":              st.column_config.NumberColumn("End",     width="small"),
                "normalised_paragraph": st.column_config.TextColumn("Paragraph", width="large"),
            },
        )
 
        # Download — always export the full unfiltered results
        st.markdown("---")
        dl_col1, dl_col2 = st.columns(2)
 
        with dl_col1:
            csv_buf = io.StringIO()
            results_df[col_order].to_csv(csv_buf, index=False)
            st.download_button(
                "⬇️ Download results as CSV",
                data=csv_buf.getvalue(),
                file_name="ner_results.csv",
                mime="text/csv",
                key="dl_csv",
            )
 
        with dl_col2:
            # Excel download via openpyxl
            try:
                xl_buf = io.BytesIO()
                with pd.ExcelWriter(xl_buf, engine="openpyxl") as writer:
                    results_df[col_order].to_excel(writer, index=False, sheet_name="NER Results")
                st.download_button(
                    "⬇️ Download results as Excel",
                    data=xl_buf.getvalue(),
                    file_name="ner_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_xlsx",
                )
            except ImportError:
                st.info("Install `openpyxl` to enable Excel export: `pip install openpyxl`")
 
    elif uploaded is not None and not run_csv_btn:
        st.info("Click **▶ Run NER on CSV** to process the uploaded file.")
    else:
        st.info("Upload a CSV file and click **▶ Run NER on CSV** to begin.")

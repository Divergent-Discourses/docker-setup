"""
Analysis logic (migrated from Streamlit)
"""
import os
import io
import uuid
from datetime import date
from typing import List, Optional, Tuple, Dict
import pandas as pd
import numpy as np
from botok import WordTokenizer
from collections import Counter
from wordcloud import WordCloud
import spacy
from spacy.tokens import Token, DocBin
import utils  # For stopwords
from utils import calculate_token_frequencies
from celery import Celery
from celery.utils.log import get_task_logger
from nltk.collocations import BigramCollocationFinder, TrigramCollocationFinder
from nltk.metrics import BigramAssocMeasures, TrigramAssocMeasures
import json
import csv


# -----------------------------
# Celery setup
# -----------------------------
app = Celery("corpus_tasks")
app.config_from_object("celeryconfig")
logger = get_task_logger(__name__)

# -----------------------------
# Paths & lazy caches
# -----------------------------
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
#CORPUS_PATH = os.path.join(BASE_PATH, "corpora", "divergent_discourses_corpus.csv")
CORPUS_PATH = os.path.join(BASE_PATH, "corpora", "divergent_discourses_corpus.csv")
OUTPUT_DIR  = os.path.join(BASE_PATH, "job_storage")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# one‑time lazy load of the corpus+spacy model into module‑level caches
_CORPUS_CACHE: Optional[pd.DataFrame] = None
_SPACY_MODEL: Optional[spacy.language.Language] = None


def load_corpus() -> pd.DataFrame:
    global _CORPUS_CACHE
    if _CORPUS_CACHE is None:
        logger.info("Loading corpus …")
        df = pd.read_csv(CORPUS_PATH)
        df = df.rename(columns={"date": "day"})
        df["full_date"] = pd.to_datetime(df[["year", "month", "day"]])
        _CORPUS_CACHE = df
    return _CORPUS_CACHE


def load_spacy_model() -> spacy.language.Language:
    global _SPACY_MODEL
    if _SPACY_MODEL is None:
        logger.info("Loading spaCy model …")
        _SPACY_MODEL = spacy.load("xx_bo_tagger")
        Token.set_extension("tsheg_stripped", getter=lambda token: str(token.text).rstrip("་"), force=True)
    return _SPACY_MODEL


def _split_terms(raw: str) -> List[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    import re
    return [t.strip().strip('"') for t in re.findall(r'"[^"]+"|\S+', raw)]


def make_streamlit_safe(obj):
    """
    Traverses data structures and ensures compatibility with Streamlit.
    """
    if isinstance(obj, dict):
        return {k: make_streamlit_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_streamlit_safe(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(make_streamlit_safe(v) for v in obj)
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif hasattr(obj, '__dict__'):
        return make_streamlit_safe(obj.__dict__)
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            return str(obj)


# -----------------------------
# FILTER JOB
# -----------------------------
@app.task(bind=True)
def filter_corpus(
    self,
    region_filter: List[str],
    newspaper_filter: List[str],
    start_date: Optional[str],
    end_date: Optional[str],
    all_words: str,
    any_words: str,
    none_words: str,
) -> str:
    """
    Returns absolute path to filtered CSV written in OUTPUT_DIR
    """
    df = load_corpus().copy()

    # metadata filters
    if region_filter:
        df = df[df["region_type"].isin(region_filter)]
    if newspaper_filter:
        df = df[df["newspaper"].isin(newspaper_filter)]
    if start_date:
        df = df[df["full_date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["full_date"] <= pd.to_datetime(end_date)]

    text_col = "normalised_paragraph"
    df[text_col] = df[text_col].astype(str)

    # ALL (AND)
    for term in _split_terms(all_words):
        df = df[df[text_col].str.contains(term, na=False, case=False, regex=False)]

    # ANY (OR)
    any_terms = _split_terms(any_words)
    if any_terms:
        mask = pd.Series(False, index=df.index)
        for term in any_terms:
            mask |= df[text_col].str.contains(term, na=False, case=False, regex=False)
        df = df[mask]

    # NONE (NOT)
    for term in _split_terms(none_words):
        df = df[~df[text_col].str.contains(term, na=False, case=False, regex=False)]

    # write out
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}.csv")
    df.to_csv(out_path, index=False)
    logger.info("Wrote filtered corpus: %s (%d rows)", out_path, len(df))
    return out_path



# -----------------------------
# WORDCLOUD JOB
# -----------------------------
@app.task(bind=True)
def generate_wordcloud_from_csv_path(self, csv_path: str, font_path: str = "Jomolhari-Regular.ttf") -> str:
    """
    Accepts CSV as a base64 string, returns SVG filepath.
    """
    nlp = load_spacy_model()

    def get_docs(text_list):
        return [nlp(text) for text in text_list if text.strip()]

    def get_token_frequencies(docs):
        overall = Counter()
        for doc in docs:
            freq = calculate_token_frequencies(doc, process_tsheg_stripped_tokens=True, remove_stopwords=True)
            overall.update(freq)
        return overall

    try:
        df = pd.read_csv(csv_path, dtype=str)
        if "normalised_paragraph" not in df.columns:
            raise ValueError("Missing 'normalised_paragraph' column")
        text_regions = df["normalised_paragraph"].dropna().tolist()

        docs = get_docs(text_regions)
        frequencies = get_token_frequencies(docs)
        if not frequencies:
            raise ValueError("No valid tokens for wordcloud")

        # Generate SVG
        wc = WordCloud(
            font_path=os.path.join(BASE_PATH, font_path),
            background_color="black",
            collocations=False,
            normalize_plurals=False,
            regexp=r"\S+"
        ).generate_from_frequencies(dict(frequencies))

        svg = wc.to_svg(embed_font=True)

        out_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)

        logger.info("Generated wordcloud: %s", out_path)
        return out_path

    except Exception as e:
        logger.error("Wordcloud generation failed: %s", str(e))
        raise


# -----------------------------
# Helpers for collocations
# -----------------------------
def _docs_from_csv(csv_path: str) -> List[spacy.tokens.Doc]:
    nlp = load_spacy_model()
    df = pd.read_csv(csv_path, dtype=str)
    if "normalised_paragraph" not in df.columns:
        raise ValueError("CSV must contain 'normalised_paragraph' column")
    paras = df["normalised_paragraph"].fillna("").astype(str).tolist()
    docs = [nlp(t) for t in paras if t.strip()]
    return docs


def _token_lists(docs: List[spacy.tokens.Doc]) -> List[List[str]]:
    return [[tok._.tsheg_stripped for tok in d] for d in docs]


def _pmis_to_sorted_pairs(d: Dict[tuple, float], positive=True, top_n=50) -> List[Tuple[tuple, float]]:
    if positive:
        pairs = [(k, v) for k, v in d.items() if v > 0]
        pairs.sort(key=lambda x: x[1], reverse=True)
    else:
        pairs = [(k, v) for k, v in d.items() if v < 0]
        pairs.sort(key=lambda x: x[1])
    return pairs[:top_n]


# -----------------------------
# COLLOCATIONS JOB (CSV out)
# -----------------------------
@app.task(bind=True, soft_time_limit=3000, time_limit=3100)
def preview_tokenised_matches(self, filepath: str, search_term: str, limit: int = 5):
    """
    Streams a CSV and previews paragraphs where the tokenised content
    contains the search_term. Uses the cached spaCy model from load_spacy_model().
    """
    nlp = load_spacy_model()
    matches = []
    total_matches = 0
    scanned_rows = 0

    search_doc = nlp(search_term.strip())
    if not search_doc or len(search_doc) == 0:
        return {"error": "Empty search term after tokenization"}

    # For simplicity assume search_term is single token
    search_token = search_doc[0].text


    docs = _docs_from_csv(filepath)
    token_docs = _token_lists(docs)

    for i, doc in enumerate(token_docs):
        scanned_rows += 1
        if search_token in doc:
            total_matches += 1
            if len(matches) < limit:
                matches.append(str(docs[i]))

    results = {
        "search_term": search_term,
        "preview_limit": limit,
        "scanned_rows": scanned_rows,
        "total_matches": total_matches,
        "previews": matches,
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"preview_{self.request.id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return out_path

@app.task(bind=True, soft_time_limit=3000, time_limit=3100)
def collocations_job(self, csv_path: str, search_term: Optional[str], top_n: int = 50) -> str:
    """
    Builds a single CSV with columns:
      section, ngram, score
    Sections:
      overall_trigram_pos / overall_trigram_neg
      bigram_pos / bigram_neg (only if search_term)
      trigram_pos / trigram_neg (only if search_term)
    """
    try:
        docs = _docs_from_csv(csv_path)
        token_docs = _token_lists(docs)

        # Overall trigram PMI
        tri_meas = TrigramAssocMeasures()
        tri_finder = TrigramCollocationFinder.from_documents(token_docs)
        all_trigrams = list(tri_finder.ngram_fd)
        tri_pmi = {
            tri: tri_finder.score_ngram(tri_meas.pmi, tri[0], tri[1], tri[2])
            for tri in all_trigrams
        }
        tri_pmi = {k: v for k, v in tri_pmi.items() if v is not None}

        overall_pos = _pmis_to_sorted_pairs(tri_pmi, positive=True, top_n=top_n)
        overall_neg = _pmis_to_sorted_pairs(tri_pmi, positive=False, top_n=top_n)

        rows = []
        for (ngram, score) in overall_pos:
            rows.append({"section": "overall_trigram_positive", "ngram": " ".join(ngram), "score": score})
        for (ngram, score) in overall_neg:
            rows.append({"section": "overall_trigram_negative", "ngram": " ".join(ngram), "score": score})

        # If a search term is provided, do focused bigram+trigram
        if search_term and search_term.strip():
            st = search_term.strip()
            # BIGRAM
            bi_meas = BigramAssocMeasures()
            bi_finder = BigramCollocationFinder.from_documents(token_docs)

            keyword_bigrams = [pair for pair in bi_finder.ngram_fd if st in pair]
            bi_pmi = {
                pair: bi_finder.score_ngram(bi_meas.pmi, pair[0], pair[1])
                for pair in keyword_bigrams
            }
            bi_pmi = {k: v for k, v in bi_pmi.items() if v is not None}

            # filter stopwords except when it's the actual search term
            filtered_bi = {}
            for (w1, w2), s in bi_pmi.items():
                if ((w1 in utils.stopwords) and (w1 != st)) or ((w2 in utils.stopwords) and (w2 != st)):
                    continue
                filtered_bi[(w1, w2)] = s

            bi_pos = _pmis_to_sorted_pairs(filtered_bi, positive=True, top_n=top_n)
            bi_neg = _pmis_to_sorted_pairs(filtered_bi, positive=False, top_n=top_n)

            for (ngram, score) in bi_pos:
                rows.append({"section": "bigram_positive", "ngram": " ".join(ngram), "score": score})
            for (ngram, score) in bi_neg:
                rows.append({"section": "bigram_negative", "ngram": " ".join(ngram), "score": score})

            # TRIGRAM (focused)
            keyword_trigrams = [tri for tri in tri_finder.ngram_fd if st in tri]
            tri_pmi_sel = {
                tri: tri_finder.score_ngram(tri_meas.pmi, tri[0], tri[1], tri[2])
                for tri in keyword_trigrams
            }
            tri_pmi_sel = {k: v for k, v in tri_pmi_sel.items() if v is not None}

            tri_pos = _pmis_to_sorted_pairs(tri_pmi_sel, positive=True, top_n=top_n)
            tri_neg = _pmis_to_sorted_pairs(tri_pmi_sel, positive=False, top_n=top_n)

            for (ngram, score) in tri_pos:
                rows.append({"section": "trigram_positive", "ngram": " ".join(ngram), "score": score})
            for (ngram, score) in tri_neg:
                rows.append({"section": "trigram_negative", "ngram": " ".join(ngram), "score": score})

        # Write single CSV
        out_csv = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}_collocations.csv")
        pd.DataFrame(rows, columns=["section", "ngram", "score"]).to_csv(out_csv, index=False)
        logger.info("Collocations CSV written: %s (%d rows)", out_csv, len(rows))
        return out_csv

    except Exception as e:
        logger.error("Collocations job failed: %s", str(e))
        raise

# -----------------------------
# CO-OCCURRENCE JOB (CSV out)
# -----------------------------

@app.task(bind=True)
def prepare_docs_for_cooccurrence(self, csv_path: str) -> str:
    """
    Reads CSV, groups paragraphs by page, sorts by readingorder_idx,
    concatenates per page, and serialises SpaCy Doc objects to disk.
    Returns path to serialised DocBin file.
    """
    nlp = load_spacy_model()
    df = pd.read_csv(csv_path)
    required_cols = ["normalised_paragraph", "filename", "readingorder_idx"]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"CSV missing required columns: {', '.join(required_cols)}")
    
    df = df.sort_values(by=["filename", "readingorder_idx"])
    df["normalised_paragraph"] = df["normalised_paragraph"].fillna("")
    
    page_texts = [
        " ".join(group["normalised_paragraph"].tolist())
        for _, group in df.groupby("filename")
    ]
    
    doc_bin = DocBin()
    for text in page_texts:
        if text.strip():
            doc = nlp(text)
            doc_bin.add(doc)
    
    out_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}_docs.spacy")
    doc_bin.to_disk(out_path)
    return out_path


@app.task(bind=True)
def compute_co_occurrences(self, docs_path: str, search_token: str, window_size: int = 100, top_n: int = 50):
    """
    Reads cached DocBin, calculates co-occurrences for search_token
    using the specified window_size, returns top_n results.
    """
    nlp = load_spacy_model()
    doc_bin = DocBin().from_disk(docs_path)
    docs = list(doc_bin.get_docs(nlp.vocab))
    
    all_counts = Counter()
    for doc in docs:
        co_occs = utils.keyword_co_occurrence(
            doc,
            search_token,
            window_size=window_size,
            stopwords=utils.stopwords,
            top_n=None
        )
        all_counts.update(dict(co_occs))
    
    if search_token in all_counts:
        del all_counts[search_token]
    
    results = all_counts.most_common(top_n)
    
    out_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}_cooccurrence.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    return out_path


# -----------------------------
# DIACHRONIC ANALYSIS JOB
# -----------------------------
@app.task(bind=True)
def diachronic_analysis(self, csv_path: str, single_words: list[str], exact_phrases: list[str]):
    """
    Perform diachronic analysis on uploaded corpus.
    Returns path to a JSON file with raw and normalised counts for words and phrases.
    """
    nlp = load_spacy_model()
    df = pd.read_csv(csv_path)
    if "year" not in df.columns or "normalised_paragraph" not in df.columns:
        raise ValueError("CSV must contain 'year' and 'normalised_paragraph' columns.")

    df["year"] = df["year"].astype(int)
    yearly_word_counts_raw = {}
    yearly_word_counts_normalised = {}
    yearly_phrase_counts_raw = {}
    yearly_phrase_counts_normalised = {}

    years = sorted(df["year"].unique())

    for year in years:
        year = int(year)
        group_df = df[df["year"] == year]

        # --- Token counts ---
        total_paragraphs = len(group_df)

        current_word_raw = {}
        current_word_norm = {}
        if single_words:
            texts = group_df["normalised_paragraph"].fillna("").astype(str).tolist()
            all_tokens = [token.text for tokens_list in nlp.pipe(texts, disable=["parser", "ner"])for token in tokens_list]
            total_tokens = len(all_tokens)
            token_counts = Counter(all_tokens)
            for kw in single_words:
                raw_count = token_counts.get(kw, 0)
                current_word_raw[kw] = raw_count
                current_word_norm[kw] = (raw_count / total_tokens * 100) if total_tokens else 0

        yearly_word_counts_raw[year] = current_word_raw
        yearly_word_counts_normalised[year] = current_word_norm

        # --- Exact phrase counts ---
        current_phrase_raw = {}
        current_phrase_norm = {}
        if exact_phrases:
            for phrase in exact_phrases:
                raw_count = group_df["normalised_paragraph"].apply(lambda x: 1 if phrase in x else 0).sum()
                current_phrase_raw[phrase] = raw_count
                current_phrase_norm[phrase] = (raw_count / total_paragraphs * 100) if total_paragraphs else 0

        yearly_phrase_counts_raw[year] = current_phrase_raw
        yearly_phrase_counts_normalised[year] = current_phrase_norm

    # --- Save JSON with all results ---
    out_path = csv_path.replace(".csv", "_diachronic.json")
    results = {
        "words_raw": yearly_word_counts_raw,
        "words_percent": yearly_word_counts_normalised,
        "phrases_raw": yearly_phrase_counts_raw,
        "phrases_percent": yearly_phrase_counts_normalised
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)

    return out_path

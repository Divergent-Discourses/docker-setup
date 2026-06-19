"""
Several functions adapted from: https://github.com/jamesosullivan/collocates/blob/main/co-occurrences.py 

Designed to be called upon from within a computational analysis notebook for Tibetan, using a custom trained Tibetan spacy model.
"""
import nltk
import nltk
from nltk.collocations import BigramCollocationFinder, TrigramCollocationFinder, BigramAssocMeasures
from nltk.metrics import BigramAssocMeasures, TrigramAssocMeasures
from collections import Counter
import re
import spacy
from spacy import displacy 
import matplotlib.font_manager as fm
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
from pyfonts import load_font
import plotly.graph_objects as go

# Stopword list includes: grammatical particles and connectors, common pronouns, auxiliary verbs and common verb forms, prepositions and locational terms, common numerals, common conjunctions and discourse markers
stopwords = ['འི', '།', 'དུ', 'གིས', 'སོགས', 'ཏེ', 'གི', 'རྣམས', 'ནི', 'ཀུན', 'ཡི', 'འདི', 'ཀྱི', 'སྙེད', 'པས', 'གཞན', 'ཀྱིས', 'ཡི', 'ལ', 'ནི', 'དང', 'སོགས', 'ཅིང', 'ར', 'དུ', 'མི', 'སུ', 'བཅས', 'ཡོངས', 'ལས', 'ཙམ', 'གྱིས', 'དེ', 'ཡང', 'མཐའ་དག', 'ཏུ', 'ཉིད', 'ས', 'ཏེ', 'གྱི', 'སྤྱི', 'དེ', 'ཀ', 'ཡིན', 'ཞིང', 'འདི', 'རུང', 'རང', 'ཞིག', 'སྟེ', 'སྟེ', 'ན་རེ', 'ངམ', 'ཤིང', 'དག', 'ཏོ', 'རེ', 'འང', 'ཀྱང', 'ལགས་པ', 'ཚུ', 'དོ', 'ཡིན་པ', 'རེ', 'ན་རེ', 'ཨེ', 'ཚང་མ', 'ཐམས་ཅད', 'དམ', 'འོ', 'ཅིག', 'གྱིན', 'ཡིན', 'ན', 'ཁོ་ན', 'འམ', 'ཀྱིན', 'ལོ', 'ཀྱིས', 'བས', 'ལགས', 'ཤིག', 'གིས', 'ཀི', 'སྣ་ཚོགས', 'རྣམས', 'སྙེད་པ', 'ཡིས', 'གྱི', 'གི', 'བམ', 'ཤིག', 'རེ་རེ', 'ནམ', 'མིན', 'ནམ', 'ངམ', 'རུ', 'འགའ', 'ཀུན', 'ཤས', 'ཏུ', 'ཡིས', 'གིན', 'གམ', 'འོ', 'ཡིན་པ', 'མིན', 'ལགས', 'གྱིས', 'ཅང', 'འགའ', 'སམ', 'ཞིག', 'འང', 'ལས་ཆེ', 'འཕྲལ', 'བར', 'རུ', 'དང', 'ཡ', 'འག', 'སམ', 'ཀ', 'ཅུང་ཟད', 'ཅིག', 'ཉིད', 'དུ་མ', 'མ', 'ཡིན་བ', 'འམ', 'མམ', 'དམ', 'དག', 'ཁོ་ན', 'ཀྱི', 'ལམ', 'ཕྱི', 'ནང', 'ཙམ', 'ནོ', 'སོ', 'རམ', 'བོ', 'ཨང', 'ཕྱི', 'ཏོ', 'ཚོ', 'ལ་ལ', 'ཚོ', 'ཅིང', 'མ་གི', 'གེ', 'གོ', 'ཡིན་ལུགས', 'རོ', 'བོ', 'ལགས་པ', 'པས', 'རབ', 'འི', 'རམ', 'གཞན', 'སྙེད་པ', 'འབའ', 'མཾ', 'པོ', 'ག', 'ག', 'གམ', 'སྤྱི', 'བམ', 'མོ', 'ཙམ་པ', 'ཤ་སྟག', 'མམ', 'རེ་རེ', 'སྙེད', 'ཏམ', 'ངོ', 'གྲང', 'ཏ་རེ', 'ཏམ', 'ཁ', 'ངེ', 'ཅོག', 'རིལ', 'ཉུང་ཤས', 'གིང', 'ཚ', 'ཀྱང', '(', ')', '། །', '། ', ' །', 'ནས', 'རེད', 'བྱེད', 'བྱས', "གྱིས", "དེས", "ཏང", "མ", "གས", "ང་རང་ཚོ", "ཤིན་ཏུ", "ང་ཚོ", "སྒང", "དགོས", "ཡོད་པའི", "༈", "། །", "༄", "—", '：', '，', '：', '：：', '。', '། ༄༅། །', ' ༄༅། །', ') 1', "ཡོད", "རྒྱུ", "'", "དང་ ", "བྱས་པ", "ཡོད་པ", "སོང", "བྱེད་པ", "གནང", "མ་ཟད", "སྐོར", "བྱུང", "གཅིག", "གཉིས", "ཞེས", "སྐབས", "ཟླ", "དགོས་པ", "ཡང་ན", "པ", "པར", "ཞེས་པ", "ད", "ཅེས", "ལྟར", "ཞིག་ཏུ", "ང", "ཁོ", "ཁོང", "ཁོ་ཚོ", "ཁྱོད", "ཁྱེད", "འདི", "དེ", "ཡིན", "རེད", "མེད", "ཡིན་པས", "པ་རེད", "རེད་ ", "མེད་པ", "འདུག", "ཡོད", "ཡོང", "བྱུང", "ཟིན", "ཐུབ", "འདི་ནི", "འདི་ལ", "དེ་དག", "དེར", "ནང", "ནང་དུ", "ནང་གི", "ཐོག", "སྟེང", "འོག", "ཕྱིར", "བར་དུ", "ད་ལྟ", "ད་རུང", "ད་དུང", "སྔོན", "རྗེས་སུ", "ཉིན", "ཚེས", "ཟླ་བ", "གཉིས་པ", "གསུམ", "བཞི", "ལྔ", "དྲུག", "བདུན", "བརྒྱད", "དགུ", "བཅུ", "འོན་ཀྱང", "དེ་བཞིན", "དེས་ན", "ཅན", "ཕེབས", "ཕེབས་པ", "ཡིན་ནོ", '"', "འདི་དག་ནི", "འགའ་ཞིག", "ཡོད་པ་རེད", "ཀྱི་རེད","**། ༈ **", "**། ༈ **", "**། ༄ **", "**། ༄ **", "**༄ **", "**༄། ** ", "**། **", "ཨ", "ཁོང་ཚོ", "གང","ཆེད","ཁག", "ཁོ", "དེང", "**། **", "**། ། **", "དེ་ནི", "**འདུག **", "དེ་ལ", "པའམ", "**། **", "ཀྱི་ཡིན", "པ་ཡིན", "ཙང", "དེ་རྗེས", "**3 **", "**17 **", "བཟོས", "བྱ", "ཅི", "**6 **", "**1963 **"]
             
# Add single digits and common Latin chars to stopwords
extra_stopwords = [str(i) for i in range(10)] + list("abcdefghijklmnopqrstuvwxyz")
stopwords.extend(extra_stopwords)


# Load the Tibetan model you have set up following the instructions linked in the description at the top of the notebook.

nlp = spacy.load("xx_bo_tagger")

def tokenise_spacy(text, stopwords=stopwords):
    """
    Input text, output list of tokens (stripped of trailing tshegs)
    """
    doc = nlp(text)
    return [str(token._.tsheg_stripped) for token in doc if token._.tsheg_stripped and str(token._.tsheg_stripped) not in stopwords]
    
def perform_collocation_analysis(spacy_doc, stopwords=stopwords):
    """Perform collocation analysis on a given text file to find top bigrams and trigrams, excluding those that occur only once."""

    # Tokenize the text
    words = [token._.tsheg_stripped for token in spacy_doc]

    # Remove stopwords
    filtered_words = [word for word in words if word not in stopwords]

    # Initialize Bigram and Trigram Finders
    bigram_measures = BigramAssocMeasures()
    trigram_measures = TrigramAssocMeasures()
    bigram_finder = BigramCollocationFinder.from_words(filtered_words)
    trigram_finder = TrigramCollocationFinder.from_words(filtered_words)

    # Apply frequency filter to exclude n-grams that occur only once
    bigram_finder.apply_freq_filter(2)
    trigram_finder.apply_freq_filter(2)

    # Find the top 10 bigrams and trigrams using PMI
    top_bigrams = bigram_finder.nbest(bigram_measures.pmi, 10)
    top_trigrams = trigram_finder.nbest(trigram_measures.pmi, 10)

    return top_bigrams, top_trigrams

def co_occurrence(spacy_doc, window_size=2, stopwords=stopwords):
    
    # Tokenize the text
    words = [token._.tsheg_stripped for token in spacy_doc]

    # Remove stopwords
    tokens = [word for word in words if word not in stopwords]
    
    # Initialise co-occurrence count
    co_occurrence_counts = Counter()
    
    # Calculate co-occurrences within the specified window size
    for i in range(len(tokens)):
        token = tokens[i]
        start = max(0, i - window_size)
        end = min(len(tokens), i + window_size + 1)
        for j in range(start, end):
            if i != j:
                co_occurred_token = tokens[j]
                co_occurrence_counts[(token, co_occurred_token)] += 1
    
    # Return the top 10 most common co-occurrences
    return co_occurrence_counts.most_common(10)


def keyword_co_occurrence(spacy_doc, keyword, window_size=5, stopwords=stopwords, top_n=10):
    """
    Finds words that frequently occur near a given keyword within a specified window.
    
    Args:
        spacy_doc: Processed spaCy document.
        keyword (str): The target word to analyse.
        window_size (int): Number of words before and after the keyword to consider.
        stopwords (list): Words to exclude from co-occurrence counts.
        
    Returns:
        Counter: Most common words appearing near the keyword.
    """
    
#    words = [token._.tsheg_stripped for token in spacy_doc if token._.tsheg_stripped not in stopwords]
    
    words = [token._.tsheg_stripped for token in spacy_doc]
    
    co_occurrence_counts = Counter()
    
    for i, word in enumerate(words):
        if word == keyword:
            start = max(0, i - window_size)
            end = min(len(words), i + window_size + 1)
            for j in range(start, end):
                if i != j:
                    co_occurrence_counts[words[j]] += 1
    for stopword in stopwords:
        co_occurrence_counts.pop(stopword, None)  # Safe removal

    if top_n is None:
        return co_occurrence_counts.most_common()  # Return all results
    else:
        return co_occurrence_counts.most_common(top_n)  # Return top X associated words


def get_top_and_negative_collocations_PMI(spacy_doc, keyword, window_size=5, top_n=10):
    
    words = [token._.tsheg_stripped for token in spacy_doc if token._.tsheg_stripped not in stopwords]
    
    bigram_measures = BigramAssocMeasures()
    
    # Find bigrams
    finder = BigramCollocationFinder.from_words(words, window_size)
    
    # Filter to keep only bigrams containing the keyword
    keyword_bigrams = [pair for pair in finder.ngram_fd.keys() if keyword in pair]
    
    # Compute PMI scores for those bigrams
    pmi_scores = {}
    for pair in keyword_bigrams:
        score = finder.score_ngram(bigram_measures.pmi, pair[0], pair[1])
        if score is not None:
            pmi_scores[pair] = score
    
    # Separate positive and negative PMI scores
    positive_pmi = {pair: score for pair, score in pmi_scores.items() if score > 0}
    negative_pmi = {pair: score for pair, score in pmi_scores.items() if score < 0}

    # Sort each set
    top_collocations = sorted(positive_pmi.items(), key=lambda x: x[1], reverse=True)[:top_n]
    negative_collocations = sorted(negative_pmi.items(), key=lambda x: x[1])  # Lowest PMI first

    return top_collocations, negative_collocations
    

def extract_context(text, entity, max_contexts=5):
    """
    Extracts the shad-segmented sub-sentence around a chosen token (e.g. a compound PROPN)
    Pattern to match: [optional to account for text-beginning] shad or 'ga ' -->  0+ spaces --> 0+ any character -->
    entity --> 0+ any character --> entity --> 0+ any character --> shad or 'ga '
    :param text: [str] text within which you wish to search for the given entity and its surrounding context
    (shad-segmented phrase containing the given entity)
    :param entity: [str] string whose contexts you are searching for within the text provided.
    :param max_contexts: [int] maximum number of contextual examples you wish to extract for the given entity
    :return: [list] containing max_contents number of entities in context (str). Returns list of strings.
    """
    # Pattern to match the entity and capture text between the nearest shads around it
    # ?: is non-capturing GROUP
    # [^།]* is 0+ characters excluding shad
    # followed by shad
    # ? is 0 or 1 of non-capturing group (accounts for entity matches in first sentence of text)
    # re.escape() is the entity escaped e.g. with \ in case of non-alphanumeric characters in entity
    # [^།]* is 0+ characters excluding shad
    # ?: is non-capturing group
    # shad
    context_pattern = re.compile(rf'(?:(ག |།)\s*)?([^།]*)({re.escape(entity)}[^།]*)(ག |།)')
    matches = context_pattern.findall(text)

    # Return up to `max_contexts` unique context strings
    unique_matches = []
    for match in matches:
        if match not in unique_matches:
            unique_matches.append(match)
        if len(unique_matches) == max_contexts:
            break

    unique_matches = ["".join(match[1:]) for match in unique_matches]

    return unique_matches

def extract_all_tokens(doc, process_tsheg_stripped_tokens=True, remove_stopwords=True):
    """
    Given spacy doc, extract all tokens and return them in list.
    
    process_tsheg_stripped_tokens (bool): If True, processes tokens pre-processed so trailing tsheg has been removed to 
    ensure counts are correct (otherwise some tokens have 2 versions - one with trailing tsheg, one without, due to botok
    tokenisation functionality). If False, processed original tokens.
    """
    if process_tsheg_stripped_tokens:
        if remove_stopwords==False:
            tokens = [token._.tsheg_stripped for token in doc]
        else:
            tokens = [token._.tsheg_stripped for token in doc if str(token._.tsheg_stripped) not in stopwords]
        
    else:
        if remove_stopwords==False:
            tokens = [token.text for token in doc]
        else:
            tokens = [token.text for token in doc if str(token._.tsheg_stripped) not in stopwords]
    
    return tokens

def extract_proper_nouns(doc, process_tsheg_stripped_tokens=True):
    """
    Given spacy doc, extract all proper nouns and return them in list.
    
    process_tsheg_stripped_tokens (bool): If True, processes tokens pre-processed so trailing tsheg has been removed to 
    ensure counts are correct (otherwise some tokens have 2 versions - one with trailing tsheg, one without, due to botok
    tokenisation functionality). If False, processed original tokens.
    """
    
    if process_tsheg_stripped_tokens:
        proper_nouns = [token._.tsheg_stripped for token in doc if token.pos_ == 'PROPN']
        
    else:
        proper_nouns = [token.text for token in doc if token.pos_ == 'PROPN']
    
    return proper_nouns


# Extract all tokens with a given POS tag from your text
def extract_pos(doc, pos, process_tsheg_stripped_tokens=True):
    """"
    Extract all tokens with a given POS tag from a given document.
    A list of possible tags can be found in the glossary here: 
    https://github.com/explosion/spaCy/blob/master/spacy/glossary.py
    doc (string)
    pos (string)
    process_tsheg_stripped_tokens (bool): If True, processes tokens pre-processed so trailing tsheg has been removed to 
    ensure counts are correct (otherwise some tokens have 2 versions - one with trailing tsheg, one without, due to botok
    tokenisation functionality). If False, processed original tokens.
    return: token_list (list of strings)
    """
    if process_tsheg_stripped_tokens:
        token_list = [token._.tsheg_stripped for token in doc if token.pos_ == pos]
    else:
        token_list = [token.text for token in doc if token.pos_ == pos]
    return token_list

def calculate_token_frequencies(doc, process_tsheg_stripped_tokens=True, remove_stopwords=True):
    """
    Calculate frequencies of tokens based on the normalised tsheg_stripped form.
    process_tsheg_stripped_tokens (bool): If True, processes tokens pre-processed so trailing tsheg has been removed to 
    ensure counts are correct (otherwise some tokens have 2 versions - one with trailing tsheg, one without, due to botok
    tokenisation functionality). If False, processed original tokens.
    """
    # if process_tsheg_stripped_tokens:
    #     frequency_dict = {}
    #     for token in doc:
    #         normalised_token = token._.tsheg_stripped  # Use the normalised form
    #         if normalised_token in frequency_dict:
    #             frequency_dict[normalised_token] += 1
    #         else:
    #             frequency_dict[normalised_token] = 1
    # else:
    #     # N.B. if you use this (process_tsheg_stripped_tokens=False), 
    #     # use old_get_token_count to get token frequencies in subsequent code rather than get_token_count
    #     frequency_dict = doc.count_by(spacy.attrs.ORTH)  
    # return frequency_dict

    if process_tsheg_stripped_tokens:
        tokens = (token._.tsheg_stripped for token in doc)
        if remove_stopwords:
            tokens = (t for t in tokens if t not in stopwords)
        return Counter(tokens)
    
    else:
        # Iterate manually if filtering is needed
        if remove_stopwords:
            tokens = (token.orth for token in doc if token.orth not in stopwords)
            return Counter(tokens)
        else:
            # Use fast built-in method if no filtering is needed
            return doc.count_by(spacy.attrs.ORTH)


def get_token_count(token, frequency_dict):
    token_count = frequency_dict.get(token, 0)
    return token_count


def extract_token_freqs(token_list, frequency_dict):
    """
    E.g. use to extract frequencies of proper noun list extracted from doc. 
    Should output same result whether set or list with duplicates inputted as token_list.
    """
    token_set = set(token_list)

    token_freqs = {}
    for token in token_set:
        token_freq = get_token_count(token, frequency_dict)
        token_freqs[token] = token_freq
        
    return token_freqs


def get_top_x_tokens(freq_dict, x):
    """Given a set number of items you wish to return (x = int) and a dictionary (key = token, value = frequency in text), 
    return the X most frequent in frequency dictionary format"""
    # Sort dictionary entries in descending order by token frequency values then return the top x items.
    top_tokens = dict(sorted(freq_dict.items(), key=lambda item: item[1], reverse=True)[:x])
    return top_tokens


# Sort frequency dictionary by values in descending order
def sort_freq_dict(freq_dict):
    sorted_freqs = dict(sorted(freq_dict.items(), key=lambda item: item[1], reverse=True))
    return sorted_freqs


def extract_compound_propns(doc):
    compound_propn_list = []
    simple_propn_list = []
    current_compound = []
    
    for token in doc:
        if token.pos_ == "PROPN":  # Check if the token is a proper noun
            current_compound.append(token._.tsheg_stripped)  # Add the token to the current compound
        else:
            if current_compound:  # If there are tokens in the current compound
                # Join them to form a single compound PROPN and add to the list
                if len(current_compound) > 1:
                    compound_propn_list.append("་".join(current_compound))
                    current_compound = []  # Reset the current compound
                else:
                    # discard current entry if only single-token PROPN as function should only return compound PROPNs 
                    current_compound = []
    
    # Handle the last compound in the document if it ends with PROPN
    if current_compound:
        compound_propn_list.append("་".join(current_compound))

    return compound_propn_list


def extract_compound_propns_and_propns(doc):
    compound_propn_list = []
    current_compound = []
    for token in doc:
        if token.pos_ == "PROPN":  # Check if the token is a proper noun
            current_compound.append(token._.tsheg_stripped)  # Add the token to the current compound
        else:
            if current_compound:  # If there are tokens in the current compound
                # Join them to form a single compound PROPN and add to the list
                compound_propn_list.append("་".join(current_compound))
                current_compound = []  # Reset the current compound
    
    # Handle the last compound in the document if it ends with PROPN
    if current_compound:
        compound_propn_list.append("་".join(current_compound))
    
    return compound_propn_list

def timeline_token_frequency(df, token_str, font, time_col='year', group_col='corpus', token_col='tokens', normalise_to=10000):
    """
    Plot timeline of relative frequency of a token over time and corpus groups.

    Parameters:
        df (DataFrame): Corpus dataframe with time, token, and group info.
        token_str (str): The token to track (e.g., 'མི་རྣམས་').
        time_col (str): Column name containing time info (e.g., 'year' or 'month').
        group_col (str): Column name identifying corpus group (e.g., 'corpus').
        token_col (str): Column containing list of tokens per document.
        normalise_to (int): Frequency is scaled per this number of tokens (default: 10,000).
    """
    # Step 1: Flatten into per-doc token counts
    df = df.copy()

    # Handle missing group column by assigning all to one group
    if group_col not in df.columns:
        df[group_col] = "All"

    df['token_count'] = df[token_col].apply(len)
    df['target_count'] = df[token_col].apply(lambda toks: toks.count(token_str))

    # Step 2: Group by time and corpus
    grouped = df.groupby([time_col, group_col]).agg({
        'target_count': 'sum',
        'token_count': 'sum'
    }).reset_index()

    # Step 3: Compute relative frequency
    grouped['rel_freq'] = grouped['target_count'] / grouped['token_count'] * normalise_to

    # Step 4: Pivot to wide format for plotting
    pivot_df = grouped.pivot(index=time_col, columns=group_col, values='rel_freq').fillna(0)

    # Step 5: Plot
    plt.figure(figsize=(12, 6))
    pivot_df.plot(marker='o', linestyle='-', figsize=(12, 6))
    plt.title(f"Relative Frequency of '{token_str}' Over Time", fontsize=14, font=font)
    plt.xlabel(time_col.capitalize(), fontsize=12)
    plt.ylabel(f"Occurrences per {normalise_to} tokens", fontsize=12, font=font)
    plt.legend(title=group_col.capitalize())
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()




 

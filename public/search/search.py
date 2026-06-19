import json
import os
import pandas as pd
import requests, uuid
from pinecone import Pinecone
import cohere
import streamlit as st
import numpy as np

st.set_page_config(page_title="Search Interface", layout="wide")
st.title("Search Interface Tool")

secrets_file_path = os.path.join(os.path.expanduser("~"), ".bknd", "secrets.json")

with open(secrets_file_path, 'r') as f:
    secrets = json.load(f)

cohere_API_key = secrets["cohere_api_key"]
pinecone_API_key = secrets["pinecone_api_key"]
azure_API_key = secrets["azure_api_key"]
endpoint = secrets["azure_endpoint"]
location = secrets["azure_location"]

path = '/translate'
constructed_url = endpoint + path

params = {
    'api-version': '3.0',
    'from': 'bo',
    'to': 'en'
}

#st.set_page_config(layout="wide")

headers = {
    'Ocp-Apim-Subscription-Key': azure_API_key,
    'Ocp-Apim-Subscription-Region': location,
    'Content-type': 'application/json',
    'X-ClientTraceId': str(uuid.uuid4())
}

def translate_text(input_str):
    body = [{'text': input_str}]
    request = requests.post(constructed_url, params=params, headers=headers, json=body)
    response = request.json()
    return response[0]['translations'][0]['text']

pc = Pinecone(api_key = pinecone_API_key)
index_name = 'diverge-test'
index = pc.Index(index_name)

def render_results_table(matches, translate=False):
    data = []
    for match in matches:
        combined_data = {**match['metadata'], 'ID': match['id'], 'Score': match['score']}
        data.append(combined_data)

    df = pd.DataFrame(data)
    if translate:
        df['translated text'] = df['text'].apply(lambda x: translate_text(x))
        df['translated title'] = df['title'].apply(lambda x: translate_text(x))
    return df

publications = ["All", "Tibet Daily"]
selected_publication = st.selectbox("Select a publication:", publications)
selected_years = st.slider("Select a year range:", 2020, 2023, (2021, 2022))
selected_months = st.slider("Select a month range:", 1, 12, (1, 12))

filters = {}
if selected_publication != "All":
    filters["publication"] = {"$eq": selected_publication}

filters["year"] = {'$in': [str(i) for i in range(selected_years[0], selected_years[1]+1)]}
filters["month"] = {'$in': [str(i) for i in range(selected_months[0], selected_months[1]+1)]}

def index_query(input_string, top_k=25, filters=None):
    co = cohere.Client(cohere_API_key)
    xq = co.embed(
        texts=[input_string],
        model='embed-multilingual-v2.0',
        input_type='search_query',
        truncate='END'
    ).embeddings
    
    query_params = {
        "vector": xq,
        "top_k": top_k,
        "include_metadata": True,
    }
    
    if filters:
        query_params['filter'] = filters

    return index.query(**query_params)

input_text = st.text_input("Enter your query text: ")

def reorder_columns(df, translate = False):
    if translate:
        cols = ['text', 'translated text', 'title', 'translated title', 'document_index', 'paragraph_index', 'date', 'year', 'month', 'day', 'ID', 'Score']
        df = df[cols]
    else:
        cols = ['text', 'title', 'document_index', 'paragraph_index', 'date', 'year', 'month', 'day', 'ID', 'Score']
        df = df[cols]
    return df

def highlight_columns(s, columns):
    return ['font-size: 18px;' if col in columns else '' for col in s.index]

def set_column_widths(df, widths):
    return [f'width: {width}px;' if col in widths else '' for col in df.columns]

if input_text:
    translate_query = st.checkbox("Toggle translated query", value=False)
    if translate_query:
        st.write(translate_text(input_text))
    num_results = st.slider("Number of results to display", min_value=1, max_value=100, value=10)
    pretty_print = st.checkbox("Toggle formatted display", value=False)
    results = index_query(input_text, top_k=num_results, filters=filters)
    if pretty_print:
        translator = st.checkbox("Translate Tibetan to English", value=False)
        if translator:
            df = reorder_columns(render_results_table(results['matches'], translate=True), translate=True)
        else:
            df = reorder_columns(render_results_table(results['matches']))
        
        columns_to_highlight = ['text', 'title']
        column_widths = {'text': 500}
        styled_df = df.style.apply(highlight_columns, columns=columns_to_highlight, axis=1).set_table_styles(
            [{'selector': f'th.col{i}', 'props': [('min-width', f'{width}px')]} for i, (col, width) in enumerate(df.items()) if col in column_widths]
        )
        st.write(styled_df.to_html(), unsafe_allow_html=True)
    else:
        st.write(results['matches'])

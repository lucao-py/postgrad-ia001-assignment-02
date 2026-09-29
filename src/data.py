import pandas as pd
import streamlit as st
import json
from urllib.request import urlopen


URL_DADOS = (
    "https://media.githubusercontent.com/media/"
    "StackExchange/Survey/refs/heads/main/"
    "packages/archive/2025/results.csv"
)


@st.cache_data(show_spinner="Carregando dados da pesquisa...")
def carregar_dados():
    df = pd.read_csv(URL_DADOS, low_memory=False)

    return df

def preparar_dados(df):

    df_analysis = df.copy()

    # Tradução das categorias
    traducao_confianca = {
        "Highly distrust": "Desconfia muito",
        "Somewhat distrust": "Desconfia parcialmente",
        "Neither trust nor distrust": "Neutro",
        "Somewhat trust": "Confia parcialmente",
        "Highly trust": "Confia muito"
    }

    rotulos_frequencia = {
        "Yes, I use AI tools monthly or infrequently": "Uso ocasional",
        "Yes, I use AI tools weekly": "Uso semanal",
        "Yes, I use AI tools daily": "Uso diário",
        "No, and I don't plan to": "Não usa e não pretende",
        "No, but I plan to soon": "Não usa, mas pretende"
    }

    rotulos_complexidade = {
        "Bad at handling complex tasks": "Ruim",
        "Neither good or bad at handling complex tasks": "Neutro",
        "Good, but not great at handling complex tasks": "Boa, com limitações",
        "Very poor at handling complex tasks": "Muito ruim",
        "I don't use AI tools for complex tasks / I don't know": "Não utiliza / não sabe",
        "Very well at handling complex tasks": "Muito boa"
    }

    # Criação das colunas traduzidas
    df_analysis["AIAcc_pt"] = (
        df_analysis["AIAcc"].replace(traducao_confianca)
    )

    df_analysis["AISelect_pt"] = (
        df_analysis["AISelect"].replace(rotulos_frequencia)
    )

    df_analysis["AIComplex_pt"] = (
        df_analysis["AIComplex"].replace(rotulos_complexidade)
    )

    return df_analysis   


@st.cache_data(show_spinner="Carregando mapa-múndi...")
def carregar_geojson():

    url_geojson = (
        'https://raw.githubusercontent.com/'
        'python-visualization/folium/main/'
        'examples/data/world-countries.json'
    )

    with urlopen(url_geojson) as resposta:
        geojson_paises = json.load(resposta)

    return geojson_paises
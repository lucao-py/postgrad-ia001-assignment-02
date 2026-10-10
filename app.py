"""Uso crescente, confiança, limites e adoção seletiva de inteligência artificial no trabalho."""

import pandas as pd
import pycountry
import streamlit as st

from src.analysis import (
    agregar_capacidade,
    agregar_frustracoes,
    agregar_mudanca,
    agregar_perfis,
    agregar_workflow,
    calcular_insight_agentes,
    calcular_serie,
)
from src.charts import (
    PROFILE_LABELS,
    criar_grafico_capacidade,
    criar_grafico_frustracoes,
    criar_grafico_mudanca,
    criar_grafico_perfis,
    criar_grafico_tendencias,
    criar_grafico_workflow,
)
from src.data import ADULT_AGE_GROUPS, carregar_base_historica, carregar_evidencias_2025
from src.responsive import tela_compacta


st.set_page_config(
    page_title="Inteligência Artificial no Desenvolvimento de Software",
    layout="wide",
    menu_items={},
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1550px;
        padding: 2.3rem clamp(2rem, 4vw, 4rem) 3rem;
    }
    h1 { font-size: 2.75rem !important; line-height: 1.20 !important;
         letter-spacing: 0.01em; margin-bottom: 0.8rem !important; }
    h2 { font-size: 1.75rem !important; line-height: 1.30 !important;
         margin-top: 1.4rem !important; margin-bottom: 1rem !important; }
    h3 { font-size: 1.45rem !important; line-height: 1.35 !important;
         margin-top: 1.4rem !important; margin-bottom: 0.8rem !important; }
    div[data-testid="stCaptionContainer"] { line-height: 1.5; margin-bottom: 0.6rem; }
    div[data-testid="stMetric"] { padding: 20px 22px; }
    div[data-testid="stMetricLabel"] { margin-bottom: 0.35rem; }
    div[data-testid="stMetricValue"] { line-height: 1.2; }
    div[data-testid="stTabs"] { margin-top: 1.2rem; }
    .st-key-viewport { display: none; }
    @media (max-width: 1023px) {
        .block-container { padding: 1.25rem 1rem 2rem; }
        h1 { font-size: clamp(1.35rem, 5.6vw, 2rem) !important;
             line-height: 1.3 !important; overflow-wrap: normal !important; }
        h2, h3 { font-size: 1.1rem !important; line-height: 1.4 !important;
                 margin-top: 1rem !important; }
        .st-key-global_filters [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap; gap: 0.75rem;
        }
        .st-key-global_filters [data-testid="stColumn"] {
            flex: 1 1 calc(50% - 0.75rem) !important;
            width: calc(50% - 0.75rem) !important; min-width: 0 !important;
        }
        .st-key-global_filters [role="combobox"] { font-size: 0.75rem; }
        [data-testid="stTabs"] [role="tablist"] { gap: 0.5rem; }
        [data-testid="stTabs"] [role="tab"] {
            flex: 1; min-width: 0; height: auto; min-height: 48px;
            white-space: normal; padding: 0.5rem 0.25rem;
        }
        [data-testid="stTabs"] [role="tab"] p {
            white-space: normal; font-size: 0.78rem; line-height: 1.4;
        }
    }
    @media (max-width: 359px) {
        .st-key-global_filters [data-testid="stColumn"] {
            flex-basis: 100% !important; width: 100% !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Verificando e harmonizando as pesquisas de 2023–2025...")
def carregar_base_dashboard():
    return carregar_base_historica().merge(
        carregar_evidencias_2025(), on="respondent_id", how="left", validate="one_to_one"
    )


AGE_LABELS = {
    "18_24": "18–24 anos",
    "25_34": "25–34 anos",
    "35_44": "35–44 anos",
    "45_54": "45–54 anos",
    "55_64": "55–64 anos",
    "65_plus": "65 anos ou mais",
}
POPULATION_LABELS = {
    "professional": "Profissionais",
    "learning": "Em aprendizado",
    "all": "Todos os perfis",
}


def rotulo_pais(code):
    if code is None:
        return "Todos os países"
    if code == "NOMADIC":
        return "Nômade (sem país)"
    if code == "XKX":
        return "Kosovo"
    if code == "PRK":
        return "Coreia do Norte"
    if code == "KOR":
        return "Coreia do Sul"
    country = pycountry.countries.get(alpha_3=code)
    return country.name if country else code


def mostrar_grafico(chart, results):
    if chart is None:
        st.info("Sem dados suficientes para este recorte.")
        return
    st.altair_chart(chart, width="stretch")
    unavailable = results.loc[~results["availability_state"].eq("available")]
    if not unavailable.empty:
        states = set(unavailable["availability_state"])
        if "insufficient_sample" in states:
            st.caption("Alguns grupos foram ocultados por amostra insuficiente.")
        elif "no_data" in states or "no_valid_responses" in states:
            st.caption("Alguns grupos não têm dados ou respostas válidas para os filtros escolhidos.")


df = carregar_base_dashboard()
compact = tela_compacta()
st.title("Inteligência Artificial no Desenvolvimento de Software")

countries = sorted(df["country"].dropna().unique().tolist(), key=rotulo_pais)
role_options = list(PROFILE_LABELS)
with st.container(key="global_filters"):
    population_col, age_col, role_col, country_col = st.columns(4)
with population_col:
    population = st.selectbox("População", list(POPULATION_LABELS),
                              format_func=POPULATION_LABELS.get, index=0)
with age_col:
    age_choice = st.selectbox(
        "Idade", ["all", *ADULT_AGE_GROUPS],
        format_func=lambda choice: "Todas as idades" if choice == "all" else AGE_LABELS[choice],
        help="Todas as faixas adultas comparáveis entre 2023 e 2025 (18 anos ou mais).",
        index=0,
    )
with role_col:
    role_choice = st.selectbox("Função", [None, *role_options],
                               format_func=lambda role: "Todas as funções" if role is None
                               else PROFILE_LABELS[role], index=0)
with country_col:
    country_choice = st.selectbox("País", [None, *countries], format_func=rotulo_pais, index=0)

filters = {
    "population": population,
    "age_groups": ADULT_AGE_GROUPS if age_choice == "all" else (age_choice,),
    "roles": None if role_choice is None else (role_choice,),
    "countries": None if country_choice is None else (country_choice,),
}

st.subheader("A adoção da inteligência artificial está crescendo. A confiança acompanha?")
adoption = calcular_serie(df, "ai_current_use", filters)
trust = calcular_serie(df, "ai_trust_positive", filters)
history = pd.concat([adoption, trust], ignore_index=True)
mostrar_grafico(criar_grafico_tendencias(adoption, trust, compact=compact), history)

profiles_tab, impact_tab = st.tabs(["Perfis profissionais", "Percepção, uso e impacto"])

with profiles_tab:
    st.markdown("### Como a adoção varia com a experiência profissional?")
    experience = agregar_perfis(df, "work_experience", 2025, filters)
    mostrar_grafico(criar_grafico_perfis(experience, "work_experience", compact=compact), experience)

    st.markdown("### O padrão varia entre funções?")
    roles = agregar_perfis(df, "role", 2025, filters)
    mostrar_grafico(criar_grafico_perfis(roles, "role", compact=compact), roles)

with impact_tab:
    st.markdown("### Quem usa inteligência artificial com mais frequência percebe maior capacidade em tarefas complexas?")
    capability = agregar_capacidade(df, 2025, filters)
    mostrar_grafico(criar_grafico_capacidade(capability, compact=compact), capability)

    st.markdown("### Que problemas aparecem no uso de inteligência artificial?")
    frustrations = agregar_frustracoes(df, 2025, filters)
    mostrar_grafico(criar_grafico_frustracoes(frustrations, compact=compact), frustrations)

    st.markdown("### Em quais tarefas a inteligência artificial já é usada — e onde há resistência?")
    workflow = agregar_workflow(df, 2025, filters)
    mostrar_grafico(criar_grafico_workflow(workflow, compact=compact), workflow)

    st.markdown("### O uso mais intenso se associa a maiores mudanças no trabalho?")
    change = agregar_mudanca(df, 2025, filters)
    mostrar_grafico(criar_grafico_mudanca(change, compact=compact), change)
 
    agent = calcular_insight_agentes(df, 2025, filters)
    if agent["availability_state"] == "available":
        numerator = f"{agent['numerator']:,}".replace(",", ".")
        denominator = f"{agent['valid_denominator']:,}".replace(",", ".")
        

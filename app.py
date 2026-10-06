"""Uso crescente, confiança, limites e adoção seletiva de IA no trabalho."""

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


st.set_page_config(
    page_title="IA no Desenvolvimento de Software",
    layout="wide",
    menu_items={},
)

st.markdown(
    """
    <style>
    .block-container { max-width: 1450px; padding-top: 2.3rem; padding-bottom: 3rem; }
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
st.title("Inteligência Artificial no Desenvolvimento de Software")

countries = sorted(df["country"].dropna().unique().tolist(), key=rotulo_pais)
role_options = list(PROFILE_LABELS)
population_col, age_col, role_col, country_col = st.columns(4)
with population_col:
    population = st.selectbox("População", list(POPULATION_LABELS),
                              format_func=POPULATION_LABELS.get, index=0)
with age_col:
    age_choice = st.selectbox(
        "Idade", ["all", *ADULT_AGE_GROUPS],
        format_func=lambda choice: "Todas as idades" if choice == "all" else AGE_LABELS[choice],
        help="Todas as faixas adultas comparáveis entre 2023 e 2025 (18+).",
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

st.subheader("A adoção de IA está crescendo. A confiança acompanha?")
adoption = calcular_serie(df, "ai_current_use", filters)
trust = calcular_serie(df, "ai_trust_positive", filters)
history = pd.concat([adoption, trust], ignore_index=True)
mostrar_grafico(criar_grafico_tendencias(adoption, trust), history)
base_note = "Bases distintas; confiança só entre usuários atuais com resposta válida."
if population == "all":
    base_note += " 2025 inclui novo perfil."
st.caption(base_note)
if role_choice is not None:
    st.caption("Função em 2025 também pode refletir o último ano de trabalho.")

profiles_tab, impact_tab = st.tabs(["Perfis profissionais · 2025", "Percepção, uso e impacto · 2025"])

with profiles_tab:
    st.markdown("### Como a adoção varia com a experiência profissional?")
    experience = agregar_perfis(df, "work_experience", 2025, filters)
    mostrar_grafico(criar_grafico_perfis(experience, "work_experience"), experience)

    st.markdown("### O padrão varia entre funções?")
    roles = agregar_perfis(df, "role", 2025, filters)
    mostrar_grafico(criar_grafico_perfis(roles, "role"), roles)

with impact_tab:
    st.markdown("### Quem usa IA com mais frequência percebe maior capacidade em tarefas complexas?")
    capability = agregar_capacidade(df, 2025, filters)
    mostrar_grafico(criar_grafico_capacidade(capability), capability)

    st.markdown("### Que problemas aparecem no uso de IA?")
    frustrations = agregar_frustracoes(df, 2025, filters)
    mostrar_grafico(criar_grafico_frustracoes(frustrations), frustrations)

    st.markdown("### Em quais tarefas a IA já é usada — e onde há resistência?")
    workflow = agregar_workflow(df, 2025, filters)
    mostrar_grafico(criar_grafico_workflow(workflow), workflow)

    st.markdown("### O uso mais intenso se associa a maiores mudanças no trabalho?")
    change = agregar_mudanca(df, 2025, filters)
    mostrar_grafico(criar_grafico_mudanca(change), change)

    agent = calcular_insight_agentes(df, 2025, filters)
    if agent["availability_state"] == "available":
        numerator = f"{agent['numerator']:,}".replace(",", ".")
        denominator = f"{agent['valid_denominator']:,}".replace(",", ".")
        st.caption(
            f"Entre usuários atuais de agentes, {agent['percentage']:.1f}% relatam mais "
            "produtividade e preocupação com precisão ao mesmo tempo "
            f"({numerator}/{denominator} respostas válidas aos dois itens)."
        )

    st.divider()
    st.markdown("### Uso não resolve a confiança")
    st.caption(
        "Adoção, confiança e impacto não avançam em bloco: o uso se distribui de forma desigual "
        "entre tarefas, e as frustrações permanecem. A IA já integra o trabalho, sem consenso de confiança."
    )

import streamlit as st
import streamlit.components.v1 as components

from src.data import (
    carregar_dados,
    preparar_dados,
    carregar_geojson
)

from src.charts import (
    criar_grafico_confianca,
    criar_grafico_complexidade,
    criar_grafico_experiencia,
    criar_grafico_agentes,
    criar_mapa_ia
)


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="IA no Desenvolvimento de Software",
    layout="wide",
    menu_items={}
)


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
    <style>

    /* Página */
    .block-container {
        max-width: 1450px;
        padding-top: 2.8rem;
        padding-bottom: 4rem;
    }


    /* Título principal */
    h1 {
        font-size: 2.75rem !important;
        line-height: 1.20 !important;
        letter-spacing: 0.01em;
        margin-bottom: 0.8rem !important;
    }


    /* Títulos das abas */
    h2 {
        font-size: 1.75rem !important;
        line-height: 1.30 !important;
        margin-top: 1.8rem !important;
        margin-bottom: 1.3rem !important;
    }


    /* Títulos dos gráficos */
    h3 {
        font-size: 1.45rem !important;
        line-height: 1.35 !important;
        margin-top: 2.2rem !important;
        margin-bottom: 1.1rem !important;
    }


    /* Fonte secundária */
    div[data-testid="stCaptionContainer"] {
        line-height: 1.5;
        margin-bottom: 0.6rem;
    }


    /* KPIs */
    div[data-testid="stMetric"] {
        padding: 20px 22px;
    }

    div[data-testid="stMetricLabel"] {
        margin-bottom: 0.35rem;
    }

    div[data-testid="stMetricValue"] {
        line-height: 1.2;
    }


    /* Mais espaço antes das abas */
    div[data-testid="stTabs"] {
        margin-top: 2.2rem;
    }


    /* Um pouco mais de respiro nos filtros */
    div[data-testid="stSelectbox"],
    div[data-testid="stMultiSelect"] {
        margin-bottom: 1rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DADOS
# ============================================================

df = carregar_dados()
df_analysis = preparar_dados(df)

geojson_paises = carregar_geojson()

if df_analysis.empty:
    st.warning("Não há dados disponíveis.")
    st.stop()


# ============================================================
# INDICADORES
# ============================================================

total_respondentes = (
    df_analysis["ResponseId"]
    .nunique()
)

total_paises = (
    df_analysis["Country"]
    .nunique()
)

usuarios_diarios = (
    df_analysis["AISelect"]
    .eq("Yes, I use AI tools daily")
    .sum()
)

respostas_validas_ia = (
    df_analysis["AISelect"]
    .notna()
    .sum()
)

percentual_diario = (
    usuarios_diarios / respostas_validas_ia * 100
    if respostas_validas_ia > 0
    else 0
)


# ============================================================
# CABEÇALHO
# ============================================================

st.title(
    "Inteligência Artificial no Desenvolvimento de Software"
)

st.caption(
    "Stack Overflow Developer Survey 2025"
)


# ============================================================
# KPIs
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Respondentes",
        f"{total_respondentes:,}"
    )

with col2:
    st.metric(
        "Uso diário de IA",
        f"{percentual_diario:.1f}%"
    )

with col3:
    st.metric(
        "Países",
        f"{total_paises:,}"
    )


# ============================================================
# ABAS
# ============================================================

aba1, aba2, aba3 = st.tabs(
    [
        "Percepção da IA",
        "Perfil e impacto",
        "Geografia"
    ],
    on_change="rerun",
    key="abas_dashboard"
)


# ============================================================
# ABA 1 — PERCEPÇÃO DA IA
# ============================================================

with aba1:

    st.subheader(
        "Como a frequência de uso muda a percepção sobre IA?"
    )

    # --------------------------------------------------------
    # FILTRO
    # --------------------------------------------------------

    rotulos_idade = {
        "Under 18 years old": "Menos de 18 anos",
        "18-24 years old": "18–24 anos",
        "25-34 years old": "25–34 anos",
        "35-44 years old": "35–44 anos",
        "45-54 years old": "45–54 anos",
        "55-64 years old": "55–64 anos",
        "65 years or older": "65 anos ou mais",
        "Prefer not to say": "Prefere não informar"
    }

    ordem_idade = [
        "Under 18 years old",
        "18-24 years old",
        "25-34 years old",
        "35-44 years old",
        "45-54 years old",
        "55-64 years old",
        "65 years or older",
        "Prefer not to say"
    ]

    faixas_disponiveis = set(
        df_analysis["Age"]
        .dropna()
        .unique()
    )

    opcoes_idade = [
        faixa
        for faixa in ordem_idade
        if faixa in faixas_disponiveis
    ]

    filtro_col, _ = st.columns(
        [1.1, 2.9]
    )

    with filtro_col:

        faixas_etarias = st.multiselect(
            "Faixa etária",
            options=opcoes_idade,
            format_func=lambda x: rotulos_idade.get(x, x),
            placeholder="Todas",
            key="idade_aba1"
        )


    # --------------------------------------------------------
    # FILTRO APLICADO
    # --------------------------------------------------------

    df_aba1 = df_analysis.copy()

    if faixas_etarias:

        df_aba1 = df_aba1.loc[
            df_aba1["Age"].isin(
                faixas_etarias
            )
        ].copy()


    # --------------------------------------------------------
    # CONFIANÇA
    # --------------------------------------------------------

    st.markdown(
        "### Quanto maior o uso, maior a confiança na IA?"
    )

    grafico = criar_grafico_confianca(
        df_aba1
    )

    if grafico is not None:

        st.altair_chart(
            grafico,
            use_container_width=True
        )

    else:

        st.info(
            "Não há dados para os filtros selecionados."
        )


    # --------------------------------------------------------
    # COMPLEXIDADE
    # --------------------------------------------------------

    st.markdown(
        "### E quando a tarefa fica mais complexa?"
    )

    grafico = criar_grafico_complexidade(
        df_aba1
    )

    if grafico is not None:

        st.altair_chart(
            grafico,
            use_container_width=True
        )

    else:

        st.info(
            "Não há dados para os filtros selecionados."
        )


# ============================================================
# ABA 2 — PERFIL E IMPACTO
# ============================================================

with aba2:

    st.subheader(
        "Quem utiliza IA e o que muda no trabalho?"
    )

    # --------------------------------------------------------
    # FILTRO
    # --------------------------------------------------------

    filtro_col, _ = st.columns(
        [1.1, 2.9]
    )

    with filtro_col:

        funcoes = st.multiselect(
            "Função profissional",
            options=sorted(
                df_analysis["DevType"]
                .dropna()
                .unique()
            ),
            placeholder="Todas",
            key="funcao_aba2"
        )


    # --------------------------------------------------------
    # FILTRO APLICADO
    # --------------------------------------------------------

    df_aba2 = df_analysis.copy()

    if funcoes:

        df_aba2 = df_aba2.loc[
            df_aba2["DevType"].isin(
                funcoes
            )
        ].copy()


    # --------------------------------------------------------
    # EXPERIÊNCIA
    # --------------------------------------------------------

    st.markdown(
        "### Quem usa IA com maior frequência tem um perfil de experiência diferente?"
    )

    grafico = criar_grafico_experiencia(
        df_aba2
    )

    if grafico is not None:

        st.altair_chart(
            grafico,
            use_container_width=True
        )

    else:

        st.info(
            "Não há dados para os filtros selecionados."
        )


    # --------------------------------------------------------
    # AGENTES
    # --------------------------------------------------------

    st.markdown(
        "### Quanto os agentes de IA mudaram a forma de trabalhar?"
    )

    grafico = criar_grafico_agentes(
        df_aba2
    )

    if grafico is not None:

        st.altair_chart(
            grafico,
            use_container_width=True
        )

    else:

        st.info(
            "Não há dados para os filtros selecionados."
        )


# ============================================================
# ABA 3 — GEOGRAFIA
# ============================================================

with aba3:

    st.subheader(
        "Onde o uso diário de IA é mais frequente?"
    )

    # --------------------------------------------------------
    # FILTRO
    # --------------------------------------------------------

    filtro_col, _ = st.columns(
        [1, 3]
    )

    with filtro_col:

        min_respondentes = st.selectbox(
            "Amostra mínima",
            options=[
                10,
                20,
                30,
                50,
                100,
                200
            ],
            index=2,
            key="min_respondentes_aba3"
        )


    # --------------------------------------------------------
    # MAPA
    # --------------------------------------------------------

    if aba3.open:

        mapa = criar_mapa_ia(
            df_analysis,
            geojson_paises,
            min_respondentes=min_respondentes
        )

        if mapa is not None:

            components.html(
                mapa.get_root().render(),
                height=570,
                scrolling=False
            )

        else:

            st.info(
                "Não há dados disponíveis."
            )
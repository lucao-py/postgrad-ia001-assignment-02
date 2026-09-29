import streamlit as st

from src.data import carregar_dados
from src.data import carregar_dados, preparar_dados
from src.charts import criar_grafico_confianca, criar_grafico_complexidade, criar_grafico_experiencia, criar_grafico_agentes

# Configuração da página
st.set_page_config(
    page_title="Stack Overflow Survey 2025",
    page_icon="📊",
    layout="wide"
)


# Carregamento dos dados
df = carregar_dados()
df_analysis = preparar_dados(df)


# Cabeçalho
st.title("Inteligência Artificial no Desenvolvimento de Software")

st.caption(
    "Uma análise exploratória da Stack Overflow Developer Survey 2025"
)

st.markdown(
    "Explore como os desenvolvedores utilizam ferramentas de IA, "
    "como avaliam sua precisão e quais mudanças percebem no trabalho."
)


# Filtros
st.sidebar.header("Filtros")

paises = st.sidebar.multiselect(
    "Países",
    options=sorted(df["Country"].dropna().unique()),
    placeholder="Todos os países"
)

min_respondentes = st.sidebar.slider(
    "Amostra mínima por país",
    min_value=10,
    max_value=200,
    value=30,
    step=10
)


# Aplicação dos filtros
df_filtrado = df_analysis.copy()

if paises:
    df_filtrado = df_filtrado.loc[
        df_filtrado["Country"].isin(paises)
    ].copy()


# Tratamento de filtros sem resultados
if df_filtrado.empty:
    st.warning("Nenhum respondente encontrado para os filtros selecionados.")
    st.stop()


# Indicadores gerais
col1, col2, col3 = st.columns(3)

col1.metric(
    "Respondentes",
    f"{df_filtrado['ResponseId'].nunique():,}"
)

col2.metric(
    "Países",
    df_filtrado["Country"].nunique()
)

col3.metric(
    "Usuários diários de IA",
    f"{(df_filtrado['AISelect'] == 'Yes, I use AI tools daily').sum():,}"
)


# Organização das análises
aba1, aba2, aba3 = st.tabs([
    "Percepção sobre IA",
    "Perfil e agentes",
    "Análise geográfica"
])

with aba1:

    st.subheader("Confiança na precisão das respostas de IA")
    grafico = criar_grafico_confianca(df_filtrado)
    st.altair_chart(
        grafico,
        use_container_width=True
    )

    st.divider()

    st.subheader("Capacidade da IA em tarefas complexas")
    grafico = criar_grafico_complexidade(df_filtrado)
    if grafico is not None:
        st.altair_chart(
            grafico,
            use_container_width=True
        )
    else:
        st.info(
            "Não há respostas disponíveis para esta análise "
            "com os filtros selecionados."
        )

with aba2:
    st.subheader('Experiência profissional por frequência de uso de IA')
    grafico = criar_grafico_experiencia(df_filtrado)
    if grafico is not None:
        st.altair_chart(
            grafico,
            use_container_width=True
        )
    else:
        st.info(
            'Não há respostas disponíveis para esta análise '
            'com os filtros selecionados.'
        )

    st.divider()

    st.subheader('Mudança percebida no trabalho pelo uso de agentes de IA')

    grafico = criar_grafico_agentes(df_filtrado)

    if grafico is not None:
        st.altair_chart(
            grafico,
            use_container_width=True
        )
    else:
        st.info(
            'Não há respostas disponíveis sobre o uso de agentes de IA '
            'com os filtros selecionados.'
        )
with aba3:
    st.subheader("Distribuição geográfica do uso de IA")
    st.info("Aqui entraremos com o mapa Folium.")
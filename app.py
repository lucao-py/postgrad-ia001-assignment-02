import streamlit as st
import streamlit.components.v1 as components
from src.data import carregar_dados
from src.data import carregar_dados, preparar_dados, carregar_geojson
from src.charts import criar_grafico_confianca, criar_grafico_complexidade, criar_grafico_experiencia, criar_grafico_agentes, criar_mapa_ia

# Configuração da página
st.set_page_config(
    page_title="Análise Int. Artificial ",
    layout="wide"
)


# Carregamento dos dados
df = carregar_dados()
df_analysis = preparar_dados(df)
geojson_paises = carregar_geojson()


# Cabeçalho
st.title("Inteligência Artificial no Desenvolvimento de Software")

st.caption(
    "Essa é uma análise feita a partir da pesquisa Stack Overflow Developer Survey 2025 onde pessoas que trabalham com tecnologia responderam perguntas sobre Inteligência artificial e como elas estão modificando seu fluxo de trabalho"
)




# Aplicação dos filtros
df_filtrado = df_analysis.copy()

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
aba1, aba2, aba3 = st.tabs(
    [
        "Percepção sobre IA",
        "Perfil e agentes",
        "Análise geográfica"
    ],
    on_change="rerun",
    key="abas_dashboard"
)

opcoes_paises = sorted(df_analysis["Country"].dropna().unique())


with aba1:

    # Filtros
    faixas_etarias = st.multiselect(
        'Faixa etária',
        options=sorted(df_analysis['Age'].dropna().unique()),
        placeholder='Todas as faixas etárias',
        key='idade_aba1'
    )

    # Aplicação dos filtros
    df_aba1 = df_analysis.copy()

    if faixas_etarias:
        df_aba1 = df_aba1.loc[
            df_aba1['Age'].isin(faixas_etarias)
        ].copy()

    # A partir daqui, mantenha seus gráficos 1 e 2

    # Gráfico 1 - Confiança
    st.subheader("Confiança na precisão das respostas de IA")

    grafico = criar_grafico_confianca(df_aba1)

    if grafico is not None:
        st.altair_chart(
            grafico,
            use_container_width=True
        )
    else:
        st.info("Não há respostas disponíveis para esta análise.")

    st.divider()

    # Gráfico 2 - Complexidade
    st.subheader("Capacidade da IA em tarefas complexas")

    grafico = criar_grafico_complexidade(df_aba1)

    if grafico is not None:
        st.altair_chart(
            grafico,
            use_container_width=True
        )
    else:
        st.info("Não há respostas disponíveis para esta análise.")


with aba2:

    # Filtros
    funcoes = st.multiselect(
        'Função profissional',
        options=sorted(df_analysis['DevType'].dropna().unique()),
        placeholder='Todas as funções',
        key='funcao_aba2'
    )

    # Aplicação dos filtros
    df_aba2 = df_analysis.copy()

    if funcoes:
        df_aba2 = df_aba2.loc[
            df_aba2['DevType'].isin(funcoes)
        ].copy()

    # A partir daqui, mantenha seus gráficos 3 e 4
    # Gráfico 3 - Experiência
    st.subheader("Experiência profissional por frequência de uso de IA")

    grafico = criar_grafico_experiencia(df_aba2)

    if grafico is not None:
        st.altair_chart(
            grafico,
            use_container_width=True
        )
    else:
        st.info("Não há respostas disponíveis para esta análise.")

    st.divider()

    # Gráfico 4 - Agentes
    st.subheader("Mudança percebida no trabalho pelo uso de agentes de IA")

    st.caption(
        "Distribuição percentual dentro de cada grupo de frequência de uso."
    )

    grafico = criar_grafico_agentes(df_aba2)

    if grafico is not None:
        st.altair_chart(
            grafico,
            use_container_width=False
        )
    else:
        st.info("Não há respostas disponíveis para esta análise.")


# ABA 3 - ANÁLISE GEOGRÁFICA
with aba3:

    # Filtros
    col1, col2 = st.columns([3, 1])

    with col1:
        paises_aba3 = st.multiselect(
            "Filtrar por país",
            options=opcoes_paises,
            placeholder="Todos os países",
            key="paises_aba3"
        )

    with col2:
        min_respondentes = st.selectbox(
            "Amostra mínima por país",
            options=[10, 20, 30, 50, 100, 200],
            index=2,
            key="min_respondentes_aba3"
        )

    df_aba3 = df_analysis.copy()

    if paises_aba3:
        df_aba3 = df_aba3.loc[
            df_aba3["Country"].isin(paises_aba3)
        ].copy()

    # Gráfico 5 - Mapa
    st.subheader("Distribuição geográfica do uso diário de IA")

    st.caption(
        "Percentual de respondentes que utilizam ferramentas de IA "
        "diariamente, por país."
    )

    if aba3.open:

        mapa = criar_mapa_ia(
            df_aba3,
            geojson_paises,
            min_respondentes=min_respondentes
        )

        if mapa is not None:
            components.html(
                mapa.get_root().render(),
                height=640,
                scrolling=False
            )

            st.caption(
                f"Países com menos de {min_respondentes} respostas válidas "
                "são apresentados em cinza. Os resultados representam "
                "os participantes da pesquisa, não a população total "
                "de desenvolvedores de cada país."
            )

        else:
            st.info(
                "Não há respostas disponíveis para a análise geográfica."
            )
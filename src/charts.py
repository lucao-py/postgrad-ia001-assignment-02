import altair as alt
import numpy as np
import folium
import pycountry
import pandas as pd

from copy import deepcopy


# ============================================================
# PADRÕES VISUAIS E CATEGORIAS
# ============================================================

AZUL_PRINCIPAL = '#4C78A8'
AZUL_MEDIO = '#8FB6D9'
AZUL_ESCURO = '#3F78B5'

TEXTO_ESCURO = '#17324D'
CINZA = '#7D8590'

# Espaço reservado aos rótulos dos eixos Y
LIMITE_ROTULO_Y = 240


# Padronização da frequência de uso em todos os gráficos
ROTULOS_USO = {
    'Não usa e não pretende': 'Não usa / não pretende',
    'Não usa, mas pretende': 'Não usa / pretende',
    'Uso ocasional': 'Uso ocasional',
    'Uso semanal': 'Uso semanal',
    'Uso diário': 'Uso diário'
}

ORDEM_USO = [
    'Não usa / não pretende',
    'Não usa / pretende',
    'Uso ocasional',
    'Uso semanal',
    'Uso diário'
]


# Confiança: escala divergente
ORDEM_CONFIANCA = [
    'Desconfia muito',
    'Desconfia parcialmente',
    'Neutro',
    'Confia parcialmente',
    'Confia muito'
]

CORES_CONFIANCA = [
    '#B54747',
    '#E08B8B',
    '#7D8590',
    '#8FB6D9',
    '#3F78B5'
]


# Capacidade em tarefas complexas
ORDEM_COMPLEXIDADE = [
    'Muito ruim',
    'Ruim',
    'Neutro',
    'Boa, com limitações',
    'Muito boa',
    'Não utiliza / não sabe'
]


# Agentes
ORDEM_USO_AGENTES = [
    'Uso ocasional',
    'Uso semanal',
    'Uso diário'
]

ORDEM_MUDANCA = [
    'Nenhuma ou mínima',
    'Moderada',
    'Grande',
    'Mudança por outros fatores'
]

CORES_MUDANCA = [
    '#C9D8E6',
    '#8FB6D9',
    '#3F78B5',
    '#8C8C8C'
]


# Países que precisam de tratamento específico
ALIASES_PAISES = {
    'United States of America': 'USA',
    'United Kingdom of Great Britain and Northern Ireland': 'GBR',
    'South Korea': 'KOR',
    'North Korea': 'PRK',
    'Taiwan': 'TWN',
    'Hong Kong (S.A.R.)': 'HKG',
    'Macao (S.A.R.)': 'MAC',
    'Iran, Islamic Republic of...': 'IRN',
    'Venezuela, Bolivarian Republic of...': 'VEN',
    'Bolivia, Plurinational State of...': 'BOL',
    'Congo, Republic of the...': 'COG',
    'Democratic Republic of the Congo': 'COD',
    'Kosovo': 'XKX'
}


def obter_iso3(pais):

    if pais in ALIASES_PAISES:
        return ALIASES_PAISES[pais]

    try:
        return pycountry.countries.lookup(pais).alpha_3

    except LookupError:
        return None


# ============================================================
# 1. CONFIANÇA NA PRECISÃO DA IA
# ============================================================

def criar_grafico_confianca(df):

    # Preparação dos dados
    df_trust_precision = (
        df[['ResponseId', 'AISelect_pt', 'AIAcc_pt']]
        .dropna(subset=['AISelect_pt', 'AIAcc_pt'])
        .copy()
    )

    if df_trust_precision.empty:
        return None

    # Padronização dos rótulos de frequência
    df_trust_precision['Uso'] = (
        df_trust_precision['AISelect_pt']
        .replace(ROTULOS_USO)
    )

    # Agregação
    df_trust_plot = (
        df_trust_precision
        .groupby(['Uso', 'AIAcc_pt'])
        .size()
        .reset_index(name='Quantidade')
    )

    df_trust_plot['Total_grupo'] = (
        df_trust_plot
        .groupby('Uso')['Quantidade']
        .transform('sum')
    )

    df_trust_plot['Percentual'] = (
        df_trust_plot['Quantidade']
        / df_trust_plot['Total_grupo']
        * 100
    )

    # Garante a ordem correta dos segmentos
    ordem_confianca = {
        categoria: indice
        for indice, categoria in enumerate(ORDEM_CONFIANCA)
    }

    df_trust_plot['Ordem_confianca'] = (
        df_trust_plot['AIAcc_pt']
        .map(ordem_confianca)
    )

    # Seleção interativa pela legenda
    selection = alt.selection_point(
        fields=['AIAcc_pt'],
        bind='legend'
    )

    # Construção do gráfico
    grafico = (
        alt.Chart(df_trust_plot)
        .mark_bar(
            size=34
        )
        .encode(
            x=alt.X(
                'Percentual:Q',
                stack='zero',
                title='Respondentes dentro de cada grupo (%)',
                scale=alt.Scale(
                    domain=[0, 100]
                ),
                axis=alt.Axis(
                    labelExpr="datum.value + '%'",
                    tickCount=6,
                    grid=False
                )
            ),
            y=alt.Y(
                'Uso:N',
                title='Frequência de uso de IA',
                sort=ORDEM_USO,
                axis=alt.Axis(
                    labelFontSize=12,
                    labelPadding=10,
                    labelLimit=LIMITE_ROTULO_Y
                )
            ),
            color=alt.Color(
                'AIAcc_pt:N',
                title='Confiança na precisão',
                scale=alt.Scale(
                    domain=ORDEM_CONFIANCA,
                    range=CORES_CONFIANCA
                ),
                legend=alt.Legend(
                    orient='right',
                    titleFontSize=12,
                    labelFontSize=11,
                    symbolType='square',
                    symbolSize=120
                )
            ),
            order=alt.Order(
                'Ordem_confianca:Q'
            ),
            opacity=alt.when(selection)
            .then(alt.value(1))
            .otherwise(alt.value(0.22)),
            tooltip=[
                alt.Tooltip(
                    'Uso:N',
                    title='Frequência'
                ),
                alt.Tooltip(
                    'AIAcc_pt:N',
                    title='Confiança'
                ),
                alt.Tooltip(
                    'Quantidade:Q',
                    title='Respondentes',
                    format=',d'
                ),
                alt.Tooltip(
                    'Percentual:Q',
                    title='Percentual (%)',
                    format='.1f'
                )
            ]
        )
        .add_params(selection)
        .properties(
            width='container',
            height=300
        )
        .configure_view(
            stroke=None
        )
        .configure_axis(
            domain=False,
            labelFontSize=11,
            titleFontSize=13
        )
    )

    return grafico


# ============================================================
# 2. CAPACIDADE DA IA EM TAREFAS COMPLEXAS
# ============================================================

def criar_grafico_complexidade(df):

    # Preparação dos dados
    df_complexidade = (
        df[['ResponseId', 'AISelect_pt', 'AIComplex_pt']]
        .dropna(subset=['AISelect_pt', 'AIComplex_pt'])
        .copy()
    )

    if df_complexidade.empty:
        return None

    # Padronização dos rótulos de frequência
    df_complexidade['Uso'] = (
        df_complexidade['AISelect_pt']
        .replace(ROTULOS_USO)
    )

    # Agregação
    df_calc_complex = (
        df_complexidade
        .groupby(['Uso', 'AIComplex_pt'])
        .size()
        .reset_index(name='Quantidade')
    )

    df_calc_complex['Total_grupo'] = (
        df_calc_complex
        .groupby('Uso')['Quantidade']
        .transform('sum')
    )

    df_calc_complex['Percentual'] = (
        df_calc_complex['Quantidade']
        / df_calc_complex['Total_grupo']
        * 100
    )

    # Rótulos
    df_calc_complex['Rotulo'] = (
        df_calc_complex['Percentual']
        .map(lambda x: f'{x:.1f}%')
    )

    # Base
    base = alt.Chart(df_calc_complex).encode(
        x=alt.X(
            'AIComplex_pt:N',
            title='Capacidade percebida',
            sort=ORDEM_COMPLEXIDADE,
            axis=alt.Axis(
                labelAngle=0,
                labelLimit=170,
                labelFontSize=11,
                labelPadding=8
            )
        ),
        y=alt.Y(
            'Uso:N',
            title='Frequência de uso de IA',
            sort=ORDEM_USO,
            axis=alt.Axis(
                labelFontSize=12,
                labelPadding=10,
                labelLimit=LIMITE_ROTULO_Y
            )
        )
    )

    # Heatmap
    heatmap = base.mark_rect(
        stroke='#0E1117',
        strokeWidth=2
    ).encode(
        color=alt.Color(
            'Percentual:Q',
            title='Respondentes (%)',
            scale=alt.Scale(
                scheme='blues'
            ),
            legend=alt.Legend(
                orient='right',
                titleFontSize=12,
                labelFontSize=11
            )
        ),
        tooltip=[
            alt.Tooltip(
                'Uso:N',
                title='Frequência'
            ),
            alt.Tooltip(
                'AIComplex_pt:N',
                title='Percepção'
            ),
            alt.Tooltip(
                'Quantidade:Q',
                title='Respondentes',
                format=',d'
            ),
            alt.Tooltip(
                'Percentual:Q',
                title='Percentual (%)',
                format='.1f'
            )
        ]
    )

    # Percentuais dentro das células
    texto = base.mark_text(
        fontSize=11,
        fontWeight='bold'
    ).encode(
        text='Rotulo:N',
        color=alt.condition(
            alt.datum.Percentual >= 30,
            alt.value('white'),
            alt.value(TEXTO_ESCURO)
        )
    )

    # Gráfico final
    grafico = (
        (heatmap + texto)
        .properties(
            width='container',
            height=300
        )
        .configure_view(
            stroke=None
        )
        .configure_axis(
            domain=False,
            titleFontSize=13
        )
    )

    return grafico


# ============================================================
# 3. EXPERIÊNCIA PROFISSIONAL
# ============================================================

def criar_grafico_experiencia(df):

    # Preparação dos dados
    df_wexp_select = (
        df[['ResponseId', 'WorkExp', 'AISelect_pt']]
        .dropna(subset=['WorkExp', 'AISelect_pt'])
        .copy()
    )

    # Tratamento dos valores inconsistentes
    df_wexp_select = (
        df_wexp_select
        .loc[df_wexp_select['WorkExp'] < 70]
        .copy()
    )

    if df_wexp_select.empty:
        return None

    # Padronização dos rótulos de frequência
    df_wexp_select['Uso'] = (
        df_wexp_select['AISelect_pt']
        .replace(ROTULOS_USO)
    )

    # Construção do gráfico
    grafico = (
        alt.Chart(df_wexp_select)
        .mark_boxplot(
            extent=1.5,
            size=30,
            color=AZUL_PRINCIPAL
        )
        .encode(
            x=alt.X(
                'WorkExp:Q',
                title='Experiência profissional (anos)',
                scale=alt.Scale(
                    zero=True
                ),
                axis=alt.Axis(
                    labelFontSize=11,
                    titleFontSize=13,
                    grid=True,
                    gridOpacity=0.12
                )
            ),
            y=alt.Y(
                'Uso:N',
                title='Frequência de uso de IA',
                sort=ORDEM_USO,
                axis=alt.Axis(
                    labelFontSize=12,
                    labelPadding=10,
                    labelLimit=LIMITE_ROTULO_Y
                )
            )
        )
        .properties(
            width='container',
            height=310
        )
        .configure_view(
            stroke=None
        )
        .configure_axis(
            domain=False
        )
    )

    return grafico


# ============================================================
# 4. MUDANÇA PERCEBIDA PELO USO DE AGENTES
# ============================================================

def criar_grafico_agentes(df):

    # Preparação dos dados
    df_agents = (
        df[['ResponseId', 'AIAgents', 'AIAgentChange']]
        .dropna(subset=['AIAgents', 'AIAgentChange'])
        .copy()
    )

    # Selecionar somente respondentes que utilizam agentes de IA
    df_agents = (
        df_agents
        .loc[
            df_agents['AIAgents']
            .str.startswith('Yes', na=False)
        ]
        .copy()
    )

    if df_agents.empty:
        return None

    # Padronização da frequência de uso
    frequencia = df_agents['AIAgents'].str.lower()

    df_agents['Uso'] = np.select(
        [
            frequencia.str.contains('daily'),
            frequencia.str.contains('weekly'),
            frequencia.str.contains(
                'monthly|infrequently',
                regex=True
            )
        ],
        [
            'Uso diário',
            'Uso semanal',
            'Uso ocasional'
        ],
        default='Não classificado'
    )

    # Padronização da percepção de mudança
    mudanca = df_agents['AIAgentChange'].str.lower()

    df_agents['Mudanca'] = np.select(
        [
            mudanca.str.contains(
                'non-ai|non ai|other factors',
                regex=True
            ),
            mudanca.str.contains(
                'not at all|minimal',
                regex=True
            ),
            mudanca.str.contains('somewhat'),
            mudanca.str.contains(
                'great extent|significant',
                regex=True
            )
        ],
        [
            'Mudança por outros fatores',
            'Nenhuma ou mínima',
            'Moderada',
            'Grande'
        ],
        default='Não classificado'
    )

    # Verificação das categorias
    nao_classificados = df_agents.loc[
        (df_agents['Uso'] == 'Não classificado')
        | (df_agents['Mudanca'] == 'Não classificado')
    ]

    if not nao_classificados.empty:

        categorias = (
            nao_classificados[
                ['AIAgents', 'AIAgentChange']
            ]
            .drop_duplicates()
            .to_dict(orient='records')
        )

        raise ValueError(
            'Existem categorias que precisam ser '
            f'classificadas: {categorias}'
        )

    # Agregação
    df_agents_plot = (
        df_agents
        .groupby(['Uso', 'Mudanca'])
        .size()
        .reset_index(name='Quantidade')
    )

    df_agents_plot['Total_grupo'] = (
        df_agents_plot
        .groupby('Uso')['Quantidade']
        .transform('sum')
    )

    df_agents_plot['Percentual'] = (
        df_agents_plot['Quantidade']
        / df_agents_plot['Total_grupo']
        * 100
    )

    # Ordenação das categorias de mudança
    ordem_mudanca = {
        categoria: indice
        for indice, categoria in enumerate(ORDEM_MUDANCA)
    }

    df_agents_plot['Ordem'] = (
        df_agents_plot['Mudanca']
        .map(ordem_mudanca)
    )

    df_agents_plot = (
        df_agents_plot
        .sort_values(['Uso', 'Ordem'])
        .copy()
    )

    # Posição dos segmentos
    df_agents_plot['Fim'] = (
        df_agents_plot
        .groupby('Uso')['Percentual']
        .cumsum()
    )

    df_agents_plot['Inicio'] = (
        df_agents_plot['Fim']
        - df_agents_plot['Percentual']
    )

    df_agents_plot['Centro'] = (
        (
            df_agents_plot['Inicio']
            + df_agents_plot['Fim']
        )
        / 2
    )

    # Percentuais exibidos dentro das barras
    df_agents_plot['Rotulo'] = (
        df_agents_plot['Percentual']
        .apply(
            lambda x: f'{x:.1f}%'
            if x >= 6
            else ''
        )
    )

    # Base
    base = alt.Chart(df_agents_plot).encode(
        y=alt.Y(
            'Uso:N',
            title='Frequência de uso de agentes',
            sort=ORDEM_USO_AGENTES,
            scale=alt.Scale(
                paddingInner=0.55,
                paddingOuter=0.25
            ),
            axis=alt.Axis(
                labelFontSize=12,
                titleFontSize=13,
                labelPadding=10,
                labelLimit=LIMITE_ROTULO_Y
            )
        )
    )

    # Barras
    barras = base.mark_bar(
        size=30,
        stroke='#0E1117',
        strokeWidth=1
    ).encode(
        x=alt.X(
            'Inicio:Q',
            title='Respondentes dentro de cada grupo (%)',
            scale=alt.Scale(
                domain=[0, 100]
            ),
            axis=alt.Axis(
                labelExpr="datum.value + '%'",
                labelFontSize=11,
                titleFontSize=13,
                tickCount=6,
                grid=False
            )
        ),
        x2='Fim:Q',
        color=alt.Color(
            'Mudanca:N',
            title='Mudança percebida',
            scale=alt.Scale(
                domain=ORDEM_MUDANCA,
                range=CORES_MUDANCA
            ),
            legend=alt.Legend(
                orient='right',
                titleFontSize=12,
                labelFontSize=11,
                symbolType='square',
                symbolSize=120,
                padding=12
            )
        ),
        tooltip=[
            alt.Tooltip(
                'Uso:N',
                title='Frequência'
            ),
            alt.Tooltip(
                'Mudanca:N',
                title='Mudança percebida'
            ),
            alt.Tooltip(
                'Quantidade:Q',
                title='Respondentes',
                format=',d'
            ),
            alt.Tooltip(
                'Total_grupo:Q',
                title='Total do grupo',
                format=',d'
            ),
            alt.Tooltip(
                'Percentual:Q',
                title='Percentual (%)',
                format='.1f'
            )
        ]
    )

    # Texto
    texto = base.mark_text(
        fontSize=11,
        fontWeight='bold'
    ).encode(
        x='Centro:Q',
        text='Rotulo:N',
        color=alt.condition(
            alt.datum.Mudanca == 'Grande',
            alt.value('white'),
            alt.value('#1F2937')
        )
    )

    # Gráfico final
    grafico = (
        (barras + texto)
        .properties(
            width='container',
            height=250
        )
        .configure_view(
            stroke=None
        )
        .configure_axis(
            domain=False
        )
        .configure_legend(
            titleLimit=190,
            labelLimit=190
        )
    )

    return grafico


# ============================================================
# 5. MAPA DE USO DIÁRIO DE IA
# ============================================================

def criar_mapa_ia(
    df,
    geojson_paises,
    min_respondentes=30
):

    # Preparação dos dados
    df_geo = (
        df[['ResponseId', 'Country', 'AISelect']]
        .dropna(subset=['Country', 'AISelect'])
        .copy()
    )

    if df_geo.empty:
        return None

    # Identificação dos usuários diários
    df_geo['Uso_diario'] = (
        df_geo['AISelect']
        == 'Yes, I use AI tools daily'
    )

    # Padronização dos países
    mapeamento_paises = {
        pais: obter_iso3(pais)
        for pais in df_geo['Country'].unique()
    }

    df_geo['ISO3'] = (
        df_geo['Country']
        .map(mapeamento_paises)
    )

    # Agregação dos dados
    df_geo_plot = (
        df_geo
        .dropna(subset=['ISO3'])
        .groupby('ISO3', as_index=False)
        .agg(
            Country=('Country', 'first'),
            Respondentes=('ResponseId', 'size'),
            Uso_diario=('Uso_diario', 'sum')
        )
    )

    if df_geo_plot.empty:
        return None

    df_geo_plot['Percentual'] = (
        df_geo_plot['Uso_diario']
        / df_geo_plot['Respondentes']
        * 100
    )

    assert df_geo_plot['ISO3'].is_unique

    # Critério de amostra mínima
    df_geo_plot['Amostra_suficiente'] = (
        df_geo_plot['Respondentes']
        >= min_respondentes
    )

    # Cópia independente do GeoJSON
    geojson_mapa = deepcopy(
        geojson_paises
    )

    codigos_mapa = {
        feature['id']
        for feature in geojson_mapa['features']
    }

    # Dados que receberão coloração
    df_geo_mapa = (
        df_geo_plot
        .loc[
            df_geo_plot['Amostra_suficiente']
            & df_geo_plot['ISO3'].isin(codigos_mapa)
        ]
        .copy()
    )

    # Informações dos tooltips
    dados_tooltip = (
        df_geo_plot
        .set_index('ISO3')
        .to_dict(orient='index')
    )

    for feature in geojson_mapa['features']:

        iso3 = feature['id']
        dados = dados_tooltip.get(iso3)

        if dados is None:

            feature['properties']['Taxa'] = (
                'Sem dados'
            )

            feature['properties']['Respondentes'] = '—'
            feature['properties']['Diarios'] = '—'

        elif dados['Respondentes'] < min_respondentes:

            feature['properties']['Taxa'] = (
                'Amostra insuficiente'
            )

            feature['properties']['Respondentes'] = str(
                dados['Respondentes']
            )

            feature['properties']['Diarios'] = str(
                dados['Uso_diario']
            )

        else:

            feature['properties']['Taxa'] = (
                f"{dados['Percentual']:.1f}%"
            )

            feature['properties']['Respondentes'] = str(
                dados['Respondentes']
            )

            feature['properties']['Diarios'] = str(
                dados['Uso_diario']
            )

    # Construção do mapa
    mapa_ia = folium.Map(
        location=[15, 0],
        zoom_start=2,

        tiles=None,

        width='100%',
        height=540,

        zoom_control=False,
        scroll_wheel_zoom=False,
        dragging=False,
        double_click_zoom=False,
        touch_zoom=False,
        box_zoom=False,
        keyboard=False,

        zoom_snap=0.1
    )

    # Coroplético
    coropletico = folium.Choropleth(
        geo_data=geojson_mapa,
        data=df_geo_mapa,

        columns=[
            'ISO3',
            'Percentual'
        ],

        key_on='feature.id',

        fill_color='Blues',
        fill_opacity=0.88,

        line_color='#FFFFFF',
        line_weight=0.6,
        line_opacity=0.8,

        nan_fill_color='#D9DEE5',
        nan_fill_opacity=0.90,

        legend_name='Uso diário de IA (%)',

        bins=[
            0,
            20,
            40,
            60,
            80,
            100
        ],

        highlight=False

    ).add_to(mapa_ia)

    # Tooltip
    folium.GeoJsonTooltip(
        fields=[
            'name',
            'Taxa',
            'Respondentes',
            'Diarios'
        ],

        aliases=[
            'País:',
            'Uso diário de IA:',
            'Respondentes:',
            'Usuários diários:'
        ],

        sticky=False,
        labels=True,

        style=(
            'background-color: white;'
            'font-family: Arial;'
            'font-size: 12px;'
            'padding: 10px;'
        )

    ).add_to(
        coropletico.geojson
    )

    # Enquadramento do mundo
    mapa_ia.fit_bounds(
        bounds=[
            [-60, -180],
            [84, 180]
        ],
        padding=(5, 5)
    )

    return mapa_ia


# Gráficos do dashboard histórico. Todos recebem somente agregações da análise.
METRIC_LABELS = {
    'ai_current_use': 'Uso atual de IA',
    'ai_daily_use': 'Uso diário de IA',
    'ai_trust_positive': 'Confiança positiva',
}
METRIC_COLORS = ['#4C78A8', '#8FB6D9', '#D4866B']
PROFILE_LABELS = {
    'academic_researcher': 'Pesquisa acadêmica',
    'cloud_infrastructure': 'Infraestrutura em nuvem',
    'data_business_analyst': 'Análise de dados/negócios',
    'qa_test': 'QA e testes',
    'back_end': 'Back-end',
    'desktop_enterprise': 'Desktop/empresarial',
    'embedded': 'Sistemas embarcados',
    'front_end': 'Front-end',
    'full_stack': 'Full-stack',
    'game_graphics': 'Jogos/gráficos',
    'mobile': 'Mobile',
    'engineering_manager': 'Gestão de engenharia',
    'product_manager': 'Gestão de produto',
    'project_manager': 'Gestão de projetos',
    'system_administrator': 'Administração de sistemas',
}
FREQUENCY_LABELS = {
    'occasional': 'Uso ocasional',
    'weekly': 'Uso semanal',
    'daily': 'Uso diário',
}
COMPLEXITY_LABELS = {
    'very_poor': 'Muito ruim',
    'bad': 'Ruim',
    'neutral': 'Neutra',
    'good_with_limits': 'Boa, com limites',
    'very_good': 'Muito boa',
    'not_used_or_unknown': 'Não usa/não sabe',
}
CHANGE_LABELS = {
    'minimal_or_none': 'Nenhuma ou mínima',
    'somewhat': 'Moderada',
    'great_extent': 'Grande',
    'non_ai_factors': 'Fatores não IA',
}


def _valid_rows(results):
    """Não transforma amostra insuficiente ou indisponibilidade em zero."""
    return results.loc[results['availability_state'].eq('available')].copy()


def criar_grafico_tendencias(adocao, confianca):
    """Duas taxas de universos distintos, na mesma escala percentual."""
    rows = _valid_rows(pd.concat([adocao, confianca], ignore_index=True))
    if rows.empty:
        return None
    rows['indicador'] = rows['metric'].map({
        'ai_current_use': 'Uso atual de IA',
        'ai_trust_positive': 'Confiança positiva',
    })
    rows['base'] = rows['metric'].map({
        'ai_current_use': 'Respostas válidas sobre uso de IA',
        'ai_trust_positive': 'Usuários atuais com resposta válida de confiança',
    })
    domain = ['Uso atual de IA', 'Confiança positiva']
    base = alt.Chart(rows).encode(
        x=alt.X('year:O', title='Ano da pesquisa', sort=[2023, 2024, 2025],
                axis=alt.Axis(labelAngle=0)),
        y=alt.Y('percentage:Q', title='Taxa (%)',
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(format='.0f', titlePadding=12)),
        color=alt.Color('indicador:N', title=None, scale=alt.Scale(
            domain=domain, range=['#4C78A8', '#D4866B']),
            legend=alt.Legend(orient='bottom')),
        tooltip=[
            alt.Tooltip('year:O', title='Ano'),
            alt.Tooltip('indicador:N', title='Indicador'),
            alt.Tooltip('numerator:Q', title='Numerador', format=',d'),
            alt.Tooltip('valid_denominator:Q', title='Base válida', format=',d'),
            alt.Tooltip('base:N', title='Universo'),
            alt.Tooltip('percentage:Q', title='Taxa (%)', format='.1f'),
        ],
    )
    hover = alt.selection_point(
        fields=['metric', 'year'], on='pointerover', nearest=True,
        clear='pointerout', empty=False,
    )
    line = base.mark_line(strokeWidth=3)
    points = base.mark_circle().add_params(hover).encode(
        size=alt.condition(hover, alt.value(210), alt.value(90))
    )
    adoption_labels = base.transform_filter(
        alt.datum.metric == 'ai_current_use'
    ).mark_text(align='left', baseline='middle', dx=9, dy=-15,
                fontWeight='bold', fontSize=12).encode(
        text=alt.Text('percentage:Q', format='.1f')
    )
    trust_labels = base.transform_filter(
        alt.datum.metric == 'ai_trust_positive'
    ).mark_text(align='left', baseline='middle', dx=9, dy=17,
                fontWeight='bold', fontSize=12).encode(
        text=alt.Text('percentage:Q', format='.1f')
    )
    return (line + points + adoption_labels + trust_labels).properties(
        width='container', height=300,
        padding={'left': 28, 'right': 36, 'top': 22, 'bottom': 8},
    ).configure_view(stroke=None)


def criar_grafico_perfis(results, dimension):
    """Taxas dentro de cada grupo, com a base válida em cada tooltip."""
    rows = _valid_rows(results)
    if rows.empty:
        return None
    labels = list(dict.fromkeys(results['group'].dropna()))
    if dimension == 'role':
        label_map = PROFILE_LABELS
        height = max(280, 54 * len(labels))
    elif dimension == 'work_experience':
        label_map = {group: group + ' anos' for group in labels}
        height = 250
    else:
        raise ValueError('Dimensão de perfil não suportada')
    rows['grupo'] = rows['group'].map(label_map)
    rows['indicador'] = rows['metric'].map(METRIC_LABELS)
    rows['base'] = rows['metric'].map({
        'ai_current_use': 'Respostas válidas sobre uso',
        'ai_daily_use': 'Respostas válidas sobre uso',
        'ai_trust_positive': 'Usuários atuais com confiança válida',
    })
    group_order = [label_map[group] for group in labels]
    metric_order = list(METRIC_LABELS.values())
    return alt.Chart(rows).mark_bar(size=10).encode(
        x=alt.X('percentage:Q', title='Taxa dentro do grupo (%)',
                scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(format='.0f')),
        y=alt.Y('grupo:N', title=None, sort=group_order,
                axis=alt.Axis(labelLimit=200)),
        yOffset=alt.YOffset('indicador:N', sort=metric_order),
        color=alt.Color('indicador:N', title=None, scale=alt.Scale(
            domain=metric_order, range=METRIC_COLORS),
            legend=alt.Legend(orient='bottom')),
        tooltip=[
            alt.Tooltip('grupo:N', title='Grupo'),
            alt.Tooltip('indicador:N', title='Indicador'),
            alt.Tooltip('numerator:Q', title='Numerador', format=',d'),
            alt.Tooltip('valid_denominator:Q', title='Base válida', format=',d'),
            alt.Tooltip('base:N', title='Universo'),
            alt.Tooltip('percentage:Q', title='Taxa (%)', format='.1f'),
        ],
    ).properties(width='container', height=height).configure_view(stroke=None)


def criar_grafico_capacidade(results):
    """Mapa de calor da capacidade percebida, com usuários atuais por frequência."""
    rows = _valid_rows(results)
    if rows.empty:
        return None
    rows['frequencia'] = rows['group'].map(FREQUENCY_LABELS)
    rows['percepcao'] = rows['category'].map(COMPLEXITY_LABELS)
    rows['rotulo'] = rows['percentage'].map(lambda value: f'{value:.0f}%' if value >= 1 else '')
    base = alt.Chart(rows).encode(
        x=alt.X('percepcao:N', title='Capacidade em tarefas complexas',
                sort=list(COMPLEXITY_LABELS.values()),
                axis=alt.Axis(labelAngle=-25, labelLimit=150, labelOverlap=False)),
        y=alt.Y('frequencia:N', title=None, sort=list(FREQUENCY_LABELS.values())),
        tooltip=[
            alt.Tooltip('frequencia:N', title='Frequência'),
            alt.Tooltip('percepcao:N', title='Percepção'),
            alt.Tooltip('numerator:Q', title='Respostas', format=',d'),
            alt.Tooltip('valid_denominator:Q', title='Base válida', format=',d'),
            alt.Tooltip('percentage:Q', title='Dentro da frequência (%)', format='.1f'),
        ],
    )
    cells = base.mark_rect(stroke='#0E1117', strokeWidth=2).encode(
        color=alt.Color('percentage:Q', title='Dentro do grupo (%)',
                        scale=alt.Scale(domain=[0, 100], scheme='blues'))
    )
    labels = base.mark_text(fontSize=11, fontWeight='bold').encode(
        text='rotulo:N',
        color=alt.condition(alt.datum.percentage >= 30, alt.value('white'), alt.value(TEXTO_ESCURO)),
    )
    return (cells + labels).properties(width='container', height=240).configure_view(stroke=None)


def criar_grafico_mudanca(results):
    """Distribuição da mudança percebida por intensidade de uso de IA."""
    rows = _valid_rows(results)
    if rows.empty:
        return None
    rows['frequencia'] = rows['group'].map(FREQUENCY_LABELS)
    rows['mudanca'] = rows['category'].map(CHANGE_LABELS)
    rows['ordem'] = rows['category'].map({key: index for index, key in enumerate(CHANGE_LABELS)})
    return alt.Chart(rows).mark_bar(size=32).encode(
        x=alt.X('percentage:Q', stack='zero', title='Respostas dentro de cada frequência (%)',
                scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(format='.0f')),
        y=alt.Y('frequencia:N', title=None, sort=list(FREQUENCY_LABELS.values())),
        color=alt.Color('mudanca:N', title='Mudança percebida', scale=alt.Scale(
            domain=list(CHANGE_LABELS.values()), range=CORES_MUDANCA),
            legend=alt.Legend(orient='bottom')),
        order=alt.Order('ordem:Q'),
        tooltip=[
            alt.Tooltip('frequencia:N', title='Frequência'),
            alt.Tooltip('mudanca:N', title='Mudança'),
            alt.Tooltip('numerator:Q', title='Respostas', format=',d'),
            alt.Tooltip('valid_denominator:Q', title='Base válida', format=',d'),
            alt.Tooltip('percentage:Q', title='Dentro da frequência (%)', format='.1f'),
        ],
    ).properties(width='container', height=245).configure_view(stroke=None)


def criar_grafico_frustracoes(results):
    """Frustrações relatadas por usuários atuais; respostas múltiplas."""
    from src.analysis import FRUSTRATION_LABELS

    rows = _valid_rows(results)
    if rows.empty:
        return None
    rows['frustracao'] = rows['group'].map(FRUSTRATION_LABELS)
    rows['destaque'] = rows['group'].isin(list(FRUSTRATION_LABELS)[:2])
    rows['tipo'] = 'Múltipla escolha; percentuais não somam 100%'
    order = list(FRUSTRATION_LABELS.values())
    base = alt.Chart(rows).encode(
        x=alt.X('percentage:Q', title='Usuários com resposta válida (%)',
                scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(format='.0f')),
        y=alt.Y('frustracao:N', title=None, sort=order,
                axis=alt.Axis(labelLimit=260)),
        tooltip=[
            alt.Tooltip('frustracao:N', title='Frustração'),
            alt.Tooltip('numerator:Q', title='Respondentes', format=',d'),
            alt.Tooltip('valid_denominator:Q', title='Base válida', format=',d'),
            alt.Tooltip('percentage:Q', title='Relataram (%)', format='.1f'),
            alt.Tooltip('tipo:N', title='Pergunta'),
        ],
    )
    bars = base.mark_bar(size=24).encode(
        color=alt.condition('datum.destaque', alt.value('#D4866B'), alt.value(AZUL_PRINCIPAL))
    )
    labels = base.mark_text(align='left', baseline='middle', dx=7,
                            fontSize=12, color='#E5E7EB').encode(
        text=alt.Text('percentage:Q', format='.1f')
    )
    return (bars + labels).properties(
        width='container', height=245,
        padding={'left': 8, 'right': 38, 'top': 8, 'bottom': 8},
    ).configure_view(stroke=None)


def criar_grafico_workflow(results):
    """Uma categoria por tarefa, com denominador válido específico."""
    from src.analysis import WORKFLOW_TASKS

    rows = _valid_rows(results)
    if rows.empty:
        return None
    labels = {'current': 'Já usa', 'plan': 'Pretende usar', 'no_plan': 'Não pretende'}
    colors = [AZUL_PRINCIPAL, AZUL_MEDIO, CINZA]
    rows['tarefa'] = rows['group'].map(WORKFLOW_TASKS)
    rows['situacao'] = rows['category'].map(labels)
    rows['situacao_tooltip'] = rows['category'].map({
        'current': 'Já usa (parcial ou majoritariamente)',
        'plan': 'Pretende usar nos próximos 3–5 anos',
        'no_plan': 'Não pretende usar nesta tarefa',
    })
    rows['ordem'] = rows['category'].map({key: index for index, key in enumerate(labels)})
    return alt.Chart(rows).mark_bar(size=26).encode(
        x=alt.X('percentage:Q', stack='zero', title='Respostas dentro de cada tarefa (%)',
                scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(format='.0f')),
        y=alt.Y('tarefa:N', title=None, sort=list(WORKFLOW_TASKS.values()),
                axis=alt.Axis(labelLimit=190)),
        color=alt.Color('situacao:N', title=None, scale=alt.Scale(
            domain=list(labels.values()), range=colors),
            legend=alt.Legend(orient='bottom')),
        order=alt.Order('ordem:Q'),
        tooltip=[
            alt.Tooltip('tarefa:N', title='Tarefa'),
            alt.Tooltip('situacao_tooltip:N', title='Situação'),
            alt.Tooltip('numerator:Q', title='Respondentes', format=',d'),
            alt.Tooltip('valid_denominator:Q', title='Base válida', format=',d'),
            alt.Tooltip('percentage:Q', title='Dentro da tarefa (%)', format='.1f'),
        ],
    ).properties(width='container', height=390).configure_view(stroke=None)

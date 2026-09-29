import altair as alt
import numpy as np

def criar_grafico_confianca(df):

    # Preparação dos dados
    df_trust_precision = (
        df[['ResponseId', 'AISelect_pt', 'AIAcc_pt']]
        .dropna(subset=['AISelect_pt', 'AIAcc_pt'])
        .copy()
    )

    # Seleção interativa pela legenda
    selection = alt.selection_point(
        fields=['AIAcc_pt'],
        bind='legend'
    )

    # Construção do gráfico
    grafico = (
        alt.Chart(df_trust_precision)
        .mark_bar()
        .encode(
            x=alt.X(
                'count():Q',
                stack='normalize',
                title='Proporção de respondentes',
                axis=alt.Axis(format='%')
            ),
            y=alt.Y(
                'AISelect_pt:N',
                title='Frequência de uso de IA'
            ),
            color=alt.Color(
                'AIAcc_pt:N',
                title='Confiança na precisão'
            ),
            opacity=alt.when(selection)
                .then(alt.value(1))
                .otherwise(alt.value(0.2)),
            tooltip=[
                alt.Tooltip('AISelect_pt:N', title='Frequência'),
                alt.Tooltip('AIAcc_pt:N', title='Confiança'),
                alt.Tooltip('count():Q', title='Respondentes')
            ]
        )
        .add_params(selection)
        .properties(
            title='Confiança na precisão da IA por frequência de uso',
            width=750,
            height=450
        )
    )

    return grafico

def criar_grafico_complexidade(df):

    # Preparação dos dados
    df_complexidade = (
        df[['ResponseId', 'AISelect_pt', 'AIComplex_pt']]
        .dropna(subset=['AISelect_pt', 'AIComplex_pt'])
        .copy()
    )

    if df_complexidade.empty:
        return None

    # Agregação dos dados
    df_calc_complext = (
        df_complexidade
        .groupby(['AISelect_pt', 'AIComplex_pt'])
        .size()
        .reset_index(name='Quantidade')
    )

    df_calc_complext['Total_grupo'] = (
        df_calc_complext
        .groupby('AISelect_pt')['Quantidade']
        .transform('sum')
    )

    df_calc_complext['Percentual'] = (
        df_calc_complext['Quantidade'] /
        df_calc_complext['Total_grupo'] * 100
    )

    # Rótulos dos percentuais
    df_calc_complext['Rotulo'] = (
        df_calc_complext['Percentual']
        .map(lambda x: f'{x:.1f}%')
    )

    # Construção do gráfico
    base = alt.Chart(df_calc_complext).encode(
        x=alt.X(
            'AIComplex_pt:N',
            title='Capacidade percebida',
            axis=alt.Axis(labelAngle=0, labelLimit=150)
        ),
        y=alt.Y(
            'AISelect_pt:N',
            title='Frequência de uso',
            axis=alt.Axis(labelFontSize=12)
        )
    )

    heatmap = base.mark_rect(
        stroke='white',
        strokeWidth=2
    ).encode(
        color=alt.Color(
            'Percentual:Q',
            title='Respondentes (%)',
            scale=alt.Scale(scheme='blues')
        ),
        tooltip=[
            alt.Tooltip('AISelect_pt:N', title='Frequência'),
            alt.Tooltip('AIComplex_pt:N', title='Percepção'),
            alt.Tooltip('Quantidade:Q', title='Respondentes', format=',d'),
            alt.Tooltip('Percentual:Q', title='Percentual (%)', format='.1f')
        ]
    )

    texto = base.mark_text(
        fontSize=12,
        fontWeight='bold'
    ).encode(
        text='Rotulo:N',
        color=alt.condition(
            alt.datum.Percentual > 30,
            alt.value('white'),
            alt.value('#17324D')
        )
    )

    grafico = (
        (heatmap + texto)
        .properties(
            title='Percepção da capacidade da IA em tarefas complexas',
            width=800,
            height=400
        )
        .configure_view(strokeWidth=0)
        .configure_axis(domain=False)
    )

    return grafico


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

    # Verificação de dados disponíveis
    if df_wexp_select.empty:
        return None

    # Ordenação das categorias
    ordem_uso = [
        'Não usa e não pretende',
        'Não usa, mas pretende',
        'Uso ocasional',
        'Uso semanal',
        'Uso diário'
    ]

    # Construção do gráfico
    grafico_wexp = (
        alt.Chart(df_wexp_select)
        .mark_boxplot(
            extent=1.5,
            size=35,
            color='#4C78A8'
        )
        .encode(
            x=alt.X(
                'WorkExp:Q',
                title='Experiência profissional (anos)',
                axis=alt.Axis(
                    labelFontSize=12,
                    titleFontSize=13
                )
            ),
            y=alt.Y(
                'AISelect_pt:N',
                title='Frequência de uso de IA',
                sort=ordem_uso,
                axis=alt.Axis(
                    labelFontSize=12,
                    labelPadding=10
                )
            )
        )
        .properties(
            title=alt.TitleParams(
                text='Experiência profissional por frequência de uso de IA',
                subtitle='Distribuição dos anos de experiência entre os respondentes de cada grupo',
                anchor='middle'
            ),
            width=800,
            height=350
        )
        .configure_view(stroke=None)
    )

    return 

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
        .loc[df_agents['AIAgents'].str.startswith('Yes', na=False)]
        .copy()
    )

    # Verificação de dados disponíveis
    if df_agents.empty:
        return None

    # Padronização da frequência de uso
    frequencia = df_agents['AIAgents'].str.lower()

    df_agents['Uso'] = np.select(
        [
            frequencia.str.contains('daily'),
            frequencia.str.contains('weekly'),
            frequencia.str.contains('monthly|infrequently', regex=True)
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
            mudanca.str.contains('non-ai|non ai|other factors', regex=True),
            mudanca.str.contains('not at all|minimal', regex=True),
            mudanca.str.contains('somewhat'),
            mudanca.str.contains('great extent|significant', regex=True)
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
        (df_agents['Uso'] == 'Não classificado') |
        (df_agents['Mudanca'] == 'Não classificado')
    ]

    if not nao_classificados.empty:
        categorias = (
            nao_classificados[['AIAgents', 'AIAgentChange']]
            .drop_duplicates()
            .to_dict(orient='records')
        )

        raise ValueError(
            f'Existem categorias que precisam ser classificadas: {categorias}'
        )

    # Agregação dos dados
    df_agents_plot = (
        df_agents
        .groupby(['Uso', 'Mudanca'])
        .size()
        .reset_index(name='Quantidade')
    )

    df_agents_plot['Total_grupo'] = (
        df_agents_plot.groupby('Uso')['Quantidade'].transform('sum')
    )

    df_agents_plot['Percentual'] = (
        df_agents_plot['Quantidade'] /
        df_agents_plot['Total_grupo'] * 100
    )

    # Ordenação das categorias
    ordem_uso = [
        'Uso diário',
        'Uso semanal',
        'Uso ocasional'
    ]

    ordem_mudanca = [
        'Nenhuma ou mínima',
        'Moderada',
        'Grande',
        'Mudança por outros fatores'
    ]

    df_agents_plot['Ordem'] = df_agents_plot['Mudanca'].map(
        {categoria: i for i, categoria in enumerate(ordem_mudanca)}
    )

    df_agents_plot = (
        df_agents_plot
        .sort_values(['Uso', 'Ordem'])
        .copy()
    )

    # Cálculo das posições dos segmentos
    df_agents_plot['Fim'] = (
        df_agents_plot.groupby('Uso')['Percentual'].cumsum()
    )

    df_agents_plot['Inicio'] = (
        df_agents_plot['Fim'] - df_agents_plot['Percentual']
    )

    df_agents_plot['Centro'] = (
        (df_agents_plot['Inicio'] + df_agents_plot['Fim']) / 2
    )

    # Rótulos dos percentuais
    df_agents_plot['Rotulo'] = df_agents_plot['Percentual'].apply(
        lambda x: f'{x:.1f}%' if x >= 6 else ''
    )

    # Construção do gráfico
    base = alt.Chart(df_agents_plot).encode(
        y=alt.Y(
            'Uso:N',
            title='Frequência de uso de agentes',
            sort=ordem_uso,
            axis=alt.Axis(
                labelFontSize=12,
                titleFontSize=13,
                labelPadding=10
            )
        )
    )

    # Barras
    barras = base.mark_bar(
        size=40,
        stroke='white',
        strokeWidth=1
    ).encode(
        x=alt.X(
            'Inicio:Q',
            title='Respondentes dentro de cada grupo (%)',
            scale=alt.Scale(domain=[0, 100]),
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
                domain=ordem_mudanca,
                range=[
                    '#C9D8E6',
                    '#8FB6D9',
                    '#3F78B5',
                    '#8C8C8C'
                ]
            ),
            legend=alt.Legend(
                orient='right',
                titleFontSize=12,
                labelFontSize=11,
                symbolType='square',
                symbolSize=140,
                padding=10
            )
        ),
        tooltip=[
            alt.Tooltip('Uso:N', title='Frequência'),
            alt.Tooltip('Mudanca:N', title='Mudança percebida'),
            alt.Tooltip('Quantidade:Q', title='Respondentes', format=',d'),
            alt.Tooltip('Total_grupo:Q', title='Total do grupo', format=',d'),
            alt.Tooltip('Percentual:Q', title='Percentual (%)', format='.1f')
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
    grafico_agents = (
        (barras + texto)
        .properties(
            title=alt.TitleParams(
                text='Mudança percebida no trabalho por frequência de uso de agentes',
                subtitle='Distribuição percentual dentro de cada grupo de frequência de uso',
                anchor='start',
                fontSize=16,
                subtitleFontSize=12
            ),
            width=760,
            height=230
        )
        .configure_view(stroke=None)
        .configure_axis(domain=False)
        .configure_legend(
            titleLimit=180,
            labelLimit=180
        )
    )

    return grafico_agents
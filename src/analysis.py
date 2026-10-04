"""Filtros e métricas puras: nenhuma dependência da interface ou dos gráficos."""

from copy import deepcopy

import pandas as pd

from src.data import (
    ADULT_AGE_GROUPS,
    AGENT_RESPONSE_LEVELS,
    AGE_MAP,
    COMPLEXITY_MAP,
    DataValidationError,
    FIELD_AVAILABILITY,
    ROLE_MAP,
    SURVEY_YEARS,
    WORKFLOW_STATUSES,
    normalizar_pais,
    validar_ano,
)


MIN_VALID_SAMPLE = 50
EXPERIENCE_GROUPS = ("1-5", "6-10", "11-20", "21+")
USAGE_FREQUENCIES = ("occasional", "weekly", "daily")
FRUSTRATION_LABELS = {
    "AI solutions that are almost right, but not quite": "Soluções quase corretas",
    "Debugging AI-generated code is more time-consuming": "Depuração mais demorada",
    "I’ve become less confident in my own problem-solving": "Menor confiança na própria resolução",
    "It’s hard to understand how or why the code works": "Código difícil de compreender",
}
FRUSTRATION_OTHER = {
    "Other (write in):", "I don’t use AI tools regularly",
    "I haven’t encountered any problems",
}
WORKFLOW_TASKS = {
    "Search for answers": "Buscar respostas",
    "Writing code": "Escrever código",
    "Learning new concepts or technologies": "Aprender conceitos",
    "Debugging or fixing code": "Depurar código",
    "Documenting code": "Documentar código",
    "Testing code": "Testar código",
    "Committing and reviewing code": "Revisar código",
    "Project planning": "Planejar projetos",
    "Deployment and monitoring": "Implantar e monitorar",
}
WORKFLOW_CATEGORIES = ("current", "plan", "no_plan")
AGENT_PRODUCTIVITY_ITEM = "AI agents have increased my productivity."
AGENT_ACCURACY_ITEM = "I am concerned about the accuracy of the information provided by AI agents."
DEFAULT_FILTERS = {
    "population": "professional",
    "age_groups": ADULT_AGE_GROUPS,
    "roles": None,
    "countries": None,
}
# Campo válido, universo e necessidade de uso atual. Não há denominador universal.
METRIC_SPECS = {
    "ai_current_use": ("ai_current_user", "valid_ai_usage_in_filtered_population", False),
    "ai_daily_use": ("ai_daily_user", "valid_ai_usage_in_filtered_population", False),
    "ai_plan_to_use": ("ai_plan_to_use", "valid_ai_usage_in_filtered_population", False),
    "ai_no_plan": ("ai_no_plan", "valid_ai_usage_in_filtered_population", False),
    "ai_trust_positive": ("ai_trust_positive", "current_ai_users_with_valid_trust", True),
    "ai_agent_use": ("ai_agent_usage", "current_ai_users_with_valid_agent_usage", True),
}
HISTORICAL_METRICS = {"ai_current_use", "ai_plan_to_use", "ai_no_plan", "ai_trust_positive"}


def normalizar_filtros(filtros=None):
    """None significa Todos; sequência vazia é uma seleção vazia, não Todos."""
    if filtros is not None and not isinstance(filtros, dict):
        raise ValueError("Filtros devem ser um dicionário")
    supplied = {} if filtros is None else filtros
    unknown = set(supplied) - set(DEFAULT_FILTERS)
    if unknown:
        raise ValueError(f"Filtros não suportados: {sorted(unknown)}; experiência não é filtro global")
    state = deepcopy(DEFAULT_FILTERS)
    state.update(deepcopy(supplied))
    if state["population"] not in {"professional", "learning", "all"}:
        raise ValueError(f"População desconhecida: {state['population']!r}")
    for field in ("age_groups", "roles", "countries"):
        values = state[field]
        if values is None:
            continue
        if not isinstance(values, (list, tuple, set, frozenset)):
            raise ValueError(f"{field} deve ser uma sequência de categorias ou None")
        if not all(isinstance(value, str) for value in values):
            raise ValueError(f"{field} contém uma categoria inválida")
        if field == "countries":
            values = [normalizar_pais(value) for value in values]
        allowed = set(AGE_MAP.values()) if field == "age_groups" else set(ROLE_MAP.values())
        if field != "countries" and set(values) - allowed:
            raise ValueError(f"{field}: categorias não suportadas {sorted(set(values) - allowed)}")
        state[field] = tuple(sorted(set(values)))
    return state


def _filtrar(df, state):
    mask = pd.Series(True, index=df.index, dtype="boolean")
    if state["population"] != "all":
        mask &= df["population_group"].eq(state["population"]).fillna(False)
    for field, column in (("age_groups", "age_group"), ("roles", "role"), ("countries", "country")):
        if state[field] is not None:
            mask &= df[column].isin(state[field])
    return df.loc[mask.fillna(False)].copy()


def filtrar_perfil(df, filtros=None):
    """Aplica o mesmo perfil a todos os anos, sem remover NA de filtros em Todos."""
    return _filtrar(df, normalizar_filtros(filtros))


def _comparabilidade(metrica, ano, state):
    if metrica not in HISTORICAL_METRICS:
        return "not_applicable", []
    status, notes = "comparable", []
    if ano == 2025:
        if state["population"] == "all":
            status = "partial"
            notes.append("A população de 2025 inclui a nova categoria de apoio a desenvolvedores.")
        if state["roles"]:
            status = "partial"
            notes.append("Em 2025, função inclui a predominante no último ano, além da função atual.")
        ages = state["age_groups"]
        if ages is None or "under_18" in ages:
            status = "not_comparable"
            notes.append("Menores de 18 anos não estão nos microdados de 2025; não conectar esta série.")
    return status, notes


def _resultado(metrica, ano, state, universo, availability, numerator=None,
               denominator=None, universe_n=None, group_by=None, group=None,
               category=None):
    comparison, notes = _comparabilidade(metrica, ano, state)
    # Dicts/tuplas retornados não compartilham estado mutável com o chamador.
    return {
        "metric": metrica,
        "year": ano,
        "numerator": numerator,
        "valid_denominator": denominator,
        "percentage": 100.0 * numerator / denominator if availability == "available" else None,
        "metric_universe": universo,
        "universe_n": universe_n,
        "filter_state": deepcopy(state),
        "availability_state": availability,
        "historical_comparability": comparison,
        "comparability_notes": notes,
        "group_by": group_by,
        "group": group,
        "category": category,
    }


def _estado_amostra(source_n, denominator):
    if source_n == 0:
        return "no_data"
    if denominator == 0:
        return "no_valid_responses"
    if denominator < MIN_VALID_SAMPLE:
        return "insufficient_sample"
    return "available"


def _taxa(source, metrica, ano, state, group_by=None, group=None, override=None):
    if metrica not in METRIC_SPECS:
        raise ValueError(f"Métrica não suportada: {metrica!r}")
    field, universe, current_only = METRIC_SPECS[metrica]
    availability = override or FIELD_AVAILABILITY[ano][field]
    if availability != "available":
        return _resultado(metrica, ano, state, universe, availability,
                          group_by=group_by, group=group)
    eligible = source.loc[source["ai_current_user"].eq(True).fillna(False)] if current_only else source
    valid = eligible.loc[eligible[field].notna()]
    positive = valid[field].isin(USAGE_FREQUENCIES) if metrica == "ai_agent_use" else valid[field].eq(True)
    denominator = len(valid)
    return _resultado(
        metrica, ano, state, universe, _estado_amostra(len(source), denominator),
        int(positive.sum()), denominator, len(eligible), group_by, group,
    )


def calcular_metrica(df, metrica, ano, filtros=None):
    """Taxa no universo especificado; percentual não arredondado e NA nunca vira não."""
    validar_ano(ano)
    state = normalizar_filtros(filtros)
    source = _filtrar(df.loc[df["survey_year"].eq(ano)], state)
    return _taxa(source, metrica, ano, state)


def calcular_serie(df, metrica, filtros=None, anos=SURVEY_YEARS):
    anos = tuple(anos)
    if not anos or len(set(anos)) != len(anos):
        raise ValueError("Selecione anos distintos, em uma sequência não vazia")
    return pd.DataFrame([calcular_metrica(df, metrica, ano, filtros) for ano in anos])


def agregar_perfis(df, dimensao, ano=2025, filtros=None):
    """Taxas dentro dos perfis; experiência não é usada como filtro histórico.

    Funções: até seis com maior base válida de uso, sem seleção pelas taxas.
    Linhas sem dimensão permanecem na base e são contabilizadas nos metadados.
    """
    validar_ano(ano)
    if dimensao not in {"work_experience", "role"}:
        raise ValueError("Dimensão aprovada: work_experience ou role")
    state = normalizar_filtros(filtros)
    source = _filtrar(df.loc[df["survey_year"].eq(ano)], state)
    metrics = ("ai_current_use", "ai_daily_use", "ai_trust_positive")
    status = FIELD_AVAILABILITY[ano][dimensao]
    if status != "available":
        return pd.DataFrame([
            _taxa(source, metric, ano, state, dimensao, override=status) for metric in metrics
        ])
    if dimensao == "work_experience":
        groups = pd.cut(source[dimensao], [0, 5, 10, 20, float("inf")], labels=EXPERIENCE_GROUPS)
        labels = EXPERIENCE_GROUPS
    else:
        groups = source["role"]
        counts = source.groupby("role")["ai_current_user"].count().reset_index(name="valid_n")
        # Empates determinísticos pelo código; frequência vem antes dos resultados.
        labels = counts.sort_values(["valid_n", "role"], ascending=[False, True])["role"].head(6).tolist()
    rows = []
    for label in labels:
        group = source.loc[groups.eq(label).fillna(False)]
        for metric in metrics:
            rows.append(_taxa(group, metric, ano, state, dimensao, label))
    if not rows:
        for metric in metrics:
            rows.append(_resultado(
                metric, ano, state, METRIC_SPECS[metric][1],
                "no_data" if source.empty else "no_valid_responses",
                0, 0, 0, dimensao,
            ))
    for row in rows:
        row["profile_missing_dimension_n"] = int(
            source["role_status"].eq("missing_response").sum()
            if dimensao == "role" else groups.isna().sum()
        )
        row["profile_not_comparable_n"] = int(
            source["role_status"].eq("not_comparable").sum()
        ) if dimensao == "role" else 0
        row["profile_not_displayed_n"] = int((groups.notna() & ~groups.isin(labels)).sum())
        if dimensao == "role" and ano == 2025 and row["metric"] in HISTORICAL_METRICS:
            if row["historical_comparability"] == "comparable":
                row["historical_comparability"] = "partial"
            note = "Em 2025, função inclui a predominante no último ano, além da função atual."
            if note not in row["comparability_notes"]:
                row["comparability_notes"].append(note)
    return pd.DataFrame(rows)


def _distribuicao(df, campo, ano, filtros, categorias, mapeamento=None):
    validar_ano(ano)
    state = normalizar_filtros(filtros)
    universe = f"current_ai_users_with_valid_{campo}_within_usage_frequency"
    status = FIELD_AVAILABILITY[ano][campo]
    if status != "available":
        return pd.DataFrame([_resultado(campo, ano, state, universe, status)])
    source = _filtrar(df.loc[df["survey_year"].eq(ano)], state)
    eligible = source.loc[source["ai_current_user"].eq(True).fillna(False)]
    rows = []
    for frequency in USAGE_FREQUENCIES:
        group = eligible.loc[eligible["ai_usage_frequency"].eq(frequency).fillna(False)]
        values = group[campo].dropna()
        if mapeamento is not None:
            values = values.replace(mapeamento)
        denominator = len(values)
        status = _estado_amostra(len(group), denominator)
        for category in categorias:
            rows.append(_resultado(
                campo, ano, state, universe, status,
                int(values.eq(category).sum()), denominator, len(group),
                "ai_usage_frequency", frequency, category,
            ))
    return pd.DataFrame(rows)


def agregar_capacidade(df, ano=2025, filtros=None):
    """Mantém não utiliza/não sabe no denominador e como categoria própria."""
    return _distribuicao(df, "ai_complexity", ano, filtros, tuple(COMPLEXITY_MAP.values()))


def agregar_mudanca(df, ano=2025, filtros=None):
    """Agrupa os dois graus de mudança não IA apenas nesta distribuição."""
    return _distribuicao(
        df, "ai_work_change", ano, filtros,
        ("minimal_or_none", "somewhat", "great_extent", "non_ai_factors"),
        {"non_ai_somewhat": "non_ai_factors", "non_ai_significant": "non_ai_factors"},
    )


def _respostas_item(source, columns, item):
    """Uma resposta por item; ausência fica sem categoria e duplicatas falham."""
    selections = pd.DataFrame({
        column: source[column].astype("string").str.split(";").map(
            lambda values: item in values if isinstance(values, list) else False
        )
        for column in columns
    }, index=source.index)
    if selections.sum(axis=1).gt(1).any():
        raise DataValidationError(f"Respostas conflitantes para {item!r}")
    return selections


def _fonte_evidencias(df, ano, filtros):
    validar_ano(ano)
    state = normalizar_filtros(filtros)
    source = _filtrar(df.loc[df["survey_year"].eq(ano)], state)
    return source.loc[source["ai_current_user"].eq(True).fillna(False)], state


def agregar_frustracoes(df, ano=2025, filtros=None):
    """Incidência de cada item entre usuários atuais com resposta à pergunta."""
    source, state = _fonte_evidencias(df, ano, filtros)
    universe = "current_ai_users_with_valid_frustration_response"
    if ano != 2025:
        return pd.DataFrame([_resultado("ai_frustration", ano, state, universe, "not_collected")])
    values = source["AIFrustration"].dropna().astype("string").str.split(";")
    observed = set(values.explode().dropna())
    unknown = observed - set(FRUSTRATION_LABELS) - FRUSTRATION_OTHER
    if unknown:
        raise DataValidationError(f"2025 / AIFrustration: itens desconhecidos {sorted(unknown)}")
    denominator = len(values)
    status = _estado_amostra(len(source), denominator)
    return pd.DataFrame([
        _resultado(
            "ai_frustration", ano, state, universe, status,
            int(values.map(lambda items: item in items).sum()), denominator,
            len(source), "frustration", item,
        )
        for item in FRUSTRATION_LABELS
    ])


def agregar_workflow(df, ano=2025, filtros=None):
    """Uma alternativa válida por tarefa; intenção permanece distinta de uso atual."""
    source, state = _fonte_evidencias(df, ano, filtros)
    universe = "current_ai_users_with_valid_response_for_each_workflow_task"
    if ano != 2025:
        return pd.DataFrame([_resultado("ai_workflow", ano, state, universe, "not_collected")])
    rows = []
    for item in WORKFLOW_TASKS:
        selections = _respostas_item(source, WORKFLOW_STATUSES, item)
        denominator = int(selections.any(axis=1).sum())
        status = _estado_amostra(len(source), denominator)
        for category in WORKFLOW_CATEGORIES:
            selected = selections.loc[:, [col for col, value in WORKFLOW_STATUSES.items() if value == category]]
            rows.append(_resultado(
                "ai_workflow", ano, state, universe, status,
                int(selected.any(axis=1).sum()), denominator,
                len(source), "workflow_task", item, category,
            ))
    return pd.DataFrame(rows)


def calcular_insight_agentes(df, ano=2025, filtros=None):
    """Produtividade percebida e preocupação com precisão no mesmo respondente."""
    source, state = _fonte_evidencias(df, ano, filtros)
    universe = "current_ai_agent_users_with_valid_productivity_and_accuracy_responses"
    if ano != 2025:
        return _resultado("ai_agent_productivity_accuracy_joint", ano, state, universe, "not_collected")
    agents = source.loc[source["ai_agent_usage"].isin(USAGE_FREQUENCIES)]
    productivity = _respostas_item(
        agents, (f"AIAgentImpact{level}" for level in AGENT_RESPONSE_LEVELS),
        AGENT_PRODUCTIVITY_ITEM,
    )
    accuracy = _respostas_item(
        agents, (f"AIAgentChallenges{level}" for level in AGENT_RESPONSE_LEVELS),
        AGENT_ACCURACY_ITEM,
    )
    valid = productivity.any(axis=1) & accuracy.any(axis=1)
    positive_levels = ("Strongly agree", "Somewhat agree")
    productivity_yes = productivity.loc[:, [f"AIAgentImpact{level}" for level in positive_levels]].any(axis=1)
    accuracy_yes = accuracy.loc[:, [f"AIAgentChallenges{level}" for level in positive_levels]].any(axis=1)
    denominator = int(valid.sum())
    return _resultado(
        "ai_agent_productivity_accuracy_joint", ano, state, universe,
        _estado_amostra(len(agents), denominator),
        int((valid & productivity_yes & accuracy_yes).sum()), denominator, len(agents),
    )

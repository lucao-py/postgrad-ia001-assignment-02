"""Fontes verificáveis e harmonização; os contratos do dashboard são preservados."""

import hashlib
import json
import tempfile
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import pycountry
import streamlit as st


SURVEY_YEARS = (2023, 2024, 2025)
SOURCE_REVISION = "32a114542da67e3759479637343718502742adfd"
SOURCE_ROOT = (
    "https://media.githubusercontent.com/media/StackExchange/Survey/"
    f"{SOURCE_REVISION}/packages/archive"
)
# SHA-256 e tamanho dos objetos Git LFS do repositório oficial, não dos ponteiros.
SOURCE_MANIFEST = {
    2023: {
        "results.csv": {
            "sha256": "828874a3cf0fa1bbb4c3da6a87e5822b8563bbc04b21f9869479480dbcff410c",
            "size": 158626799,
        },
        "schema.csv": {
            "sha256": "43ceb5126b9622bd863b366093c5373c1c0a0e65a3b8f640947b70524c94c1ec",
            "size": 16442,
        },
    },
    2024: {
        "results.csv": {
            "sha256": "7f2c2dbf6989d00b80a7351de4bb3af4b52b21cc52d5c947891bbc4f4e5cbe49",
            "size": 159525875,
        },
        "schema.csv": {
            "sha256": "d9c03fd43949dd9b0fea4847894c4011a6fe3c4390d5d8c48e078a8bfe623833",
            "size": 12503,
        },
    },
    2025: {
        "results.csv": {
            "sha256": "2d1f65308877282edfb4470520eabbc08cb499118432a3dcec6a66c086aa2baa",
            "size": 140893245,
        },
        "schema.csv": {
            "sha256": "1d24951e04eab46c6f9fecef6ce8e6b32a0a14a3f0eecdcf62f70833a74b3ff8",
            "size": 30403,
        },
    },
}
for _year, _files in SOURCE_MANIFEST.items():
    for _filename, _metadata in _files.items():
        _metadata["url"] = f"{SOURCE_ROOT}/{_year}/{_filename}"

POPULATION_MAP = {
    "I am a developer by profession": "professional",
    "I am learning to code": "learning",
    "I am not primarily a developer, but I write code sometimes as part of my work/studies": "work_or_study_coder",
    "I code primarily as a hobby": "hobbyist",
    "I used to be a developer by profession, but no longer am": "former_professional",
    "I work with developers or my work supports developers but am not a developer by profession": "developer_support",
    "None of these": "none",
}
POPULATIONS_BY_YEAR = {
    year: {
        raw for raw, value in POPULATION_MAP.items()
        if value != "developer_support" and (year == 2023 or value != "none")
    }
    for year in (2023, 2024)
}
POPULATIONS_BY_YEAR[2025] = {
    raw for raw, value in POPULATION_MAP.items() if value != "none"
}

AGE_MAP = {
    "Under 18 years old": "under_18",
    "18-24 years old": "18_24",
    "25-34 years old": "25_34",
    "35-44 years old": "35_44",
    "45-54 years old": "45_54",
    "55-64 years old": "55_64",
    "65 years or older": "65_plus",
    "Prefer not to say": "undisclosed",
}
ADULT_AGE_GROUPS = ("18_24", "25_34", "35_44", "45_54", "55_64", "65_plus")

# Lista conservadora: rótulos específicos comuns aos três instrumentos.
# Student e Other são conhecidos, mas não equivalem a uma função harmonizada.
ROLE_MAP = {
    "Academic researcher": "academic_researcher",
    "Cloud infrastructure engineer": "cloud_infrastructure",
    "Data or business analyst": "data_business_analyst",
    "Developer, QA or test": "qa_test",
    "Developer, back-end": "back_end",
    "Developer, desktop or enterprise applications": "desktop_enterprise",
    "Developer, embedded applications or devices": "embedded",
    "Developer, front-end": "front_end",
    "Developer, full-stack": "full_stack",
    "Developer, game or graphics": "game_graphics",
    "Developer, mobile": "mobile",
    "Engineering manager": "engineering_manager",
    "Product manager": "product_manager",
    "Project manager": "project_manager",
    "System administrator": "system_administrator",
}
_OLDER_ROLES = {
    "Blockchain", "Data scientist or machine learning specialist",
    "Database administrator", "Designer", "DevOps specialist",
    "Developer Advocate", "Developer Experience", "Educator",
    "Engineer, site reliability", "Hardware Engineer",
    "Marketing or sales professional", "Research & Development role",
    "Scientist", "Security professional", "Senior Executive (C-Suite, VP, etc.)",
}
KNOWN_ROLES = {
    2023: set(ROLE_MAP) | _OLDER_ROLES | {"Engineer, data", "Student", "Other (please specify):"},
    2024: set(ROLE_MAP) | _OLDER_ROLES | {"Data engineer", "Developer, AI", "Student", "Other (please specify):"},
    2025: set(ROLE_MAP) | {
        "AI/ML engineer", "Applied scientist", "Architect, software or solutions",
        "Cybersecurity or InfoSec professional", "Data engineer", "Data scientist",
        "Database administrator or engineer", "DevOps engineer or professional",
        "Developer, AI apps or physical AI", "Financial analyst or engineer",
        "Founder, technology or otherwise", "Other (please specify):", "Retired",
        "Senior executive (C-suite, VP, etc.)", "Student", "Support engineer or analyst",
        "UX, Research Ops or UI design professional",
    },
}

COUNTRY_ALIASES = {
    "Cape Verde": "CPV",
    "Congo, Republic of the...": "COG",
    "Democratic Republic of the Congo": "COD",
    "Hong Kong (S.A.R.)": "HKG",
    "Iran, Islamic Republic of...": "IRN",
    "Kosovo": "XKX",  # Código de uso corrente, não atribuído oficialmente pelo ISO.
    "Libyan Arab Jamahiriya": "LBY",
    "Micronesia, Federated States of...": "FSM",
    "Nomadic": "NOMADIC",  # Categoria de residência, não um país inventado.
    "Palestine": "PSE",
    "Republic of Korea": "KOR",
    "Swaziland": "SWZ",
    "The former Yugoslav Republic of Macedonia": "MKD",
    "Turkey": "TUR",
    "Venezuela, Bolivarian Republic of...": "VEN",
}
USAGE_MAP = {
    "Yes": "current",
    "Yes, I use AI tools daily": "daily",
    "Yes, I use AI tools weekly": "weekly",
    "Yes, I use AI tools monthly or infrequently": "occasional",
    "No, but I plan to soon": "plan_to_use",
    "No, and I don't plan to": "no_plan",
}
TRUST_MAP = {
    "Highly distrust": "highly_distrust",
    "Somewhat distrust": "somewhat_distrust",
    "Neither trust nor distrust": "neutral",
    "Somewhat trust": "somewhat_trust",
    "Highly trust": "highly_trust",
}
COMPLEXITY_MAP = {
    "Very poor at handling complex tasks": "very_poor",
    "Bad at handling complex tasks": "bad",
    "Neither good or bad at handling complex tasks": "neutral",
    "Good, but not great at handling complex tasks": "good_with_limits",
    "Very well at handling complex tasks": "very_good",
    "I don't use AI tools for complex tasks / I don't know": "not_used_or_unknown",
}
AGENT_MAP = {
    "Yes, I use AI agents at work daily": "daily",
    "Yes, I use AI agents at work weekly": "weekly",
    "Yes, I use AI agents at work monthly or infrequently": "occasional",
    "No, I use AI exclusively in copilot/autocomplete mode": "copilot_only",
    "No, but I plan to": "plan_to_use",
    "No, and I don't plan to": "no_plan",
}
WORK_CHANGE_MAP = {
    "Not at all or minimally": "minimal_or_none",
    "Yes, somewhat": "somewhat",
    "Yes, to a great extent": "great_extent",
    "No, but my development work has changed somewhat due to non-AI factors": "non_ai_somewhat",
    "No, but my development work has significantly changed due to non-AI factors": "non_ai_significant",
}

# Perguntas de 2025 usadas apenas para contextualizar os indicadores históricos.
# As matrizes exportam alternativas como colunas e tarefas como itens separados por ';'.
WORKFLOW_STATUSES = {
    "AIToolCurrently partially AI": "current",
    "AIToolCurrently mostly AI": "current",
    "AIToolPlan to partially use AI": "plan",
    "AIToolPlan to mostly use AI": "plan",
    "AIToolDon't plan to use AI for this task": "no_plan",
}
AGENT_RESPONSE_LEVELS = (
    "Strongly agree", "Somewhat agree", "Neutral",
    "Somewhat disagree", "Strongly disagree",
)
EVIDENCE_COLUMNS_2025 = (
    "ResponseId", "AIFrustration", *WORKFLOW_STATUSES,
    *(f"AIAgentImpact{level}" for level in AGENT_RESPONSE_LEVELS),
    *(f"AIAgentChallenges{level}" for level in AGENT_RESPONSE_LEVELS),
)

CANONICAL_DTYPES = {
    "survey_year": "Int64", "respondent_id": "string",
    "population_group": "string", "age_group": "string",
    "role": "string", "role_raw": "string", "role_status": "string",
    "country": "string", "country_raw": "string",
    "ai_current_user": "boolean", "ai_daily_user": "boolean",
    "ai_usage_frequency": "string", "ai_plan_to_use": "boolean",
    "ai_no_plan": "boolean", "ai_trust": "string",
    "ai_trust_positive": "boolean", "ai_complexity": "string",
    "work_experience": "Int64", "ai_agent_usage": "string",
    "ai_work_change": "string",
}
FIELD_AVAILABILITY = {
    year: {field: "available" for field in CANONICAL_DTYPES}
    for year in SURVEY_YEARS
}
for _year in (2023, 2024):
    for _field in ("ai_daily_user", "ai_usage_frequency", "ai_agent_usage", "ai_work_change"):
        FIELD_AVAILABILITY[_year][_field] = "not_collected"
    FIELD_AVAILABILITY[_year]["work_experience"] = "not_comparable"
FIELD_AVAILABILITY[2023]["ai_complexity"] = "not_collected"
FIELD_AVAILABILITY[2024]["ai_complexity"] = "not_comparable"


class DataValidationError(ValueError):
    """Fonte ou categorias diferentes do contrato auditado."""


def validar_ano(ano):
    if type(ano) is not int or ano not in SURVEY_YEARS:
        raise DataValidationError(f"Ano não suportado: {ano!r}; use {SURVEY_YEARS}.")


def colunas_obrigatorias(ano):
    validar_ano(ano)
    columns = ["ResponseId", "MainBranch", "Age", "DevType", "Country", "AISelect", "WorkExp"]
    columns.append("AIBen" if ano == 2023 else "AIAcc")
    if ano >= 2024:
        columns.append("AIComplex")
    if ano == 2025:
        columns.extend(["AIAgents", "AIAgentChange"])
    return columns


def normalizar_pais(pais):
    """ISO-3, com exceções documentadas XKX e NOMADIC; ausências são preservadas."""
    if pd.isna(pais):
        return pd.NA
    if pais in ("XKX", "NOMADIC"):
        return pais
    if pais in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[pais]
    try:
        return pycountry.countries.lookup(pais).alpha_3
    except (LookupError, TypeError) as exc:
        raise DataValidationError(f"País sem correspondência validada: {pais!r}") from exc


def _validar_arquivo(path, metadata):
    if path.stat().st_size != metadata["size"]:
        raise DataValidationError(f"Tamanho incorreto no arquivo {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != metadata["sha256"]:
        raise DataValidationError(f"SHA-256 incorreto no arquivo {path}")


def obter_arquivo_fonte(ano, arquivo="results.csv", cache_dir=None):
    """Baixa uma fonte fixada e verificada. Cache inválido falha sem ser sobrescrito."""
    validar_ano(ano)
    if arquivo not in SOURCE_MANIFEST[ano]:
        raise DataValidationError(f"Arquivo não suportado: {arquivo!r}")
    metadata = SOURCE_MANIFEST[ano][arquivo]
    root = Path(cache_dir) if cache_dir is not None else Path.home() / ".cache" / "ufrgs-ai-survey"
    path = root / SOURCE_REVISION / str(ano) / arquivo
    if path.exists():
        _validar_arquivo(path, metadata)
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".part", delete=False) as target:
            temporary = Path(target.name)
            with urlopen(metadata["url"], timeout=90) as response:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    target.write(chunk)
        _validar_arquivo(temporary, metadata)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def _validar_categorias(series, conhecidas, ano):
    unknown = set(series.dropna().unique()) - set(conhecidas)
    if unknown:
        raise DataValidationError(f"{ano} / {series.name}: categorias desconhecidas {sorted(unknown, key=str)!r}")


def validar_dados_anuais(df, ano):
    """Valida a fonte sem eliminar linhas, corrigir respostas ou imputar valores."""
    required = colunas_obrigatorias(ano)
    missing = set(required) - set(df.columns)
    if missing:
        raise DataValidationError(f"{ano}: colunas obrigatórias ausentes: {sorted(missing)}")
    if not df.columns.is_unique:
        raise DataValidationError(f"{ano}: nomes de colunas duplicados")
    ids = pd.to_numeric(df["ResponseId"], errors="coerce")
    if ids.isna().any() or ids.le(0).any() or ids.mod(1).ne(0).any() or ids.duplicated().any():
        raise DataValidationError(f"{ano}: ResponseId deve ser inteiro positivo, não nulo e único")
    _validar_categorias(df["MainBranch"], POPULATIONS_BY_YEAR[ano], ano)
    _validar_categorias(df["Age"], AGE_MAP, ano)
    _validar_categorias(df["DevType"], KNOWN_ROLES[ano], ano)
    usage = {
        raw for raw, value in USAGE_MAP.items()
        if (value != "current" if ano == 2025 else value in {"current", "plan_to_use", "no_plan"})
    }
    _validar_categorias(df["AISelect"], usage, ano)
    _validar_categorias(df["AIBen" if ano == 2023 else "AIAcc"], TRUST_MAP, ano)
    if ano >= 2024:
        complexity = {
            raw for raw, value in COMPLEXITY_MAP.items()
            if ano == 2025 or value != "not_used_or_unknown"
        }
        _validar_categorias(df["AIComplex"], complexity, ano)
    if ano == 2025:
        _validar_categorias(df["AIAgents"], AGENT_MAP, ano)
        _validar_categorias(df["AIAgentChange"], WORK_CHANGE_MAP, ano)
    for country in df["Country"].dropna().unique():
        normalizar_pais(country)
    experience = pd.to_numeric(df["WorkExp"], errors="coerce")
    invalid = df["WorkExp"].notna() & (experience.isna() | experience.mod(1).ne(0))
    invalid |= experience.lt(1 if ano == 2025 else 0)
    if ano < 2025:
        invalid |= experience.gt(50)
    if invalid.any():
        raise DataValidationError(f"{ano}: WorkExp fora do formato/domínio do instrumento")


def carregar_dados_anuais(ano, cache_dir=None, somente_analise=True):
    """Carrega CSV e schema verificados; por padrão lê apenas as colunas da análise."""
    required = colunas_obrigatorias(ano)
    schema_path = obter_arquivo_fonte(ano, "schema.csv", cache_dir)
    schema = pd.read_csv(schema_path)
    schema_fields = set(schema["qname"])
    if set(required) - {"ResponseId"} - schema_fields:
        raise DataValidationError(f"{ano}: schema não contém as perguntas requeridas")
    path = obter_arquivo_fonte(ano, "results.csv", cache_dir)
    columns = (lambda column: column in required) if somente_analise else None
    df = pd.read_csv(path, usecols=columns, low_memory=False)
    validar_dados_anuais(df, ano)
    return df


def _booleano_anulavel(series, positivos):
    return series.isin(positivos).astype("boolean").mask(series.isna(), pd.NA)


def harmonizar_dados(df, ano):
    """Uma linha por resposta anual; preserva a fonte recebida e ausências reais."""
    validar_dados_anuais(df, ano)
    result = pd.DataFrame({
        field: pd.Series(pd.NA, index=df.index, dtype=dtype)
        for field, dtype in CANONICAL_DTYPES.items()
    })
    result["survey_year"] = ano
    ids = pd.to_numeric(df["ResponseId"]).astype("Int64").astype("string")
    result["respondent_id"] = str(ano) + ":" + ids
    result["population_group"] = df["MainBranch"].map(POPULATION_MAP)
    result["age_group"] = df["Age"].map(AGE_MAP)
    result["role_raw"] = df["DevType"]
    result["role"] = df["DevType"].map(ROLE_MAP)
    result["role_status"] = "available"
    result.loc[df["DevType"].notna() & result["role"].isna(), "role_status"] = "not_comparable"
    result.loc[df["DevType"].isna(), "role_status"] = "missing_response"
    result["country_raw"] = df["Country"]
    country_map = {country: normalizar_pais(country) for country in df["Country"].dropna().unique()}
    result["country"] = df["Country"].map(country_map)
    usage = df["AISelect"].map(USAGE_MAP)
    result["ai_current_user"] = _booleano_anulavel(usage, {"current", "daily", "weekly", "occasional"})
    result["ai_plan_to_use"] = _booleano_anulavel(usage, {"plan_to_use"})
    result["ai_no_plan"] = _booleano_anulavel(usage, {"no_plan"})
    result["ai_trust"] = df["AIBen" if ano == 2023 else "AIAcc"].map(TRUST_MAP)
    result["ai_trust_positive"] = _booleano_anulavel(result["ai_trust"], {"somewhat_trust", "highly_trust"})
    if ano == 2025:
        result["ai_daily_user"] = _booleano_anulavel(usage, {"daily"})
        result["ai_usage_frequency"] = usage.replace({"plan_to_use": "non_user", "no_plan": "non_user"})
        result["ai_complexity"] = df["AIComplex"].map(COMPLEXITY_MAP)
        result["work_experience"] = pd.to_numeric(df["WorkExp"])
        result["ai_agent_usage"] = df["AIAgents"].map(AGENT_MAP)
        result["ai_work_change"] = df["AIAgentChange"].map(WORK_CHANGE_MAP)
    return result.astype(CANONICAL_DTYPES).reset_index(drop=True)


def carregar_base_historica(anos=SURVEY_YEARS, cache_dir=None):
    anos = tuple(anos)
    for ano in anos:
        validar_ano(ano)
    if not anos or len(set(anos)) != len(anos):
        raise DataValidationError("Selecione anos distintos; a seleção não pode ser vazia")
    frames = [harmonizar_dados(carregar_dados_anuais(ano, cache_dir), ano) for ano in anos]
    result = pd.concat(frames, ignore_index=True)
    if not result["respondent_id"].is_unique:
        raise DataValidationError("Chave canônica duplicada entre fontes")
    return result


def carregar_evidencias_2025(cache_dir=None):
    """Lê somente respostas suplementares de 2025, com chave canônica única."""
    path = obter_arquivo_fonte(2025, "results.csv", cache_dir)
    missing = set(EVIDENCE_COLUMNS_2025) - set(pd.read_csv(path, nrows=0).columns)
    if missing:
        raise DataValidationError(f"2025: colunas de evidência ausentes: {sorted(missing)}")
    evidence = pd.read_csv(path, usecols=list(EVIDENCE_COLUMNS_2025), low_memory=False)
    ids = pd.to_numeric(evidence["ResponseId"], errors="coerce")
    if ids.isna().any() or ids.le(0).any() or ids.mod(1).ne(0).any() or ids.duplicated().any():
        raise DataValidationError("2025: ResponseId inválido nas evidências")
    evidence["respondent_id"] = "2025:" + ids.astype("Int64").astype("string")
    return evidence.drop(columns="ResponseId")


def relatorio_cobertura(df, anos=SURVEY_YEARS):
    """Cobertura de todos os campos canônicos, antes de qualquer filtro de perfil."""
    rows = []
    for ano in anos:
        validar_ano(ano)
        source = df.loc[df["survey_year"].eq(ano)]
        for field in CANONICAL_DTYPES:
            status = FIELD_AVAILABILITY[ano][field]
            observed = int(source[field].notna().sum())
            non_comparable = len(source) if status == "not_comparable" else 0
            not_collected = len(source) if status == "not_collected" else 0
            if field == "role":
                non_comparable = int(source["role_status"].eq("not_comparable").sum())
            rows.append({
                "year": ano, "field": field, "dtype": CANONICAL_DTYPES[field],
                "availability_state": status, "total_respondents": len(source),
                "observed_count": observed,
                "missing_response_count": len(source) - observed - non_comparable - not_collected,
                "not_comparable_count": non_comparable, "not_collected_count": not_collected,
            })
    return pd.DataFrame(rows)


URL_DADOS = SOURCE_MANIFEST[2025]["results.csv"]["url"]


@st.cache_data(show_spinner="Carregando dados da pesquisa...")
def carregar_dados():
    return carregar_dados_anuais(2025, somente_analise=False)

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

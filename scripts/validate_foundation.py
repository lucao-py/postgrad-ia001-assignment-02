"""Revalida a fundação inteira contra as fontes oficiais fixadas, sem mocks."""

import argparse
import json
from pathlib import Path

from src.analysis import (
    agregar_capacidade,
    agregar_mudanca,
    agregar_perfis,
    calcular_metrica,
)
from src.data import (
    CANONICAL_DTYPES,
    SOURCE_MANIFEST,
    SOURCE_REVISION,
    SURVEY_YEARS,
    carregar_base_historica,
    relatorio_cobertura,
)


EXPECTED_HISTORY = {
    2023: {"ai_current_use": (29381, 66684, 44.1), "ai_trust_positive": (13533, 29283, 46.2)},
    2024: {"ai_current_use": (29393, 46463, 63.3), "ai_trust_positive": (12073, 29142, 41.4)},
    2025: {"ai_current_use": (20991, 25975, 80.8), "ai_trust_positive": (7962, 20732, 38.4)},
}
EXPECTED_PROFILES = {
    "work_experience": {
        "1-5": (85.2, 55.6, 39.0),
        "6-10": (83.2, 52.9, 38.3),
        "11-20": (80.2, 50.2, 38.4),
        "21+": (73.7, 43.2, 37.3),
    },
    "role": {
        "front_end": (87.2, 60.0, 43.3),
        "embedded": (65.2, 29.6, 28.6),
    },
}
METRICS = ("ai_current_use", "ai_daily_use", "ai_trust_positive")


def validar(cache_dir=None):
    canonical = carregar_base_historica(cache_dir=cache_dir)
    assert len(canonical) == 203812, "Quantidade total de respostas alterada"
    assert canonical.respondent_id.is_unique, "Identificadores compostos duplicados"
    assert canonical.dtypes.astype(str).to_dict() == CANONICAL_DTYPES, "Schema canônico alterado"
    year_counts = {int(year): int(count) for year, count in canonical.survey_year.value_counts().items()}
    assert year_counts == {2023: 89184, 2024: 65437, 2025: 49191}, year_counts

    coverage = relatorio_cobertura(canonical)
    assert len(coverage) == len(SURVEY_YEARS) * len(CANONICAL_DTYPES)
    coverage_parts = ["observed_count", "missing_response_count", "not_comparable_count", "not_collected_count"]
    assert coverage[coverage_parts].sum(axis=1).eq(coverage.total_respondents).all(), "Cobertura não particiona as respostas"
    assert coverage[coverage_parts].ge(0).all().all(), "Contagem de cobertura negativa"

    historical = []
    for year, expected in EXPECTED_HISTORY.items():
        for metric, (numerator, denominator, display) in expected.items():
            result = calcular_metrica(canonical, metric, year)
            actual = (result["numerator"], result["valid_denominator"], round(result["percentage"], 1))
            assert actual == (numerator, denominator, display), (year, metric, actual)
            assert result["availability_state"] == "available"
            historical.append(result)

    profiles = []
    for dimension, reference in EXPECTED_PROFILES.items():
        result = agregar_perfis(canonical, dimension)
        for group, expected_rates in reference.items():
            rows = result.loc[result.group.eq(group)].set_index("metric")
            actual_rates = tuple(round(rows.loc[metric, "percentage"], 1) for metric in METRICS)
            assert actual_rates == expected_rates, (dimension, group, actual_rates)
            assert rows.availability_state.eq("available").all()
            profiles.extend(rows.reset_index().to_dict("records"))

    roles = agregar_perfis(canonical, "role")
    selected_roles = roles.loc[roles.metric.eq("ai_current_use"), "group"].tolist()
    assert selected_roles == ["full_stack", "back_end", "desktop_enterprise", "front_end", "mobile", "embedded"], selected_roles

    agent = calcular_metrica(canonical, "ai_agent_use", 2025)
    assert (agent["numerator"], agent["valid_denominator"]) == (7686, 19915)
    for title, distribution, expected_denominators in (
        ("complexity", agregar_capacidade(canonical), {"occasional": 3258, "weekly": 4475, "daily": 13001}),
        ("work_change", agregar_mudanca(canonical), {"occasional": 3134, "weekly": 4294, "daily": 12399}),
    ):
        denominators = distribution.groupby("group").valid_denominator.first().to_dict()
        assert denominators == expected_denominators, (title, denominators)
        assert distribution.groupby("group").percentage.sum().sub(100).abs().lt(1e-9).all(), title

    return {
        "source_revision": SOURCE_REVISION,
        "source_manifest": SOURCE_MANIFEST,
        "total_respondents": len(canonical),
        "year_counts": year_counts,
        "schema": CANONICAL_DTYPES,
        "coverage": coverage.to_dict("records"),
        "historical_metrics": historical,
        "profile_metrics": profiles,
        "selected_roles": selected_roles,
        "agent_metric": agent,
        "distribution_denominators": {
            "complexity": {"occasional": 3258, "weekly": 4475, "daily": 13001},
            "work_change": {"occasional": 3134, "weekly": 4294, "daily": 12399},
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, help="Cache externo ao repositório")
    parser.add_argument("--output", type=Path, help="Salvar relatório JSON após todas as asserções")
    args = parser.parse_args()
    report = validar(args.cache_dir)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Fontes {report['source_revision']}: {report['total_respondents']:,} respostas únicas; validação aprovada")
    for row in report["historical_metrics"]:
        print(f"{row['year']} {row['metric']}: {row['numerator']}/{row['valid_denominator']} = {row['percentage']:.1f}%")
    for dimension, reference in EXPECTED_PROFILES.items():
        for group in reference:
            rows = [row for row in report["profile_metrics"] if row["group"] == group and row["group_by"] == dimension]
            rates = {row["metric"]: row["percentage"] for row in rows}
            print(f"2025 {dimension} {group}: " + ", ".join(f"{metric} {rates[metric]:.1f}%" for metric in METRICS))


if __name__ == "__main__":
    main()

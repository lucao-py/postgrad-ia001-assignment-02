"""Contratos sintéticos, sem rede. Regressões dos microdados: scripts/validate_foundation.py."""

import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from src import analysis, data


def raw_fixture(year=2025, n=60):
    """Respostas válidas; testes alteram somente a condição que querem verificar."""
    values = {
        "ResponseId": range(1, n + 1),
        "MainBranch": "I am a developer by profession",
        "Age": "25-34 years old",
        "DevType": "Developer, back-end",
        "Country": "Brazil",
        "AISelect": "Yes, I use AI tools daily" if year == 2025 else "Yes",
        "WorkExp": 5,
        "AIBen" if year == 2023 else "AIAcc": "Somewhat trust",
    }
    if year >= 2024:
        values["AIComplex"] = "Good, but not great at handling complex tasks"
    if year == 2025:
        values["AIAgents"] = "Yes, I use AI agents at work daily"
        values["AIAgentChange"] = "Yes, somewhat"
    return pd.DataFrame(values)


class SourceTests(unittest.TestCase):
    def test_manifest_has_only_pinned_sources(self):
        self.assertEqual(tuple(data.SOURCE_MANIFEST), (2023, 2024, 2025))
        for year, sources in data.SOURCE_MANIFEST.items():
            self.assertEqual(set(sources), {"results.csv", "schema.csv"})
            for name, metadata in sources.items():
                self.assertIn(f"/{data.SOURCE_REVISION}/packages/archive/{year}/{name}", metadata["url"])
                self.assertEqual(len(metadata["sha256"]), 64)
                self.assertGreater(metadata["size"], 0)

    def test_download_and_cached_files_require_size_and_hash(self):
        payload = b"known source\n"
        metadata = {"url": "https://example.invalid/source", "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            data.SOURCE_MANIFEST[2025], {"results.csv": metadata}
        ):
            with patch.object(data, "urlopen", return_value=io.BytesIO(payload)) as download:
                source = data.obter_arquivo_fonte(2025, cache_dir=temporary)
                download.assert_called_once_with(metadata["url"], timeout=90)
            self.assertEqual(source.read_bytes(), payload)
            with patch.object(data, "urlopen", side_effect=AssertionError("Cache deve funcionar offline")):
                self.assertEqual(data.obter_arquivo_fonte(2025, cache_dir=temporary), source)
                for corruption in (b"x" * len(payload), b"short"):
                    source.write_bytes(corruption)
                    with self.assertRaises(data.DataValidationError):
                        data.obter_arquivo_fonte(2025, cache_dir=temporary)
                    self.assertEqual(source.read_bytes(), corruption)

    def test_invalid_download_is_not_promoted_to_cache(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            data, "urlopen", return_value=io.BytesIO(b"invalid")
        ):
            with self.assertRaises(data.DataValidationError):
                data.obter_arquivo_fonte(2025, cache_dir=temporary)
            self.assertFalse(any(path.is_file() for path in Path(temporary).rglob("*")))

    def test_unsupported_years_files_and_duplicate_years_rejected(self):
        for year in (2022, 2026, "2025", True):
            with self.subTest(year=year), self.assertRaises(data.DataValidationError):
                data.carregar_dados_anuais(year)
        with self.assertRaises(data.DataValidationError):
            data.obter_arquivo_fonte(2025, "../anything.csv")
        for years in ((), (2025, 2025), (2023, 2026)):
            with self.subTest(years=years), self.assertRaises(data.DataValidationError):
                data.carregar_base_historica(years)

    def test_loader_requires_question_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            schema = Path(temporary) / "schema.csv"
            pd.DataFrame({"qname": ["AISelect"]}).to_csv(schema, index=False)
            with patch.object(data, "obter_arquivo_fonte", return_value=schema):
                with self.assertRaisesRegex(data.DataValidationError, "schema"):
                    data.carregar_dados_anuais(2025)

    def test_loader_analysis_projection_and_legacy_full_columns(self):
        with tempfile.TemporaryDirectory() as temporary:
            schema, results = Path(temporary) / "schema.csv", Path(temporary) / "results.csv"
            pd.DataFrame({"qname": data.colunas_obrigatorias(2025)}).to_csv(schema, index=False)
            raw_fixture().assign(unrelated="preserved").to_csv(results, index=False)
            def local_source(year, filename, cache_dir):
                return schema if filename == "schema.csv" else results
            with patch.object(data, "obter_arquivo_fonte", side_effect=local_source):
                self.assertNotIn("unrelated", data.carregar_dados_anuais(2025))
                self.assertIn("unrelated", data.carregar_dados_anuais(2025, somente_analise=False))


class HarmonizationTests(unittest.TestCase):
    def test_unique_composite_keys_and_nullable_schema(self):
        with patch.object(data, "carregar_dados_anuais", side_effect=lambda year, cache: raw_fixture(year)):
            canonical = data.carregar_base_historica()
        self.assertEqual(len(canonical), 180)
        self.assertTrue(canonical.respondent_id.is_unique)
        self.assertEqual(set(canonical.respondent_id.str.split(":").str[0]), {"2023", "2024", "2025"})
        self.assertEqual(canonical.dtypes.astype(str).to_dict(), data.CANONICAL_DTYPES)

    def test_duplicate_missing_or_noninteger_ids_rejected(self):
        for invalid in (1, None, 1.5, 0, "1", "bad"):
            raw = raw_fixture().astype({"ResponseId": "object"})
            raw.loc[1, "ResponseId"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(data.DataValidationError):
                data.harmonizar_dados(raw, 2025)

    def test_required_columns_and_unknown_categories_fail_closed(self):
        for year in data.SURVEY_YEARS:
            for column in data.colunas_obrigatorias(year):
                with self.subTest(year=year, missing=column), self.assertRaises(data.DataValidationError):
                    data.harmonizar_dados(raw_fixture(year).drop(columns=column), year)
            for column in ("MainBranch", "Age", "DevType", "Country", "AISelect",
                           "AIBen" if year == 2023 else "AIAcc"):
                raw = raw_fixture(year)
                raw.loc[0, column] = "unexpected category"
                with self.subTest(year=year, unknown=column), self.assertRaises(data.DataValidationError):
                    data.harmonizar_dados(raw, year)
        for column in ("AIComplex", "AIAgents", "AIAgentChange"):
            raw = raw_fixture()
            raw.loc[0, column] = "unexpected category"
            with self.subTest(column=column), self.assertRaises(data.DataValidationError):
                data.harmonizar_dados(raw, 2025)

    def test_absent_responses_are_not_negative_or_zero_and_input_is_preserved(self):
        raw = raw_fixture().astype({"WorkExp": "Float64"})
        for column in raw.columns.difference(["ResponseId"]):
            raw.loc[0, column] = pd.NA
        original = raw.copy(deep=True)
        result = data.harmonizar_dados(raw, 2025)
        for field in data.CANONICAL_DTYPES.keys() - {"survey_year", "respondent_id", "role_status"}:
            self.assertTrue(pd.isna(result.loc[0, field]), field)
        self.assertEqual(result.loc[0, "role_status"], "missing_response")
        assert_frame_equal(raw, original)

    def test_daily_and_current_mapping_2025(self):
        raw = raw_fixture(n=6)
        raw["AISelect"] = [
            "Yes, I use AI tools daily", "Yes, I use AI tools weekly",
            "Yes, I use AI tools monthly or infrequently", "No, but I plan to soon",
            "No, and I don't plan to", None,
        ]
        result = data.harmonizar_dados(raw, 2025)
        self.assertEqual(result.ai_current_user.iloc[:5].tolist(), [True, True, True, False, False])
        self.assertEqual(result.ai_daily_user.iloc[:5].tolist(), [True, False, False, False, False])
        self.assertEqual(result.ai_plan_to_use.iloc[:5].tolist(), [False, False, False, True, False])
        self.assertEqual(result.ai_no_plan.iloc[:5].tolist(), [False, False, False, False, True])
        self.assertEqual(result.ai_usage_frequency.iloc[:5].tolist(), ["daily", "weekly", "occasional", "non_user", "non_user"])
        self.assertTrue(result.loc[5, ["ai_daily_user", "ai_current_user", "ai_plan_to_use", "ai_no_plan"]].isna().all())
        for year in (2023, 2024):
            self.assertTrue(data.harmonizar_dados(raw_fixture(year), year).ai_daily_user.isna().all())

    def test_2023_trust_uses_aiben_and_neutral_is_valid(self):
        raw = raw_fixture(2023, 3)
        raw["AIBen"] = ["Highly trust", "Neither trust nor distrust", None]
        raw["AIAcc"] = "Increase productivity"  # Outra pergunta em 2023.
        result = data.harmonizar_dados(raw, 2023)
        self.assertEqual(result.ai_trust.iloc[:2].tolist(), ["highly_trust", "neutral"])
        self.assertEqual(result.ai_trust_positive.iloc[:2].tolist(), [True, False])
        self.assertTrue(pd.isna(result.ai_trust_positive.iloc[2]))

    def test_historical_roles_and_known_noncomparable_categories(self):
        for year in data.SURVEY_YEARS:
            raw = raw_fixture(year, len(data.ROLE_MAP) + 2)
            raw["DevType"] = list(data.ROLE_MAP) + ["Student", None]
            result = data.harmonizar_dados(raw, year)
            self.assertEqual(result.role.dropna().tolist(), list(data.ROLE_MAP.values()))
            self.assertEqual(result.role_status.iloc[-2:].tolist(), ["not_comparable", "missing_response"])
            self.assertEqual(result.role_raw.iloc[-2], "Student")
            self.assertEqual(len(analysis.filtrar_perfil(result)), len(raw))

    def test_explicit_country_aliases_and_nomadic(self):
        raw = raw_fixture(n=5)
        raw["Country"] = ["Brazil", "Turkey", "Türkiye", "Nomadic", None]
        result = data.harmonizar_dados(raw, 2025)
        self.assertEqual(result.country.iloc[:4].tolist(), ["BRA", "TUR", "TUR", "NOMADIC"])
        self.assertTrue(pd.isna(result.country.iloc[4]))
        self.assertEqual(data.normalizar_pais("Kosovo"), "XKX")
        self.assertEqual(data.normalizar_pais("BRA"), "BRA")

    def test_experience_respects_year_instrument_and_no_arbitrary_outlier_cut(self):
        for invalid in (-1, 0, 1.5, "unknown"):
            raw = raw_fixture().astype({"WorkExp": "object"})
            raw.loc[0, "WorkExp"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(data.DataValidationError):
                data.harmonizar_dados(raw, 2025)
        raw = raw_fixture(n=3).astype({"WorkExp": "object"})
        raw["WorkExp"] = [1, 100, None]
        result = data.harmonizar_dados(raw, 2025)
        self.assertEqual(result.work_experience.dropna().tolist(), [1, 100])
        for year in (2023, 2024):
            raw = raw_fixture(year, 2).assign(WorkExp=[0, 50])
            self.assertTrue(data.harmonizar_dados(raw, year).work_experience.isna().all())

    def test_field_availability_and_coverage_partition(self):
        frames = []
        for year in data.SURVEY_YEARS:
            raw = raw_fixture(year)
            raw.loc[0, "DevType"] = "Student"
            raw.loc[1, "DevType"] = None
            frames.append(data.harmonizar_dados(raw, year))
        coverage = data.relatorio_cobertura(pd.concat(frames))
        self.assertEqual(len(coverage), 60)
        counts = ["observed_count", "missing_response_count", "not_comparable_count", "not_collected_count"]
        self.assertTrue(coverage[counts].sum(axis=1).eq(coverage.total_respondents).all())
        roles = coverage.loc[coverage.field.eq("role")]
        self.assertTrue(roles.observed_count.eq(58).all())
        self.assertTrue(roles.not_comparable_count.eq(1).all())
        self.assertTrue(roles.missing_response_count.eq(1).all())
        self.assertEqual(data.FIELD_AVAILABILITY[2023]["ai_complexity"], "not_collected")
        self.assertEqual(data.FIELD_AVAILABILITY[2024]["ai_complexity"], "not_comparable")
        self.assertEqual(data.FIELD_AVAILABILITY[2024]["work_experience"], "not_comparable")


class MetricTests(unittest.TestCase):
    def test_metric_denominators_and_current_users_only_trust(self):
        raw = raw_fixture(2023, 120)
        raw.loc[40:59, "AIBen"] = "Highly distrust"
        raw.loc[59, "AIBen"] = None
        raw.loc[60:99, "AISelect"] = "No, but I plan to soon"
        raw.loc[100:109, "AISelect"] = "No, and I don't plan to"
        raw.loc[110:, "AISelect"] = None
        canonical = data.harmonizar_dados(raw, 2023)
        expected = {"ai_current_use": (60, 110), "ai_trust_positive": (40, 59),
                    "ai_plan_to_use": (40, 110), "ai_no_plan": (10, 110)}
        for metric, (numerator, denominator) in expected.items():
            with self.subTest(metric=metric):
                result = analysis.calcular_metrica(canonical, metric, 2023)
                self.assertEqual((result["numerator"], result["valid_denominator"]), (numerator, denominator))
                self.assertAlmostEqual(result["percentage"], 100 * numerator / denominator)
                self.assertEqual(result["availability_state"], "available")
                self.assertEqual(result["year"], 2023)
                self.assertIn("metric_universe", result)
                self.assertEqual(result["filter_state"], analysis.normalizar_filtros())

    def test_sample_boundary_and_zero_are_not_unavailability(self):
        for n, expected in ((49, "insufficient_sample"), (50, "available")):
            canonical = data.harmonizar_dados(raw_fixture(n=n).assign(AISelect="No, and I don't plan to"), 2025)
            result = analysis.calcular_metrica(canonical, "ai_current_use", 2025)
            self.assertEqual(result["availability_state"], expected)
            self.assertEqual((result["numerator"], result["valid_denominator"]), (0, n))
            self.assertEqual(result["percentage"], None if n == 49 else 0.0)

    def test_no_data_no_valid_and_unavailable_are_distinct(self):
        canonical = data.harmonizar_dados(raw_fixture().assign(AISelect=None), 2025)
        result = analysis.calcular_metrica(canonical, "ai_current_use", 2025)
        self.assertEqual((result["availability_state"], result["valid_denominator"]), ("no_valid_responses", 0))
        result = analysis.calcular_metrica(canonical, "ai_current_use", 2025, {"roles": []})
        self.assertEqual(result["availability_state"], "no_data")
        self.assertEqual(result["valid_denominator"], 0)
        result = analysis.calcular_metrica(canonical, "ai_daily_use", 2023)
        self.assertEqual(result["availability_state"], "not_collected")
        self.assertIsNone(result["valid_denominator"])
        self.assertEqual(analysis.agregar_capacidade(canonical, 2024).availability_state.tolist(), ["not_comparable"])
        self.assertTrue(analysis.agregar_perfis(canonical, "work_experience", 2023).availability_state.eq("not_comparable").all())

    def test_agent_numerator_excludes_copilot_and_noncurrent_users(self):
        raw = raw_fixture(n=80)
        raw.loc[20:39, "AIAgents"] = "No, I use AI exclusively in copilot/autocomplete mode"
        raw.loc[40:59, "AIAgents"] = "No, but I plan to"
        raw.loc[60:69, "AIAgents"] = None
        raw.loc[70:, "AISelect"] = "No, but I plan to soon"
        result = analysis.calcular_metrica(data.harmonizar_dados(raw, 2025), "ai_agent_use", 2025)
        self.assertEqual((result["numerator"], result["valid_denominator"], result["universe_n"]), (20, 60, 70))
        self.assertAlmostEqual(result["percentage"], 100 / 3)

    def test_unsupported_metric_and_invalid_year_sequences(self):
        canonical = data.harmonizar_dados(raw_fixture(), 2025)
        with self.assertRaises(ValueError):
            analysis.calcular_metrica(canonical, "unknown", 2025)
        for years in ((), (2025, 2025), (2022,), (2026,)):
            with self.subTest(years=years), self.assertRaises(ValueError):
                analysis.calcular_serie(canonical, "ai_current_use", anos=years)


class FilterTests(unittest.TestCase):
    def test_default_adult_categories_are_common_across_years(self):
        for year in data.SURVEY_YEARS:
            raw = raw_fixture(year, len(data.AGE_MAP) + 1)
            raw["Age"] = list(data.AGE_MAP) + [None]
            result = analysis.filtrar_perfil(data.harmonizar_dados(raw, year))
            self.assertEqual(set(result.age_group), set(data.ADULT_AGE_GROUPS))
            self.assertEqual(len(result), 6)

    def test_professional_default_is_self_declared_and_all_keeps_unknown_profile(self):
        raw = raw_fixture(n=3)
        raw["MainBranch"] = ["I am a developer by profession", "I am learning to code", None]
        raw["DevType"] = ["Student", None, None]
        raw["Country"] = None
        canonical = data.harmonizar_dados(raw, 2025)
        self.assertEqual(len(analysis.filtrar_perfil(canonical)), 1)
        self.assertEqual(len(analysis.filtrar_perfil(canonical, {"population": "all"})), 3)

    def test_reusable_country_role_age_filters_and_immutability(self):
        canonical = data.harmonizar_dados(raw_fixture(), 2025)
        original = canonical.copy(deep=True)
        filters = {"countries": ["Brazil"], "roles": ["back_end"], "age_groups": ["25_34"]}
        self.assertEqual(len(analysis.filtrar_perfil(canonical, filters)), 60)
        result = analysis.calcular_metrica(canonical, "ai_current_use", 2025, filters)
        self.assertEqual(result["filter_state"]["countries"], ("BRA",))
        result["filter_state"]["population"] = "all"
        self.assertEqual(filters["countries"], ["Brazil"])
        self.assertEqual(analysis.DEFAULT_FILTERS["population"], "professional")
        assert_frame_equal(canonical, original)
        self.assertTrue(analysis.filtrar_perfil(canonical, {"countries": ["USA"]}).empty)

    def test_experience_and_unknown_filter_values_rejected(self):
        for filters in ({"work_experience": [1, 5]}, {"experience": "1-5"},
                        {"year": 2025}, {"population": "unknown"}, {"roles": ["unmapped"]},
                        {"age_groups": ["adult"]}, {"countries": ["imaginary"]},
                        {"roles": "back_end"}, {"age_groups": [None]}):
            with self.subTest(filters=filters), self.assertRaises(ValueError):
                analysis.normalizar_filtros(filters)

    def test_incompatible_historical_filters_are_explicit_not_silent_exclusions(self):
        canonical = data.harmonizar_dados(raw_fixture(), 2025)
        for filters, expected in (({}, "comparable"), ({"population": "all"}, "partial"),
                                  ({"roles": ["back_end"]}, "partial"),
                                  ({"age_groups": None}, "not_comparable")):
            result = analysis.calcular_metrica(canonical, "ai_current_use", 2025, filters)
            self.assertEqual(result["historical_comparability"], expected)
            self.assertEqual(result["percentage"], 100)
            if expected != "comparable":
                self.assertTrue(result["comparability_notes"])


class AggregationTests(unittest.TestCase):
    def test_experience_rates_are_within_group_and_boundaries_are_inclusive(self):
        raw = raw_fixture(n=9).astype({"WorkExp": "object"})
        raw["WorkExp"] = [1, 5, 6, 10, 11, 20, 21, 100, None]
        raw.loc[1, "AISelect"] = "No, and I don't plan to"
        profiles = analysis.agregar_perfis(data.harmonizar_dados(raw, 2025), "work_experience")
        adoption = profiles.loc[profiles.metric.eq("ai_current_use")]
        self.assertEqual(adoption.group.tolist(), list(analysis.EXPERIENCE_GROUPS))
        self.assertEqual(adoption.valid_denominator.tolist(), [2, 2, 2, 2])
        self.assertEqual(adoption.numerator.tolist(), [1, 2, 2, 2])
        self.assertTrue(profiles.profile_missing_dimension_n.eq(1).all())
        self.assertTrue(profiles.availability_state.eq("insufficient_sample").all())

    def test_roles_selected_by_valid_sample_not_high_rates(self):
        raw = raw_fixture(n=73)
        labels = list(data.ROLE_MAP)[:7]
        raw["DevType"] = [role for role, count in zip(labels, [5, 6, 7, 8, 9, 10, 26]) for _ in range(count)] + ["Student", None]
        raw.loc[raw.DevType.eq(labels[-1]), "AISelect"] = "No, and I don't plan to"
        profiles = analysis.agregar_perfis(data.harmonizar_dados(raw, 2025), "role")
        self.assertEqual(profiles.group.drop_duplicates().tolist(), [data.ROLE_MAP[label] for label in labels[:0:-1]])
        self.assertTrue(profiles.profile_not_displayed_n.eq(5).all())
        self.assertTrue(profiles.profile_not_comparable_n.eq(1).all())
        self.assertTrue(profiles.profile_missing_dimension_n.eq(1).all())

    def test_unknown_only_or_empty_profile_has_explicit_state(self):
        canonical = data.harmonizar_dados(raw_fixture().assign(DevType="Student"), 2025)
        self.assertTrue(analysis.agregar_perfis(canonical, "role").availability_state.eq("no_valid_responses").all())
        empty = analysis.agregar_perfis(canonical, "role", filtros={"countries": []})
        self.assertTrue(empty.availability_state.eq("no_data").all())

    def test_capability_distributions_have_valid_question_denominators(self):
        raw = raw_fixture(n=181)
        raw.loc[0:59, "AISelect"] = "Yes, I use AI tools monthly or infrequently"
        raw.loc[60:119, "AISelect"] = "Yes, I use AI tools weekly"
        raw.loc[180, "AISelect"] = "No, and I don't plan to"
        raw.loc[0:9, "AIComplex"] = "I don't use AI tools for complex tasks / I don't know"
        raw.loc[10:19, "AIComplex"] = None
        results = analysis.agregar_capacidade(data.harmonizar_dados(raw, 2025))
        self.assertEqual(results.groupby("group").valid_denominator.first().to_dict(), {"occasional": 50, "weekly": 60, "daily": 60})
        self.assertTrue(results.groupby("group").percentage.sum().sub(100).abs().lt(1e-9).all())
        unknown = results.loc[results.group.eq("occasional") & results.category.eq("not_used_or_unknown")].iloc[0]
        self.assertEqual((unknown.numerator, unknown.percentage), (10, 20))
        self.assertTrue(results.loc[results.category.eq("very_poor"), "percentage"].eq(0).all())

    def test_work_change_keeps_non_ai_factors_and_excludes_missing_and_nonusers(self):
        raw = raw_fixture(n=70)
        raw.loc[0:19, "AIAgentChange"] = "No, but my development work has changed somewhat due to non-AI factors"
        raw.loc[20:29, "AIAgentChange"] = "No, but my development work has significantly changed due to non-AI factors"
        raw.loc[60:64, "AIAgentChange"] = None
        raw.loc[65:, "AISelect"] = "No, but I plan to soon"
        canonical = data.harmonizar_dados(raw, 2025)
        self.assertEqual(canonical.ai_work_change.iloc[0], "non_ai_somewhat")
        self.assertEqual(canonical.ai_work_change.iloc[20], "non_ai_significant")
        results = analysis.agregar_mudanca(canonical)
        daily = results.loc[results.group.eq("daily")]
        self.assertTrue(daily.valid_denominator.eq(60).all())
        self.assertEqual(daily.loc[daily.category.eq("non_ai_factors"), "percentage"].item(), 50)
        self.assertEqual(daily.numerator.sum(), 60)
        self.assertTrue(results.loc[~results.group.eq("daily"), "availability_state"].eq("no_data").all())


class LegacyContractTests(unittest.TestCase):
    def test_legacy_loader_still_returns_full_2025_source(self):
        expected = raw_fixture().assign(unrelated="retained")
        with patch.object(data, "carregar_dados_anuais", return_value=expected) as loader:
            self.assertIs(data.carregar_dados.__wrapped__(), expected)
            loader.assert_called_once_with(2025, somente_analise=False)

    def test_legacy_preparation_retains_raw_columns_and_translations(self):
        raw = raw_fixture()
        original = raw.copy(deep=True)
        prepared = data.preparar_dados(raw)
        self.assertEqual(set(prepared) - set(raw), {"AIAcc_pt", "AISelect_pt", "AIComplex_pt"})
        self.assertEqual(prepared.loc[0, "AIAcc_pt"], "Confia parcialmente")
        self.assertEqual(prepared.loc[0, "AISelect_pt"], "Uso diário")
        self.assertEqual(prepared.loc[0, "AIComplex_pt"], "Boa, com limitações")
        assert_frame_equal(raw, original)

    def test_legacy_geojson_contract(self):
        payload = b'{"type":"FeatureCollection","features":[]}'
        with patch.object(data, "urlopen", return_value=io.BytesIO(payload)):
            self.assertEqual(data.carregar_geojson.__wrapped__(), {"type": "FeatureCollection", "features": []})


if __name__ == "__main__":
    unittest.main()

"""Contratos das evidências de 2025 e resultados auditados no recorte padrão."""

import unittest

import pandas as pd

from src.analysis import (
    AGENT_ACCURACY_ITEM,
    AGENT_PRODUCTIVITY_ITEM,
    FRUSTRATION_LABELS,
    WORKFLOW_STATUSES,
    WORKFLOW_TASKS,
    agregar_frustracoes,
    agregar_workflow,
    calcular_insight_agentes,
)
from src.charts import criar_grafico_workflow
from src.data import DataValidationError, carregar_base_historica, carregar_evidencias_2025


def _synthetic(n=60):
    frame = pd.DataFrame({
        "survey_year": [2025] * n,
        "population_group": ["professional"] * n,
        "age_group": ["25_34"] * n,
        "role": ["front_end"] * n,
        "country": ["BRA"] * n,
        "ai_current_user": pd.Series([True] * n, dtype="boolean"),
        "ai_agent_usage": ["daily"] * n,
        "AIFrustration": [None] * n,
    })
    for column in WORKFLOW_STATUSES:
        frame[column] = pd.Series([None] * n, dtype="string")
    for prefix in ("AIAgentImpact", "AIAgentChallenges"):
        for level in ("Strongly agree", "Somewhat agree", "Neutral",
                      "Somewhat disagree", "Strongly disagree"):
            frame[prefix + level] = pd.Series([None] * n, dtype="string")
    return frame


class StoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = carregar_base_historica().merge(
            carregar_evidencias_2025(), on="respondent_id", how="left", validate="one_to_one"
        )

    def test_frustration_reference_and_denominator(self):
        results = agregar_frustracoes(self.data)
        self.assertEqual(results.valid_denominator.tolist(), [19740] * 4)
        self.assertEqual(results.numerator.tolist(), [14967, 9666, 4341, 3106])
        self.assertEqual(set(results.group), set(FRUSTRATION_LABELS))

    def test_workflow_reference_and_mutually_exclusive_states(self):
        results = agregar_workflow(self.data)
        expected = {
            "Search for answers": (19080, [13582, 4284, 1214]),
            "Writing code": (19194, [11359, 5877, 1958]),
            "Project planning": (18661, [3342, 5216, 10103]),
            "Deployment and monitoring": (18660, [2018, 5401, 11241]),
        }
        self.assertEqual(set(results.group), set(WORKFLOW_TASKS))
        for task, (denominator, numerators) in expected.items():
            with self.subTest(task=task):
                rows = results.loc[results.group.eq(task)]
                self.assertEqual(rows.valid_denominator.tolist(), [denominator] * 3)
                self.assertEqual(rows.numerator.tolist(), numerators)
        self.assertTrue(results.groupby("group").apply(
            lambda rows: rows.numerator.sum() == rows.valid_denominator.iloc[0],
            include_groups=False,
        ).all())

    def test_workflow_chart_uses_a_diverging_scale_without_reaggregating(self):
        chart = criar_grafico_workflow(agregar_workflow(self.data)).to_dict()
        bar_layer = next(layer for layer in chart["layer"] if layer["mark"]["type"] == "bar")
        bars = bar_layer["encoding"]
        self.assertEqual(bars["x"]["field"], "inicio")
        self.assertEqual(bars["x2"]["field"], "fim")
        self.assertNotIn("stack", bars["x"])
        self.assertEqual(bars["x"]["scale"]["domain"], [-70, 100])

    def test_joint_agent_reference(self):
        result = calcular_insight_agentes(self.data)
        self.assertEqual((result["numerator"], result["valid_denominator"]), (4422, 6739))
        self.assertAlmostEqual(result["percentage"], 65.61804422021072)
        self.assertEqual(result["universe_n"], 7686)

    def test_missing_insufficient_zero_and_empty_filters(self):
        frame = _synthetic()
        self.assertEqual(agregar_frustracoes(frame).availability_state.iloc[0], "no_valid_responses")
        self.assertEqual(agregar_workflow(frame).availability_state.iloc[0], "no_valid_responses")
        self.assertEqual(calcular_insight_agentes(frame)["availability_state"], "no_valid_responses")
        frame.loc[:48, "AIFrustration"] = next(iter(FRUSTRATION_LABELS))
        frame.loc[:48, "AIToolCurrently partially AI"] = next(iter(WORKFLOW_TASKS))
        frame.loc[:48, "AIAgentImpactStrongly agree"] = AGENT_PRODUCTIVITY_ITEM
        frame.loc[:48, "AIAgentChallengesStrongly agree"] = AGENT_ACCURACY_ITEM
        frustration = agregar_frustracoes(frame)
        self.assertEqual(frustration.valid_denominator.iloc[0], 49)
        self.assertEqual(frustration.availability_state.iloc[0], "insufficient_sample")
        self.assertIsNone(frustration.percentage.iloc[0])
        self.assertEqual(agregar_workflow(frame).availability_state.iloc[0], "insufficient_sample")
        self.assertEqual(calcular_insight_agentes(frame)["availability_state"], "insufficient_sample")
        frame.loc[49, "AIFrustration"] = "I haven’t encountered any problems"
        zero = agregar_frustracoes(frame)
        self.assertEqual(zero.availability_state.iloc[1], "available")
        self.assertEqual(zero.percentage.iloc[1], 0)
        empty = agregar_frustracoes(frame, filtros={"countries": ["USA"]})
        self.assertEqual(empty.availability_state.iloc[0], "no_data")

    def test_unknown_and_conflicting_matrix_answers(self):
        frame = _synthetic()
        frame.loc[0, "AIFrustration"] = "Invented frustration"
        with self.assertRaises(DataValidationError):
            agregar_frustracoes(frame)
        task = next(iter(WORKFLOW_TASKS))
        frame.loc[0, "AIToolCurrently partially AI"] = task
        frame.loc[0, "AIToolDon't plan to use AI for this task"] = task
        with self.assertRaises(DataValidationError):
            agregar_workflow(frame)

    def test_agent_joint_requires_both_answers_and_current_use(self):
        frame = _synthetic()
        frame.loc[:49, "AIAgentImpactSomewhat agree"] = AGENT_PRODUCTIVITY_ITEM
        frame.loc[:48, "AIAgentChallengesSomewhat agree"] = AGENT_ACCURACY_ITEM
        result = calcular_insight_agentes(frame)
        self.assertEqual(result["valid_denominator"], 49)
        self.assertEqual(result["availability_state"], "insufficient_sample")
        frame.loc[49, "AIAgentChallengesNeutral"] = AGENT_ACCURACY_ITEM
        frame.loc[0, "ai_current_user"] = False
        result = calcular_insight_agentes(frame)
        self.assertEqual(result["valid_denominator"], 49)
        self.assertEqual(result["numerator"], 48)


if __name__ == "__main__":
    unittest.main()

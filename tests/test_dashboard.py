"""Execução real do Streamlit com as fontes fixadas já armazenadas no cache."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest
from src.analysis import calcular_serie
from src.data import ADULT_AGE_GROUPS, carregar_base_historica


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def chart_count(test):
    return sum(element.type == "vega_lite_chart" for element in test._tree)


class DashboardTests(unittest.TestCase):
    def test_default_story_and_filters(self):
        app = AppTest.from_file(APP_PATH, default_timeout=60).run()
        self.assertFalse(app.exception)
        self.assertEqual([box.label for box in app.selectbox], ["População", "Idade", "Função", "País"])
        self.assertEqual([box.value for box in app.selectbox], ["professional", "all", None, None])
        self.assertNotIn("adult", app.selectbox[1].options)
        self.assertEqual([tab.label for tab in app.tabs], ["Perfis profissionais · 2025", "Percepção, uso e impacto · 2025"])
        self.assertEqual(chart_count(app), 7)
        self.assertEqual(len(app.metric), 0)
        self.assertTrue(any("65.6%" in item.value for item in app.caption))
        self.assertTrue(any(
            element.type == "markdown" and "Uso não resolve a confiança" in element.value
            for element in app._tree
        ))
        self.assertFalse(any("2025 inclui novo perfil" in item.value for item in app.caption))
        self.assertFalse(app.warning)

    def test_default_chart_uses_all_profiles_in_common_adult_ages(self):
        canonical = carregar_base_historica()
        filters = {"population": "all", "age_groups": ADULT_AGE_GROUPS}
        adoption = calcular_serie(canonical, "ai_current_use", filters)
        trust = calcular_serie(canonical, "ai_trust_positive", filters)
        self.assertEqual(list(zip(adoption.numerator, adoption.valid_denominator)),
                         [(36753, 83615), (36103, 58264), (26349, 33523)])
        self.assertEqual(list(zip(trust.numerator, trust.valid_denominator)),
                         [(17441, 36611), (15343, 35766), (10241, 26007)])

    def test_incompatible_and_sparse_filters_do_not_crash(self):
        app = AppTest.from_file(APP_PATH, default_timeout=60).run()
        app.selectbox[0].set_value("all").run()
        self.assertTrue(any("2025 inclui novo perfil" in item.value for item in app.caption))
        app.selectbox[2].set_value("front_end").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Função em 2025" in item.value for item in app.caption))
        app.selectbox[1].set_value("65_plus").run()
        app.selectbox[2].set_value("academic_researcher").run()
        app.selectbox[3].set_value("NOMADIC").run()
        self.assertFalse(app.exception)
        self.assertGreaterEqual(len(app.info), 1)


if __name__ == "__main__":
    unittest.main()

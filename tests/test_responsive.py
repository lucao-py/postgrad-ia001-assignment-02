"""O layout compacto preserva valores, universos e tooltips de cada evidência."""

import unittest

from src.analysis import (
    agregar_capacidade, agregar_frustracoes, agregar_mudanca,
    agregar_perfis, agregar_workflow, calcular_serie,
)
from src.charts import (
    criar_grafico_capacidade, criar_grafico_frustracoes, criar_grafico_mudanca,
    criar_grafico_perfis, criar_grafico_tendencias, criar_grafico_workflow,
)
from src.data import carregar_base_historica, carregar_evidencias_2025


class ResponsiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = carregar_base_historica().merge(
            carregar_evidencias_2025(), on="respondent_id", validate="one_to_one", how="left"
        )
        cls.cases = [
            (criar_grafico_tendencias, (calcular_serie(data, "ai_current_use"),
                                       calcular_serie(data, "ai_trust_positive"))),
            (criar_grafico_perfis, (agregar_perfis(data, "work_experience", 2025), "work_experience")),
            (criar_grafico_perfis, (agregar_perfis(data, "role", 2025), "role")),
            (criar_grafico_capacidade, (agregar_capacidade(data, 2025),)),
            (criar_grafico_frustracoes, (agregar_frustracoes(data),)),
            (criar_grafico_workflow, (agregar_workflow(data),)),
            (criar_grafico_mudanca, (agregar_mudanca(data, 2025),)),
        ]

    def test_layouts_preserve_all_chart_data_and_tooltips(self):
        for builder, args in self.cases:
            with self.subTest(chart=builder.__name__, dimension=str(args[-1]) if len(args) == 2 else ""):
                desktop = builder(*args).to_dict()
                mobile = builder(*args, compact=True).to_dict()
                self.assertEqual(desktop["datasets"], mobile["datasets"])
                desktop_layers = desktop.get("layer", [desktop])
                mobile_layers = mobile.get("layer", [mobile])
                for full, small in zip(desktop_layers, mobile_layers):
                    self.assertEqual(full.get("encoding", {}).get("tooltip"),
                                     small.get("encoding", {}).get("tooltip"))

    def test_heatmap_transposes_without_changing_color_scale(self):
        builder, args = self.cases[3]
        desktop = builder(*args).to_dict()["layer"][0]["encoding"]
        mobile = builder(*args, compact=True).to_dict()["layer"][0]["encoding"]
        self.assertEqual(mobile["x"]["field"], desktop["y"]["field"])
        self.assertEqual(mobile["y"]["field"], desktop["x"]["field"])
        self.assertEqual(mobile["color"]["scale"], desktop["color"]["scale"])

    def test_unavailable_groups_still_have_no_chart(self):
        for builder, args in self.cases:
            unavailable = []
            for arg in args:
                if isinstance(arg, str):
                    unavailable.append(arg)
                else:
                    rows = arg.copy()
                    rows["availability_state"] = "insufficient_sample"
                    rows["percentage"] = None
                    unavailable.append(rows)
            with self.subTest(chart=builder.__name__):
                self.assertIsNone(builder(*unavailable, compact=True))


if __name__ == "__main__":
    unittest.main()

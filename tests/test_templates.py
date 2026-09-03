import unittest

from main import render_template, template_variables


class TemplateTests(unittest.TestCase):
    def test_extracts_unique_variables_in_document_order(self):
        value = "{symbol1} を確認し、{symbol2} を修正し、{symbol1} を再確認"

        self.assertEqual(template_variables(value), ["symbol1", "symbol2"])

    def test_renders_repeated_variables_with_the_same_value(self):
        value = "{target} を確認してください。{target} に問題があれば修正してください。"

        self.assertEqual(
            render_template(value, {"target": "main.py"}),
            "main.py を確認してください。main.py に問題があれば修正してください。",
        )

    def test_keeps_text_without_template_variables(self):
        value = "通常のプロンプトです。"

        self.assertEqual(template_variables(value), [])
        self.assertEqual(render_template(value, {}), value)


if __name__ == "__main__":
    unittest.main()
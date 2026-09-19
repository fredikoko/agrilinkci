import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class MobileDynamicCategoryTests(unittest.TestCase):
    def _source(self, name):
        return (ROOT / "mobile" / "screens" / name).read_text(encoding="utf-8")

    def _tree(self, name):
        return ast.parse(self._source(name))

    def test_home_uses_api_categories_and_horizontal_scroll(self):
        source = self._source("home_screen.py")
        self.assertIn('ApiClient.request("categories/"', source)
        self.assertIn("_render_quick_categories", source)
        self.assertIn("quick_categories_scroll = ScrollView", source)
        self.assertIn("_categories_error", source)

    def test_conseil_uses_api_categories_and_horizontal_scroll(self):
        source = self._source("conseil_screen.py")
        self.assertIn('ApiClient.request("conseil/categories/"', source)
        self.assertIn("_render_category_filters", source)
        self.assertIn("filter_scroll = ScrollView", source)
        self.assertIn("_categories_error", source)

    def test_category_callbacks_have_loading_and_error_parameters(self):
        for filename, method_name in (("home_screen.py", "_render_quick_categories"), ("conseil_screen.py", "_render_category_filters")):
            methods = [node for node in self._tree(filename).body if isinstance(node, ast.ClassDef) for node in node.body if isinstance(node, ast.FunctionDef) and node.name == method_name]
            self.assertEqual(len(methods), 1)
            arguments = {arg.arg for arg in methods[0].args.args}
            self.assertIn("loading", arguments)
            self.assertIn("error", arguments)


if __name__ == "__main__":
    unittest.main()

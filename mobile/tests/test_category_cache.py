import ast
from pathlib import Path
import unittest
from typing import Any


CORE_PATH = Path(__file__).resolve().parents[1] / "core.py"
CORE_TREE = ast.parse(CORE_PATH.read_text(encoding="utf-8"))
CACHE_NODES = [node for node in CORE_TREE.body if isinstance(node, ast.FunctionDef) and node.name in {"load_category_cache", "save_category_cache"}]
CACHE_NAMESPACE = {"Any": Any}
exec(compile(ast.Module(body=CACHE_NODES, type_ignores=[]), str(CORE_PATH), "exec"), CACHE_NAMESPACE)


class FakeStore:
    def __init__(self):
        self.data = {}

    def exists(self, key):
        return key in self.data

    def get(self, key):
        return self.data[key]

    def put(self, key, **values):
        self.data[key] = values


class CategoryCacheTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        CACHE_NAMESPACE["CATEGORY_CACHE_STORE"] = self.store

    def test_categories_are_saved_and_loaded_by_namespace(self):
        products = [{"id": 1, "name": "Semences"}]
        conseil = [{"id": 2, "name": "Cacao"}]
        CACHE_NAMESPACE["save_category_cache"]("products", products)
        CACHE_NAMESPACE["save_category_cache"]("conseil", conseil)
        self.assertEqual(CACHE_NAMESPACE["load_category_cache"]("products"), products)
        self.assertEqual(CACHE_NAMESPACE["load_category_cache"]("conseil"), conseil)

    def test_missing_or_invalid_cache_returns_empty_list(self):
        self.assertEqual(CACHE_NAMESPACE["load_category_cache"]("products"), [])
        self.store.data["products"] = {"items": "invalid"}
        self.assertEqual(CACHE_NAMESPACE["load_category_cache"]("products"), [])
        self.store.data["broken"] = {"items": [{"name": "OK"}]}
        self.assertEqual(CACHE_NAMESPACE["load_category_cache"]("broken"), [{"name": "OK"}])


if __name__ == "__main__":
    unittest.main()

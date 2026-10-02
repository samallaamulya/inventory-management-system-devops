import os
import tempfile
import unittest

from app import create_app


class InventoryApiTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.app = create_app({"DATABASE": self.db_path, "TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        os.remove(self.db_path)

    def _create(self, **overrides):
        payload = {"sku": "SKU-1", "name": "Widget", "category": "Parts",
                   "quantity": 10, "price": 2.5, "reorder_level": 3}
        payload.update(overrides)
        return self.client.post("/api/products", json=payload)

    def test_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")

    def test_home_page_renders(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_create_and_get_product(self):
        res = self._create()
        self.assertEqual(res.status_code, 201)
        pid = res.get_json()["id"]
        got = self.client.get(f"/api/products/{pid}")
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.get_json()["name"], "Widget")

    def test_duplicate_sku_rejected(self):
        self._create()
        self.assertEqual(self._create().status_code, 409)

    def test_validation_errors(self):
        self.assertEqual(self._create(sku="").status_code, 400)
        self.assertEqual(self._create(sku="X", quantity=-1).status_code, 400)
        self.assertEqual(self._create(sku="Y", price="abc").status_code, 400)

    def test_update_product(self):
        pid = self._create().get_json()["id"]
        res = self.client.put(f"/api/products/{pid}", json={"name": "Gadget", "price": 9})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["name"], "Gadget")
        self.assertEqual(res.get_json()["price"], 9.0)

    def test_update_missing_product(self):
        res = self.client.put("/api/products/999", json={"name": "x"})
        self.assertEqual(res.status_code, 404)

    def test_adjust_stock(self):
        pid = self._create().get_json()["id"]
        up = self.client.post(f"/api/products/{pid}/adjust", json={"change": 5})
        self.assertEqual(up.get_json()["quantity"], 15)
        down = self.client.post(f"/api/products/{pid}/adjust", json={"change": -15})
        self.assertEqual(down.get_json()["quantity"], 0)

    def test_cannot_go_below_zero(self):
        pid = self._create().get_json()["id"]
        res = self.client.post(f"/api/products/{pid}/adjust", json={"change": -11})
        self.assertEqual(res.status_code, 400)

    def test_delete_product(self):
        pid = self._create().get_json()["id"]
        self.assertEqual(self.client.delete(f"/api/products/{pid}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/products/{pid}").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/products/{pid}").status_code, 404)

    def test_search(self):
        self._create(sku="A1", name="Red Bolt")
        self._create(sku="B1", name="Blue Nut")
        res = self.client.get("/api/products?q=bolt")
        self.assertEqual([p["sku"] for p in res.get_json()], ["A1"])

    def test_stats_and_low_stock(self):
        self._create(sku="A1", quantity=10, price=2, reorder_level=3)
        self._create(sku="B1", quantity=2, price=5, reorder_level=3)
        stats = self.client.get("/api/stats").get_json()
        self.assertEqual(stats["total_products"], 2)
        self.assertEqual(stats["total_units"], 12)
        self.assertEqual(stats["total_value"], 30.0)
        self.assertEqual(stats["low_stock_count"], 1)
        low = self.client.get("/api/low-stock").get_json()
        self.assertEqual([p["sku"] for p in low], ["B1"])


if __name__ == "__main__":
    unittest.main()

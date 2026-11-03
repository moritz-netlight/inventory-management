"""
Tests for restocking API endpoints.
"""
import pytest

from mock_data import orders as shared_orders


@pytest.fixture(autouse=True)
def restore_orders():
    """POST /api/restocking/orders appends to the shared in-memory orders list.

    Snapshot and restore it so created orders don't leak into other test modules.
    """
    snapshot = list(shared_orders)
    yield
    shared_orders[:] = snapshot


class TestRestockingRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_recommendations_structure(self, client):
        """Response has budget summary fields and an items list."""
        response = client.get("/api/restocking/recommendations?budget=20000")
        assert response.status_code == 200

        data = response.json()
        assert data["budget"] == 20000
        assert "spent" in data
        assert "remaining" in data
        assert isinstance(data["items"], list)

        for item in data["items"]:
            for field in ["sku", "name", "unit_cost", "on_hand", "forecasted_demand", "trend", "quantity", "cost"]:
                assert field in item

    def test_spent_plus_remaining_equals_budget(self, client):
        """Spent and remaining always add up to the budget."""
        response = client.get("/api/restocking/recommendations?budget=20000")
        data = response.json()
        assert abs(data["spent"] + data["remaining"] - data["budget"]) < 0.01

    def test_spent_matches_item_costs(self, client):
        """Spent equals the sum of the selected line costs."""
        response = client.get("/api/restocking/recommendations?budget=20000")
        data = response.json()
        assert abs(data["spent"] - sum(item["cost"] for item in data["items"])) < 0.01

    def test_never_exceeds_budget(self, client):
        """Selected items never cost more than the budget."""
        for budget in [0, 500, 5000, 20000, 100000]:
            data = client.get(f"/api/restocking/recommendations?budget={budget}").json()
            assert data["spent"] <= budget + 0.01
            assert data["remaining"] >= -0.01

    def test_zero_budget_selects_nothing(self, client):
        """A zero budget yields no items."""
        data = client.get("/api/restocking/recommendations?budget=0").json()
        assert data["items"] == []
        assert data["spent"] == 0

    def test_large_budget_selects_all_needed_items(self, client):
        """A very large budget selects every item that needs restocking."""
        data = client.get("/api/restocking/recommendations?budget=10000000").json()
        # PSU-501 is excluded: it has 420 on hand against a forecast of 252, so no shortfall.
        # The other eight forecast items have a shortfall and should all be selected.
        assert len(data["items"]) == 8
        assert "PSU-501" not in [item["sku"] for item in data["items"]]

    def test_increasing_trend_ranked_first(self, client):
        """Increasing-demand items come before stable and decreasing ones."""
        data = client.get("/api/restocking/recommendations?budget=10000000").json()
        trend_order = {"increasing": 0, "stable": 1, "decreasing": 2}
        ranks = [trend_order[item["trend"]] for item in data["items"]]
        assert ranks == sorted(ranks)

    def test_quantity_is_shortfall(self, client):
        """Quantity equals forecasted demand minus on-hand stock."""
        data = client.get("/api/restocking/recommendations?budget=10000000").json()
        for item in data["items"]:
            assert item["quantity"] == item["forecasted_demand"] - item["on_hand"]
            assert item["quantity"] > 0

    def test_greedy_skips_items_that_do_not_fit(self, client):
        """An expensive item that doesn't fit is skipped, but cheaper later items still get picked."""
        # WDG-001 costs 450 * 29.99 = 13495.50 and ranks after the cheaper GSK-203.
        # After FLT-405 ($7837.50) and GSK-203 ($2850) only $9312.50 remains, so WDG-001 is skipped.
        data = client.get("/api/restocking/recommendations?budget=20000").json()
        skus = [item["sku"] for item in data["items"]]
        assert "WDG-001" not in skus
        assert "GSK-203" in skus

    def test_negative_budget_rejected(self, client):
        """Negative budgets fail validation."""
        response = client.get("/api/restocking/recommendations?budget=-1")
        assert response.status_code == 422

    def test_missing_budget_rejected(self, client):
        """Budget is a required parameter."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422


class TestRestockingOrders:
    """Test suite for POST /api/restocking/orders."""

    def test_place_order_returns_submitted_order(self, client):
        """A valid request creates a Submitted order with 201."""
        response = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "FLT-405", "quantity": 10}, {"sku": "WDG-001", "quantity": 5}]},
        )
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["customer"] == "Internal Restocking"
        assert order["order_number"].startswith("RST-")
        assert len(order["items"]) == 2

    def test_place_order_total_value(self, client):
        """Total value equals the sum of quantity times unit price."""
        response = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "FLT-405", "quantity": 10}, {"sku": "WDG-001", "quantity": 5}]},
        )
        order = response.json()
        expected = 10 * 8.25 + 5 * 29.99
        assert abs(order["total_value"] - expected) < 0.01

    def test_place_order_delivery_lead_time(self, client):
        """Expected delivery is 14 days after the order date."""
        from datetime import datetime

        response = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "PSU-501", "quantity": 1}]},
        )
        order = response.json()
        ordered = datetime.fromisoformat(order["order_date"])
        delivery = datetime.fromisoformat(order["expected_delivery"])
        assert (delivery - ordered).days == 14

    def test_placed_order_appears_in_orders_list(self, client):
        """A submitted restocking order is visible through GET /api/orders."""
        created = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "PSU-501", "quantity": 3}]},
        ).json()

        orders = client.get("/api/orders").json()
        assert created["id"] in [o["id"] for o in orders]

        submitted = client.get("/api/orders?status=Submitted").json()
        assert all(o["status"] == "Submitted" for o in submitted)
        assert created["id"] in [o["id"] for o in submitted]

    def test_empty_items_rejected(self, client):
        """An order with no items is rejected with 400."""
        response = client.post("/api/restocking/orders", json={"items": []})
        assert response.status_code == 400

    def test_unknown_sku_rejected(self, client):
        """An unknown SKU is rejected with 400."""
        response = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "NOPE-000", "quantity": 1}]},
        )
        assert response.status_code == 400
        assert "NOPE-000" in response.json()["detail"]

    def test_non_positive_quantity_rejected(self, client):
        """Zero or negative quantities fail validation."""
        response = client.post(
            "/api/restocking/orders",
            json={"items": [{"sku": "PSU-501", "quantity": 0}]},
        )
        assert response.status_code == 422

    def test_order_ids_are_unique(self, client):
        """Each placed order gets a new id."""
        first = client.post("/api/restocking/orders", json={"items": [{"sku": "PSU-501", "quantity": 1}]}).json()
        second = client.post("/api/restocking/orders", json={"items": [{"sku": "PSU-501", "quantity": 1}]}).json()
        assert first["id"] != second["id"]

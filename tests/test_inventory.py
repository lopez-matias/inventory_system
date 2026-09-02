from tests.conftest import create_entry, create_location, create_product


def test_stock_entry_increases_inventory(client):
    product = create_product(client)
    location = create_location(client)

    movement = create_entry(client, product["id"], location["id"], 25)
    inventory = client.get("/api/inventory").json()

    assert movement.status_code == 201
    assert movement.json()["movement_type"] == "ENTRY"
    assert len(inventory) == 1
    assert float(inventory[0]["quantity"]) == 25


def test_stock_exit_decreases_inventory(client):
    product = create_product(client)
    location = create_location(client)
    create_entry(client, product["id"], location["id"], 25)

    response = client.post(
        "/api/movements",
        json={
            "movement_type": "EXIT",
            "product_id": product["id"],
            "quantity": 7,
            "source_location_id": location["id"],
        },
    )
    inventory = client.get("/api/inventory").json()

    assert response.status_code == 201
    assert float(inventory[0]["quantity"]) == 18


def test_insufficient_stock_is_rejected_without_changing_history(client):
    product = create_product(client)
    location = create_location(client)
    create_entry(client, product["id"], location["id"], 5)

    response = client.post(
        "/api/movements",
        json={
            "movement_type": "EXIT",
            "product_id": product["id"],
            "quantity": 8,
            "source_location_id": location["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "insufficient_stock"
    assert float(client.get("/api/inventory").json()[0]["quantity"]) == 5
    assert len(client.get("/api/movements").json()) == 1


def test_transfer_updates_both_locations_and_keeps_one_movement(client):
    product = create_product(client)
    origin = create_location(client, "Origen")
    destination = create_location(client, "Destino")
    create_entry(client, product["id"], origin["id"], 30)

    response = client.post(
        "/api/movements",
        json={
            "movement_type": "TRANSFER",
            "product_id": product["id"],
            "quantity": 12,
            "source_location_id": origin["id"],
            "destination_location_id": destination["id"],
            "notes": "Transferencia de prueba",
        },
    )
    inventory = {row["location_id"]: float(row["quantity"]) for row in client.get("/api/inventory").json()}
    movements = client.get("/api/movements").json()

    assert response.status_code == 201
    assert inventory[origin["id"]] == 18
    assert inventory[destination["id"]] == 12
    assert len(movements) == 2
    assert movements[0]["movement_type"] == "TRANSFER"


def test_dashboard_low_stock_uses_total_across_locations(client):
    low_product = create_product(client, "LOW-001", minimum_stock=20)
    enough_product = create_product(client, "OK-001", minimum_stock=10)
    empty_product = create_product(client, "EMPTY-001", minimum_stock=5)
    location_a = create_location(client, "Depósito A")
    location_b = create_location(client, "Depósito B")
    create_entry(client, low_product["id"], location_a["id"], 6)
    create_entry(client, low_product["id"], location_b["id"], 7)
    create_entry(client, enough_product["id"], location_a["id"], 10)

    response = client.get("/api/dashboard")
    body = response.json()
    low_ids = {item["product_id"] for item in body["low_stock_products"]}

    assert response.status_code == 200
    assert body["low_stock_count"] == 2
    assert low_product["id"] in low_ids
    assert empty_product["id"] in low_ids
    assert enough_product["id"] not in low_ids

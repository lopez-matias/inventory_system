def test_product_creation(client, product_payload):
    response = client.post("/api/products", json=product_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["sku"] == "PROD-001"
    assert body["name"] == product_payload["name"]
    assert body["is_active"] is True
    assert body["id"] > 0


def test_duplicate_sku_is_rejected(client, product_payload):
    first = client.post("/api/products", json=product_payload)
    duplicate_payload = {**product_payload, "name": "Otro nombre", "sku": "prod-001"}
    duplicate = client.post("/api/products", json=duplicate_payload)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate_sku"

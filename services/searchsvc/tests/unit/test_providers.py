def test_providers_basic(client):
    resp = client.get("/api/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data and isinstance(data["providers"], list)
    if data["providers"]:
        p0 = data["providers"][0]
        assert "chatModels" in p0 and "embeddingModels" in p0

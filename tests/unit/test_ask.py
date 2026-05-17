def test_ask_validation_rejects_empty(app):
    _, client = app
    r = client.post("/api/v1/ask", json={"question": ""})
    assert r.status_code == 422


def test_ask_returns_answer(app):
    _, client = app
    r = client.post("/api/v1/ask", json={"question": "hi", "use_rag": False})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "stub answer"
    assert body["sources"] == []


def test_ask_with_rag(app):
    a, client = app
    client.post("/api/v1/index", json={
        "documents": [{"id": "d1", "text": "Check-in is at 3 PM."}]
    })
    r = client.post("/api/v1/ask", json={"question": "when?", "use_rag": True, "top_k": 1})
    assert r.status_code == 200
    assert len(r.json()["sources"]) == 1

def test_agent_returns_final(app):
    _, client = app
    r = client.post("/api/v1/agent", json={"task": "what is 7*6?", "max_steps": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["final_answer"] == "42"
    assert len(body["steps"]) >= 1

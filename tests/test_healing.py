from autoops.healing.engine import HealingEngine


def test_healing_engine_returns_simulation(app):
    engine = HealingEngine(app)
    snapshot = {
        "metrics": {"cpu": 95, "memory": 20, "disk": 20, "swap": 0},
        "processes": [{"pid": 99999, "name": "demo-worker"}],
    }
    analysis = {"recommendation": {"next_actions": ["Inspect workload."]}}
    actions = engine.evaluate(snapshot, analysis)
    assert actions
    assert actions[0]["status"] in {"awaiting_confirmation", "simulated", "blocked", "rate_limited"}

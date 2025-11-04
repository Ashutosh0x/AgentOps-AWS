import os
from orchestrator.guardrail import GuardrailService, DEFAULT_INSTANCE_PRICING
from orchestrator.models import SageMakerDeploymentConfig, Environment


def test_env_pricing_fallback(monkeypatch):
    monkeypatch.delenv('COST_SOURCE', raising=False)
    gs = GuardrailService()
    cfg = SageMakerDeploymentConfig(
        model_name='m', endpoint_name='e', instance_type='ml.m5.large', instance_count=2
    )
    est = gs.estimate_cost(cfg)
    assert est == DEFAULT_INSTANCE_PRICING['ml.m5.large'] * 2


def test_pricing_cache(monkeypatch):
    monkeypatch.setenv('COST_SOURCE', 'env')
    gs = GuardrailService()
    t = 'ml.m5.large'
    v1 = gs._get_price_from_cache_or_source(t)
    assert t in gs._pricing_cache
    v2 = gs._get_price_from_cache_or_source(t)
    assert v1 == v2



import os
from orchestrator.sage_tool import SageMakerTool
from orchestrator.models import SageMakerDeploymentConfig


def test_dry_run_deploy(monkeypatch):
    monkeypatch.setenv('EXECUTE', 'false')
    tool = SageMakerTool(region='us-east-1')
    cfg = SageMakerDeploymentConfig(
        model_name='m', endpoint_name='e', instance_type='ml.m5.large', instance_count=1
    )
    result = tool.deploy_model(cfg)
    assert result.dry_run is True
    assert result.success is True
    assert result.endpoint_name == 'e'



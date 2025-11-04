from orchestrator.models import DeploymentPlan, PlanStatus, Environment, SageMakerDeploymentConfig


def test_plan_serialization_datetime():
    cfg = SageMakerDeploymentConfig(
        model_name='m', endpoint_name='e', instance_type='ml.m5.large', instance_count=1
    )
    plan = DeploymentPlan(
        plan_id='p1', status=PlanStatus.DEPLOYING, user_id='u', intent='i', env=Environment.STAGING, artifact=cfg
    )
    d = plan.dict()
    assert 'created_at' in d



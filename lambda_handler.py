"""AWS Lambda handler for AgentOps Orchestrator."""

from mangum import Mangum
from orchestrator.main import app

# Wrap FastAPI app with Mangum for Lambda compatibility
# Use lifespan="on" to enable startup events
handler = Mangum(app, lifespan="on")


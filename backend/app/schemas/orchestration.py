from pydantic import BaseModel, Field
from typing import List, Optional

class OrchestrationStep(BaseModel):
    """A single step in an orchestration plan."""
    group_id: int = Field(..., description="Tasks with the same group_id run in parallel.")
    agent_name: str = Field(..., description="The exact name of the agent to delegate to.")
    task: str = Field(..., description="Detailed instructions for the agent.")
    depends_on_groups: List[int] = Field(default_factory=list, description="List of group_ids that must complete before this step starts.")

class OrchestrationPlan(BaseModel):
    """The full plan produced by the System Agent."""
    needs_delegation: bool = Field(..., description="Whether delegation to other agents is required.")
    reasoning: str = Field(..., description="Brief explanation of why this plan was chosen.")
    steps: List[OrchestrationStep] = Field(default_factory=list, description="List of steps to execute.")
    aggregation_needed: bool = Field(default=True, description="Whether a final synthesis step by the System Agent is required.")

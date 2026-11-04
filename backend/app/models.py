from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class EnvironmentEnum(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class InstanceStatus(str, Enum):
    PENDING = "PENDING"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    ACTION_IN_PROGRESS = "ACTION_IN_PROGRESS"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


class BlueprintFieldOption(BaseModel):
    label: str
    value: str
    cost_multiplier: float = 1.0


class BlueprintField(BaseModel):
    name: str
    label: str
    type: str  # "text", "select", "number", "boolean"
    description: str
    required: bool = True
    default: Optional[Any] = None
    options: Optional[List[BlueprintFieldOption]] = None


class Blueprint(BaseModel):
    id: str
    title: str
    category: str  # "Ambienti Demo", "Database & Storage", "DevOps & Microservizi", "Strumenti SaaS"
    badge: str
    icon: str  # Lucide icon name, e.g., "server", "database", "cloud", "boxes"
    description: str
    long_description: str
    connector_id: str
    base_monthly_cost: float
    provisioning_time_seconds: int = 15
    auto_approval_limit_eur: float = 250.0
    fields: List[BlueprintField] = []
    day2_actions: List[str] = ["restart", "extend_ttl"]


class ProvisionRequest(BaseModel):
    blueprint_id: str
    name: str = Field(..., min_length=3, max_length=60)
    owner_name: str
    owner_email: str
    team: str
    cost_center: str
    environment: EnvironmentEnum = EnvironmentEnum.DEV
    ttl_days: int = Field(default=14, ge=1, le=90)
    parameters: Dict[str, Any] = {}


class ActionRequest(BaseModel):
    action: str  # "restart", "extend_ttl", "backup", "stop", "start"
    parameters: Optional[Dict[str, Any]] = None


class Instance(BaseModel):
    id: str
    blueprint_id: str
    blueprint_title: str
    category: str
    icon: str
    name: str
    owner_name: str
    owner_email: str
    team: str
    cost_center: str
    environment: EnvironmentEnum
    status: InstanceStatus
    progress_percentage: int = 0
    progress_message: str = "In attesa di elaborazione"
    created_at: str
    expires_at: str
    ttl_days: int
    monthly_cost: float
    endpoints: Dict[str, str] = {}
    credentials: Dict[str, str] = {}
    parameters: Dict[str, Any] = {}
    day2_actions: List[str] = []
    logs: List[str] = []


class ConnectorInfo(BaseModel):
    id: str
    name: str
    type: str  # "cloud", "database", "kubernetes", "saas"
    description: str
    status: str = "ONLINE"
    active_instances_count: int = 0


class FinOpsStats(BaseModel):
    total_active_instances: int
    total_monthly_spend: float
    total_savings_via_ttl: float
    instances_by_environment: Dict[str, int]
    instances_by_category: Dict[str, int]

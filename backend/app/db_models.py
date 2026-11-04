import uuid
import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    billing_account = Column(String(50), default="CORP-BILLING-MAIN")
    created_at = Column(DateTime, default=datetime.utcnow)

    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    cost_center = Column(String(50), nullable=False)
    lead_email = Column(String(100), nullable=False)
    monthly_budget_eur = Column(Float, default=1500.0)
    max_instances = Column(Integer, default=20)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="teams")
    users = relationship("User", back_populates="team")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="developer", nullable=False)  # admin, devops_lead, developer, auditor
    is_active = Column(Boolean, default=True)
    is_2fa_enabled = Column(Boolean, default=False)
    totp_secret = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    team = relationship("Team", back_populates="users")


class BlueprintCategory(Base):
    __tablename__ = "blueprint_categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(64), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0)

    blueprints = relationship("BlueprintModel", back_populates="category")


class BlueprintModel(Base):
    __tablename__ = "blueprints"

    id = Column(String(64), primary_key=True)  # es. "postgres-enterprise"
    category_id = Column(String(36), ForeignKey("blueprint_categories.id"), nullable=True)
    category_name = Column(String(64), nullable=False, default="Database & Storage")
    title = Column(String(128), nullable=False)
    badge = Column(String(32), default="DevOps Core")
    icon = Column(String(32), default="server")
    description = Column(String(255), nullable=False)
    long_description = Column(Text, nullable=True)
    connector_id = Column(String(64), nullable=False)  # docker-connector, process-connector, etc.
    base_monthly_cost = Column(Float, default=25.0)
    provisioning_time_seconds = Column(Integer, default=10)
    auto_approval_limit_eur = Column(Float, default=200.0)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("BlueprintCategory", back_populates="blueprints")
    inputs = relationship("BlueprintInput", back_populates="blueprint", cascade="all, delete-orphan", order_by="BlueprintInput.display_order")


class BlueprintInput(Base):
    __tablename__ = "blueprint_inputs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    blueprint_id = Column(String(64), ForeignKey("blueprints.id"), nullable=False)
    name = Column(String(64), nullable=False)  # es. "db_size", "vpc_network", "backup_window"
    label = Column(String(128), nullable=False)
    input_type = Column(String(32), default="text")  # text, select, number, boolean, secret_vault
    description = Column(String(255), nullable=True)
    required = Column(Boolean, default=True)
    default_value = Column(String(255), nullable=True)
    options_json = Column(Text, default="[]")  # lista di {"label": "...", "value": "...", "cost_multiplier": 1.0}
    display_order = Column(Integer, default=0)

    blueprint = relationship("BlueprintModel", back_populates="inputs")

    @property
    def options(self):
        try:
            return json.loads(self.options_json)
        except Exception:
            return []

    @options.setter
    def options(self, val):
        self.options_json = json.dumps(val)


class InstanceRecord(Base):
    __tablename__ = "instances"

    id = Column(String(64), primary_key=True, index=True)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    blueprint_id = Column(String(64), nullable=False)
    blueprint_title = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)
    icon = Column(String(32), default="server")
    name = Column(String(128), nullable=False)
    owner_name = Column(String(100), nullable=False)
    owner_email = Column(String(100), nullable=False)
    team = Column(String(100), nullable=False)
    cost_center = Column(String(50), nullable=False)
    environment = Column(String(20), default="dev")
    status = Column(String(30), default="PENDING")
    progress_percentage = Column(Integer, default=0)
    progress_message = Column(String(255), default="Inizializzazione...")
    created_at = Column(String(30), nullable=False)
    expires_at = Column(String(30), nullable=False)
    ttl_days = Column(Integer, default=14)
    monthly_cost = Column(Float, default=0.0)

    # Parametri strutturati
    endpoints_json = Column(Text, default="{}")
    credentials_json = Column(Text, default="{}")
    parameters_json = Column(Text, default="{}")
    env_vars_json = Column(Text, default="{}")
    tags_json = Column(Text, default="{}")
    day2_actions_json = Column(Text, default="[]")
    logs_json = Column(Text, default="[]")

    @property
    def endpoints(self):
        try:
            return json.loads(self.endpoints_json)
        except Exception:
            return {}

    @endpoints.setter
    def endpoints(self, val):
        self.endpoints_json = json.dumps(val)

    @property
    def credentials(self):
        try:
            return json.loads(self.credentials_json)
        except Exception:
            return {}

    @credentials.setter
    def credentials(self, val):
        self.credentials_json = json.dumps(val)

    @property
    def parameters(self):
        try:
            return json.loads(self.parameters_json)
        except Exception:
            return {}

    @parameters.setter
    def parameters(self, val):
        self.parameters_json = json.dumps(val)

    @property
    def env_vars(self):
        try:
            return json.loads(self.env_vars_json)
        except Exception:
            return {}

    @env_vars.setter
    def env_vars(self, val):
        self.env_vars_json = json.dumps(val)

    @property
    def tags(self):
        try:
            return json.loads(self.tags_json)
        except Exception:
            return {}

    @tags.setter
    def tags(self, val):
        self.tags_json = json.dumps(val)

    @property
    def day2_actions(self):
        try:
            return json.loads(self.day2_actions_json)
        except Exception:
            return []

    @day2_actions.setter
    def day2_actions(self, val):
        self.day2_actions_json = json.dumps(val)

    @property
    def logs(self):
        try:
            return json.loads(self.logs_json)
        except Exception:
            return []

    @logs.setter
    def logs(self, val):
        self.logs_json = json.dumps(val)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    instance_id = Column(String(64), ForeignKey("instances.id"), nullable=False)
    requested_by = Column(String(100), nullable=False)
    team_name = Column(String(100), nullable=False)
    trigger_reason = Column(String(100), nullable=False)  # es. "PROD_ENVIRONMENT", "BUDGET_EXCEEDED"
    status = Column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(String(100), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    resource_id = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), default="127.0.0.1")
    timestamp = Column(String(30), nullable=False)

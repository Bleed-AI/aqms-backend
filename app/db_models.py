import os
import datetime
from peewee import *
from playhouse.postgres_ext import JSONField
from dotenv import load_dotenv

load_dotenv()

# db = SqliteDatabase("app.db")

db = PostgresqlDatabase(
    os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"))


class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    username = CharField(unique=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    password = CharField()
    is_admin = BooleanField(default=False)
    disabled = BooleanField(default=False)


class ScheduledFunctionLog(BaseModel):
    function = CharField()
    execution_time = DateTimeField(default=datetime.datetime.now)


class RateList(BaseModel):
    id = PrimaryKeyField()
    file_name = CharField()
    is_active = BooleanField(default=False)
    tags = JSONField(null=True)
    uploaded_at = DateTimeField(default=datetime.datetime.now(), null=True)
    is_scheduled = BooleanField(default=False)
    config_time = DateTimeField(null=True)
    status = CharField(default="pending", choices=["pending", "processed"])


class Organization(BaseModel):
    id = CharField(unique=True, index=True)
    name = CharField(index=True)
    org_code = CharField(index=True)
    primary = BooleanField(null=True)
    status = CharField(null=True)
    branch_id = IntegerField(null=True)
    url = CharField(null=True)


class Group(BaseModel):
    id = IntegerField(unique=True, index=True)
    org_id = CharField(index=True)
    name = CharField(index=True)
    online_device_count = IntegerField(null=True)
    offline_device_count = IntegerField(null=True)
    client_count = IntegerField(null=True)
    dev_client_count = IntegerField(null=True)
    expiry_count = IntegerField(null=True)
    expiry_soon_count = IntegerField(null=True)
    group_type = CharField(null=True)
    timezone = CharField(null=True)
    country = CharField(null=True)
    favorite = BooleanField(null=True)


class Device(BaseModel):
    sn = CharField(unique=True, index=True)
    id = IntegerField(index=True)
    org_id = CharField(index=True)
    group_id = IntegerField(index=True, null=True)
    last_topup_attempt = DateTimeField(null=True)
    tuIncr = IntegerField(null=True, default=0)
    dcStp = IntegerField(null=True, default=0)
    wcStp = IntegerField(null=True, default=0)
    country = CharField(null=True)
    last_topup_status = CharField(
        null=True, choices=["successful", "unsuccessful"])
    last_topup_state = CharField(null=True, choices=[
                                 "ok", "no-ack", "m-budget-reached", "y-budget-reached", "d-limit-reached", "w-limit-reached", "api-failure"])
    sim1_summary = JSONField(null=True)
    sim2_summary = JSONField(null=True)
    both_sims_summary = JSONField(null=True)
    monthly_budget = FloatField(null=True, default=0.1)
    yearly_budget = FloatField(null=True, default=0.1)
    y_budget_start = DateTimeField(null=True)
    daily_stp = IntegerField(null=True, default=0)
    weekly_stp = IntegerField(null=True, default=0)
    topup_mb = IntegerField(default=0)
    tags = JSONField(null=True)
    ratelist = IntegerField(null=True)


class BudgetInfo(BaseModel):
    id = PrimaryKeyField()
    org_id = CharField(null=True, index=True)
    group_id = IntegerField(null=True, index=True)
    budget = FloatField()
    budget_type = CharField(null=True, choices=["monthly", "yearly"])
    is_scheduled = BooleanField(default=False)
    config_time = DateTimeField(null=True)
    device_selection_tags = JSONField(null=True)
    timestamp = DateTimeField(default=datetime.datetime.now(), null=True)
    status = CharField(default="pending", choices=["pending", "processed"])


class BudgetStartInfo(BaseModel):
    id = PrimaryKeyField()
    org_id = CharField(null=True, index=True)
    group_id = IntegerField(null=True, index=True)
    start_date = DateField(null=True)
    is_scheduled = BooleanField(default=False)
    config_time = DateTimeField(null=True)
    device_selection_tags = JSONField(null=True)
    timestamp = DateTimeField(default=datetime.datetime.now(), null=True)
    status = CharField(default="pending", choices=["pending", "processed"])


class STPInfo(BaseModel):
    id = PrimaryKeyField()
    org_id = CharField(null=True, index=True)
    group_id = IntegerField(null=True, index=True)
    max_stp = IntegerField(default=0)
    stp_tenure = CharField(null=True, choices=["daily", "weekly"])
    is_scheduled = BooleanField(default=False)
    config_time = DateTimeField(null=True)
    device_selection_tags = JSONField(null=True)
    timestamp = DateTimeField(default=datetime.datetime.now(), null=True)
    status = CharField(default="pending", choices=["pending", "processed"])


class TopupInfo(BaseModel):
    id = PrimaryKeyField()
    org_id = CharField(null=True, index=True)
    group_id = IntegerField(null=True, index=True)
    topup_mb = IntegerField(default=0)
    is_scheduled = BooleanField(default=False)
    config_time = DateTimeField(null=True)
    device_selection_tags = JSONField(null=True)
    timestamp = DateTimeField(default=datetime.datetime.now(), null=True)
    status = CharField(default="pending", choices=["pending", "processed"])


class ScheduledActions(BaseModel):
    id = PrimaryKeyField()
    org_id = CharField(null=True, index=True)
    group_id = IntegerField(null=True, index=True)
    device_id = IntegerField(null=True, index=True)
    sn = CharField(index=True)
    sim = CharField(null=True, choices=["A", "B"])
    action_type = CharField(null=True, choices=[
                            "topup", "monthly_allowance_reset"])
    topup_incr = IntegerField(default=0)
    action_status = CharField(default="pending", choices=[
        "pending", "successful", "unsuccessful"])
    action_state = CharField(null=True, choices=[
        "ok", "y-budget-reached", "no-ack", "m-budget-reached", "d-budget-reached", "api-failure"])
    last_action_attempt = DateTimeField(
        default=datetime.datetime.now(), null=True)


class DeviceSimUsageInfo(BaseModel):
    id = PrimaryKeyField()
    org_id = CharField(null=True, index=True)
    group_id = IntegerField(null=True, index=True)
    device_id = IntegerField(null=True, index=True)
    sn = CharField(index=True)
    sim = CharField(null=True, choices=["A", "B"])
    polling_time = DateTimeField(default=datetime.datetime.now())
    enabled = BooleanField(null=True)
    limit = IntegerField(null=True)
    unit = CharField(null=True)
    used = IntegerField(null=True)
    consumption = IntegerField(null=True)
    expenditure = FloatField(null=True)
    last_recorded_country = CharField(null=True)

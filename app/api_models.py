from pydantic import BaseModel
from typing import Optional, List, Union
import datetime
import json

from app.config import AppConfig

config = AppConfig()


class UserAPIModel(BaseModel):
    class Config:
        orm_mode = True
    username: str
    password: str
    first_name: str | None = None
    last_name: str | None = None
    is_admin: bool | None = None
    disabled: bool | None = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class SchedulingFunction():
    class Config:
        arbitrary_types_allowed = True
    a_dummy_repeat_after_function = "a_dummy_repeat_after_function"
    a_dummy_daily_function = "a_dummy_daily_function"
    a_dummy_weekly_function = "a_dummy_weekly_function"
    a_dummy_bi_weekly_function = "a_dummy_bi_weekly_function"
    a_dummy_monthly_function = "a_dummy_monthly_function"


class SchedulingFrequency():
    class Config:
        arbitrary_types_allowed = True
    daily = "daily"
    weekly = "weekly"
    bi_weekly = "bi_weekly"
    monthly = "monthly"
    repeat_after = "repeat_after"


class DayOfWeek(BaseModel):
    monday = 0
    tuesday = 1
    wednesday = 2
    thursday = 3
    friday = 4
    saturday = 5
    sunday = 9

# class for how a scheduling config item should be


class SchedulingConfigItem(BaseModel):
    def __str__(self):
        obj = {
            "function": self.function,
            "frequency": self.frequency,
            "seconds": self.seconds,
            "scheduled_day_of_week": self.scheduled_day_of_week,
            "scheduled_time": self.scheduled_time,
            "scheduled_day_of_month": self.scheduled_day_of_month
        }
        return json.dumps(obj)
    function = SchedulingFunction.a_dummy_daily_function
    frequency = SchedulingFrequency.daily
    # for weekly and bi-weekly schedules
    scheduled_day_of_week: Optional[DayOfWeek]
    scheduled_day_of_month: Optional[int]  # for monthly schedules
    # for daily, weekly, bi-weekly, and monthly schedules
    scheduled_time: Optional[datetime.time]
    seconds: Optional[int]  # for repeat_after schedules


class AppConfig(BaseModel):
    init_param_1: Optional[int]
    init_param_2: Optional[int]
    init_param_3: Optional[int]
    scheduling_config: Optional[List[SchedulingConfigItem]]

    def initialize_config(self):
        self.init_param_1 = config.init_parameters["init_param_1"]
        self.init_param_2 = config.init_parameters["init_param_2"]
        self.init_param_3 = config.init_parameters["init_param_3"]
        sc = []
        for c in config.scheduling_config:
            sci = SchedulingConfigItem()
            sci.function = c["function"]
            sci.frequency = c["frequency"]
            if c["frequency"] == SchedulingFrequency.daily:
                sci.scheduled_time = c["scheduled_time"]
            if c["frequency"] == SchedulingFrequency.weekly or c["frequency"] == SchedulingFrequency.bi_weekly:
                sci.scheduled_day_of_week = c["scheduled_day_of_week"]
                sci.scheduled_time = c["scheduled_time"]
            if c["frequency"] == SchedulingFrequency.monthly:
                sci.scheduled_day_of_month = c["scheduled_day_of_month"]
                sci.scheduled_time = c["scheduled_time"]
            if c["frequency"] == SchedulingFrequency.repeat_after:
                sci.seconds = c["seconds"]
            sc.append(sci)
        self.scheduling_config = sc

    def set_config(self, config):
        if config.init_param_1 is not None:
            self.init_param_1 = config.init_param_1
        if config.init_param_2 is not None:
            self.init_param_2 = config.init_param_2
        if config.init_param_3 is not None:
            self.init_param_3 = config.init_param_3
        if config.scheduling_config is not None:
            self.scheduling_config = config.scheduling_config


class OrgAPIModel(BaseModel):
    class Config:
        orm_mode = True
    id: str
    name: Union[str, None]
    org_code: Union[str, None]
    primary: Union[bool, None]
    status: Union[str, None]
    branch_id: Union[int, None]
    url: Union[str, None]


class GroupAPIModel(BaseModel):
    class Config:
        orm_mode = True
    id: int
    name: str
    online_device_count: Union[int, None]
    offline_device_count: Union[int, None]
    client_count: Union[int, None]
    dev_client_count: Union[int, None]
    expiry_count: Union[int, None]
    expiry_soon_count: Union[int, None]
    group_type: Union[str, None]
    timezone: Union[str, None]
    country: Union[str, None]
    favorite: Union[bool, None]


class DeviceAPIModel(BaseModel):
    class Config:
        orm_mode = True
    id: int
    org_id: Union[str, None]
    group_id: Union[int, None]
    group_name: Union[str, None]
    sn: str
    name: str
    status: str
    product_id: Union[int, None]
    country: Union[str, None]
    first_appear: Union[datetime.datetime, None]
    expiry_date: Union[datetime.datetime, None]
    expired: Union[bool, None]
    uptime: Union[int, None]
    onlineStatus: Union[str, None]
    monthly_budget: Union[float, None]
    yearly_budget: Union[float, None]
    tuIncr: Union[int, None]
    dcStp: Union[int, None]
    wcStp: Union[int, None]
    tags: Union[list[str], None]
    sim1: Union[dict, None]
    sim2: Union[dict, None]
    sim1_summary: Union[str, None]
    sim2_summary: Union[str, None]
    both_sims_summary: Union[str, None]
    monthly_budget: Union[float, None]
    yearly_budget: Union[float, None]
    y_budget_start: Union[datetime.date, None]
    daily_stp: Union[int, None]
    weekly_stp: Union[int, None]
    topup_mb: Union[int, None]
    last_topup_attempt: Union[datetime.datetime, None]
    last_topup_status: Union[str, None]
    last_topup_state: Union[str, None]
    ratelist: Union[int, None]


class BudgetInfo(BaseModel):
    budget: float


class BudgetInfoAPIModel(BaseModel):
    class Config:
        orm_mode = True
    org_id: Union[str, None]
    group_id: int
    budget: float
    is_scheduled: bool
    config_time: Union[datetime.datetime, None]
    device_selection_tags: Union[list[str], None]


class BudgetStartInfoAPIModel(BaseModel):
    class Config:
        orm_mode = True
    org_id: str
    group_id: int
    start_date: datetime.date
    is_scheduled: bool
    config_time: Union[datetime.datetime, None]
    device_selection_tags: Union[list[str], None]


class STPInfoAPIModel(BaseModel):
    class Config:
        orm_mode = True
    org_id: str
    group_id: int
    max_stp: int
    is_scheduled: bool
    config_time: Union[datetime.datetime, None]
    device_selection_tags: Union[list[str], None]


class TopupInfoAPIModel(BaseModel):
    class Config:
        orm_mode = True
    org_id: str
    group_id: int
    topup_mb: int
    is_scheduled: bool
    config_time: Union[datetime.datetime, None]
    device_selection_tags: Union[list[str], None]


class RateListAPIModel(BaseModel):
    class Config:
        orm_mode = True
    id: int
    file_name: str
    is_active: bool
    tags: Union[str, None]
    uploaded_at: Union[datetime.datetime, None]
    is_scheduled: bool
    config_time: Union[datetime.datetime, None]
    status: Union[str, None]

from fastapi import Depends, FastAPI, Form, UploadFile, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_utils.tasks import repeat_every
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional, Annotated

import datetime as dt

from app.database import DatabaseConfig
from app.api_models import UserAPIModel, AppConfig, BudgetInfo, BudgetInfoAPIModel, BudgetStartInfoAPIModel, STPInfoAPIModel, TopupInfoAPIModel
from app.auth import get_current_active_user, get_auth_token, create_new_user, get_user_list, delete_user
from app.utils import Log as log, create_missing_dirs
from app.scheduled_task_manager import ScheduledTaskManager
from app.rate_list import RateList
from app.budget_topup_facade import BudgetAndTopupFacade

from app.peplink_api import PeplinkApi
from app.quota_service import AutomatedQuotaService

app = FastAPI()
api = PeplinkApi()
rl = RateList()
dc = DatabaseConfig()
batf = BudgetAndTopupFacade()
qs = AutomatedQuotaService()

# create missing folders if they don't exist
create_missing_dirs()

origins = [
    "http://localhost:3000",
    "https://quota-management-system.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# create tables if they don't exist
dc.create_tables()
dc.seed_data()

# initialize instance of WolfpackConfig
ac = AppConfig()
ac.initialize_config()

# Just for the sake of recording how much time it takes to do something
start = dt.datetime.now()
# do something
done = dt.datetime.now()
elapsed = done - start

log.event(
    "All instances created in {} seconds".format(elapsed.seconds))

# replacement of Celery Tasks
stm = ScheduledTaskManager()

log.event("app started")
print("app started", flush=True)


@app.get("/")
async def hello():
    return {"message": "AQMS API is listening..."}


@app.post("/users/create")
async def create_user(user: UserAPIModel):
    return create_new_user(user)


@app.post("/token")
async def get_token(data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    return get_auth_token(data.username, data.password)


@app.get("/users")
async def get_registered_users(current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    userlist = await get_user_list(current_user)
    return userlist


@app.delete("/users/{user_id}")
async def get_registered_users(user_id: int, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    userlist = await delete_user(current_user, user_id)
    return userlist


@app.get("/users/me")
async def read_users_me(current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return current_user


@app.get("/config")
async def get_config(current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return ac


# Shahbaz: todo: right now all of the posted config does not become effective
# need to make the posted config effected in all of the classes


@app.post("/config")
async def set_config(config: AppConfig, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    ac.set_config(config)
    return ac


@app.get("/orgs")
async def get_orgs(current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.get_orgs()


@app.get("/orgs/{org_id}")
async def get_org_detail(org_id: str, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.get_org_by_id(org_id)


@app.get("/orgs/{org_id}/groups")
async def get_org_groups(org_id: str, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.get_groups(org_id)


@app.get("/orgs/{org_id}/groups/{group_id}")
async def get_group_detail(org_id: str, group_id: int, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.get_group_by_id(org_id, group_id)


@app.get("/orgs/{org_id}/devices")
async def get_org_devices(org_id: str, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.get_devices(org_id)


@app.get("/orgs/{org_id}/devices/{dev_id}")
async def get_device_details(org_id: str, dev_id: str, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.get_device_details(org_id, dev_id)


@app.get("/orgs/{org_id}/groups/{group_id}/devices")
async def get_group_devices(org_id: str, group_id: int, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.get_devices_by_group(org_id, group_id)


@app.post("/orgs/{org_id}/devices/{dev_id}/tags")
async def update_device_tags(org_id: str, dev_id: int, tags: list[str], current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.update_device_tags(org_id, dev_id, tags)


@app.delete("/orgs/{org_id}/devices/{dev_id}/tags")
async def delete_device_tags(org_id: str, dev_id: int, tags: list[str], current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.delete_device_tags(org_id, dev_id, tags)


@app.post("/devices/{sn}/budget/monthly")
async def update_monthly_budget(sn: str, budget: BudgetInfo, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.update_budget(sn, budget, tenure="monthly")


@app.post("/devices/{sn}/budget/yearly")
async def update_yearly_budget(sn: str, budget: BudgetInfo, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.update_budget(sn, budget, tenure="yearly")


@app.post("/config/{sn}/budget/yearly")
async def update_yearly_budget(sn: str, budget: BudgetInfo, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return api.update_budget(sn, budget, tenure="yearly")


@app.get("/ratelists")
async def get_ratelists(current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return rl.get_ratelists()


@app.post("/ratelists")
async def upload_ratelist(current_user: Annotated[UserAPIModel, Depends(get_current_active_user)], file: UploadFile, is_scheduled: bool = Form(...), config_time: datetime = Form(...), tags: Optional[list[str]] = Form(None)):
    return rl.upload_ratelist(file, is_scheduled, config_time, tags)


@app.get("/ratelists/{ratelist_id}")
def download_ratelist(ratelist_id: int, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return rl.download_ratelist(ratelist_id)


@app.delete("/ratelists/{ratelist_id}")
async def delete_ratelist(ratelist_id: int, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return rl.delete_ratelist(ratelist_id)


@app.post("/budget-info/monthly")
async def add_monthly_budget_info(b: BudgetInfoAPIModel, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.add_budget_info(b, "monthly")


@app.post("/budget-info/yearly")
async def add_yearly_budget_info(b: BudgetInfoAPIModel, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.add_budget_info(b, "yearly")


@app.get("/budget-info/{org_id}")
async def get_monthly_budget_info_for_org(org_id: str, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.get_org_budget_info(org_id)


@app.get("/budget-info/{org_id}/{group_id}")
async def get_monthly_budget_info_for_group(org_id: str, group_id: int, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.get_group_budget_info(org_id, group_id)


@app.post("/budget-start-info")
async def add_budget_start_info(bs: BudgetStartInfoAPIModel, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.add_budget_start_info(bs)


@app.get("/budget-start-info/{org_id}")
async def get_monthly_budget_start_info_for_org(org_id: str, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.get_org_budget_start_info(org_id)


@app.get("/budget-start-info/{org_id}/{group_id}")
async def get_monthly_budget_start_info_for_group(org_id: str, group_id: int, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.get_group_budget_start_info(org_id, group_id)


@app.post("/stp-info/daily")
async def add_stp_info(si: STPInfoAPIModel, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.add_stp_info(si, "daily")


@app.post("/stp-info/weekly")
async def add_stp_info(si: STPInfoAPIModel, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.add_stp_info(si, "weekly")


@app.get("/stp-info/{org_id}")
async def get_stp_info_for_org(org_id: str, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.get_org_stp_info(org_id)


@app.get("/stp-info/{org_id}/{group_id}")
async def get_stp_info_for_group(org_id: str, group_id: int, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.get_group_stp_info(org_id, group_id)


@app.post("/topup-info")
async def add_topup_info(ti: TopupInfoAPIModel, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.add_topup_info(ti)


@app.get("/topup-info/{org_id}")
async def get_topup_info_for_org(org_id: str, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.get_org_topup_info(org_id)


@app.get("/topup-info/{org_id}/{group_id}")
async def get_topup_info_for_group(org_id: str, group_id: int, current_user: Annotated[UserAPIModel, Depends(get_current_active_user)]):
    return batf.get_group_topup_info(org_id, group_id)


# todo: remove this test call later
@app.get("/just-invoke")
async def invoke_function():
    # q1 = {"device_selection_tags": ["t1", "t2", "t3"]}
    # q2 = {"device_selection_tags": ["t2", "t4", "t3"]}
    # q3 = {"device_selection_tags": ["t1", "t3", "t4", "t5"]}
    # q4 = {"device_selection_tags": ["t1", "t6"]}
    # q5 = {"device_selection_tags": ["t3"]}
    # q6 = {"device_selection_tags": ["t3", "t4"]}
    # q7 = {"device_selection_tags": ["t2", "t6"]}
    # q8 = {"device_selection_tags": ["t1", "t4", "t5"]}
    # q = [q1, q2, q3, q4, q5, q6, q7, q8]
    # dt = {"tags": ["t1", "t5", "t4"]}
    # return qs.tally_device_tags(dt["tags"], q)

    # return rl.get_rate_for_country_code("AF")
    # return qs.check_if_new_month("process_devices")
    return qs.process_devices()
    #rl = RateList()
    #return rl.process_pending_ratelists()


@app.on_event("startup")
@repeat_every(seconds=30)
def invoke_scheduled_tasks() -> None:
    stm.invoke_scheduled_tasks(ac)

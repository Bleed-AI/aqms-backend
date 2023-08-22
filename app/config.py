import os
from pydantic import BaseSettings
from typing import Dict, List


class AppConfig(BaseSettings):
    init_parameters: dict = {
        "init_param_1": 1500,
        "init_param_2": 45,
        "init_param_3": 60
    }

    log_dir = os.getcwd() + "/data/log"
    ratelist_dir = os.getcwd() + "/data/ratelists"

    api_secret_key: str = "94ae0794944e63d2931a41875591768f9602f607676462f53bdd40212424fc3b"
    api_crypto_algo: str = "HS256"
    api_token_expires_mins: int = 90

    # frequency: daily, weekly, bi_weekly, monthly, repeat_after
    # daily: need to specify time
    # weekly, bi_weekly, and monthly: need to specify day and time
    # repeat_after: need to specify number of seconds
    scheduling_config: List = [
        {
            "function": "process_devices",
            "frequency": "repeat_after",
            "seconds": 60 * 45
        },
        {
            "function": "set_all_devices_to_1mb",
            "frequency": "monthly",
            "scheduled_day_of_month": 1,
            "scheduled_time": "00:00",
        },
        {
            "function": "process_pending_actions",
            "frequency": "repeat_after",
            "seconds": 30,
        },
        {
            "function": "process_scheduled_info_items",
            "frequency": "repeat_after",
            "seconds": 60 * 10
        },
        {
            "function": "process_pending_ratelists",
            "frequency": "repeat_after",
            "seconds": 60 * 1
        },
        # {
        #     "function": "refresh_all_devices",
        #     "frequency": "weekly",
        #     "scheduled_day_of_week": 7,
        #     "scheduled_time": "04:00"
        # },
        # {
        #     "function": "refresh_all_orgs",
        #     "frequency": "daily",
        #     "scheduled_time": "03:30"
        # },
        # {
        #     "function": "refresh_all_devices",
        #     "frequency": "daily",
        #     "scheduled_time": "04:30"
        # },
        # {
        #     "function": "refresh_all_devices",
        #     "frequency": "repeat_after",
        #     "seconds": 60 * 60
        # }
    ]
    ic_api_client_id: str = "2b0c7c8ef70cb2bd63a0095f6b2b1c78"
    ic_api_client_secret: str = "de545b8f6b8822444dcdd8c909160b46"


class ICApiUrls():
    base_url = "https://api.ic.peplink.com"
    get_token = "/api/oauth2/token"
    get_orgs = "/rest/o"
    get_org_detail = "/rest/o/{organization_id}"
    get_org_devices_basic = "/rest/o/{organization_id}/d/basic"
    get_org_devices = "/rest/o/{organization_id}/d"
    get_device_details = "/rest/o/{organization_id}/d/{device_id}"
    get_bandwidth_per_dev = "/rest/o/{organization_id}/bandwidth_per_device"
    add_del_device_tags = "/rest/o/{organization_id}/device_tags"
    get_add_groups = "/rest/o/{organization_id}/g"
    get_group_details = "/rest/o/{organization_id}/g/{group_id}"
    get_group_devices = "/rest/o/{organization_id}/g/{group_id}/d"
    get_group_devices_basic = "/rest/o/{organization_id}/g/{group_id}/d/basic"
    add_devices_in_group = "/rest/o/{organization_id}/g/{group_id}/add_devices"
    get_dev_bandwidth_in_group = "/rest/o/{organization_id}/g/{group_id}/add_devices"
    get_client_usage_summ_in_group = "/rest/o/{organization_id}/g/{group_id}/client_usage_summary"
    get_device_usage_info = "/rest/o/{organization_id}/g/{group_id}/d/{device_id}/devapi/status.wan.connection.allowance"
    set_device_sim_allowance = "/rest/o/{organization_id}/g/{group_id}/d/{device_id}/devapi/config.wan.connection"
    apply_device_config = "/rest/o/{organization_id}/g/{group_id}/d/{device_id}/devapi/cmd.config.apply"
    get_router_sim_conn_usage = "/rest/o/{organization_id}/g/{group_id}/d/{device_id}/sim_usages/monthly?start={start}&end={end}"


class DataPickleFiles():
    orgs_pickle_file = os.getcwd() + "/pickles/orgs.pickle"
    groups_pickle_file = os.getcwd() + "/pickles/groups.pickle"
    devices_pickle_file = os.getcwd() + "/pickles/devices.pickle"

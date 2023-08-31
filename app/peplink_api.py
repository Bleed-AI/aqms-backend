import sys
import inspect
import pandas as pd
from os.path import exists
from urllib.parse import urlparse
# chalk colors 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
from fastapi.exceptions import HTTPException
import pendulum

from app.utils import Log as log, nameprint, log_and_print_error
from app.utils import Singleton
from app.config import AppConfig, ICApiUrls
from app.db_models import Device, db
from app.api_models import DeviceAPIModel, GroupAPIModel
from app.peplink_core import PeplinkCore

config = AppConfig()
pepcore = PeplinkCore()


class PeplinkApi(metaclass=Singleton):
    def get_orgs(self):
        try:
            #print(ICApiUrls.get_orgs)
            result = pepcore.fetch_api_data(
                ICApiUrls.get_orgs)
            if "data" in result and type(result["data"] == list):
                return result["data"]
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in fetching orgs: {}".format(e))

    def get_org_by_id(self, org_id):
        try:
            result = pepcore.fetch_api_data(
                ICApiUrls.get_org_detail.format(organization_id=org_id))
            if "data" in result and type(result["data"] == object):
                return result["data"]
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in fetching org detail: {}".format(e))

    def get_groups(self, org_id):
        groups = []
        try:
            result = pepcore.fetch_api_data(
                ICApiUrls.get_add_groups.format(organization_id=org_id))
            if "data" in result and type(result["data"] == list):
                org_groups = result["data"]
                if len(org_groups) > 0:
                    for grp in org_groups:
                        new_grp = GroupAPIModel.parse_obj(grp)
                        groups.append(new_grp)
            return groups
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in fetching groups: {}".format(e))

    def get_group_by_id(self, org_id, group_id):
        try:
            result = pepcore.fetch_api_data(
                ICApiUrls.get_group_details.format(organization_id=org_id, group_id=group_id))
            if "data" in result and type(result["data"] == object):
                group = result["data"]
                new_group = GroupAPIModel.parse_obj(group)
                return new_group
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in fetching group info: {}".format(e))

    def get_devices(self, org_id):
        devices = []
        try:
            result = pepcore.fetch_api_data(
                ICApiUrls.get_org_devices.format(organization_id=org_id))
            if "data" in result and type(result["data"] == list):
                org_devs = result["data"]
                if len(org_devs) > 0:
                    tally_devices = self.tally_devices_with_db(
                        org_id, 0, org_devs, True)
                    for dev in tally_devices:
                        new_dev = DeviceAPIModel.parse_obj(dev)
                        devices.append(new_dev)
                    return devices
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in get_devices: {}".format(e))

    def get_device_details(self, org_id, dev_id):
        try:
            result = pepcore.fetch_api_data(
                ICApiUrls.get_device_details.format(organization_id=org_id, device_id=dev_id))
            if "data" in result and type(result["data"] == object):
                api_dev = result["data"]
                db_dev = Device.get(Device.sn == api_dev["sn"])
                if db_dev and db_dev.sn == api_dev["sn"]:
                    api_dev["id"] = db_dev.id
                    api_dev["sn"] = db_dev.sn
                    api_dev["org_id"] = db_dev.org_id
                    api_dev["group_id"] = db_dev.group_id
                    api_dev["monthly_budget"] = db_dev.monthly_budget
                    api_dev["yearly_budget"] = db_dev.yearly_budget
                    api_dev["tuIncr"] = db_dev.tuIncr
                    api_dev["dcStp"] = db_dev.dcStp
                    api_dev["wcStp"] = db_dev.wcStp
                    dev = DeviceAPIModel.parse_obj(api_dev)
                    return dev
                else:
                    raise HTTPException(204, detail="Could not find device.")
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in fetching device details: {}".format(e))

    def get_devices_by_group(self, org_id, group_id, is_background_processing=False):
        print ("get_devices_by_group")
        devices = []
        try:
            print ("get_devices_by_group 1")
            result = pepcore.fetch_api_data(
                ICApiUrls.get_group_devices.format(organization_id=org_id, group_id=group_id))
            if "data" in result and type(result["data"] == list):
                group_devs = result["data"]
                total=0
                if group_devs is not None and len(group_devs) > 0:

                    tally_devices = self.tally_devices_with_db(
                        org_id, group_id, group_devs, False)
                    if tally_devices is not None and type(tally_devices) == list and len(tally_devices) > 0:
                        for dev in tally_devices:
                            total = total + 1
                            dev["org_id"] = org_id
                            new_dev = DeviceAPIModel.parse_obj(dev)
                            if is_background_processing:
                                if dev['monthly_budget'] > 0.1 and dev['yearly_budget'] > 0.1 and dev['dcStp'] < dev['daily_stp'] and dev['wcStp'] < dev['weekly_stp'] and dev['status'] == 'online':
                                    sim1_usage = 0
                                    sim2_usage = 0
                                    usage_info = self.get_router_sim_conn_usage(
                                        org_id, group_id, new_dev.id)
                                    print(dev['sn'])
                                    if dev['sn'] == '293B-8BD6-5C78':
                                        print(usage_info)
                                    if usage_info is not None and len(usage_info) > 0:
                                        for info in usage_info:
                                            if info["sim"] == 1:
                                                sim1_usage = info["usage"]
                                            if info["sim"] == 2:
                                                sim2_usage = info["usage"]
                                    usage_info = self.get_router_wan_conn_usage(
                                        org_id, group_id, new_dev.id)
                                    if dev['sn'] == '293B-8BD6-5C78':
                                        print(usage_info)
                                    if usage_info is not None and type(usage_info) == dict:
                                        if "1" in usage_info and type(usage_info["1"]) == dict:
                                            new_dev.sim1 = usage_info["1"]
                                            new_dev.sim1["usage_kb"] = sim1_usage
                                        if "2" in usage_info and type(usage_info["2"]) == dict:
                                            new_dev.sim2 = usage_info["2"]
                                            new_dev.sim2["usage_kb"] = sim2_usage
                            devices.append(new_dev)
                            # #break the loop and return devices if total is 5
                            # if total == 5:
                            #     break
                            print (total, "get_devices_by_group total")
                    return devices
        except Exception as e:
            print(e,"get_devices_by_group 2")
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in get_devices_by_group: {}".format(e))

    def tally_devices_with_db(self, org_id, group_id, devices, org_devs_only=False):
        try:
            for device in devices:
                Device.insert(
                    id=device["id"] if "id" in device else None,
                    sn=device["sn"] if "sn" in device else None,
                    org_id=org_id,
                    group_id=group_id,
                    tags=device["tags"] if "tags" in device else None
                ).on_conflict(
                    conflict_target=(Device.sn,),
                    update={Device.group_id: group_id,
                            Device.tags: device["tags"]
                            if "tags" in device else None}
                ).execute()
            db_devs = Device.select().where(Device.org_id == org_id) if org_devs_only else Device.select(
            ).where(Device.org_id == org_id, Device.group_id == group_id)
            for dev in db_devs:
                match_devs = [
                    device for device in devices if device["sn"] == dev.sn]
                if len(match_devs) > 0:
                    match_dev = match_devs[0]
                    match_dev["id"] = dev.id
                    match_dev["sn"] = dev.sn
                    match_dev["org_id"] = dev.org_id
                    match_dev["group_id"] = dev.group_id
                    match_dev["monthly_budget"] = dev.monthly_budget
                    match_dev["yearly_budget"] = dev.yearly_budget
                    match_dev["tuIncr"] = dev.tuIncr
                    match_dev["dcStp"] = dev.dcStp
                    match_dev["wcStp"] = dev.wcStp
                    match_dev["y_budget_start"] = dev.y_budget_start
                    match_dev["daily_stp"] = dev.daily_stp
                    match_dev["weekly_stp"] = dev.weekly_stp
                    match_dev["topup_mb"] = dev.topup_mb
                    match_dev["last_topup_status"] = dev.last_topup_status
                    match_dev["last_topup_state"] = dev.last_topup_state
                    match_dev["last_topup_attempt"] = dev.last_topup_attempt
                    match_dev["sim1_summary"] = dev.sim1_summary
                    match_dev["sim2_summary"] = dev.sim2_summary
                    match_dev["both_sims_summary"] = dev.both_sims_summary
                    match_dev["country"] = dev.country
                    match_dev["tags"] = dev.tags
                    match_dev["ratelist"] = dev.ratelist
            return devices
        except Exception as e:
            print (e)
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in tally_devices_with_db: {}".format(e))

    def update_device_tags(self, org_id, dev_id, tags):
        try:
            data = {
                "data": {
                    "device_ids": [dev_id],
                    "tag_names": tags
                }
            }
            result = pepcore.put_api_data(
                ICApiUrls.add_del_device_tags.format(organization_id=org_id), data)
            if result and "resp_code" in result:
                return result
            else:
                return "Could not update tags for the device"
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in updating device tags: {}".format(e))

    def delete_device_tags(self, org_id, dev_id, tags):
        try:
            data = {
                "data": {
                    "device_ids": [dev_id],
                    "tag_names": tags
                }
            }
            result = pepcore.delete_api_data(
                ICApiUrls.add_del_device_tags.format(organization_id=org_id), data)
            if result and "resp_code" in result:
                return result
            else:
                return "Could not update tags for the device"
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in deleting device tags: {}".format(e))

    def update_budget(self, sn, budget, **kwargs):
        try:
            tenure = kwargs["tenure"]
            device = Device.get(Device.sn == sn)
            if tenure == "monthly":
                device.monthly_budget = budget.budget
            if tenure == "yearly":
                device.yearly_budget = budget.budget
            device.save()
            return device
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in updating device budget: {}".format(e))

    def get_router_wan_conn_usage(self, org_id, group_id, device_id):
        try:
            result = pepcore.fetch_api_data(
                ICApiUrls.get_device_usage_info.format(organization_id=org_id, group_id=group_id, device_id=device_id))
            if result is not None and "resp_code" in result and result["resp_code"] == "SUCCESS" and "data" in result and type(result["data"]) == dict:
                data = result["data"]
                if data and "stat" in data and "response" in data and data["stat"] == "ok":
                    response = data["response"]
                    if "2" in response and type(response["2"]) == dict:
                        sims_info = response["2"]
                        if "1" in sims_info and "2" in sims_info:
                            return sims_info
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in fetching device usage status: {}".format(e))

    def get_router_sim_conn_usage(self, org_id, group_id, device_id):
        start = pendulum.now().start_of("month").strftime("%Y-%m-%d")
        end = pendulum.now().end_of("month").strftime("%Y-%m-%d")
        try:
            usage = []
            result = pepcore.fetch_api_data(
                ICApiUrls.get_router_sim_conn_usage.format(organization_id=org_id, group_id=group_id, device_id=device_id, start=start, end=end))
            if result is not None and "resp_code" in result and result["resp_code"] == "SUCCESS" and "data" in result:
                data = result["data"]
                if data is not None and type(data) == list and len(data) > 0:
                    for item in data:
                        if item is not None and type(item) == dict and "tx" in item and "rx" in item and "slot" in item:
                            usage.append({
                                "sim": item["slot"],
                                "usage": item["tx"] + item["rx"]
                            })
            if len(usage) > 0:
                return usage
            else:
                return None
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in get_router_sim_conn_usage: {}".format(e))

    def set_allowance_on_device_sim(self, org_id, group_id, device_id, sim, allowance):
        try:
            data = {
                "action": "update",
                "list": [
                    {
                        "id": 2,
                        "cellular": {
                            "sim": [
                                {
                                    "id": 1 if sim == "A" else 2,
                                    "bandwidthAllowanceMonitor": {
                                        "enable": True,
                                        "action": ["restrict"],
                                        "start": 0,
                                        "monthlyAllowance": {
                                            "value": allowance,
                                            "unit": "MB"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            result = pepcore.post_api_data(
                ICApiUrls.set_device_sim_allowance.format(organization_id=org_id, group_id=group_id, device_id=device_id), data, "text/plain")
            if result and "resp_code" in result:
                # todo: check in detail if response is a success
                log.event("{}MB allowance set for org: {}, group: {}, device: {}, sim: {}".format(
                    allowance, org_id, group_id, device_id, sim))
                res = self.apply_config_on_device(org_id, group_id, device_id)
                if res and "resp_code" in result:
                   return True
                return False
            else:
                return False
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in setting allowance on device: {}".format(e))

    def apply_config_on_device(self, org_id, group_id, device_id):
        try:
            data = {}
            result = pepcore.post_api_data(
                ICApiUrls.apply_device_config.format(organization_id=org_id, group_id=group_id, device_id=device_id), data, "text/plain")
            if result and "resp_code" in result:
                # todo: check in detail if response is a success
                log.event("Apply config executed for org: {}, group: {}, device: {}".format(
                    org_id, group_id, device_id))
                return result
            else:
                return "Could not apply config on device"
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            pepcore.raise_and_print_error(
                "Exception in applying device configuration: {}".format(e))

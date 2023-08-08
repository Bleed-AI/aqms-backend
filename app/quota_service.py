import os
import sys
import datetime
from peewee import *
import json
import pendulum
import threading

from app.peplink_api import PeplinkApi
from app.db_models import db, BudgetInfo, BudgetStartInfo, STPInfo, TopupInfo, DeviceSimUsageInfo, Device, ScheduledActions, ScheduledFunctionLog
from app.utils import Log as log, nameprint, Print as p
from app.utils import Singleton, intersection
from app.rate_list import RateList

api = PeplinkApi()
rl = RateList()


class AutomatedQuotaService(metaclass=Singleton):
    def process_devices(self):
        try:
            orgs = api.get_orgs()
            if orgs is not None and len(orgs) > 0:
                log.event(
                    "process_devices: Got {} orgs from API.".format(len(orgs)))
                for org in orgs:
                    groups = api.get_groups(org["id"])
                    if groups is not None and len(groups) > 0:
                        log.event(
                            "process_devices: Got {} groups from API.".format(len(groups)))
                        for group in groups:
                            devices = api.get_devices_by_group(
                                org["id"], group.id, True)
                            if devices is not None and len(devices) > 0:
                                log.event(
                                    "process_devices: Got {} devices from API.".format(len(devices)))
                                # tally and save devices to db
                                dict_devs = [device.dict()
                                             for device in devices]
                                api.tally_devices_with_db(
                                    org["id"], group.id, dict_devs, False)
                                log.event("process_devices: Total devices for group {} are {}.".format(
                                    group.id, len(devices)))
                                for device in devices:
                                    log.event(
                                        "process_devices: device {} onlineStatus: {}.".format(device.id, device.onlineStatus))
                                    if device.onlineStatus == "ONLINE":
                                        if device is not None and device.sim1 is not None and "enable" in device.sim1 and device.sim1["enable"] == True:
                                            # sim1 is enabled for this device. we can process sim allowances
                                            log.event("process_devices: compute_usage_info for device {} sim A usage {}".format(
                                                device.id, device.sim1))
                                            self.compute_usage_info(
                                                org["id"], group, device, "A")
                                            log.event("process_devices: process_sim_allowances for device {} sim A usage {}".format(
                                                device.id, device.sim1))
                                            self.process_sim_allowances(
                                                org["id"], group, device, "A", device.sim1)
                                            log.event("process_devices: compute_usage_info again for device {} sim A usage {}".format(
                                                device.id, device.sim1))
                                            self.compute_usage_info(
                                                org["id"], group, device, "A")
                                        if device is not None and device.sim2 is not None and "enable" in device.sim2 and device.sim2["enable"] == True:
                                            # sim2 is enabled for this device. we can process sim allowances
                                            log.event("process_devices: compute_usage_info for device {} sim B usage {}".format(
                                                device.id, device.sim2))
                                            self.compute_usage_info(
                                                org["id"], group, device, "B")
                                            log.event("process_devices: process_sim_allowances for device {} sim B usage {}".format(
                                                device.id, device.sim2))
                                            self.process_sim_allowances(
                                                org["id"], group, device, "B", device.sim2)
                                            log.event("process_devices: compute_usage_info again for device {} sim B usage {}".format(
                                                device.id, device.sim2))
                                            self.compute_usage_info(
                                                org["id"], group, device, "B")

                                        # with summary computed for individual device, compute summary for both devices, if both devices are enabled
                                        if device is not None and device.sim1 is not None and device.sim2 is not None and "enable" in device.sim1 and "enable" in device.sim2 and device.sim1["enable"] == True and device.sim2["enable"] == True:
                                            self.compute_summary_for_both_sims(
                                                org["id"], group.id, device.id)
                                    else:
                                        log.event(
                                            "Device sn {} is offline. Moving on to next device, if any.".format(device.sn))
                            else:
                                log.event(
                                    "No devices found for group {}.".format(group))
                    else:
                        log.event(
                            "No groups found for organization {}".format(org["id"]))
            else:
                log.event("Didn't find any orgs".format(org["id"]))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            log.error(
                "Exception in process_devices: type: {}, file: {}, line: {}, detail: {}".format(exc_type, fname, exc_tb.tb_lineno, e))

    def process_sim_allowances(self, org_id, group, device, sim, sim_usage):
        log.event("process_sim_allowances: org_id: {}, group: {}, device: {}, sim: {}, sim_usage: {}".format(
            org_id, group, device, sim, sim_usage))
        try:
            # some verification of a few fields, just to confirm if dict is right
            if type(sim_usage) == dict and "enable" in sim_usage and "limit" in sim_usage:
                # pull important variables for both sims
                enabled = sim_usage["enable"] if "enable" in sim_usage else None
                limit = sim_usage["limit"] if "limit" in sim_usage else None
                unit = sim_usage["unit"] if "unit" in sim_usage else None
                consumption = sim_usage["usage_kb"] if "usage_kb" in sim_usage else None
                # because usage is recorded in KBs and we are using MBs
                consumption = consumption / 1024 if consumption != 0 else 0
                percent = sim_usage["percent"] if "percent" in sim_usage else None
                log.event("process_sim_allowances: enabled: {}, limit: {}, unit: {}, consumption: {}, percent: {}".format(
                    enabled, limit, unit, consumption, percent))
                last_usage_info = DeviceSimUsageInfo.select().where(
                    DeviceSimUsageInfo.org_id == org_id,
                    DeviceSimUsageInfo.group_id == group.id,
                    DeviceSimUsageInfo.device_id == device.id,
                    DeviceSimUsageInfo.sim == sim,
                    DeviceSimUsageInfo.polling_time.month == datetime.datetime.now().month
                ).order_by(DeviceSimUsageInfo.polling_time.desc()).limit(1)
                expenditure = 0
                new_consumption = 0
                if last_usage_info is not None and len(last_usage_info) > 0 and device.ratelist > 0:
                    for u in last_usage_info:
                        log.event("process_sim_allowances: last_usage_info-{}: limit: {}, used: {}, consumption: {}, expenditure: {}.".format(
                            device.id, u.limit, u.used, u.consumption, u.expenditure))
                    last_usage_info = last_usage_info[0]
                    new_consumption = consumption - last_usage_info.used
                    log.event("process_sim_allowances: last_usage_info-{}: new_consumption: {}, consumption: {}, last_usage_info.used: {}, group country: {}.".format(
                        device.id, new_consumption, consumption, last_usage_info.used, group.country))
                    expenditure = new_consumption * \
                        rl.get_rate_for_country_code(
                            device.id, device.ratelist, group.country)
                log.event(
                    "process_sim_allowances: last_usage_info-{}: {}".format(device.id, last_usage_info))
                log.event("process_sim_allowances: expenditure: {}, new_consumption: {}".format(
                    expenditure, new_consumption))
                curr_usage_info = DeviceSimUsageInfo.create(
                    org_id=org_id,
                    group_id=group.id,
                    device_id=device.id,
                    sn=device.sn,
                    sim=sim,
                    polling_time=datetime.datetime.now(),
                    enabled=enabled,
                    limit=limit,
                    unit=unit,
                    used=consumption,
                    consumption=new_consumption,
                    expenditure=expenditure,
                    last_recorded_country=group.country)
                log.event("process_sim_allowances: curr_usage_info: {}".format(
                    curr_usage_info))
                # if consumption has rached 100%
                percent_consumption = consumption / limit * 100
                log.event("process_sim_allowances: percent_consumption = {}".format(
                    percent_consumption))
                print("process_sim_allowances: process sim allowance for device {}, sim: {}".format(
                    device.id, sim))
                # if percent_consumption > 99.999:
                if percent_consumption > 99:
                    log.event("process_sim_allowances: utilization exceeds 100 percent for device {}, sim {}, checking if topup is already in progress".format(
                        device.id, sim))
                    pending_allowance_reset = ScheduledActions.select().where(
                        ScheduledActions.org_id == org_id,
                        ScheduledActions.group_id == group.id,
                        ScheduledActions.device_id == device.id,
                        ScheduledActions.sn == device.sn,
                        ScheduledActions.sim == sim,
                        ScheduledActions.action_type == "monthly_allowance_reset",
                        ScheduledActions.action_status == "pending",
                        ScheduledActions.last_action_attempt.month == datetime.datetime.now().month
                    ).limit(1)
                    if pending_allowance_reset is not None and len(pending_allowance_reset) > 0:
                        # There is at least one record but it's pending. We need to log and skip.
                        # We should wait for other scheduled function to reset monthly allowance.
                        log.event("process_sim_allowances: monthly allowance for device {} sim {} isn't set yet.".format(
                            device.sn, sim))
                    else:
                        # check if there is some pending topup action already in database
                        pending_topup = ScheduledActions.select().where(
                            ScheduledActions.org_id == org_id,
                            ScheduledActions.group_id == group.id,
                            ScheduledActions.device_id == device.id,
                            ScheduledActions.sn == device.sn,
                            ScheduledActions.sim == sim,
                            ScheduledActions.action_type == "topup",
                            ScheduledActions.action_status == "pending",
                            ScheduledActions.last_action_attempt.month == datetime.datetime.now().month
                        ).limit(1)
                        if pending_topup is not None and len(pending_topup) > 0:
                            log.event("process_sim_allowances: there is a pending topup for device {} sim {}. Skipping for now.".format(
                                device.sn, sim))
                        else:
                            # we need to decide if we can topup this device sim or not, based on various factors
                            log.event("process_sim_allowances: no pending topup for device {} sim {}. Going to determine if can topup.".format(
                                device.sn, sim))
                            self.process_topup_as_per_restrictions(
                                org_id, group, device, sim, sim_usage)
                else:
                    log.event("Usage for device {} sim {} hasn't reached 100%. Skipping it.".format(
                        device.id, sim))
        except Exception as e:
            log.error(
                "Exception in executing process_sim_allowances: {}".format(e))

    def compute_usage_info(self, org_id, group, device, sim):
        now = datetime.datetime.now()
        month_start = datetime.datetime(now.year, now.month, 1)
        year_start = datetime.datetime(now.year, 1, 1)
        log.event("compute_usage_info for org: {}, group: {}, device: {}, sim: {}".format(
            org_id, group.id, device.id, sim))
        try:
            mtd = DeviceSimUsageInfo.select(
                DeviceSimUsageInfo.sn,
                fn.Sum(DeviceSimUsageInfo.consumption).alias(
                    "total_consumption"),
                fn.Sum(DeviceSimUsageInfo.expenditure).alias("total_expenditure")).where(
                    DeviceSimUsageInfo.org_id == org_id,
                    DeviceSimUsageInfo.group_id == group.id,
                    DeviceSimUsageInfo.device_id == device.id,
                    DeviceSimUsageInfo.sim == sim,
                    DeviceSimUsageInfo.polling_time >= month_start,
                    DeviceSimUsageInfo.polling_time <= now
            ).group_by(DeviceSimUsageInfo.sn)
            log.event("compute_usage_info: mtd query: {}".format(mtd))
            sn = ""
            total_consumption = 0
            total_expenditure = 0
            for item in mtd:
                sn = item.sn
                total_consumption = item.total_consumption
                total_expenditure = item.total_expenditure
            summary_mtd = {
                "sn": sn,
                "total_consumption": total_consumption,
                "total_expenditure": total_expenditure,
            }
            log.event("compute_usage_info: summary_mtd: {}.".format(summary_mtd))
            ytd = DeviceSimUsageInfo.select(
                DeviceSimUsageInfo.sn,
                fn.Sum(DeviceSimUsageInfo.consumption).alias(
                    "total_consumption"),
                fn.Sum(DeviceSimUsageInfo.expenditure).alias("total_expenditure")).where(
                    DeviceSimUsageInfo.org_id == org_id,
                    DeviceSimUsageInfo.group_id == group.id,
                    DeviceSimUsageInfo.device_id == device.id,
                    DeviceSimUsageInfo.sim == sim,
                    DeviceSimUsageInfo.polling_time >= year_start,
                    DeviceSimUsageInfo.polling_time <= now
            ).group_by(DeviceSimUsageInfo.sn)
            log.event("compute_usage_info: ytd query: {}".format(ytd))
            for item in ytd:
                sn = item.sn
                total_consumption = item.total_consumption
                total_expenditure = item.total_expenditure
            summary_ytd = {
                "sn": sn,
                "total_consumption": total_consumption,
                "total_expenditure": total_expenditure,
            }
            log.event("compute_usage_info: summary_ytd: {}.".format(summary_ytd))
            summary = {
                "timestamp": datetime.datetime.now(),
                "sn": sn,
                "country": group.country,
                "mtd_data": summary_mtd["total_consumption"],
                "mtd_expenditure": summary_mtd["total_expenditure"],
                "ytd_data": summary_ytd["total_consumption"],
                "ytd_expenditure": summary_ytd["total_expenditure"]
            }
            log.event("compute_usage_info: summary: {}.".format(summary))
            db_dev = Device.select().where(Device.org_id == org_id, Device.group_id ==
                                           group.id, Device.id == device.id)
            if db_dev is not None and len(db_dev) > 0:
                db_dev = db_dev[0]
                if db_dev is not None and db_dev.id > 0:
                    db_dev.country = group.country
                    if sim == "A":
                        db_dev.sim1_summary = json.dumps(
                            summary, default=str) if summary is not None else None
                    if sim == "B":
                        db_dev.sim2_summary = json.dumps(
                            summary, default=str) if summary is not None else None
                    db_dev.save()
        except Exception as e:
            log.error(
                "Exception in compute_usage_info: {}".format(e))

    def compute_summary_for_both_sims(self, org_id, group_id, device_id):
        log.event("compute_summary_for_both_sims: org_id: {}, group_id: {}, device_id: {}.".format(
            org_id, group_id, device_id))
        try:
            dev = Device.get(Device.org_id == org_id,
                             Device.group_id == group_id, Device.id == device_id)
            if dev is not None:
                sim1_summary = json.loads(dev.sim1_summary)
                sim2_summary = json.loads(dev.sim2_summary)
                log.event("compute_summary_for_both_sims: sim1_summary: {}, sim2_summary: {}.".format(
                    sim1_summary, sim2_summary))
                if sim1_summary != 'null' and sim2_summary != 'null':
                    dev.both_sims_summary = json.dumps({
                        "timestamp": datetime.datetime.now(),
                        "sn": sim1_summary["sn"],
                        "country": sim1_summary["country"],
                        "mtd_data": sim1_summary["mtd_data"] + sim2_summary["mtd_data"],
                        "mtd_expenditure": sim1_summary["mtd_expenditure"] + sim2_summary["mtd_expenditure"],
                        "ytd_data": sim1_summary["ytd_data"] + sim2_summary["ytd_data"],
                        "ytd_expenditure": sim1_summary["ytd_expenditure"] + sim2_summary["ytd_expenditure"],
                    }, default=str)
                elif sim1_summary != 'null' and sim2_summary == 'null':
                    dev.both_sims_summary = dev.sim1_summary
                elif sim1_summary == 'null' and sim2_summary != 'null':
                    dev.both_sims_summary = dev.sim2_summary
                else:
                    dev.both_sims_summary = None
                # finally save the record back to db
                dev.save()
                log.event(
                    "compute_summary_for_both_sims: both dev summary saved in db: {}.".format(dev.both_sims_summary))
        except Exception as e:
            log.error(
                "Exception in compute_summary_for_both_sims: " + str(e))
            print("{}".format(e))

    def set_all_devices_to_1mb(self):
        try:
            orgs = api.get_orgs()
            if orgs is not None and len(orgs) > 0:
                log.event("-- Got {} orgs from API.".format(len(orgs)))
                for org in orgs:
                    groups = api.get_groups(org["id"])
                    if groups is not None and len(groups) > 0:
                        log.event(
                            "-- Got {} groups from API.".format(len(groups)))
                        for group in groups:
                            devices = api.get_devices_by_group(
                                org["id"], group.id)
                            if devices is not None and len(devices) > 0:
                                log.event(
                                    "-- Got {} devices from API.".format(len(devices)))
                                for device in devices:
                                    # todo: if buget is set to 0.1, skip the device
                                    if device.yearly_budget == 0.1 or device.monthly_budget == 0.1:
                                        continue
                                    if device.onlineStatus == "ONLINE":
                                        if device is not None and device.sim1 is not None and "enable" in device.sim1 and device.sim1["enable"] == True:
                                            # sim1 is enabled for this device. we can set it to 1mb
                                            ScheduledActions.create(
                                                org_id=org["id"],
                                                group_id=group.id,
                                                device_id=device.id,
                                                sn=device.sn,
                                                sim="A",
                                                action_type="monthly_allowance_reset",
                                                action_status="pending")
                                        if device is not None and device.sim2 is not None and "enable" in device.sim2 and device.sim2["enable"] == True:
                                            # sim2 is enabled for this device. we can set it to 1mb
                                            ScheduledActions.create(
                                                org_id=org["id"],
                                                group_id=group.id,
                                                device_id=device.id,
                                                sn=device.sn,
                                                sim="B",
                                                action_type="monthly_allowance_reset",
                                                action_status="pending")
                                    else:
                                        log.event(
                                            "Device sn {} is offline. Moving on to next device, if any.".format(device.sn))
                            else:
                                log.event(
                                    "No devices found for group {}.".format(group))
        except Exception as e:
            log.error(
                "Exception in set_all_devices_to_1mb: {}".format(e))

    def process_topup_as_per_restrictions(self, org_id, group, device, sim, sim_usage):
        log.event("process_topup_as_per_restrictions: org_id: {}, group: {}, device: {}, sim: {}, sim_usage: {}".format(
            org_id, group, device, sim, sim_usage))
        try:
            now = datetime.datetime.now()
            month_start = pendulum.now().start_of("month")
            year_start = pendulum.now().start_of("year")
            if device is not None and device.id > 0:
                monthly_budget = device.monthly_budget
                yearly_budget = device.yearly_budget
                budget_start = device.y_budget_start
                daily_stp = device.daily_stp
                weekly_stp = device.weekly_stp
                topup_mb = device.topup_mb

                log.event("process_topup_as_per_restrictions: monthly_budget: {}, yearly_budget: {}, budget_start: {}, daily_stp: {}, weekly_stp: {}, topup_mb: {}.".format(
                    monthly_budget, yearly_budget, budget_start, daily_stp, weekly_stp, topup_mb))

                total_mtd_consumption = 0
                total_mtd_expense = 0
                total_ytd_consumption = 0
                total_ytd_expense = 0

                dev = Device.get(
                    Device.org_id == org_id, Device.group_id == group.id, Device.id == device.id)

                mtd_spent = DeviceSimUsageInfo.select(
                    DeviceSimUsageInfo.sn,
                    fn.Sum(DeviceSimUsageInfo.consumption).alias(
                        "mtd_consumption"),
                    fn.Sum(DeviceSimUsageInfo.expenditure).alias("mtd_expenditure")).where(
                        DeviceSimUsageInfo.org_id == org_id,
                        DeviceSimUsageInfo.group_id == group.id,
                        DeviceSimUsageInfo.device_id == device.id,
                        DeviceSimUsageInfo.polling_time >= month_start,
                        DeviceSimUsageInfo.polling_time <= now
                ).group_by(DeviceSimUsageInfo.sn)
                log.event(
                    "process_topup_as_per_restrictions: mtd_spent: {}.".format(mtd_spent))
                for item in mtd_spent:
                    total_mtd_consumption = item.mtd_consumption
                    total_mtd_expense = item.mtd_expenditure
                log.event("process_topup_as_per_restrictions: total_mtd_consumption: {}, total_mtd_expense: {}.".format(
                    total_mtd_consumption, total_mtd_expense))

                ytd_spent = DeviceSimUsageInfo.select(
                    DeviceSimUsageInfo.sn,
                    fn.Sum(DeviceSimUsageInfo.consumption).alias(
                        "total_ytd_consumption"),
                    fn.Sum(DeviceSimUsageInfo.expenditure).alias("total_ytd_expenditure")).where(
                        DeviceSimUsageInfo.org_id == org_id,
                        DeviceSimUsageInfo.group_id == group.id,
                        DeviceSimUsageInfo.device_id == device.id,
                        DeviceSimUsageInfo.sim == sim,
                        DeviceSimUsageInfo.polling_time >= year_start,
                        DeviceSimUsageInfo.polling_time <= now
                ).group_by(DeviceSimUsageInfo.sn)
                log.event(
                    "process_topup_as_per_restrictions: ytd_spent: {}.".format(mtd_spent))
                for item in ytd_spent:
                    total_ytd_consumption = item.total_ytd_consumption
                    total_ytd_expense = item.total_ytd_expenditure
                log.event("process_topup_as_per_restrictions: total_ytd_consumption: {}, total_ytd_expense: {}.".format(
                    total_ytd_consumption, total_ytd_expense))

                # check if effective monthly or yearly budget is 0
                if monthly_budget != 0 and total_mtd_expense >= monthly_budget:
                    # unlimited monthly budget is not set, and expense exceeds monthly budget
                    # let the user know via email
                    log.event(
                        "Monthly budget exceeded on device sn {}.".format(device.sn))
                    dev.last_topup_status = "unsuccessful"
                    dev.last_topup_state = "m-budget-reached"
                    dev.last_topup_attempt = now
                elif monthly_budget == 0 or total_mtd_expense < monthly_budget:
                    if monthly_budget == 0:
                        log.event(
                            "Monthly budget set to unlimited on device sn {}.".format(device.sn))
                    # either monthly budget is set to zero, or monthly limit not reached yet
                    # we need to check for yearly budget
                    if yearly_budget != 0 and total_ytd_expense >= yearly_budget:
                        # unlimited yearly budget is not set, and expense exceeds yearly budget
                        # todo: let the user know via email
                        log.event(
                            "Yearly budget exceeded on device sn {}.".format(device.sn))
                        dev.last_topup_status = "unsuccessful"
                        dev.last_topup_state = "y-budget-reached"
                        dev.last_topup_attempt = now
                    elif yearly_budget == 0 or total_ytd_expense < yearly_budget:
                        if yearly_budget == 0:
                            log.event(
                                "Yearly budget set to unlimited on device sn {}.".format(device.sn))
                        # either monthly budget is set to zero, or monthly limit not reached yet
                        # check if intended topup is going beyond budget limit
                        rem_budget = dev.monthly_budget - total_mtd_expense
                        rate = rl.get_rate_for_country_code(
                            device.id, group.country)
                        if yearly_budget != 0 and dev.topup_mb * rate > rem_budget:
                            # going beyond limit, can't topup device
                            log.event(
                                "Intended topup going beyond monthly limit on device sn {}.".format(device.sn))
                            dev.last_topup_status = "unsuccessful"
                            dev.last_topup_state = "m-budget-reached"
                            dev.last_topup_attempt = now
                        else:
                            # check if daily successful stp counter < daily stp limit
                            # get daily successful topup counter
                            dstpc = self.get_successful_topup_counter(
                                org_id, group.id, device.id, "daily")
                            if dstpc < daily_stp:
                                # we can go ahead and check if weekly limit reached
                                # get weekly successful topup counter
                                wstpc = self.get_successful_topup_counter(
                                    org_id, group.id, device.id, "weekly")
                                log.event("process_topup_as_per_restrictions wstpc: {}, ewstp.max_stp: {}".format(
                                    wstpc, weekly_stp))
                                if wstpc < weekly_stp:
                                    # everything seems good till now, we can go ahead and make a topup
                                    # get effective topup increment for the device
                                    if topup_mb > 0 and "limit" in sim_usage:
                                        new_limit = sim_usage["limit"] + \
                                            topup_mb
                                        log.event("process_topup_as_per_restrictions going to create topup entry for device {} with {}.".format(
                                            device.id, new_limit))
                                        ScheduledActions.create(
                                            org_id=org_id,
                                            group_id=group.id,
                                            device_id=device.id,
                                            sn=device.sn,
                                            sim=sim,
                                            topup_incr=new_limit,
                                            action_type="topup",
                                            action_status="pending")
                                        # now we can update certain counters/info for device
                                        # will have to update again when topup is successful
                                        topup_increment = round(
                                            topup_mb / 1024, 2)
                                        dev.monthly_budget = monthly_budget
                                        dev.yearly_budget = yearly_budget
                                        dev.tuIncr = topup_increment
                                        dev.dcStp = dstpc
                                        dev.wcStp = wstpc
                                else:
                                    log.event(
                                        "Weekly stp limit reached on device sn {}.".format(device.sn))
                                    dev.last_topup_status = "unsuccessful"
                                    dev.last_topup_state = "w-limit-reached"
                                    dev.last_topup_attempt = now
                                    # todo: send email to user for wstpc reached, and move on to next device
                            else:
                                # todo: send email to user for dstpc reached, and move on to next device
                                log.event(
                                    "Daily stp limit reached on device sn {}.".format(device.sn))
                                dev.last_topup_status = "unsuccessful"
                                dev.last_topup_state = "d-limit-reached"
                                dev.last_topup_attempt = now
                dev.save()
            else:
                log.event("Device {} has no tags.".format(device.sn))
        except Exception as e:
            log.error(
                "Exception in process_topup_as_per_restrictions: " + str(e))
            print("{}".format(e))

    def process_pending_actions(self):
        try:
            pending_monthly_resets = ScheduledActions.select().where(
                ScheduledActions.action_type == "monthly_allowance_reset",
                ScheduledActions.action_status == "pending",
                ScheduledActions.last_action_attempt.month == datetime.datetime.now().month)
            self.handle_pending_actions(pending_monthly_resets, True)

            pending_topups = ScheduledActions.select().where(
                ScheduledActions.action_type == "topup",
                ScheduledActions.action_status == "pending",
                ScheduledActions.last_action_attempt.month == datetime.datetime.now().month)
            self.handle_pending_actions(pending_topups, False)
        except Exception as e:
            log.error(
                "Exception in process_pending_actions: " + str(e))
            print("{}".format(e))

    def handle_pending_actions(self, pending_actions, is_monthly_reset):
        try:
            now = datetime.datetime.now()
            if pending_actions is not None and len(pending_actions) > 0:
                log.event(
                    "process_pending_actions: there are {} actions to process".format(len(pending_actions)))
                for action in pending_actions:
                    success = api.set_allowance_on_device_sim(
                        action.org_id, action.group_id, action.device_id, action.sim, 1 if is_monthly_reset else action.topup_incr)
                    if success:
                        a = ScheduledActions.get_by_id(action.id)
                        if success:
                            a.action_status = "successful"
                            a.action_state = "ok"
                            a.last_topup_attempt = now
                        else:
                            a.action_status = "unsuccessful"
                            a.action_state = "api-failure"
                            a.last_topup_attempt = now
                        a.last_action_attempt = now
                        updated_records = a.save()
                        if success and updated_records > 0:
                            # set allowance was successful need to update counters if it's topup attempt
                            if not is_monthly_reset:
                                device = Device.get(
                                    Device.org_id == action.org_id, Device.group_id == action.group_id, Device.id == action.device_id)
                                device.last_topup_attempt = now
                                device.action_status = a.action_status
                                device.action_state = a.action_state
                                device.dcStp = device.dcStp + 1
                                device.wcStp = device.wcStp + 1
                                device.save()
        except Exception as e:
            log.error(
                "Exception in handle_pending_actions: " + str(e))
            print("{}".format(e))

    def check_if_new_month(self, func):
        try:
            last_iter = ScheduledFunctionLog.select().where(ScheduledFunctionLog.function ==
                                                            func).order_by(ScheduledFunctionLog.id.desc()).get()
            if last_iter is not None and last_iter.function == func:
                today = datetime.date.today()
                if today.month == last_iter.execution_time.month:
                    return False
                else:
                    return True
            else:
                return False
        except Exception as e:
            log.error(
                "Exception in check_if_new_month: " + str(e))
            print("{}".format(e))

    def tally_device_tags(self, device_tags, query_result):
        try:
            tag_summ = []
            for item in query_result:
                if item is not None:
                    item_dict = {
                        "id": item.id,
                        "org_id": item.org_id,
                        "group_id": item.group_id,
                        "start_date": item.start_date if hasattr(item, "start_date") else None,
                        "budget": item.budget if hasattr(item, "budget") else 0,
                        "budget_type": item.budget_type if hasattr(item, "budget_type") else None,
                        "max_stp": item.max_stp if hasattr(item, "max_stp") else None,
                        "stp_tenure": item.stp_tenure if hasattr(item, "stp_tenure") else None,
                        "topup_mb": item.topup_mb if hasattr(item, "topup_mb") else None,
                        "is_scheduled": item.is_scheduled,
                        "config_time": item.config_time,
                        "device_selection_tags": item.device_selection_tags,
                        "timestamp": item.timestamp,
                    }
                    if item_dict["device_selection_tags"] is not None and len(item_dict["device_selection_tags"]) > 0:
                        q_tags = item_dict["device_selection_tags"]
                        matching_tags = intersection(device_tags, q_tags)
                        tag_summ.append({
                            "total_matches": len(matching_tags) if type(matching_tags) == list else 0,
                            "matching_tags": matching_tags,
                            "item": item,
                        })
            return sorted(tag_summ, key=lambda x: x["total_matches"], reverse=True)
        except Exception as e:
            log.error(
                "Exception in tally_device_tags: " + str(e))
            print("{}".format(e))

    def get_successful_topup_counter(self, org_id, group_id, device_id, tenure):
        log.event("get_successful_topup_counter org_id: {}, group: {}, device: {}, tenure: {}".format(
            org_id, group_id, device_id, tenure))
        try:
            day_start = pendulum.now().start_of("day")
            day_end = pendulum.now().end_of("day")
            start_of_week = pendulum.now().start_of("week")
            end_of_week = pendulum.now().end_of('week')
            stpc = 0
            stps = ScheduledActions.select(
                ScheduledActions.sn,
                fn.Count(ScheduledActions.sn).alias("total_stps")).where(
                    ScheduledActions.org_id == org_id,
                    ScheduledActions.group_id == group_id,
                    ScheduledActions.device_id == device_id,
                    ScheduledActions.action_status == 'successful',
                    ScheduledActions.last_action_attempt >= (
                        day_start if tenure == "daily" else start_of_week),
                    ScheduledActions.last_action_attempt <= (
                        day_end if tenure == "daily" else end_of_week)
            ).group_by(ScheduledActions.sn)
            log.event("get_successful_topup_counter query: {}".format(stps))
            for stp in stps:
                stpc = stp.total_stps
            return stpc
        except Exception as e:
            log.error(
                "Exception in get_successful_topup_counter: " + str(e))
            print("{}".format(e))

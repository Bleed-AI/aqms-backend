import sys
import inspect
import datetime
from peewee import *
import json
import pendulum
import threading

from app.peplink_api import PeplinkApi
from app.db_models import db, BudgetInfo, BudgetStartInfo, STPInfo, TopupInfo, DeviceSimUsageInfo, Device, ScheduledActions, ScheduledFunctionLog
from app.utils import Log as log, nameprint, Print as p, log_and_print_error
from app.utils import Singleton, intersection
from app.rate_list import RateList
from app.utils import setup_logger

api = PeplinkApi()
rl = RateList()

processDevicesLogger = setup_logger("process_devices.log")
processSimAllowanceLogger = setup_logger("process_sim_allowance.log")
processTopUpAsPerRestrictionsLogger = setup_logger("process_topup_as_per_restrictions.log")
process_pending_actionsLogger = setup_logger("process_pending_actions.log")
handlePendingActionsLogger = setup_logger("handle_pending_actions.log")
checkIfNewMonthLogger = setup_logger("check_if_new_month.log")
tallyDeviceTagsLogger = setup_logger("tally_device_tags.log")
getSuccessfullTopUpCountLogger = setup_logger("get_successfull_topup_count.log")
computeUsageInfoLogger = setup_logger("compute_usage_info.log")
setDevicesTo1mbLogger = setup_logger("set_devices_to_1mb.log")
compute_summary_for_both_simsLogger = setup_logger("compute_summary_for_both_sims.log")
class AutomatedQuotaService(metaclass=Singleton):
    def process_devices(self):
        try:
            orgs = api.get_orgs()
            if orgs is not None and len(orgs) > 0:
                processDevicesLogger.info("process_devices: Got {} orgs from API.".format(len(orgs)))

                log.event(
                    "process_devices: Got {} orgs from API.".format(len(orgs)))
                for org in orgs:
                    processDevicesLogger.info("orgs are: {}".format(org))
                    groups = api.get_groups(org["id"])
                    #only run for group 27
                    if groups is not None and len(groups) > 0:
                        processDevicesLogger.info("process_devices: Got {} groups from API.".format(len(groups)))

                        log.event(
                            "process_devices: Got {} groups from API.".format(len(groups)))
                        for group in groups:
                            if group.id != 27:
                                print("skipping group {}".format(group.id))
                                continue
                            processDevicesLogger.info("groups are: {}".format(group))
                            devices = api.get_devices_by_group(
                                org["id"], group.id, True)
                            processDevicesLogger.info("devices are: {}".format(devices))
                            if devices is not None and len(devices) > 0:
                                processDevicesLogger.info("process_devices: Got {} devices from API.".format(len(devices)))
                                log.event(
                                    "process_devices: Got {} devices from API.".format(len(devices)))
                                # tally and save devices to db
                                print("tallying devices for group {}".format(group.id) )
                                dict_devs = [device.dict()
                                             for device in devices]
                                
                                api.tally_devices_with_db(
                                    org["id"], group.id, dict_devs, False)
                                print ("tallying devices for group {} done".format(group.id))
                                processDevicesLogger.info("process_devices: Total devices for group {} are {}.".format(group.id, len(devices)))

                                log.event("process_devices: Total devices for group {} are {}.".format(
                                    group.id, len(devices)))
                                for device in devices:
                                    processDevicesLogger.info("process_devices: device {} onlineStatus: {}.".format(device.id, device.onlineStatus))

                                    log.event(
                                        "process_devices: device {} onlineStatus: {}.".format(device.id, device.onlineStatus))
                                    #log if equal to online status
                                    if(device.onlineStatus=="ONLINE"):
                                        processDevicesLogger.info("process_devices: Passed first check for device {}.".format(device))
                                    if device.onlineStatus == "ONLINE":
                                        if device is not None and device.sim1 is not None and "enable" in device.sim1 and device.sim1["enable"] == True:
                                            # sim1 is enabled for this device. we can process sim allowances
                                            log.event("process_devices: compute_usage_info for device {} sim A usage {}".format(
                                                device.id, device.sim1))
                                            processDevicesLogger.info("process_devices: compute_usage_info for device {} sim A usage {}".format(
                                                device.id, device.sim1))
                                            self.compute_usage_info(
                                                org["id"], group, device, "A")
                                            processDevicesLogger.info("process_devices: process_sim_allowances for device {} sim A usage {}".format(
                                                device.id, device.sim1))
                                            log.event("process_devices: process_sim_allowances for device {} sim A usage {}".format(
                                                device.id, device.sim1))
                                            self.process_sim_allowances(
                                                org["id"], group, device, "A", device.sim1)
                                            processDevicesLogger.info("process_devices: compute_usage_info again for device {} sim A usage {}".format(
                                                device.id, device.sim1))
                                            log.event("process_devices: compute_usage_info again for device {} sim A usage {}".format(
                                                device.id, device.sim1))
                                            self.compute_usage_info(
                                                org["id"], group, device, "A")
                                        if device is not None and device.sim2 is not None and "enable" in device.sim2 and device.sim2["enable"] == True:
                                            # sim2 is enabled for this device. we can process sim allowances
                                            processDevicesLogger.info("process_devices: compute_usage_info for device {} sim B usage {}".format(
                                                device.id, device.sim2))
                                            log.event("process_devices: compute_usage_info for device {} sim B usage {}".format(
                                                device.id, device.sim2))
                                            self.compute_usage_info(
                                                org["id"], group, device, "B")
                                            processDevicesLogger.info("process_devices: process_sim_allowances for device {} sim B usage {}".format(
                                                device.id, device.sim2))
                                            log.event("process_devices: process_sim_allowances for device {} sim B usage {}".format(
                                                device.id, device.sim2))
                                            self.process_sim_allowances(
                                                org["id"], group, device, "B", device.sim2)
                                            processDevicesLogger.info("process_devices: compute_usage_info again for device {} sim B usage {}".format(
                                                device.id, device.sim2))
                                            log.event("process_devices: compute_usage_info again for device {} sim B usage {}".format(
                                                device.id, device.sim2))
                                            self.compute_usage_info(
                                                org["id"], group, device, "B")

                                        # with summary computed for individual device, compute summary for both devices, if both devices are enabled
                                        if device is not None and device.sim1 is not None and device.sim2 is not None and "enable" in device.sim1 and "enable" in device.sim2 and device.sim1["enable"] == True and device.sim2["enable"] == True:
                                            self.compute_summary_for_both_sims(
                                                org["id"], group.id, device.id)
                                    else:
                                        processDevicesLogger.info("Device sn {} is offline. Moving on to next device, if any.".format(device.sn))
                                        log.event(
                                            "Device sn {} is offline. Moving on to next device, if any.".format(device.sn))
                            else:
                                processDevicesLogger.info("No devices found for group {}.".format(group))
                                log.event(
                                    "No devices found for group {}.".format(group))
                    else:
                        processDevicesLogger.info("No groups found for organization {}".format(org["id"]))
                        log.event(
                            "No groups found for organization {}".format(org["id"]))
            else:
                processDevicesLogger.info("No orgs found.")
                log.event("Didn't find any orgs".format(org["id"]))
        except Exception as e:
            processDevicesLogger.error("process_devices: Error: {}".format(e))
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())

    def process_sim_allowances(self, org_id, group, device, sim, sim_usage):
        processSimAllowanceLogger.info("process_sim_allowances: org_id: {}, group: {}, device: {}, sim: {}, sim_usage: {}".format(
            org_id, group, device, sim, sim_usage))
        log.event("process_sim_allowances: org_id: {}, group: {}, device: {}, sim: {}, sim_usage: {}".format(
            org_id, group, device, sim, sim_usage))
        try:
            # some verification of a few fields, just to confirm if dict is right
            processSimAllowanceLogger.info("process_sim_allowances: sim_usage: {}".format(sim_usage))
            if type(sim_usage) == dict and "enable" in sim_usage and "limit" in sim_usage:
                # pull important variables for both sims
                enabled = sim_usage["enable"] if "enable" in sim_usage else None
                limit = sim_usage["limit"] if "limit" in sim_usage else None
                unit = sim_usage["unit"] if "unit" in sim_usage else None
                consumption = sim_usage["usage_kb"] if "usage_kb" in sim_usage else None
                # because usage is recorded in KBs and we are using MBs
                consumption = consumption / 1024 if consumption != 0 else 0
                percent = sim_usage["percent"] if "percent" in sim_usage else None
                processSimAllowanceLogger.info("process_sim_allowances: enabled: {}, limit: {}, unit: {}, consumption: {}, percent: {}".format(
                    enabled, limit, unit, consumption, percent))
                log.event("process_sim_allowances: enabled: {}, limit: {}, unit: {}, consumption: {}, percent: {}".format(
                    enabled, limit, unit, consumption, percent))
                last_usage_info = DeviceSimUsageInfo.select().where(
                    DeviceSimUsageInfo.org_id == org_id,
                    DeviceSimUsageInfo.group_id == group.id,
                    DeviceSimUsageInfo.device_id == device.id,
                    DeviceSimUsageInfo.sim == sim,
                    DeviceSimUsageInfo.polling_time.month == datetime.datetime.now().month
                ).order_by(DeviceSimUsageInfo.polling_time.desc()).limit(1)
                processSimAllowanceLogger.info("process_sim_allowances: last_usage_info: {}".format(last_usage_info))
                expenditure = 0
                new_consumption = 0
                processSimAllowanceLogger.info("process_sim_allowances: device.ratelist: {}".format(device.ratelist))
                if last_usage_info is not None and len(last_usage_info) > 0 and device.ratelist > 0:
                    for u in last_usage_info:
                        processSimAllowanceLogger.info("process_sim_allowances: last_usage_info-{}: limit: {}, used: {}, consumption: {}, expenditure: {}.".format(
                            device.id, u.limit, u.used, u.consumption, u.expenditure))
                        log.event("process_sim_allowances: last_usage_info-{}: limit: {}, used: {}, consumption: {}, expenditure: {}.".format(
                            device.id, u.limit, u.used, u.consumption, u.expenditure))
                    last_usage_info = last_usage_info[0]
                    new_consumption = consumption - last_usage_info.used
                    processSimAllowanceLogger.info("process_sim_allowances: last_usage_info-{}: new_consumption: {}, consumption: {}, last_usage_info.used: {}, group country: {}.".format(
                        device.id, new_consumption, consumption, last_usage_info.used, group.country))
                    log.event("process_sim_allowances: last_usage_info-{}: new_consumption: {}, consumption: {}, last_usage_info.used: {}, group country: {}.".format(
                        device.id, new_consumption, consumption, last_usage_info.used, group.country))
                    expenditure = new_consumption * \
                        rl.get_rate_for_country_code(
                            device.id, device.ratelist, group.country)
                log.event(
                    "process_sim_allowances: last_usage_info-{}: {}".format(device.id, last_usage_info))
                log.event("process_sim_allowances: expenditure: {}, new_consumption: {}".format(
                    expenditure, new_consumption))
                processSimAllowanceLogger.info("process_sim_allowances: expenditure: {}, new_consumption: {}".format(
                    expenditure, new_consumption))
                processSimAllowanceLogger.info("process_sim_allowances: last_usage_info: {}".format(last_usage_info))
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
                processSimAllowanceLogger.info("process_sim_allowances: curr_usage_info: {}".format(
                    curr_usage_info))
                log.event("process_sim_allowances: curr_usage_info: {}".format(
                    curr_usage_info))
                # if consumption has rached 100%
                percent_consumption = consumption / limit * 100
                processSimAllowanceLogger.info("process_sim_allowances: percent_consumption = {}".format(
                    percent_consumption))
                log.event("process_sim_allowances: percent_consumption = {}".format(
                    percent_consumption))
                print("process_sim_allowances: process sim allowance for device {}, sim: {}".format(
                    device.id, sim))
                processSimAllowanceLogger.info("process_sim_allowances: process sim allowance for device {}, sim: {}".format(
                    device.id, sim))
                # if percent_consumption > 99.999:
                if percent_consumption > 99:
                    log.event("process_sim_allowances: utilization exceeds 100 percent for device {}, sim {}, checking if topup is already in progress".format(
                        device.id, sim))
                    processSimAllowanceLogger.info("process_sim_allowances: utilization exceeds 100 percent for device {}, sim {}, checking if topup is already in progress".format(
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
                    processSimAllowanceLogger.info("process_sim_allowances: pending_allowance_reset: {}".format(
                        pending_allowance_reset))
                    if pending_allowance_reset is not None and len(pending_allowance_reset) > 0:
                        # There is at least one record but it's pending. We need to log and skip.
                        # We should wait for other scheduled function to reset monthly allowance.
                        log.event("process_sim_allowances: monthly allowance for device {} sim {} isn't set yet.".format(
                            device.sn, sim))
                        processSimAllowanceLogger.info("process_sim_allowances: monthly allowance for device {} sim {} isn't set yet.".format(
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
                        log.event("process_sim_allowances: pending_topup: {}".format(
                            pending_topup))
                        if pending_topup is not None and len(pending_topup) > 0:
                            log.event("process_sim_allowances: there is a pending topup for device {} sim {}. Skipping for now.".format(
                                device.sn, sim))
                            processSimAllowanceLogger.info("process_sim_allowances: there is a pending topup for device {} sim {}. Skipping for now.".format(
                                device.sn, sim))
                        else:
                            # we need to decide if we can topup this device sim or not, based on various factors
                            log.event("process_sim_allowances: no pending topup for device {} sim {}. Going to determine if can topup.".format(
                                device.sn, sim))
                            processSimAllowanceLogger.info("process_sim_allowances: no pending topup for device {} sim {}. Going to determine if can topup.".format(
                                device.sn, sim))
                            self.process_topup_as_per_restrictions(
                                org_id, group, device, sim, sim_usage)
                else:
                    processSimAllowanceLogger.info("process_sim_allowances: usage for device {} sim {} hasn't reached 100%. Skipping it.".format(
                        device.id, sim))
                    log.event("Usage for device {} sim {} hasn't reached 100%. Skipping it.".format(
                        device.id, sim))
        except Exception as e:
            processSimAllowanceLogger.error("process_sim_allowances: Exception: {}".format(e))
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())

    def compute_usage_info(self, org_id, group, device, sim):

        now = datetime.datetime.now()
        month_start = datetime.datetime(now.year, now.month, 1)
        year_start = datetime.datetime(now.year, 1, 1)
        computeUsageInfoLogger.info("compute_usage_info for org: {}, group: {}, device: {}, sim: {}".format(
            org_id, group.id, device.id, sim))
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
            computeUsageInfoLogger.info("compute_usage_info: mtd query: {}".format(mtd))
            log.event("compute_usage_info: mtd query: {}".format(mtd))
            sn = ""
            total_consumption = 0
            total_expenditure = 0
            for item in mtd:
                computeUsageInfoLogger.info("compute_usage_info: item in mtd: {}".format(item))
                sn = item.sn
                total_consumption = item.total_consumption
                total_expenditure = item.total_expenditure
            summary_mtd = {
                "sn": sn,
                "total_consumption": total_consumption,
                "total_expenditure": total_expenditure,
            }
            computeUsageInfoLogger.info("compute_usage_info: summary_mtd: {}.".format(summary_mtd))
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
            computeUsageInfoLogger.info("compute_usage_info: ytd query: {}".format(ytd))
            log.event("compute_usage_info: ytd query: {}".format(ytd))
            for item in ytd:
                computeUsageInfoLogger.info("compute_usage_info: item in ytd: {}".format(item))
                sn = item.sn
                total_consumption = item.total_consumption
                total_expenditure = item.total_expenditure
            summary_ytd = {
                "sn": sn,
                "total_consumption": total_consumption,
                "total_expenditure": total_expenditure,
            }
            computeUsageInfoLogger.info("compute_usage_info: summary_ytd: {}.".format(summary_ytd))
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
            computeUsageInfoLogger.info("compute_usage_info: summary: {}.".format(summary))
            log.event("compute_usage_info: summary: {}.".format(summary))
            db_dev = Device.select().where(Device.org_id == org_id, Device.group_id ==
                                           group.id, Device.id == device.id)
            computeUsageInfoLogger.info("compute_usage_info: db_dev: {}.".format(db_dev))
            if db_dev is not None and len(db_dev) > 0:
                computeUsageInfoLogger.info("compute_usage_info: db_dev[0]: {}.".format(db_dev[0]))
                db_dev = db_dev[0]
                if db_dev is not None and db_dev.id > 0:
                    computeUsageInfoLogger.info("compute_usage_info: db_dev.id: {}.".format(db_dev.id))
                    db_dev.country = group.country
                    if sim == "A":
                        computeUsageInfoLogger.info("compute_usage_info: sim == A.")
                        db_dev.sim1_summary = json.dumps(
                            summary, default=str) if summary is not None else None
                        computeUsageInfoLogger.info("compute_usage_info: db_dev.sim1_summary: {}.".format(db_dev.sim1_summary))
                    if sim == "B":
                        computeUsageInfoLogger.info("compute_usage_info: sim == B.")
                        db_dev.sim2_summary = json.dumps(
                            summary, default=str) if summary is not None else None
                        computeUsageInfoLogger.info("compute_usage_info: db_dev.sim2_summary: {}.".format(db_dev.sim2_summary))
                    db_dev.save()
        except Exception as e:
            computeUsageInfoLogger.error("compute_usage_info: Exception: {}.".format(e))
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())

    def compute_summary_for_both_sims(self, org_id, group_id, device_id):
        compute_summary_for_both_simsLogger.info("compute_summary_for_both_sims: org_id: {}, group_id: {}, device_id: {}.".format(
            org_id, group_id, device_id))
        log.event("compute_summary_for_both_sims: org_id: {}, group_id: {}, device_id: {}.".format(
            org_id, group_id, device_id))
        try:
            dev = Device.get(Device.org_id == org_id,
                             Device.group_id == group_id, Device.id == device_id)
            compute_summary_for_both_simsLogger.info("compute_summary_for_both_sims: dev: {}.".format(dev))
            if dev is not None:
                sim1_summary = json.loads(dev.sim1_summary)
                sim2_summary = json.loads(dev.sim2_summary)
                compute_summary_for_both_simsLogger.info("compute_summary_for_both_sims: sim1_summary: {}, sim2_summary: {}.".format(
                    sim1_summary, sim2_summary))
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
                    compute_summary_for_both_simsLogger.info("compute_summary_for_both_sims: both dev summary: {}.".format(
                        dev.both_sims_summary))
                elif sim1_summary != 'null' and sim2_summary == 'null':
                    dev.both_sims_summary = dev.sim1_summary
                    compute_summary_for_both_simsLogger.info("compute_summary_for_both_sims equal to sim1: both dev summary: {}.".format(
                        dev.both_sims_summary))
                elif sim1_summary == 'null' and sim2_summary != 'null':
                    dev.both_sims_summary = dev.sim2_summary
                    compute_summary_for_both_simsLogger.info("compute_summary_for_both_sims equal to sim2: both dev summary: {}.".format(
                        dev.both_sims_summary))
                else:
                    dev.both_sims_summary = None
                    compute_summary_for_both_simsLogger.info("compute_summary_for_both_sims: both dev summary: {}.".format(
                        dev.both_sims_summary))
                # finally save the record back to db
                dev.save()
                compute_summary_for_both_simsLogger.info("compute_summary_for_both_sims: both dev summary saved in db: {}.".format(
                    dev.both_sims_summary))
                log.event(
                    "compute_summary_for_both_sims: both dev summary saved in db: {}.".format(dev.both_sims_summary))
        except Exception as e:
            compute_summary_for_both_simsLogger.error("compute_summary_for_both_sims: Exception: {}.".format(e))
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())

    def set_all_devices_to_1mb(self):
        try:
            orgs = api.get_orgs()
            setDevicesTo1mbLogger.info("set_all_devices_to_1mb: orgs: {}.".format(orgs))
            if orgs is not None and len(orgs) > 0:
                log.event("-- Got {} orgs from API.".format(len(orgs)))
                for org in orgs:
                    setDevicesTo1mbLogger.info("set_all_devices_to_1mb: org: {}.".format(org))
                    groups = api.get_groups(org["id"])
                    if groups is not None and len(groups) > 0:
                        setDevicesTo1mbLogger.info("set_all_devices_to_1mb: groups: {}.".format(groups))
                        log.event(
                            "-- Got {} groups from API.".format(len(groups)))
                        for group in groups:
                            setDevicesTo1mbLogger.info("set_all_devices_to_1mb: group: {}.".format(group))
                            devices = api.get_devices_by_group(
                                org["id"], group.id)
                            if devices is not None and len(devices) > 0:
                                setDevicesTo1mbLogger.info("set_all_devices_to_1mb: devices: {}.".format(devices))
                                log.event(
                                    "-- Got {} devices from API.".format(len(devices)))
                                for device in devices:
                                    setDevicesTo1mbLogger.info("set_all_devices_to_1mb: device: {}.".format(device))
                                    # todo: if buget is set to 0.1, skip the device
                                    setDevicesTo1mbLogger.info("set_all_devices_to_1mb: device.yearly_budget: {}.".format(device.yearly_budget))
                                    if device.yearly_budget == 0.1 or device.monthly_budget == 0.1:
                                        continue
                                    if device.onlineStatus == "ONLINE":
                                        setDevicesTo1mbLogger.info("set_all_devices_to_1mb: device.onlineStatus: {}.".format(device.onlineStatus))
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
                                        setDevicesTo1mbLogger.info("set_all_devices_to_1mb: device.onlineStatus: {}.".format(device.onlineStatus))
                                        log.event(
                                            "Device sn {} is offline. Moving on to next device, if any.".format(device.sn))
                            else:
                                setDevicesTo1mbLogger.info("set_all_devices_to_1mb: devices: {}.".format(devices))
                                log.event(
                                    "No devices found for group {}.".format(group))
        except Exception as e:
            setDevicesTo1mbLogger.error("set_all_devices_to_1mb: Exception: {}.".format(e))
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())

    def process_topup_as_per_restrictions(self, org_id, group, device, sim, sim_usage):
        log.event("process_topup_as_per_restrictions: org_id: {}, group: {}, device: {}, sim: {}, sim_usage: {}".format(
            org_id, group, device, sim, sim_usage))
        processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: org_id: {}, group: {}, device: {}, sim: {}, sim_usage: {}".format(
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
                processTopUpAsPerRestrictionsLogger.info("The device has the following values: monthly_budget: {}, yearly_budget: {}, budget_start: {}, daily_stp: {}, weekly_stp: {}, topup_mb: {}.".format(
                    monthly_budget, yearly_budget, budget_start, daily_stp, weekly_stp, topup_mb))
                log.event("process_topup_as_per_restrictions: monthly_budget: {}, yearly_budget: {}, budget_start: {}, daily_stp: {}, weekly_stp: {}, topup_mb: {}.".format(
                    monthly_budget, yearly_budget, budget_start, daily_stp, weekly_stp, topup_mb))

                total_mtd_consumption = 0
                total_mtd_expense = 0
                total_ytd_consumption = 0
                total_ytd_expense = 0

                dev = Device.get(
                    Device.org_id == org_id, Device.group_id == group.id, Device.id == device.id)
                processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: dev: {}.".format(
                    dev))
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
                processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: mtd_spent: {}.".format(
                    mtd_spent))

                log.event(
                    "process_topup_as_per_restrictions: mtd_spent: {}.".format(mtd_spent))
                for item in mtd_spent:
                    total_mtd_consumption = item.mtd_consumption
                    total_mtd_expense = item.mtd_expenditure
                processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: total_mtd_consumption: {}, total_mtd_expense: {}.".format(
                    total_mtd_consumption, total_mtd_expense))
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
                processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: ytd_spent: {}.".format(
                    ytd_spent))
                log.event(
                    "process_topup_as_per_restrictions: ytd_spent: {}.".format(mtd_spent))
                for item in ytd_spent:
                    total_ytd_consumption = item.total_ytd_consumption
                    total_ytd_expense = item.total_ytd_expenditure
                processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: total_ytd_consumption: {}, total_ytd_expense: {}.".format(
                    total_ytd_consumption, total_ytd_expense))
                log.event("process_topup_as_per_restrictions: total_ytd_consumption: {}, total_ytd_expense: {}.".format(
                    total_ytd_consumption, total_ytd_expense))

                # check if effective monthly or yearly budget is 0
                processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: monthly_budget: {}, yearly_budget: {}.".format(
                    monthly_budget, yearly_budget))
                if monthly_budget != 0 and total_mtd_expense >= monthly_budget:
                    # unlimited monthly budget is not set, and expense exceeds monthly budget
                    # let the user know via email
                    processTopUpAsPerRestrictionsLogger.info(
                        "Monthly budget exceeded on device sn {}.".format(device.sn))
                    log.event(
                        "Monthly budget exceeded on device sn {}.".format(device.sn))
                    dev.last_topup_status = "unsuccessful"
                    dev.last_topup_state = "m-budget-reached"
                    dev.last_topup_attempt = now
                    processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: dev after monthly budget check: {}.".format(
                        dev))
                elif monthly_budget == 0 or total_mtd_expense < monthly_budget:
                    if monthly_budget == 0:
                        processTopUpAsPerRestrictionsLogger.info(
                            "Monthly budget set to unlimited on device sn {}.".format(device.sn))
                        log.event(
                            "Monthly budget set to unlimited on device sn {}.".format(device.sn))
                    # either monthly budget is set to zero, or monthly limit not reached yet
                    # we need to check for yearly budget
                    if yearly_budget != 0 and total_ytd_expense >= yearly_budget:
                        # unlimited yearly budget is not set, and expense exceeds yearly budget
                        # todo: let the user know via email
                        processTopUpAsPerRestrictionsLogger.info(
                            "Yearly budget exceeded on device sn {}.".format(device.sn))
                        log.event(
                            "Yearly budget exceeded on device sn {}.".format(device.sn))
                        dev.last_topup_status = "unsuccessful"
                        dev.last_topup_state = "y-budget-reached"
                        dev.last_topup_attempt = now
                        processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: dev after yearly budget check: {}.".format(
                            dev))
                    elif yearly_budget == 0 or total_ytd_expense < yearly_budget:
                        if yearly_budget == 0:
                            processTopUpAsPerRestrictionsLogger.info(
                                "Yearly budget set to unlimited on device sn {}.".format(device.sn))
                            log.event(
                                "Yearly budget set to unlimited on device sn {}.".format(device.sn))
                        # either monthly budget is set to zero, or monthly limit not reached yet
                        # check if intended topup is going beyond budget limit
                        rem_budget = dev.monthly_budget - total_mtd_expense
                        processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: rem_budget: {}.".format(
                            rem_budget))
                        processTopUpAsPerRestrictionsLogger.info("The device id and the country of the group is {} and {}.".format(
                            device.id, group.country))
                        rate = rl.get_rate_for_country_code(
                            device.id,device.ratelist, group.country)
                        if yearly_budget != 0 and dev.topup_mb * rate > rem_budget:
                            # going beyond limit, can't topup device
                            processTopUpAsPerRestrictionsLogger.info(
                                "Intended topup going beyond monthly limit on device sn {}.".format(device.sn))
                            log.event(
                                "Intended topup going beyond monthly limit on device sn {}.".format(device.sn))
                            dev.last_topup_status = "unsuccessful"
                            dev.last_topup_state = "m-budget-reached"
                            dev.last_topup_attempt = now
                            processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: dev after monthly limit check: {}.".format(
                                dev))
                        else:
                            # check if daily successful stp counter < daily stp limit
                            # get daily successful topup counter
                            processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: daily_stp: {}.".format(
                                daily_stp))
                            dstpc = self.get_successful_topup_counter(
                                org_id, group.id, device.id, "daily")
                            if dstpc < daily_stp:
                                # we can go ahead and check if weekly limit reached
                                # get weekly successful topup counter
                                wstpc = self.get_successful_topup_counter(
                                    org_id, group.id, device.id, "weekly")
                                log.event("process_topup_as_per_restrictions wstpc: {}, ewstp.max_stp: {}".format(
                                    wstpc, weekly_stp))
                                processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions wstpc: {}, ewstp.max_stp: {}".format(
                                    wstpc, weekly_stp))
                                if wstpc < weekly_stp:
                                    # everything seems good till now, we can go ahead and make a topup
                                    # get effective topup increment for the device
                                    processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: topup_mb: {}.".format(
                                        topup_mb))
                                    if topup_mb > 0 and "limit" in sim_usage:
                                        new_limit = sim_usage["limit"] + \
                                            topup_mb
                                        processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: new_limit: {}.".format(
                                            new_limit))
                                        log.event("process_topup_as_per_restrictions going to create topup entry for device {} with {}.".format(
                                            device.id, new_limit))
                                        processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions going to create topup entry for device {} with {}.".format(
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
                                        dev.last_topup_status = "successful"
                                        dev.last_topup_state = "successful"
                                        processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: dev after topup entry creation: {}.".format(
                                            dev))
                                else:
                                    log.event(
                                        "Weekly stp limit reached on device sn {}.".format(device.sn))
                                    dev.last_topup_status = "unsuccessful"
                                    dev.last_topup_state = "w-limit-reached"
                                    dev.last_topup_attempt = now
                                    processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: dev after weekly limit check: {}.".format(
                                        dev))
                                    # todo: send email to user for wstpc reached, and move on to next device
                            else:
                                # todo: send email to user for dstpc reached, and move on to next device
                                log.event(
                                    "Daily stp limit reached on device sn {}.".format(device.sn))
                                dev.last_topup_status = "unsuccessful"
                                dev.last_topup_state = "d-limit-reached"
                                dev.last_topup_attempt = now
                                processTopUpAsPerRestrictionsLogger.info("process_topup_as_per_restrictions: dev after daily limit check: {}.".format(
                                    dev))
                dev.save()
            else:
                log.event("Device {} has no tags.".format(device.sn))
                processTopUpAsPerRestrictionsLogger.info("Device {} has no tags.".format(
                    device.sn))
        except Exception as e:
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())
            processTopUpAsPerRestrictionsLogger.error(
                "process_topup_as_per_restrictions: Exception: {}".format(e))
            

    def process_pending_actions(self):

        try:
            process_pending_actionsLogger.info("process_pending_actions: starting and selecting scheduled actions.")
            pending_monthly_resets = ScheduledActions.select().where(
                ScheduledActions.action_type == "monthly_allowance_reset",
                ScheduledActions.action_status == "pending",
                ScheduledActions.last_action_attempt.month == datetime.datetime.now().month)
            process_pending_actionsLogger.info("process_pending_actions: there are {} monthly resets to process.".format(
                len(pending_monthly_resets)))
            self.handle_pending_actions(pending_monthly_resets, True)

            pending_topups = ScheduledActions.select().where(
                ScheduledActions.action_type == "topup",
                ScheduledActions.action_status == "pending",
                ScheduledActions.last_action_attempt.month == datetime.datetime.now().month)
            process_pending_actionsLogger.info("process_pending_actions: there are {} topups to process.".format(
                len(pending_topups)))
            self.handle_pending_actions(pending_topups, False)

        except Exception as e:
            process_pending_actionsLogger.error(
                "process_pending_actions: Exception: {}".format(e))
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())

    def handle_pending_actions(self, pending_actions, is_monthly_reset):
        try:
            now = datetime.datetime.now()
            handlePendingActionsLogger.info("handle_pending_actions: starting with pending actions {}.".format(
                pending_actions))
            if pending_actions is not None and len(pending_actions) > 0:
                handlePendingActionsLogger.info("handle_pending_actions: there are {} actions to process.".format(
                    len(pending_actions)))
                log.event(
                    "process_pending_actions: there are {} actions to process".format(len(pending_actions)))
                for action in pending_actions:
                    handlePendingActionsLogger.info("handle_pending_actions: processing action {}.".format(
                        action))
                    success = api.set_allowance_on_device_sim(
                        action.org_id, action.group_id, action.device_id, action.sim, 1 if is_monthly_reset else action.topup_incr)
                    handlePendingActionsLogger.info("handle_pending_actions: success is {}.".format(
                        success))
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
                        handlePendingActionsLogger.info("handle_pending_actions: updated_records is {}.".format(
                            a))
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
                                handlePendingActionsLogger.info("handle_pending_actions: device is {}.".format(
                                    device))
        except Exception as e:
            handlePendingActionsLogger.error(
                "handle_pending_actions: Exception: {}".format(e))
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())

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
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())

    def tally_device_tags(self, device_tags, query_result):
        tallyDeviceTagsLogger.info("tally_device_tags: starting with device_tags {} and query_result {}.".format(
            device_tags, query_result))
        try:
            tag_summ = []
            for item in query_result:
                tallyDeviceTagsLogger.info("tally_device_tags: processing item {}.".format(
                    item))
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
                    tallyDeviceTagsLogger.info("tally_device_tags: item_dict is {}.".format(
                        item_dict))
                    if item_dict["device_selection_tags"] is not None and len(item_dict["device_selection_tags"]) > 0:
                        q_tags = item_dict["device_selection_tags"]
                        matching_tags = intersection(device_tags, q_tags)
                        tag_summ.append({
                            "total_matches": len(matching_tags) if type(matching_tags) == list else 0,
                            "matching_tags": matching_tags,
                            "item": item,
                        })
                        tallyDeviceTagsLogger.info("tally_device_tags: tag_summ is {}.".format(
                            tag_summ))
            tallyDeviceTagsLogger.info("tally_device_tags: returning tag_summ {}.".format(
                tag_summ))
            return sorted(tag_summ, key=lambda x: x["total_matches"], reverse=True)
        except Exception as e:
            tallyDeviceTagsLogger.error(
                "tally_device_tags: Exception: {}".format(e))
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())

    def get_successful_topup_counter(self, org_id, group_id, device_id, tenure):
        getSuccessfullTopUpCountLogger.info("get_successful_topup_counter: starting with org_id {}, group_id {}, device_id {} and tenure {}.".format(
            org_id, group_id, device_id, tenure))
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
            getSuccessfullTopUpCountLogger.info("get_successful_topup_counter: stps is {}.".format(
                stps))
            log.event("get_successful_topup_counter query: {}".format(stps))
            for stp in stps:
                getSuccessfullTopUpCountLogger.info("get_successful_topup_counter: stp is {}.".format(
                    stp))
                stpc = stp.total_stps
            getSuccessfullTopUpCountLogger.info("get_successful_topup_counter: returning stpc {}.".format(
                stpc))
            return stpc
        except Exception as e:
            getSuccessfullTopUpCountLogger.error(
                "get_successful_topup_counter: Exception: {}".format(e))
            log_and_print_error(inspect.stack()[0][3], e, sys.exc_info())

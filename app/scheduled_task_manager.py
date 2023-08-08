import datetime
import time
from dateutil import parser
import threading

from app.utils import Log as log
from app.config import AppConfig
from app.api_models import AppConfig
from app.db_models import ScheduledFunctionLog
from app.peplink_api import PeplinkApi
from app.quota_service import AutomatedQuotaService
from app.budget_topup_facade import BudgetAndTopupFacade
from app.rate_list import RateList

config = AppConfig()

elapsed_seconds = {
    "weekly": 518400,  # seconds for 6 days
    "bi_weekly": 1123200  # seconds for 13 days
}


class ScheduledTaskManager:
    def __init__(self):
        self.peplink_api = PeplinkApi()
        self.qs = AutomatedQuotaService()
        self.bf = BudgetAndTopupFacade()
        self.rl = RateList()

    def invoke_function_in_thread(self, func):
        t = threading.Thread(target=func)
        t.start()

    def process_devices(self):
        self.invoke_function_in_thread(self.qs.process_devices)

    def set_all_devices_to_1mb(self):
        self.invoke_function_in_thread(self.qs.set_all_devices_to_1mb)

    def process_pending_actions(self):
        self.invoke_function_in_thread(self.qs.process_pending_actions)

    def process_scheduled_info_items(self):
        self.invoke_function_in_thread(self.bf.process_scheduled_info_items)
    
    def process_pending_ratelists(self):
        self.invoke_function_in_thread(self.rl.process_pending_ratelists)

    def invoke_function_and_save_log(self, sci):
        try:
            sfl = ScheduledFunctionLog.create(
                function=sci.function, execution_time=datetime.datetime.now())
            sfl.save()
            getattr(self, sci.function)()
        except Exception as e:
            log.scheduler_event(
                "Error in invoke_function_and_save_log: {}".format(e))

    def invoke_scheduled_tasks(self, config):
        log.scheduler_event(
            "################################################################")
        for sci in config.scheduling_config:
            now = datetime.datetime.now()
            sflog = None
            try:
                log.scheduler_event("function: " + sci.function)
                sflog = ScheduledFunctionLog.select().where(ScheduledFunctionLog.function ==
                                                            sci.function).order_by(ScheduledFunctionLog.id.desc()).limit(1)
                if sflog is not None and len(sflog) > 0:
                    sflog = sflog[0]
                else:
                    sflog = None
            except Exception as e:
                log.scheduler_event("Exception: " + str(e))

            # check if daily, weekly, bi-weekly, monthly, or repeat_after
            if sci.frequency == "repeat_after":
                if sflog == None:
                    # no history exists: save to database and execute
                    log.scheduler_event(
                        "No history exists. Executing function: " + sci.function)
                    self.invoke_function_and_save_log(sci)
                else:
                    # check difference between execution_time and now
                    diff = now - sflog.execution_time
                    log.scheduler_event(
                        "diff is {} seconds".format(diff.seconds))
                    if diff.seconds > sci.seconds:
                        log.scheduler_event(
                            "Executing function: " + sci.function)
                        self.invoke_function_and_save_log(sci)
                    else:
                        log.scheduler_event(
                            "Nothing to do for function: " + sci.function)
            if sci.frequency == "daily":
                parsed_time = parser.parse(sci.scheduled_time)
                if sflog == None:
                    # no history exists: save to database and execute
                    if now > parsed_time:
                        log.scheduler_event(
                            "No history exists. Executing function: " + sci.function)
                        self.invoke_function_and_save_log(sci)
                    else:
                        log.scheduler_event(
                            "No history exists. But not a right time for " + sci.function)
                else:
                    log.scheduler_event(
                        "Now: " + now.strftime("%Y-%m-%d %H:%M:%S"))
                    log.scheduler_event(
                        "Parsed time: " + parsed_time.strftime("%Y-%m-%d %H:%M:%S"))
                    if now > parsed_time and now.day > sflog.execution_time.day:
                        log.scheduler_event(
                            "Executing function: " + sci.function)
                        self.invoke_function_and_save_log(sci)
                    else:
                        log.scheduler_event(
                            "Nothing to do for function: " + sci.function)
            if sci.frequency in ["weekly", "bi_weekly"]:
                parsed_time = parser.parse(sci.scheduled_time)
                if sflog == None:
                    if now.weekday() == sci.scheduled_day_of_week and now > parsed_time:
                        log.scheduler_event(
                            "No history exists. Executing function: " + sci.function)
                        self.invoke_function_and_save_log(sci)
                    else:
                        log.scheduler_event(
                            "No history exists. But not a right time for " + sci.function)
                else:
                    log.scheduler_event(
                        "Now: " + now.strftime("%Y-%m-%d %H:%M:%S"))
                    log.scheduler_event(
                        "Parsed time: " + parsed_time.strftime("%Y-%m-%d %H:%M:%S"))
                    diff = parsed_time - sflog.execution_time
                    log.scheduler_event(
                        "diff is {} seconds".format(diff.seconds))
                    if now.weekday() == sci.scheduled_day_of_week and now > parsed_time and diff.seconds > elapsed_seconds[sci.frequency]:
                        log.scheduler_event(
                            "Executing function: " + sci.function)
                        self.invoke_function_and_save_log(sci)
                    else:
                        log.scheduler_event(
                            "Nothing to do for function: " + sci.function)
            if sci.frequency == "monthly":
                parsed_time = parser.parse(sci.scheduled_time)
                if sflog == None:
                    # no history exists: check if day of month is right and time reached
                    if now.day == sci.scheduled_day_of_month and now > parsed_time:
                        log.scheduler_event(
                            "No history exists. Executing function: " + sci.function)
                        self.invoke_function_and_save_log(sci)
                    else:
                        log.scheduler_event(
                            "No history exists. But not a right day/time for " + sci.function)
                else:
                    # check if monthly scheduled time reached
                    # if it was last month when executed, year will need to changed for next execution
                    if sflog.execution_time.month == 12:
                        sched_year = sflog.execution_time.year + 1
                    else:
                        sched_year = sflog.execution_time.year
                    scheduled_day_time = datetime.datetime(
                        sched_year,
                        sflog.execution_time.month + 1,
                        sci.scheduled_day_of_month,
                        parsed_time.hour,
                        parsed_time.minute
                    )
                    if now > scheduled_day_time:
                        log.scheduler_event(
                            "Executing function: " + sci.function)
                        self.invoke_function_and_save_log(sci)
                    else:
                        log.scheduler_event(
                            "Nothing to do for function: " + sci.function)
            log.scheduler_event(
                "################################################################")

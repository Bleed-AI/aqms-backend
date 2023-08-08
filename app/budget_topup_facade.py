import json
import threading
import datetime
from fastapi.exceptions import HTTPException
from playhouse.shortcuts import model_to_dict

from app.api_models import BudgetInfoAPIModel
from app.db_models import BudgetInfo, BudgetStartInfo, Device, STPInfo, TopupInfo, ScheduledActions
from app.utils import Log as log


class BudgetAndTopupFacade():
    def add_budget_info(self, budget_info, tenure):
        try:
            bi = BudgetInfo.create(
                org_id=budget_info.org_id,
                group_id=budget_info.group_id,
                budget=budget_info.budget,
                budget_type=tenure,
                is_scheduled=budget_info.is_scheduled,
                config_time=budget_info.config_time,
                device_selection_tags=budget_info.device_selection_tags
            )
            if bi is not None and hasattr(bi, "id") and bi.id > 0:
                # budget info created, check if it can be applied right now
                threading.Thread(target=self.process_budget_info,
                                 args=(bi, )).start()
                return bi

        except Exception as e:
            log.error("Error in saving budget info. {}".format(e))
            raise HTTPException(
                500, detail="Error in saving budget info. {}".format(e))

    def get_org_budget_info(self, org_id):
        try:
            return [bi for bi in BudgetInfo.select().where(BudgetInfo.org_id == org_id)]
        except Exception as e:
            log.error("Error in fetching budget info. {}".format(e))
            raise HTTPException(
                500, detail="Error in fetching budget info. {}".format(e))

    def get_group_budget_info(self, org_id, group_id):
        try:
            return [bi for bi in BudgetInfo.select().where(BudgetInfo.org_id == org_id, BudgetInfo.group_id == group_id)]
        except Exception as e:
            log.error("Error in get_group_budget_info. {}".format(e))
            raise HTTPException(
                500, detail="Error in fetching budget info. {}".format(e))

    def add_budget_start_info(self, b_start_info):
        try:
            bsi = BudgetStartInfo.create(
                org_id=b_start_info.org_id,
                group_id=b_start_info.group_id,
                start_date=b_start_info.start_date,
                is_scheduled=b_start_info.is_scheduled,
                config_time=b_start_info.config_time,
                device_selection_tags=b_start_info.device_selection_tags,
            )
            if bsi is not None and hasattr(bsi, "id") and bsi.id > 0:
                # budget start info created, check if it can be applied right now
                threading.Thread(target=self.process_budget_start_info,
                                 args=(bsi, )).start()
                return bsi
        except Exception as e:
            log.error("Error in saving budget start info. {}".format(e))
            raise HTTPException(
                500, detail="Error in saving budget start info. {}".format(e))

    def get_org_budget_start_info(self, org_id):
        try:
            return [bsi for bsi in BudgetStartInfo.select().where(BudgetStartInfo.org_id == org_id)]
        except Exception as e:
            log.error("Error in fetching budget start info. {}".format(e))
            raise HTTPException(
                500, detail="Error in fetching budget start info. {}".format(e))

    def get_group_budget_start_info(self, org_id, group_id):
        try:
            return [bsi for bsi in BudgetStartInfo.select().where(BudgetStartInfo.org_id == org_id, BudgetStartInfo.group_id == group_id)]
        except Exception as e:
            log.error("Error in fetching budget start info. {}".format(e))
            raise HTTPException(
                500, detail="Error in fetching budget start info. {}".format(e))

    def add_stp_info(self, stp_info, tenure):
        try:
            stp = STPInfo.create(
                org_id=stp_info.org_id,
                group_id=stp_info.group_id,
                max_stp=stp_info.max_stp,
                stp_tenure=tenure,
                is_scheduled=stp_info.is_scheduled,
                config_time=stp_info.config_time,
                device_selection_tags=stp_info.device_selection_tags,
            )
            if stp is not None and hasattr(stp, "id") and stp.id > 0:
                # stp info created, check if it can be applied right now
                threading.Thread(target=self.process_stp, args=(stp, )).start()
                return stp
        except Exception as e:
            log.error("Error in saving STP info. {}".format(e))
            raise HTTPException(
                500, detail="Error in saving STP info. {}".format(e))

    def get_org_stp_info(self, org_id):
        try:
            return [si for si in STPInfo.select().where(STPInfo.org_id == org_id)]
        except Exception as e:
            log.error("Error in fetching STP info. {}".format(e))
            raise HTTPException(
                500, detail="Error in fetching STP info. {}".format(e))

    def get_group_stp_info(self, org_id, group_id):
        try:
            return [si for si in STPInfo.select().where(STPInfo.org_id == org_id, STPInfo.group_id == group_id)]
        except Exception as e:
            log.error("Error in fetching STP info. {}".format(e))
            raise HTTPException(
                500, detail="Error in fetching STP info. {}".format(e))

    def add_topup_info(self, topup_info):
        try:
            topup = TopupInfo.create(
                org_id=topup_info.org_id,
                group_id=topup_info.group_id,
                topup_mb=topup_info.topup_mb,
                is_scheduled=topup_info.is_scheduled,
                config_time=topup_info.config_time,
                device_selection_tags=topup_info.device_selection_tags,
            )
            if topup is not None and hasattr(topup, "id") and topup.id > 0:
                # topup info created, check if it can be applied right now
                threading.Thread(target=self.process_topup_info,
                                 args=(topup, )).start()
                return topup
        except Exception as e:
            log.error("Error in saving topup info. {}".format(e))
            raise HTTPException(
                500, detail="Error in saving topup info. {}".format(e))

    def get_org_topup_info(self, org_id):
        try:
            return [ti for ti in TopupInfo.select().where(TopupInfo.org_id == org_id)]
        except Exception as e:
            log.error("Error in fetching topup info. {}".format(e))
            raise HTTPException(
                500, detail="Error in fetching topup info. {}".format(e))

    def get_group_topup_info(self, org_id, group_id):
        try:
            return [ti for ti in TopupInfo.select().where(TopupInfo.org_id == org_id, TopupInfo.group_id == group_id)]
        except Exception as e:
            log.error("Error in fetching topup info. {}".format(e))
            raise HTTPException(
                500, detail="Error in fetching topup info. {}".format(e))

    def process_budget_info(self, bi):
        try:
            if bi.is_scheduled and bi.config_time > datetime.datetime.now():
                # this is a scueduled entry, need to skip for later
                log.event("process_budget_info: budget info for org: {} group: {} is scheduled, skipping for now: {}.".format(
                    bi.org_id, bi.group_id))
            else:
                bi_dev_sql = "select * from device where org_id = '{}' and group_id = {}".format(
                    bi.org_id, bi.group_id)
                if bi.device_selection_tags is not None and type(bi.device_selection_tags) == list and len(bi.device_selection_tags) > 0:
                    where_tags = ""
                    for idx, tag in enumerate(bi.device_selection_tags):
                        if idx == 0:
                            where_tags = "tags::jsonb ? '{}'".format(
                                tag)
                        else:
                            where_tags = "{} and tags::jsonb ? '{}'".format(
                                where_tags, tag)
                    where_tags = "({})".format(where_tags)
                    bi_dev_sql = "{} and {};".format(bi_dev_sql, where_tags)
                log.event(
                    "process_budget_info: bi_dev_sql: {}.".format(bi_dev_sql))
                bi_dev_query = Device.raw(bi_dev_sql)
                log.event(
                    "process_budget_info: bi_dev_query: {}.".format(bi_dev_query))
                for dev in bi_dev_query:
                    if dev is not None:
                        if bi.budget_type == "monthly":
                            Device.update(monthly_budget=bi.budget).where(
                                Device.id == dev.id,
                                Device.org_id == dev.org_id,
                                Device.group_id == dev.group_id).execute()
                        else:
                            Device.update(yearly_budget=bi.budget).where(
                                Device.id == dev.id,
                                Device.org_id == dev.org_id,
                                Device.group_id == dev.group_id).execute()
                bi.status = "processed"
                bi.save()
        except Exception as e:
            log.error("Error in process_budget_info. {}".format(e))

    def process_budget_start_info(self, bsi):
        try:
            if bsi.is_scheduled and bsi.config_time > datetime.datetime.now():
                # this is a scueduled entry, need to skip for later
                log.event("process_budget_start_info: budget start info for org: {} group: {} is scheduled, skipping for now.".format(
                    bsi.org_id, bsi.group_id))
            elif bsi.start_date > datetime.date.today():
                log.event("process_budget_start_info: budget start info schedule reached but budget start date hasn't reached for org: {} group: {}, skipping for now.".format(
                    bsi.org_id, bsi.group_id))
            else:
                bsi_dev_sql = "select * from device where org_id = '{}' and group_id = {}".format(
                    bsi.org_id, bsi.group_id)
                if bsi.device_selection_tags is not None and type(bsi.device_selection_tags) == list and len(bsi.device_selection_tags) > 0:
                    where_tags = ""
                    for idx, tag in enumerate(bsi.device_selection_tags):
                        if idx == 0:
                            where_tags = "tags::jsonb ? '{}'".format(
                                tag)
                        else:
                            where_tags = "{} and tags::jsonb ? '{}'".format(
                                where_tags, tag)
                    where_tags = "({})".format(where_tags)
                    bsi_dev_sql = "{} and {};".format(bsi_dev_sql, where_tags)
                log.event(
                    "process_budget_start_info: bsi_dev_sql: {}.".format(bsi_dev_sql))
                bsi_dev_query = Device.raw(bsi_dev_sql)
                log.event(
                    "process_budget_start_info: bsi_dev_query: {}.".format(bsi_dev_query))
                for dev in bsi_dev_query:
                    if dev is not None:
                        Device.update(y_budget_start=bsi.start_date).where(
                            Device.id == dev.id,
                            Device.org_id == dev.org_id,
                            Device.group_id == dev.group_id).execute()
                bsi.status = "processed"
                bsi.save()
        except Exception as e:
            log.error("Error in process_budget_start_info. {}".format(e))

    def process_stp(self, stp):
        try:
            if stp.is_scheduled and stp.config_time > datetime.datetime.now():
                # this is a scueduled entry, need to skip for later
                log.event("process_stp: stp info for org: {} group: {} is scheduled, skipping for now: {}.".format(
                    stp.org_id, stp.group_id))
            else:
                stp_dev_sql = "select * from device where org_id = '{}' and group_id = {}".format(
                    stp.org_id, stp.group_id)
                if stp.device_selection_tags is not None and type(stp.device_selection_tags) == list and len(stp.device_selection_tags) > 0:
                    where_tags = ""
                    for idx, tag in enumerate(stp.device_selection_tags):
                        if idx == 0:
                            where_tags = "tags::jsonb ? '{}'".format(
                                tag)
                        else:
                            where_tags = "{} and tags::jsonb ? '{}'".format(
                                where_tags, tag)
                    where_tags = "({})".format(where_tags)
                    stp_dev_sql = "{} and {};".format(stp_dev_sql, where_tags)
                log.event("process_stp: stp_dev_sql: {}.".format(stp_dev_sql))
                stp_dev_query = Device.raw(stp_dev_sql)
                log.event(
                    "process_stp: stp_dev_query: {}.".format(stp_dev_query))
                for dev in stp_dev_query:
                    if dev is not None:
                        if stp.stp_tenure == "daily":
                            Device.update(daily_stp=stp.max_stp).where(
                                Device.id == dev.id,
                                Device.org_id == dev.org_id,
                                Device.group_id == dev.group_id).execute()
                        else:
                            Device.update(weekly_stp=stp.max_stp).where(
                                Device.id == dev.id,
                                Device.org_id == dev.org_id,
                                Device.group_id == dev.group_id).execute()
                stp.status = "processed"
                stp.save()
        except Exception as e:
            log.error("Error in process_budget_start_info. {}".format(e))

    def process_topup_info(self, topup):
        try:
            if topup.is_scheduled and topup.config_time > datetime.datetime.now():
                # this is a scueduled entry, need to skip for later
                log.event("process_topup_info: stp info for org: {} group: {} is scheduled, skipping for now: {}.".format(
                    topup.org_id, topup.group_id))
            else:
                topup_dev_sql = "select * from device where org_id = '{}' and group_id = {}".format(
                    topup.org_id, topup.group_id)
                if topup.device_selection_tags is not None and type(topup.device_selection_tags) == list and len(topup.device_selection_tags) > 0:
                    where_tags = ""
                    for idx, tag in enumerate(topup.device_selection_tags):
                        if idx == 0:
                            where_tags = "tags::jsonb ? '{}'".format(
                                tag)
                        else:
                            where_tags = "{} and tags::jsonb ? '{}'".format(
                                where_tags, tag)
                    where_tags = "({})".format(where_tags)
                    topup_dev_sql = "{} and {};".format(
                        topup_dev_sql, where_tags)
                log.event(
                    "process_topup_info: topup_dev_sql: {}.".format(topup_dev_sql))
                topup_dev_query = Device.raw(topup_dev_sql)
                log.event(
                    "process_topup_info: topup_dev_query: {}.".format(topup_dev_query))
                for dev in topup_dev_query:
                    if dev is not None:
                        Device.update(topup_mb=topup.topup_mb).where(
                            Device.id == dev.id,
                            Device.org_id == dev.org_id,
                            Device.group_id == dev.group_id).execute()
                topup.status = "processed"
                topup.save()
        except Exception as e:
            log.error("Error in process_budget_start_info. {}".format(e))

    def process_scheduled_info_items(self):
        now = datetime.datetime.now()
        hour_ago = now - datetime.timedelta(hours=1)

        # get all budget info items whose time has approached during last hour
        bis = BudgetInfo.select().where(BudgetInfo.is_scheduled == True,
                                        BudgetInfo.config_time > hour_ago, BudgetInfo.config_time <= now, BudgetInfo.status == "pending")
        log.event("process_scheduled_info_items: bis: {}.".format(bis))
        for bi in bis:
            if bi is not None and bi.id > 0:
                self.process_budget_info(bi)

        # get all budget start info items whose time has approached during last hour
        bsis = BudgetStartInfo().select().where(BudgetStartInfo.is_scheduled == True,
                                                BudgetStartInfo.config_time > hour_ago, BudgetStartInfo.config_time <= now, BudgetStartInfo.status == "pending")
        log.event("process_scheduled_info_items: bis: {}.".format(bsis))
        for bsi in bsis:
            if bsi is not None and bsi.id > 0:
                self.process_budget_start_info(bsi)

        # get all stp info items whose time has approached during last hour
        stps = STPInfo.select().where(STPInfo.is_scheduled == True,
                                      STPInfo.config_time > hour_ago, STPInfo.config_time <= now, STPInfo.status == "pending")
        log.event("process_scheduled_info_items: bis: {}.".format(stps))
        for stp in stps:
            if stp is not None and stp.id > 0:
                self.process_stp(stp)

        # get all topup info items whose time has approached during last hour
        topups = TopupInfo.select().where(TopupInfo.is_scheduled == True,
                                          TopupInfo.config_time > hour_ago, TopupInfo.config_time <= now, TopupInfo.status == "pending")
        log.event("process_scheduled_info_items: bis: {}.".format(topups))
        for topup in topups:
            if topup is not None and topup.id > 0:
                self.process_topup_info(topup)

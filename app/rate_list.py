import os
from datetime import datetime
from fastapi.exceptions import HTTPException
from pathlib import Path
import pycountry
import pandas as pd
import json
from peewee import Value
from app.utils import Singleton
from app.db_models import Device, RateList as RateListModel
from app.utils import Print as p
from app.api_models import RateListAPIModel
from app.utils import Log as log


class RateList(metaclass=Singleton):
    ratelist_dir = os.getcwd() + "/data/ratelists/"
    ratelist_file = os.getcwd() + "/data/ratelists/current.xlsx"
    ratelist_df = None

    def upload_ratelist(self, file, is_scheduled, config_time, tags):
        try:
            contents = file.file.read()
            dt = datetime.now()
            new_name = f"ratelist-{dt.year}-{dt.month}-{dt.day}-{dt.hour}-{dt.minute}-{dt.second}.xlsx"
            with open(f"{self.ratelist_dir}{new_name}", "wb") as f:
                f.write(contents)
                new_rl = RateListModel.create(
                    file_name=new_name, is_active=True, is_scheduled=is_scheduled, config_time=config_time, tags=json.dumps(tags))
                if is_scheduled and config_time > dt:
                    # skip processing the file for later
                    log.event(
                        f"Uploaded ratelist is scheduled for a later time. Skipping for now.")
                else:
                    if tags is not None and type(tags) is list and len(tags) > 0:
                        # get devices for tags and apply ratelist only to those devices
                        devices = self.get_devices_for_tags(tags)
                        if devices is not None and len(devices) > 0:
                            for device in devices:
                                if device is not None:
                                    Device.update(ratelist=new_rl.id).where(
                                        Device.sn == device.sn).execute()
                    else:
                        # no tags are specified, update ratelist for all devices
                        Device.update(ratelist=new_rl.id).execute()
                    new_rl.status = "processed"
                    new_rl.save()
                return {
                    "id": new_rl.id,
                    "file_name": new_rl.file_name,
                    "is_active": new_rl.is_active,
                    "is_scheduled": new_rl.is_scheduled,
                    "config_time": new_rl.config_time,
                    "tags": json.loads(new_rl.tags),
                    "uploaded_at": new_rl.uploaded_at,
                    "status": new_rl.status,
                }
        except Exception as e:
            log.error("Exception in upload_ratelist: {}".format(e))
            raise HTTPException(
                422, detail="Error in uploading or saving file. {}".format(e))

    def get_ratelists(self):
        # for dev in tally_devices:
        #                 new_dev = DeviceAPIModel.parse_obj(dev)
        #                 devices.append(new_dev)
        ratelists = []
        try:
            rls = RateListModel.select()
            for rl in rls:
                rl_model = RateListAPIModel.from_orm(rl)
                ratelists.append(rl_model)
            return ratelists
        except Exception as e:
            log.error("Exception in get_ratelists: {}".format(e))
            raise HTTPException(
                422, detail="Error in getting list of rate files. {}".format(e))

    def get_rate_for_country_code(self, device_id, ratelist_id, code):
        try:
            # because UK is not standard form but returned from peplink API
            if code == "UK":
                code = "GB"
            rl = RateListModel.select().where(RateListModel.is_active ==
                                              Value(True), RateListModel.id == ratelist_id)
            log.event("get_rate_for_country_code: getting rate for device: {}, country {}, rate: {}.".format(
                device_id, code, rl))
            log.event("get_rate_for_country_code: ratelist query: {}.".format(rl))
            if rl is not None and len(rl) > 0:
                rl = rl[0]
                log.event("get_rate_for_country_code: rate: {}.".format(rl))
                country = [c for c in list(
                    pycountry.countries) if c.alpha_2 == code]
                if country is not None and len(country) > 0:
                    country = country[0]
                log.event(
                    "get_rate_for_country_code: country: {}.".format(country))
                # having country we can get rate from dataframe
                df = pd.read_excel("{}{}".format(
                    self.ratelist_dir, rl.file_name))
                country_df = df[df["Country"] == country.name.upper()]
                if len(country_df) == 1:
                    rate = df.iloc[0]["Cost €/MB"]
                    log.event("get_rate_for_country_code: obtained rate for {}: {}.".format(
                        country.name, rate))
                    return rate
                else:
                    return 0
            else:
                log.error("Could not get rate list file.".format(e))
        except Exception as e:
            log.error("Exception in get_rate_for_country_code, device_id: {}, country: {}: {}".format(
                device_id, code, e))

    def get_devices_for_tags(self, tags):
        print(f"tags: {tags}")
        if tags is not None and type(tags) is list and len(tags) > 0:
            sql = "select id, sn from device where"
            where_tags = ""
            for idx, tag in enumerate(tags):
                if idx == 0:
                    where_tags = f"tags::jsonb ? '{tag}'"
                else:
                    where_tags = f"{where_tags} and tags::jsonb ? '{tag}'"
            sql = f"{sql} {where_tags};"
            print(f"sql: {sql}")
            return Device.raw(sql)

    def process_pending_ratelists(self):
        pending_rls = RateListModel.select().where(RateListModel.is_scheduled == True,
                                                   RateListModel.status == "pending")
        log.event(f"There are {len(pending_rls)} ratelist(s) to be processed.")
        if pending_rls is not None:
            for rl in pending_rls:
                if datetime.now() > rl.config_time:
                    log.event(f"Processing ratelist: {rl.file_name}")
                    if rl.tags is not None and type(rl.tags) is list and len(rl.tags) > 0:
                        devices = self.get_devices_for_tags(rl.tags)
                        if devices is not None and len(devices) > 0:
                            for device in devices:
                                if device is not None:
                                    Device.update(ratelist=rl.id).where(
                                        Device.id == device.id,
                                        Device.sn == device.sn).execute()
                    else:
                        Device.update(ratelist=rl.id).execute()
                    RateListModel.update(status="processed").where(
                        RateListModel.id == rl.id).execute()
                else:
                    log.event(
                        f"Not the suitabe time for ratelist: {rl.file_name}. Skipping for now")

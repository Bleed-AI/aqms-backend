from app.db_models import User, ScheduledFunctionLog, RateList, Device, BudgetInfo, BudgetStartInfo, STPInfo, TopupInfo, ScheduledActions, DeviceSimUsageInfo


class DatabaseConfig():
    def create_tables(self):
        # create tables if don't exist
        User.create_table()
        ScheduledFunctionLog.create_table()
        RateList.create_table()
        Device.create_table()
        BudgetInfo.create_table()
        BudgetStartInfo.create_table()
        STPInfo.create_table()
        TopupInfo.create_table()
        ScheduledActions.create_table()
        DeviceSimUsageInfo.create_table()

    def seed_data(self):
        pass


'''
Organization: wSQIhx | Group 27
449
448
350
374
97
132
649
200
285
377
428
433
222

Organization: wSQIhx | Group 49
543
545

Organization: wSQIhx | Group 38
514
554
549
540
'''

import datetime
import os
import chalk
import inspect
from app.config import AppConfig

os.makedirs('data/log/', exist_ok=True)
config = AppConfig()


class Log:
    def event(message):
        today = datetime.datetime.now().strftime("%Y-%m-%d") 
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        with open("{}/event-log-{}.txt".format(config.log_dir, today), "a+") as log_file:
            log_file.write("{} {}".format(datetime.datetime.now().strftime(
                "%m/%d/%Y, %H:%M:%S "), message))
            log_file.write("\r\n")

    def error(message):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        with open("{}/error-log-{}.txt".format(config.log_dir, today), "a+") as log_file:
            log_file.write("{} {}".format(datetime.datetime.now().strftime(
                "%m/%d/%Y, %H:%M:%S "), message))
            log_file.write("\r\n")

    def scheduler_event(message):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        with open("{}/scheduler-log-{}.txt".format(config.log_dir, today), "a+") as log_file:
            log_file.write("{} {}".format(datetime.datetime.now().strftime(
                "%m/%d/%Y, %H:%M:%S "), message))
            log_file.write("\r\n")


def convert_datetime_to_string(d):
    if isinstance(d, datetime.datetime) or isinstance(d, datetime.date) or isinstance(d, datetime.time):
        return d.__str__()


def intersection(l1, l2, ignore_case=False):
    if type(l1) != list:
        raise Exception("Sorry, first argument passed is not a valid list")
    if type(l2) != list:
        raise Exception("Sorry, second argument passed is not a valid list")
    if ignore_case:  # if case is to be ignored, convert both lists to same case
        l1 = [v.upper() for v in l1]
        l2 = [v.upper() for v in l2]
    return [v for v in l1 if v in l2]


def nameprint(msg):
    frame = inspect.currentframe()
    frame = inspect.getouterframes(frame)[1]
    string = inspect.getframeinfo(frame[0]).code_context[0].strip()
    args = string[string.find('(') + 1:-1].split(',')
    names = []
    for i in args:
        if i.find('=') != -1:
            names.append(i.split('=')[1].strip())
        else:
            names.append(i)
    print(chalk.green("####### {} #######".format(names[0])))
    print(chalk.green(msg))


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Print:
    # chalk colors 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
    def r(msg):
        print(chalk.red(msg))

    def g(msg):
        print(chalk.green(msg))

    def y(msg):
        print(chalk.yellow(msg))

    def b(msg):
        print(chalk.blue(msg))

    def m(msg):
        print(chalk.magenta(msg))

    def c(msg):
        print(chalk.cyan(msg))

    def w(msg):
        print(chalk.white(msg))

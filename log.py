import time
INFO = 0
DEBUG = 1
WARNING = 2
ERROR = 3

log_level = INFO


def logi(tag, message):
    if log_level >= INFO:
        log(tag, message)


def logd(tag, message):
    if log_level >= DEBUG:
        log(tag, message)


def logw(tag, message):
    if log_level >= WARNING:
        log(tag, message)


def loge(tag, message):
    if log_level >= ERROR:
        log(tag, message)


def log(tag, message):
    print('%s %s: %s' % (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), tag, message))

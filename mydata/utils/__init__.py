import psutil


def PidIsRunning(pid):
    try:
        p = psutil.Process(int(pid))
        if p.status == psutil.STATUS_DEAD:
            return False
        if p.status == psutil.STATUS_ZOMBIE:
            return False
        return True  # Assume other status are valid
    except psutil.NoSuchProcess:
        return False


def HumanReadableSizeString(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.0f %s" % (num, x)
        num /= 1024.0
    return "%3.0f %s" % (num, 'TB')

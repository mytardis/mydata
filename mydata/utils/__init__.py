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
    """
    Returns human-readable string.
    """
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.0f %s" % (num, x)
        num /= 1024.0
    return "%3.0f %s" % (num, 'TB')

def UnderscoreToCamelcase(value):
    """
    Convert underscore_separated to camelCase.
    """
    output = ""
    firstWordPassed = False
    for word in value.split("_"):
        if not word:
            output += "_"
            continue
        if firstWordPassed:
            output += word.capitalize()
        else:
            output += word.lower()
        firstWordPassed = True
    return output

def BytesToHuman(numBytes):
    """
    Returns human-readable string.
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for index, symbol in enumerate(symbols):
        prefix[symbol] = 1 << (index + 1) * 10
    for symbol in reversed(symbols):
        if numBytes >= prefix[symbol]:
            value = float(numBytes) / prefix[symbol]
            return '%.1f%s' % (value, symbol)
    return "%sB" % numBytes

import sys

def get_free_memory():
    """Return current free memory on the machine.

    Currently supported for Windows, Linux, MacOS.

    :returns: Free memory in MB unit
    :rtype: int
    """
    if 'win32' in sys.platform:
        # windows
        return get_free_memory_win()
    elif 'linux' in sys.platform:
        # linux
        return get_free_memory_linux()
    elif 'darwin' in sys.platform:
        # mac
        return get_free_memory_osx()


def get_free_memory_win():
    """Return current free memory on the machine for windows.

    Warning : this script is really not robust
    Return in MB unit
    """
    stat = MEMORYSTATUSEX()
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    return int(stat.ullAvailPhys / 1024 / 1024)


def get_free_memory_linux():
    """Return current free memory on the machine for linux.

    Warning : this script is really not robust
    Return in MB unit
    """
    try:
        p = Popen('free -m', shell=True, stdout=PIPE, encoding='utf8')
        stdout_string = p.communicate()[0].split('\n')[2]
    except OSError:
        raise OSError
    stdout_list = stdout_string.split(' ')
    stdout_list = [x for x in stdout_list if x != '']
    return int(stdout_list[3])


def get_free_memory_osx():
    """Return current free memory on the machine for mac os.

    Warning : this script is really not robust
    Return in MB unit
    """
    try:
        p = Popen('echo -e "\n$(top -l 1 | awk \'/PhysMem/\';)\n"',
                  shell=True, stdout=PIPE, encoding='utf8')
        stdout_string = p.communicate()[0].split('\n')[1]
        # e.g. output (its a single line) OSX 10.9 Mavericks
        # PhysMem: 6854M used (994M wired), 1332M unused.
        # output on Mountain lion
        # PhysMem: 1491M wired, 3032M active, 1933M inactive,
        # 6456M used, 1735M free.
    except OSError:
        raise OSError
    platform_version = platform.mac_ver()[0]
    # Might get '10.9.1' so strop off the last no
    parts = platform_version.split('.')
    platform_version = parts[0] + parts[1]
    # We make version a int by concatenating the two parts
    # so that we can successfully determine that 10.10 (release version)
    # is greater than e.g. 10.8 (release version)
    # 1010 vs 108
    platform_version = int(platform_version)

    if platform_version > 108:
        stdout_list = stdout_string.split(',')
        unused = stdout_list[1].replace('M unused', '').replace(' ', '')
        unused = unused.replace('.', '')
        return int(unused)
    else:
        stdout_list = stdout_string.split(',')
        inactive = stdout_list[2].replace('M inactive', '').replace(' ', '')
        free = stdout_list[4].replace('M free.', '').replace(' ', '')
        return int(inactive) + int(free)

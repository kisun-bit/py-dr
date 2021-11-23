import os

from cpkt.core import xlogging as lg

if True:  # 必须在所有代码加载前配置日志参数，抑制IDE警告
    from cpkt.core import xpopen
    import time
    from cpkt.store import mount_point_api
    from cpkt.core import filelockv2

_logger = lg.get_logger(__name__)


# mount -t nfs 172.16.6.49:/home/mnt/nodes/7036d9cf444a41b0820ee32470a1152a
#                                                                   /home/mnt/nodes/7036d9cf444a41b0820ee32470a1152a/
def mount_nfs(src_device_dir, mount_point):
    try:
        os.makedirs(mount_point)
    except Exception as e:
        _ = e
        pass
    _old_mount_point = mount_point_api.get_mount_point_info(mount_point)
    if _old_mount_point is not None:
        if _old_mount_point['device'] == src_device_dir:
            return True     # 已经mount了，不会mount其他节点，可能就是当前节点，所以不再重新mount.

        umount_nfs(mount_point)
    _cmd = "mount -t nfs {} {}".format(src_device_dir, mount_point)
    r, out, err = xpopen.execute_cmd(_cmd, timeout=30)
    _logger.info("cmd:{} r:{} out:{} err:{}".format(_cmd, r, out, err))
    if mount_point_api.get_mount_point_info(mount_point) is not None:
        return True     # 已经mount了，不会mount其他节点，可能就是当前节点，所以不再重新mount.

    # mount 不成功？
    return False


def umount_nfs(mount_point):
    while mount_point_api.get_mount_point_info(mount_point):
        _cmd = "umount  -f  {path}".format(path=mount_point)
        r, out, err = xpopen.execute_cmd(_cmd, timeout=30)
        _logger.info("cmd:{} r:{} out:{} err:{}".format(_cmd, r, out, err))
        # 这里应该用 lsof | grep 7036d9cf444a41b0820ee32470a1152a 来杀进程的，但是太暴力了。手工来做。
        # 需要维护人员手工关闭这些应用后，会能自动的umount....
        time.sleep(1)
    return


def reload_nfs_config():
    _cmd = "exportfs -ra"
    r, out, err = xpopen.execute_cmd(_cmd, timeout=30)
    _logger.info("cmd:{} r:{} out:{} err:{}".format(_cmd, r, out, err))
    return


def get_export_dir_from_cfg_file():
    _guid_list = list()
    with open("/etc/exports", 'r') as f:
        _lines = f.readlines()
        for _l in _lines:
            _l = _l.strip().split()
            if len(_l) < 1:
                continue
            _guid = _l[0]
            _guid_list.append(_guid)
    return _guid_list


def add_nfs_server_dir(src_dir: str, nfs_flag: str):

    with filelockv2.FileExLockV2("/etc/exports"):
        _logger.info("add_nfs_server_dir({},{})".format(src_dir, nfs_flag))
        _old_dir_list = get_export_dir_from_cfg_file()
        if src_dir in _old_dir_list:
            #  已经加过了。
            return

        with open("/etc/exports", 'a') as f:
                _line = "{}     {}\n".format(src_dir, nfs_flag)
                f.write(_line)
                _logger.info("new nfs({})".format(_line))

    reload_nfs_config()
    return


if __name__ == '__main__':

    add_nfs_server_dir('/home/img', '172.16.0.0/16(rw,sync,no_root_squash)')

    pass


import os

from cpkt.core import xlogging as lg

if True:
    import psutil

_logger = lg.get_logger(__name__)


g_cluster_local_path1 = r'/home/mnt/nodes/'
g_cluster_local_path2 = r'/mnt/nodes/'


def get_guid_from_path(path: str):
    _ = path.strip()
    _guid = None
    if _.startswith(g_cluster_local_path1):
        _guid = _[len(g_cluster_local_path1):]
    elif _.startswith(g_cluster_local_path2):
        _guid = _[len(g_cluster_local_path2):]

    if _guid is None:
        return None
    # 在 /home/mnt/nodes 下:
    _guid = _guid.strip('/')
    if len(_guid.split('/')) != 1:
        # 子目录有mount 点，忽略。
        return None
    return _guid

def makedirs_safe(new_dirs):
    try:
        os.makedirs(new_dirs)
    except Exception as e:
        _ = e
        pass

def get_mount_point_info(mount_point: str):
    _all_pt = psutil.disk_partitions(all=True)
    for _m in _all_pt:
        if _m.mountpoint == mount_point:
            _r = dict()
            _r['device'] = _m.device
            _r['fstype'] = _m.fstype
            _r['mountpoint'] = _m.mountpoint
            return _r
    return None


def list_mounted_uuid_info(mount_point_name_check_fun):
    local_mount_point = dict()
    nfs_mount_point = dict()
    _all_pt = psutil.disk_partitions(all=True)
    for _m in _all_pt:
        _guid = mount_point_name_check_fun(_m.mountpoint)
        if _guid is None:  # 不是我们的目录
            continue

        _mt = dict()
        _mt['guid'] = _guid
        _mt['device'] = _m.device
        _mt['fstype'] = _m.fstype
        _mt['mountpoint'] = _m.mountpoint

        if _m.device[0:5] == '/dev/':  # 本地设备
            local_mount_point[_guid] = _mt
            continue
        else:  # NFS
            nfs_mount_point[_guid] = _mt
            continue
    return local_mount_point, nfs_mount_point


if __name__ == '__main__':
    get_mount_point_info("/run/img")
    pass


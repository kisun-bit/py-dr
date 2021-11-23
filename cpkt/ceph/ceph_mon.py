import os
import json
import socket
from cpkt.core import xlogging as lg

if True:  # 必须在所有代码加载前配置日志参数，抑制IDE警告
    from cpkt.core import xpopen

_logger = lg.get_logger(__name__)


def get_ceph_leader(timeout):
    try:
        file = '/tmp/check_is_leader.json'

        cmd = 'ceph quorum_status --format json-pretty -o {}'.format(file)
        _logger.info("[get_ceph_leader] cmd={}".format(cmd))

        retval, out, err = xpopen.execute_cmd(cmd, timeout=timeout)
        if retval != 0:
            _logger.error("[get_ceph_leader] execute failed, retval={} out={} err={}".format(retval, out, err))
            return None

        if not os.path.exists(file):
            _logger.error("[get_ceph_leader] not exist file={}".format(file))
            return None

        with open(file) as f:
            quorum = json.load(f)

        leader = quorum.get("quorum_leader_name")

        return leader

    except Exception as e:
        _logger.error("[get_ceph_leader] exeept={}".format(e))
        return None


def get_ceph_mgr(timeout):
    try:
        file = '/tmp/get_ceph_mgr.json'

        cmd = 'ceph mgr dump --format json-pretty -o {}'.format(file)
        _logger.info("[get_ceph_mgr] cmd={}".format(cmd))

        retval, out, err = xpopen.execute_cmd(cmd, timeout=timeout)
        if retval != 0:
            _logger.error("[get_ceph_mgr] execute failed, retval={} out={} err={}".format(retval, out, err))
            return None

        if not os.path.exists(file):
            _logger.error("[get_ceph_mgr] not exist file={}".format(file))
            return None

        with open(file) as f:
            config = json.load(f)

        mgr = config.get("active_name")

        return mgr

    except Exception as e:
        _logger.error("[get_ceph_mgr] exeept={}".format(e))
        return None


def check_is_leader(timeout, is_mon=True):
    """
    1 : is leader
    0 : not leader
    -1: timeout or error
    """

    _logger.info("[check_is_leader] is_mon={}".format(is_mon))

    if is_mon:
        leader = get_ceph_leader(timeout)
    else:
        leader = get_ceph_mgr(timeout)

    if not leader:
        _logger.error("[check_is_leader] get_ceph_leader failed")
        return -1

    _logger.info("[check_is_leader] leader={}".format(leader))

    node = socket.gethostname()
    if not node:
        _logger.error("[check_is_leader] gethostname failed")
        return -1

    _logger.info("[check_is_leader] node={}".format(node))

    if node == leader:
        return 1

    return 0


if __name__ == '__main__':
    result = check_is_leader(10, False)
    print("check_is_leader result={}".format(result))

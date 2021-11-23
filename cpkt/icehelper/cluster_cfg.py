import json

CFG_PATH = '/etc/aio/cluster.json'
"""
{
    "master_node_external_ip":"172.16.10.20",
    "master_node_external_ip_prefix":16,
    "master_node_external_eth_name":"ens160",
    "master_node_internal_ip":"192.168.10.20",
    "master_node_internal_ip_prefix":24,
    "master_node_internal_eth_name":"ens192",
    
    ceph的配置参数
    "root_ceph_uuid":"ceph的挂载点/home/mnt/nodes/f2224bdc7xxxxxxxxx9126e6f568ff7f97",
    "root_ceph_options":"ceph的mount参数",
    "root_ceph_source":"挂载源",
    
    非ceph环境（调试或开发使用）
    "disable_ceph":bool,
    "is_master_node":bool,
}
"""

_cfg = None


def _fetch_from_cfg_file(key, default):
    load_cfg_file_only_once()
    return _cfg.get(key, default)


def fetch_from_cfg(key, default):
    return _fetch_from_cfg_file(key, default)


def fetch_master_node_external_ip(default='*') -> str:
    """获取主节点业务IP（业务漂移IP）"""
    return _fetch_from_cfg_file('master_node_external_ip', default).lower()


def fetch_master_node_internal_ip(default='127.0.0.1') -> str:
    """获取主节点内部IP（内部漂移IP）"""
    return _fetch_from_cfg_file('master_node_internal_ip', default).lower()


def is_cluster_mode() -> bool:
    """是否工作在集群模式"""
    return fetch_master_node_internal_ip() != '127.0.0.1'


def load_cfg_file_only_once():
    global _cfg

    if _cfg is not None:
        return

    try:
        with open(CFG_PATH) as f:
            _cfg = json.load(f)
    except Exception as e:
        _ = e
        _cfg = dict()

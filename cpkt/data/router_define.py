from cpkt.core import exc
from cpkt.data import errstatus
from cpkt.icehelper import cluster_cfg

DASHBOARD_ROUTER_LOCATOR = 'dashboard_internal@master'  # 路由到 dashboard 服务
DSS_ROUTER_LOCATOR = 'disk_snapshot_service@master'  # 路由到 disk_snapshot_service 服务

DASHBOARD_INTERNAL = 'dashboard_internal'
DISK_SNAPSHOT_SERVICE = 'disk_snapshot_service'
LOGIC_SERVICE_INTERNAL = 'logic_service_internal'
IMG_CLUSTER_MGR = "img_cluster_mgr"

"""
DASHBOARD_INTERNAL: <-----  定义好的服务名称，与 server_name 的内容一致。 不要有除开 '_' 的特殊字符
        {
            # 路由时的服务名称，需要确保每个都不一样
            'server_name': DASHBOARD_INTERNAL,
            
            # Tcp监听端口，需要确保每个服务都不一样
            # 相关文档在 http://172.16.1.63/doku.php?id=%E7%AB%AF%E5%8F%A3%E5%88%86%E5%B8%83
            'listen_port': 21140,  
             
            # ICE初始化时，使用的名称。不要有特殊字符，需要确保每个服务都不一样，尽可能短一些
            # ！！注意！！ 这个名称仅仅时ice使用 ，不作为 router locator 使用
            # 用过 ice_service、 listen_port 和 ip 可路由到唯一的服务进程
            'ice_service': 'dashboard',
            
            # 是否使用 内部网络的漂移IP。
            'using_cluster_master_ip': True,
        },
"""

define = {

    DASHBOARD_INTERNAL:
        {
            'server_name': DASHBOARD_INTERNAL,
            'listen_port': 21140,
            'ice_service': 'dashboard',
            'using_cluster_master_ip': True,
        },

    DISK_SNAPSHOT_SERVICE:
        {
            'server_name': DISK_SNAPSHOT_SERVICE,
            'listen_port': 21119,
            'ice_service': 'dss',
            'using_cluster_master_ip': True,
        },

    LOGIC_SERVICE_INTERNAL:
        {
            'server_name': LOGIC_SERVICE_INTERNAL,
            'listen_port': 21141,
            'ice_service': 'logic',
        },

    IMG_CLUSTER_MGR:
        {
            'server_name': IMG_CLUSTER_MGR,
            'listen_port': 21142,
            'ice_service': 'img_cluster_mgr',
        },
}


def get_cfg(server_name, raise_exception=False) -> dict:
    if raise_exception and server_name not in define:
        raise exc.generate_exception_and_logger(errstatus.ClwErrorStatus.ROUTER_ANALYZE_TARGET_FAILED_MSG,
                                                'cpkt/data/router_define get cfg failed {}'.format(server_name),
                                                errstatus.ClwErrorStatus.ROUTER_ANALYZE_TARGET_FAILED)
    return define.get(server_name)


_ICE_ENDPOINT_FLAG = 'ice_endpoint:'
_ICE_ENDPOINT_FLAG_LEN = len(_ICE_ENDPOINT_FLAG)


def convert_router_locator_2_ice_endpoint(router: str) -> str:
    """通过 router locator 生成 ice endpoint 字符串
    三种格式
        1. 原生 ice endpoint
            ice_endpoint:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            固定前缀 ice_endpoint:
        2. 预定义
            server_name@ip
            server_name 必须在 cpkt/data/router_define.py 有定义
            特殊ip：如果ip为master，意为 master_node_internal_ip
        3. 完全信息描述
            port:ice_service@ip
    """
    if router.startswith(_ICE_ENDPOINT_FLAG):
        # 原生 ice endpoint
        return router[_ICE_ENDPOINT_FLAG_LEN:]

    router_params = router.split(r'@')
    internal_ip = router_params[1]
    if internal_ip == 'master':
        internal_ip = cluster_cfg.fetch_master_node_internal_ip()

    if ':' not in router_params[0]:
        # 预定义描述
        cfg = get_cfg(router_params[0], True)
        return "{}:tcp -h {} -p {}".format(cfg['ice_service'], internal_ip, cfg['listen_port'])

    # 完全信息描述
    router_params = router_params[0].split(':')
    return "{}:tcp -h {} -p {}".format(router_params[1], internal_ip, router_params[0])


def generate_router_locator(server_cfg, internal_ip):
    if server_cfg.get('server_name', '__') in define:
        # 使用预定义描述
        router_locator = '{}@{}'.format(server_cfg['server_name'], internal_ip)
    else:
        # 使用完全信息描述
        router_locator = '{}:{}@{}'.format(server_cfg['listen_port'], server_cfg['ice_service'], internal_ip)

    ice_enpoint = 'tcp -h {} -p {}'.format(internal_ip, server_cfg['listen_port'])
    return router_locator, server_cfg['ice_service'], ice_enpoint


def get_router_locator(server_name, ip):
    get_cfg(server_name)  # 仅有预定义服务可以用 服务名称@ip 的方式进行路由
    return '{}@{}'.format(server_name, ip)


def fetch_ip_in_sender(sender):
    assert '@' in sender
    return sender.split('@')[-1]

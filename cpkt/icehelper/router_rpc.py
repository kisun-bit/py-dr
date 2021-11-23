import json
import threading

import IPy
import Ice
import psutil

from cpkt.core import exc
from cpkt.core import xjson as xj
from cpkt.core import xlogging as lg
from cpkt.data import define
from cpkt.data import errstatus
from cpkt.data import router_define as rd
from cpkt.icehelper import cluster_cfg
from cpkt.icehelper import communicator
from cpkt.icehelper import ice_interface
from cpkt.rpc import ice

IceSystemError = ice.Utils.SystemError
IceSnapshot = ice.SnapshotApi.Snapshot
IceRpcPrx = ice.RpcWithRouter.RpcPrx

LOG_INFO = define.Base.LOG_LEVEL_INFO
LOG_DEBUG = define.Base.LOG_LEVEL_DEBUG
LOG_NONE = define.Base.LOG_LEVEL_NONE


def log_none(*_, **__):
    pass  # do nothing


class RouterRpcClient(object):

    def __init__(self, router_prx, logger, router_locator):
        self.router_prx = router_prx
        self.logger = logger
        self.router_locator = router_locator

        self._unique_number_locker = threading.Lock()
        self._unique_number = 0

    def op(self, router_locator, call, in_json, log_level=None):
        assert self.router_prx

        op_index = self.unique_number

        log_fn = self.logger.info

        if log_level:
            if log_level == LOG_DEBUG:
                log_fn = self.logger.debug
            elif log_level == LOG_NONE:
                log_fn = log_none

        log_fn('op [{}] {} {} : {}'.format(op_index, router_locator, call, in_json))

        try:
            out_json = json.loads(
                self.router_prx.Op(router_locator, r'{}#{}'.format(call, self.router_locator), json.dumps(in_json))
            )
            log_fn('op [{}] {} {} : {}'.format(op_index, router_locator, call, out_json))
            return out_json
        except IceSystemError as se:
            log_fn('op [{}] {} {} failed. {}'.format(op_index, router_locator, call, se))
            raise exc.CpktException(se.description, se.debug, se.rawCode)
        except exc.CpktException as ce:
            log_fn('op [{}] {} {} failed. {}'.format(op_index, router_locator, call, ce.description))
            raise
        except Ice.Exception as ie:
            debug_msg = 'op [{}] {} {} failed. {}'.format(op_index, router_locator, call, ie)
            log_fn(debug_msg)
            raise exc.CpktException(
                errstatus.ClwErrorStatus.ICE_RPC_FAILED_MSG, debug_msg, errstatus.ClwErrorStatus.ICE_RPC_FAILED
            )
        except Exception as e:
            log_fn('op [{}] {} failed\n{}'.format(op_index, call, lg.format_exception(e)))
            raise exc.standardize_exception(e)

    @property
    def unique_number(self) -> int:
        with self._unique_number_locker:
            self._unique_number += 1
            return self._unique_number


class RouterRpc(communicator.Communicator):

    def __init__(self, logger, server_cfg: dict, module_list: list, ignore_import_exception=False):
        """集群内部通信客户端/服务器端

        重型对象，原则上每个进程仅实例化一个

        :param logger: 日志对象
        :param server_cfg: 接口服务配置，格式： {'demo_define': {'listen_port': 60014, 'ice_service': 'demo60014', }}
            支持两种模式：
                1. 预先在 cpkt/data/router_define.py 中定义
                2. 由调用者自定义
        :param module_list: 定义有服务接口的 module 列表
            使用 python 标准import全路径
        :param ignore_import_exception  是否忽略import时的异常
        """
        super(RouterRpc, self).__init__(logger)
        self.server_cfg = server_cfg

        execute = ice_interface.fetch_ice_interface(module_list, logger, ignore_import_exception)
        self._server_interface = ServiceInterface(execute, self)

        self.internal_ip = None  # 本地服务监听IP
        self.router_locator = None  # 路由定位信息，其他服务通过该信息向本服务发起调用
        self.router_prx = None  # 发起调用时使用的 prx

        self._unique_number_locker = threading.Lock()
        self._unique_number = 0

    def more_init(self, args):
        try:
            self.router_prx = IceRpcPrx.checkedCast(self.communicator().propertyToProxy(r'Router.Proxy'))

            if self.server_cfg.get('using_cluster_master_ip'):
                self.internal_ip = cluster_cfg.fetch_master_node_internal_ip()
            else:
                self.internal_ip = json.loads(
                    self.router_prx.RouterOp('query_internal_ip', json.dumps(
                        {'server_name': self.server_cfg.get('server_name', '__')}))
                )['internal_ip']

            self.logger.info('internal_ip : {}'.format(self.internal_ip))

            self.router_locator, ice_service_name, ice_endpoint = rd.generate_router_locator(
                self.server_cfg, self.internal_ip)

            self.logger.info('router_locator:{} | ice_service_name:{} | ice_endpoint:{}'.format(
                self.router_locator, ice_service_name, ice_endpoint))

            adapter = self.communicator().createObjectAdapterWithEndpoints("RouterAdapter", ice_endpoint)
            adapter.add(self._server_interface, self.communicator().stringToIdentity(ice_service_name))
            adapter.activate()

        except IceSystemError as se:
            self.logger.error('RouterRpcRunner failed. {}'.format(se))
            raise exc.generate_exception_and_logger(se.description, se.debug, se.rawCode, self.logger)
        except exc.CpktException as ce:
            self.logger.error('RouterRpcRunner failed. {} {} {}'.format(ce.description, ce.debug, ce.rawCode))
            raise
        except Ice.Exception as ie:
            raise exc.generate_exception_and_logger(
                errstatus.ClwErrorStatus.ICE_RPC_FAILED_MSG,
                'RouterRpcRunner failed. {}'.format(ie),
                errstatus.ClwErrorStatus.ICE_RPC_FAILED,
                self.logger
            )
        except Exception as e:
            debug_msg = 'RouterRpcRunner failed. {}'.format(e)
            self.logger.error('{}\n{}'.format(debug_msg, lg.format_exception(e)))
            raise exc.generate_exception_and_logger(
                '内部异常，初始化网络模块失败', debug_msg, errstatus.ClwErrorStatus.UNKNOW_BUG, self.logger)

        else:
            self.logger.info('RouterRpcRunner init successful')

    def init(self, cfg_path='/etc/aio/router_rpc_client.cfg'):

        master_node_internal_ip = cluster_cfg.fetch_master_node_internal_ip()
        router_prx_cfg = r'router : tcp -h {} -p 21120'.format(master_node_internal_ip)
        source_address = self.calc_source_address(master_node_internal_ip)

        self.logger.info('router_prx_cfg : {}, source_address:{}'.format(router_prx_cfg, source_address))

        _default_properties = [
            (r'Ice.ThreadPool.Server.Size', r'1'),
            (r'Ice.ThreadPool.Server.SizeMax', r'512'),
            (r'Ice.ThreadPool.Server.StackSize', r'2097152'),  # 2 MB
            (r'Ice.ThreadPool.Client.Size', r'1'),
            (r'Ice.ThreadPool.Client.SizeMax', r'512'),
            (r'Ice.ThreadPool.Client.StackSize', r'2097152'),  # 2 MB
            (r'Ice.Warn.Connections', r'1'),
            (r'Ice.ACM.Heartbeat', r'3'),  # HeartbeatAlways
            (r'Ice.ThreadPool.Client.ThreadIdleTime', r'900'),  # 15min
            (r'Ice.ThreadPool.Server.ThreadIdleTime', r'900'),  # 15min
            (r'Ice.MessageSizeMax', r'131072'),  # 单位KB, 128MB
            (r'Router.Proxy', router_prx_cfg),
        ]

        if source_address:
            _default_properties.append((r'Ice.Default.SourceAddress', source_address,))

        self.start([], cfg_path, _default_properties)

        global rpc, rpc_server
        rpc = RouterRpcClient(self.router_prx, self.logger, self.router_locator)
        rpc_server = self

    def stop(self):
        self.communicator().shutdown()

    def wait_for_shutdown(self):
        self.communicator().waitForShutdown()

    def destroy(self):
        self.communicator().destroy()

    def calc_source_address(self, master_node_internal_ip):
        if master_node_internal_ip == '127.0.0.1':
            return '127.0.0.1'  # 单机模式

        iip = IPy.IP(master_node_internal_ip)
        if iip.version() != 4:
            raise exc.generate_exception_and_logger(
                '网络配置异常，集群内部网络不支持IPv6', 'master_node_internal_ip is ipv6', 0)

        net_if_addrs = psutil.net_if_addrs()

        """查找是否存在 master_node_internal_ip"""

        def _find_master_node_internal_ip_netmask():
            for one_if in net_if_addrs.values():
                for one_ip in one_if:
                    if isinstance(one_ip.address, str) and one_ip.address.lower() == master_node_internal_ip:
                        return one_ip.netmask.lower()

        net_mask = _find_master_node_internal_ip_netmask()
        self.logger.info('_find_master_node_internal_ip_netmask : {}'.format(net_mask))

        if not net_mask:
            return None  # 集群模式，非主节点

        iip = iip.make_net(net_mask)  # 转换为子网

        """查找与 master_node_internal_ip 同子网的 ip"""

        def _find_ip_with_same_master_node_internal_ip_netmask():
            for one_if in net_if_addrs.values():
                for one_ip in one_if:
                    if not isinstance(one_ip.address, str):
                        continue
                    if one_ip.address.lower() == master_node_internal_ip:
                        continue

                    try:
                        if IPy.IP(one_ip.address) in iip:
                            return one_ip.address.lower()
                    except Exception as e:
                        _ = e

        result_ip = _find_ip_with_same_master_node_internal_ip_netmask()
        if result_ip:
            return result_ip
        else:
            raise exc.generate_exception_and_logger(
                '网络配置异常，集群内部网络IP与主节点内部网络IP重复', 'can NOT find same {}'.format(iip), 0)


class ServiceInterface(IceSnapshot):

    def __init__(self, execute, router_):
        self.EXECUTE = execute
        self.router_ = router_  # type: communicator.Communicator
        self._unique_number_locker = threading.Lock()
        self._unique_number = 0

    @property
    def unique_number(self) -> int:
        with self._unique_number_locker:
            self._unique_number += 1
            return self._unique_number

    def split_call(self, call):
        try:
            call = call.split('#')
            return call[0], call[1]
        except Exception as e:
            self.router_.logger.error('split_call {} failed\n{}'.format(call, lg.format_exception(e)))
            raise exc.standardize_exception(e)

    def Op(self, call, in_json, current=None):
        _ = current
        op_index = self.unique_number

        interface, sender = self.split_call(call)

        call_item = self.EXECUTE.get(interface)
        if not call_item:
            raise exc.generate_exception_and_logger(
                errstatus.ClwErrorStatus.ROUTER_ANALYZE_CALL_FAILED_MSG,
                'OP [{}] {} failed. NOT EXIST call ??!!'.format(op_index, call),
                errstatus.ClwErrorStatus.ROUTER_ANALYZE_CALL_FAILED,
                self.router_.logger
            )

        log_fn = self.router_.logger.info

        try:
            if call_item[3]:
                if call_item[3] == LOG_DEBUG:
                    log_fn = self.router_.logger.debug
                elif call_item[3] == LOG_NONE:
                    log_fn = log_none

            log_fn('OP [{}] {} : {}'.format(op_index, call, in_json))

            if call_item[0]:
                # 定义有反序列化器
                params, errors = call_item[0]().loads(in_json)
                assert not errors, ('内部异常，代码 LoadJsonFailed', 'load input failed {}'.format(errors), 0,)
            else:
                params = json.loads(in_json)

            result = call_item[1](params, sender)

            if call_item[2]:
                # 定义有序列化器
                out_json, errors = call_item[2]().dumps(result, ensure_ascii=False, cls=xj.ExtendJSONEncoder)
                assert not errors, ('内部异常，代码 DumpJsonFailed', 'dump failed {}'.format(errors), 0,)
            else:
                if result is None:
                    out_json = '{}'
                else:
                    out_json = json.dumps(result)

            log_fn('OP [{}] {} : {}'.format(op_index, call, out_json))

            return out_json
        except IceSystemError as se:
            log_fn('OP [{}] {} failed. {}'.format(op_index, call, se))
            raise exc.CpktException(se.description, se.debug, se.rawCode)
        except exc.CpktException as ce:
            log_fn('OP [{}] {} failed. {}'.format(op_index, call, ce.description))
            raise
        except Ice.Exception as ie:
            debug_msg = 'OP [{}] {} failed. {}'.format(op_index, call, ie),
            raise log_fn(
                errstatus.ClwErrorStatus.ICE_RPC_FAILED_MSG, debug_msg, errstatus.ClwErrorStatus.ICE_RPC_FAILED
            )
        except Exception as e:
            log_fn('OP [{}] {} failed\n{}'.format(op_index, call, lg.format_exception(e)))
            raise exc.standardize_exception(e)


"""存储本进程的内网通信对象"""
rpc = None  # type: RouterRpcClient
rpc_server = None  # type: RouterRpc

_is_running_on_master = None


def is_running_on_master() -> bool:
    """是否工作在主节点上

    单机模式，返回在主节点上
    """
    if not cluster_cfg.is_cluster_mode():
        return True

    global _is_running_on_master
    if _is_running_on_master is not None:
        return _is_running_on_master

    master_node_internal_ip = cluster_cfg.fetch_master_node_internal_ip()

    net_if_addrs = psutil.net_if_addrs()
    for one_if in net_if_addrs.values():
        for one_ip in one_if:
            if not isinstance(one_ip.address, str):
                continue
            if one_ip.address.lower() == master_node_internal_ip:
                _is_running_on_master = True

    if _is_running_on_master is None:
        _is_running_on_master = False

    return _is_running_on_master

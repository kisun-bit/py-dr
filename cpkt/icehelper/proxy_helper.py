import threading
import re

from cpkt.rpc import ice


class ProxyHelper(object):
    NAME_MATCH_P = re.compile(r'(\w+).*:.*')

    LOGIC_SERVICE = 'logic_service'
    BOX_SERVICE = 'box_service'
    IMAGE_SERVICE = 'image_service'
    INSTALL_SERVICE = 'install_service'
    KT_SERVICE = 'kt_service'
    TCP_PROXY = 'tcp_proxy'
    WATCH_POWER = 'watch_power'
    DATA_QUEUE = 'data_queue'
    DSS = 'dss'

    service_map = {
        LOGIC_SERVICE: {
            'proxy_str': 'logicInternal : tcp -h {} -p 21109',
            'factory_func': ice.BoxLogic.LogicInternalPrx.checkedCast,
        },
        BOX_SERVICE: {
            'proxy_str': 'apis : tcp -h {} -p 21105',
            'factory_func': ice.Box.ApisPrx.checkedCast,
        },
        IMAGE_SERVICE: {
            'proxy_str': 'img : tcp -h {} -p 21101',
            'factory_func': ice.IMG.ImgServicePrx.checkedCast,
        },
        INSTALL_SERVICE: {
            'proxy_str': 'install : tcp -h {} -p 21106',
            'factory_func': ice.InstallModule.InstallInterfacePrx.checkedCast,
        },
        KT_SERVICE: {
            'proxy_str': 'kts : tcp -h {} -p 21108',
            'factory_func': ice.KTService.KTSPrx.checkedCast,
        },
        TCP_PROXY: {
            'proxy_str': 'tcpcproxy : tcp -h {} -p 21107',
            'factory_func': ice.CProxy.TunnelManagerPrx.checkedCast,
        },
        WATCH_POWER: {
            'proxy_str': 'poweroffproc : tcp -h {} -p 21110',
            'factory_func': ice.WatchPowerServ.PowerOffProcPrx.checkedCast,
        },
        DATA_QUEUE: {
            'proxy_str': 'datacreator:tcp -h {} -p 21113',
            'factory_func': ice.DataQueuingIce.DataCreatorPrx.checkedCast,
        },
        DSS: {
            'proxy_str': 'dss : tcp -h {} -p 21119',
            'factory_func': ice.SnapshotApi.SnapshotPrx.checkedCast,
        },
    }

    def __init__(self, communicator):
        self._communicator = communicator
        self._proxy_cache = dict()
        self._locker = threading.RLock()

    def _get_proxy_info(self, ident):
        """获取代理信息
        ident : logic_service@172.16.6.23 or install : tcp -h {} -p 21106
        return factory func, proxy_str
        """

        def _match_service(src_string):
            return self.NAME_MATCH_P.match(src_string).group(1)

        def _same_service(proxy_str1, proxy_str2):
            return _match_service(proxy_str1) == _match_service(proxy_str2)

        if '@' in ident:
            name, ip = ident.split('@')
            assert name in self.service_map
            return self.service_map[name]['factory_func'], self.service_map[name]['proxy_str'].format(ip)
        else:
            for service_name, info in self.service_map.items():
                if _same_service(ident, info['proxy_str']):
                    break
            else:
                raise Exception('not found proxy info')
            return info['factory_func'], ident

    def get_proxy(self, ident):
        with self._locker:
            prx = self._proxy_cache.get(ident)
            if prx:
                return prx

        factory_func, proxy_str = self._get_proxy_info(ident)
        prx = factory_func(self._communicator.stringToProxy(proxy_str))
        with self._locker:
            self._proxy_cache[ident] = prx
        return prx

    @staticmethod
    def gen_ident(service_name, ip=None):
        return '{}@{}'.format(service_name, ip if ip else '127.0.0.1')

    def test_get_api(self):
        proxy_str_list = list()
        for service_name in self.service_map.keys():
            try:
                proxy = self.get_proxy(self.gen_ident(service_name))
            except Exception as e:
                print('get_proxy error {} {}'.format(e, service_name))
            else:
                print(service_name, proxy, id(proxy))
                proxy_str_list.append(proxy.ice_toString())

        for proxy_str in proxy_str_list:
            proxy = self.get_proxy(proxy_str)
            print(proxy, id(proxy))

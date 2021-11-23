import ipaddress

import IPy
import psutil


def if_exist(if_name: str) -> bool:
    """检查指定网卡设备是否存在

    :param if_name: 网卡设备名，例如 ens33
    """
    net_if_addrs = psutil.net_if_addrs()
    return if_name in net_if_addrs


def is_ip_on_if(if_name: str, ip: str) -> bool:
    """检查指定IP是否在指定网卡设备上

    如果指定网卡设备不存在，那么总是返回 False

    :param if_name: 网卡设备名，例如 ens33
    :param ip: IP地址， 例如 192.168.1.123
    """
    net_if_addrs = psutil.net_if_addrs()
    one_if = net_if_addrs.get(if_name)
    if not one_if:
        return False

    for one_ip in one_if:
        if isinstance(one_ip.address, str) and one_ip.address.lower() == ip.lower():
            return True

    return False


def get_same_subnet_on_if(if_name: str, ip_with_prefix: str) -> list:
    """获取指定网卡设备上，与指定IP的同子网的IP

    如果指定网卡设备不存在，那么总是返回 空list
    如果指定网卡设备已经有指定的IP，那么该IP也将被返回

    :param if_name: 网卡设备名，例如 ens33
    :param ip_with_prefix: IP地址含掩码，例如 192.168.1.123/24
    """
    _list_of_same = list()
    net_if_addrs = psutil.net_if_addrs()
    one_if = net_if_addrs.get(if_name)
    if not one_if:
        return _list_of_same

    find_ = ipaddress.ip_network(ip_with_prefix, False).with_prefixlen

    for one_ip in one_if:
        try:
            if not isinstance(one_ip.address, str):
                continue

            iip = IPy.IP(one_ip.address).make_net(one_ip.netmask)
            if str(iip) == find_:
                _list_of_same.append(one_ip)

        except Exception as e:
            _ = e  # do nothing

    return _list_of_same

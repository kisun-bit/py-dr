"""
本示例访问 router_rpc_server 提供的远程调用接口
"""

import logging

import sys

logger = logging.getLogger()
stdout_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stdout_handler)
logger.setLevel(logging.DEBUG)

from cpkt.icehelper import router_rpc as rr
from cpkt.data import router_define as rd
import random
import time

rand_int = random.randint(60011, 60020)  # 自定义模式下，自行保证不重复

server_cfg = {
    'listen_port': 0,  # 或者 rand_int
    'ice_service': 'demo{}'.format(rand_int),  # 自定义模式下，自行保证不重复，不要有特殊字符
}

rr.RouterRpc(logger, server_cfg, []).init()

# 以上为初始化代码，更多信息见 router_rpc_server

##############################################################################
# 发送请求的简单示例

"""
向 router_rpc_server 发送远程调用
    
    整个调用需要 DiskSnapshot 服务进行转发

router_locator 的规则为  “服务名@ip”

    实际使用时，三种情况：
    
    1. 调用 dashboard 之类的使用内部网络漂移IP的服务
        可使用使用 rd.DASHBOARD_ROUTER_LOCATOR 

    2. 已知需要调用的集群计算机节点的内网IP
        例如 主业务逻辑 向 192.168.123.11 的节点上的 logic service 发送调用“启动虚拟机”
        可使用 rd.get_router_locator(rd.LOGIC_SERVICE_INTERNAL, '192.168.123.11')

        本例中 服务名为 rd.LOGIC_SERVICE_INTERNAL
               ip 可以在 rpc.internal_ip 中获取

    3. 本服务收到一个请求，需要将结果“回调”给发送者
        例如，logic service 收到“启动虚拟机”后，需要报告后续状态给调用者
        可在 “启动虚拟机” 将 sender 参数保存到上下文中
        在发起请求时，直接用 sender 作为 router_locator 参数使用

        可参考下面的 recursive_callback 示例

全局的发送器
    对于单个进程而言，仅有一份 RouterRpc
    为了方便调用，框架使用一个全局变量来存储 RouterRpc 实例
    发起调用时，使用   rr.rpc.op(......)
"""

target_ip = input('input target ip:')
target_server_name = rd.LOGIC_SERVICE_INTERNAL  # 因为 router_rpc_server 使用的是 logic service 的配置

if target_ip == 'dss':
    router_locator = rd.DSS_ROUTER_LOCATOR
else:
    router_locator = rd.get_router_locator(target_server_name, target_ip)

msg = input('input name :\n')
print('\n============= begin hello world ==============')
result = rr.rpc.op(router_locator, 'hello_world', {'in': msg})
print(result['out'])
print('\n============= end hello world ================')

##############################################################################
# 回调示例
#   1. 异步 hello world
#   2. 递归
#       最大递归次数限制 1000， 测试代码中的方法为同步调用，会将线程耗尽


from cpkt.icehelper import ice_interface


@ice_interface.register('hello_world_report')
def hello_world_report(params: dict, sender):
    """异步 hello world"""
    _ = sender
    print('\ni am in hello_world_report : {}'.format(params['out']))


@ice_interface.register('recursive_callback')
def recursive_callback(params: dict, sender):
    """递归 callback
        params {'count' : int}
        每次调用 count 都减1， 直到小于等于0
    """
    _ = sender
    count_ = params['count']
    print('\n--------\ni am in recursive_callback count: {}\n--------\n'.format(count_))
    count_ -= 1
    if count_ > 0:
        rr.rpc.op(sender, 'recursive_callback', {'count': count_})


##############################################################################

print('\n')

delay = input('input callback delay :\n')

print('\n============= begin hello_world_callback ==============')
rr.rpc.op(router_locator, 'hello_world_callback', {'msg': msg, 'delay': int(delay)})

time.sleep(int(delay) + 2)
print('\n============= end hello_world_callback ================')

################################################################################

print('\n')

count = input('input recursive_callback count :\n')

print('\n============= begin recursive_callback ==============')
result = rr.rpc.op(router_locator, 'recursive_callback', {'count': int(count)})
print('\n============= end recursive_callback ================')

###############################################################################


rr.rpc_server.stop()
rr.rpc_server.wait_for_shutdown()
rr.rpc_server.destroy()

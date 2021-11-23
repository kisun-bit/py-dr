"""
本示例 提供服务接口

提供的服务方法都实现在 router_rpc_interface/interface_demo.py 中

只要被 @ice_interface.register 装饰器包裹的函数，都可以被集群内部所有服务器远程调用

备注：
    这里用 logic service 的配置作为示例，运行时需要保证 logic service 未运行
"""

import logging

import sys

logger = logging.getLogger()
stdout_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stdout_handler)
logger.setLevel(logging.DEBUG)

from cpkt.icehelper import router_rpc as rr
from cpkt.data import router_define as rd

# 以下两句为实际有效代码，需要在实际的服务组件启动时执行一次。
# ！！注意！！仅应该执行一次，不可多次执行

server_cfg = rd.get_cfg(rd.LOGIC_SERVICE_INTERNAL)
rr.RouterRpc(logger, server_cfg, ['router_rpc_interface.interface_demo', ]).init()

print('current ip : {}'.format(rr.rpc_server.internal_ip))

while input('input "q" quit') != 'q':
    pass

rr.rpc_server.stop()
rr.rpc_server.wait_for_shutdown()
rr.rpc_server.destroy()

"""
其他说明
--------------------------
关于 RouterRpc 的第三个参数 ['router_rpc_interface.interface_demo', ]
意义是指定需要主动加载的py文件

现在是实现 服务接口 的代码文件，主动将 接口信息注册到框架中
如果 某个文件没有被 import 过，那么其中的接口也不会被 注册到框架中

这个参数的意义就是去主动加载一下这类文件

如果没有对外提供服务，可传入空数组 或者 None
如果对应的py文件已经依靠其他代码import过，那么可以用在该数组中出现

--------------------------
使用 自定义模式 的示例  <---  仅少数几个服务使用，这里不做演示
import random
rand_int = random.randint(60011, 60020)

server_cfg = {
    'listen_port': rand_int,  # 自定义模式下，自行保证不重复
    'ice_service': 'demo{}'.format(rand_int),  # 自定义模式下，自行保证不重复，不要有特殊字符
}
"""

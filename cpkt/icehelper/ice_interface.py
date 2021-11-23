import inspect
import re
import threading
from importlib import import_module

from cpkt.core import xlogging as lg

_interface_mgr = None
_interface_mgr_locker = threading.Lock()


class _InterfaceMgr(object):

    def __init__(self):
        self._execute_dict = dict()
        self.logger = lg.get_logger(__name__)

    def register(self, func_obj, interface_name, input_checker, output_checker, log_level):
        if interface_name in self._execute_dict:
            self.logger.warning('InterfaceMgr register [{}] ({}:{}) already in'.format(
                interface_name, func_obj.__qualname__, inspect.getfile(func_obj)))

        self.logger.info('InterfaceMgr register [{}] -> ({}:{})'.format(
            interface_name, func_obj.__qualname__, inspect.getfile(func_obj)))

        self._execute_dict[interface_name] = [
            input_checker,
            func_obj,
            output_checker,
            log_level
        ]

    def get_execute_dict(self):
        return self._execute_dict

    @staticmethod
    def get_inst():
        global _interface_mgr
        global _interface_mgr_locker

        if _interface_mgr:
            return _interface_mgr

        with _interface_mgr_locker:
            if not _interface_mgr:
                _interface_mgr = _InterfaceMgr()

        _interface_mgr_locker = None  # 不再使用，直接销毁
        return _interface_mgr


def fetch_ice_interface(module_list, logger=None, ignore_exception=False):
    """
    :param module_list: ['parket1.parket2.moudule_name', ]
    :param logger:
    :param ignore_exception: 是否忽略模块加载错误
    :return: {'interface_name':[input_checker, func, output_checker]}
    """
    if not module_list:
        return _InterfaceMgr.get_inst().get_execute_dict()

    if not logger:
        logger = lg.get_logger(__name__)

    for module in module_list:
        try:
            module = import_module(module)
        except Exception as e:
            logger.warning('can not import_module {} e:{}'.format(module, e))
            if not ignore_exception:
                raise

    return _InterfaceMgr.get_inst().get_execute_dict()


def register(interface_name, input_checker=None, output_checker=None, log_level=None):
    """将被装饰的函数添加到服务接口列表中

    被装饰的函数需要支持以下签名
    def func(params, sender):
        return result

    参数为：
        params 输入的参数
            当没有 input_checker 时，该值类型为 dict。
                被装饰的函数必须在注释中说明其结构定义，并在编码中自行对有效性进行检查
            当有 input_checker 时，该值为反序列化器指定类型。
        sender 发送者的 router_locator
            当需要回调发送者时，可传入该值
        result 返回值
            当没有 output_checker 时，该值类型为 None 或 可序列化为json字符串的dict
            当有 output_checker 时，该值类型为序列化器指定类型

    序列化器 与 反序列化器 的使用见 demo

    :param interface_name: 服务接口的名称，不可有除开 _ 以外的特殊字符
    :param input_checker: 输入参数的反序列化器
    :param output_checker: 输出结果的序列化器
    :param log_level: 日志级别 cpkt/icehelper/router_rpc.py
                        LOG_INFO = 'i'
                        LOG_DEBUG = 'd'
                        LOG_NONE = 'n'
    """

    def wrap_func(func):
        assert interface_name
        assert re.match(r'^[\d\w_]+$', interface_name)
        _InterfaceMgr.get_inst().register(func, interface_name, input_checker, output_checker, log_level)

        return func

    return wrap_func

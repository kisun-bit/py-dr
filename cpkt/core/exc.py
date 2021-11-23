import logging
from datetime import datetime

from cpkt.core import rt

try:
    from cpkt.rpc import ice

    SystemErrorException = ice.Utils.SystemError
except Exception as e:
    _ = e
    SystemErrorException = Exception


class CpktException(SystemErrorException):
    """标准异常类

    :remark:所有跨类的异常必须使用本异常类
            或者使用派生自该类的异常类
    """

    class CpktExcContext(object):
        """记录异常栈的自定义上下文"""

        def __init__(self, msg: str, frame_level: int):
            self.msg = msg
            self.date_time = datetime.now()
            self.func_name, self.file_lineno, self.module_name = rt.get_back_function_info(frame_level)

    def __init__(self, description: str, debug: str, code: int = 0):
        """
        :param description: 描述信息，用户可读的内容
        :param debug: 调试信息，工程师可读的内容，
        :param code: 错误代码，0为不特指
        """
        super(CpktException, self).__init__()
        self.description = description
        self.debug = debug
        self.rawCode = code
        self._traces = list()
        self._traces.append(CpktException.CpktExcContext('{}   {}'.format(description, debug), 3))

    def add_more_debug(self, debug: str):
        """添加更多调试信息

        :param debug: 追加的调试信息
        """
        self._traces.append(CpktException.CpktExcContext(debug, 2))
        if debug:
            self.debug += '\n-----\n{}'.format(debug)

    def change_description(self, description):
        """更换描述信息

        :param description: 新的描述信息
        """
        old_description = self.description
        self.description = description
        self._traces.append(CpktException.CpktExcContext(
            'alter description {}  ->  {}'.format(old_description, self.description), 2)
        )


def generate_exception_and_logger(
        description, debug, code, logger=None, module_name=None, caller_level=1, exception_class=CpktException):
    """
    创建异常，并打印调试日志
    :param description: CpktException.description
    :param debug: CpktException.debug
    :param code: CpktException.code
    :param logger: None意为使用module_name对应的logger
    :param module_name: None意为自动获取调用者模块名
    :param caller_level: 设置调用者相对于该调用的调用栈层数，从1开始计数
    :param exception_class: 生成的异常类型，应派生自CpktException
    """
    func_name, file_lineno, _module_name = rt.get_back_function_info(caller_level)
    if module_name is None:
        module_name = _module_name
    if logger is None:
        logger = logging.getLogger(module_name)

    err_log = r'{func_name}({file_lineno}):{description} debug:{debug}' \
        .format(func_name=func_name, file_lineno=file_lineno, description=description, debug=debug)

    logger.error(err_log)

    return exception_class(description, debug, code)


def standardize_exception(eee: Exception) -> CpktException:
    """标准化异常，将各种异常标准化为 CpktException

    :remark:
        支持 AssertionError:
            当AssertionError的参数为元组，且元素个数为2或3，且前两个元素为str类型时，支持转换为带有特定描述的CpktException
    """

    if isinstance(eee, CpktException):
        return eee

    if isinstance(eee, AssertionError):
        if eee.args:
            if isinstance(eee.args[0], tuple):
                tuple_len = len(eee.args[0])
                if tuple_len == 2 and isinstance(eee.args[0][0], str) and isinstance(eee.args[0][1], str):
                    return CpktException(description=eee.args[0][0], debug=eee.args[0][1])
                if (len(eee.args[0]) == 3 and isinstance(eee.args[0][0], str) and isinstance(eee.args[0][1], str)
                        and isinstance(eee.args[0][2], int)):
                    return CpktException(description=eee.args[0][0], debug=eee.args[0][1], code=eee.args[0][2])
            elif isinstance(eee.args[0], str):
                return CpktException(description='内部异常，代码 {}'.format(eee.__class__.__name__), debug=eee.args[0])

    return CpktException(description='内部异常，代码 {}'.format(eee.__class__.__name__), debug='{}'.format(eee))

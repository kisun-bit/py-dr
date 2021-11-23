import ctypes
import functools
import os
import time

from cpkt.core import xdebug as xd
from cpkt.core import xlogging as lg

_logger = lg.get_logger(__name__)


def check_debug_flag_and_wait(debug_flag_file: str, wait_del_file: str, logger=None):
    try:
        if os.path.exists(debug_flag_file):
            with open(wait_del_file, 'w') as f:
                f.flush()
            time.sleep(1)
        elif os.path.exists(wait_del_file):
            os.remove(wait_del_file)
    except Exception as e:
        if logger:
            logger.warning('check_debug_flag_and_wait: {}'.format(e))

    while os.path.exists(wait_del_file):
        time.sleep(10)
        logger.warning(r'!!! need remove pause flag file : {}'.format(wait_del_file))


def log_native_thread_id(thread_obj, logger=None):
    """用于打印线程的tid
    在 run 方法调用一次
    """
    linux_thread_id = ctypes.CDLL('libc.so.6').syscall(186)
    thread_name = thread_obj.name if thread_obj.name else thread_obj.__class__.__name__
    if logger is None:
        logger = _logger
    logger.info('tid: {}  ----  {}'.format(linux_thread_id, thread_name))


def log_exec_time(logger=None, more_msg='', always_log=False):
    """用于打印方法的执行时间，装饰器
    使用 xdebug 中的标记进行控制
    """

    def _real_decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kv):
            fn_name = fn.__name__

            if (not always_log) and (not xd.flag_name_exist(fn_name)):
                return fn(*args, **kv)

            __logger = logger if logger else _logger
            start_time = time.time()
            result = fn(*args, **kv)
            end_time = time.time()
            consume_time = end_time - start_time
            __logger.debug('log_exec_time: {} {} --- {:.3f}s'.format(fn_name, more_msg, consume_time))
            return result

        return wrapper

    return _real_decorator


if __name__ == "__main__":
    pass

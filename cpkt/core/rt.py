import functools
import glob
import inspect
import os
import pathlib
import shutil

import psutil


def get_back_function_info(level: int):
    """获取栈帧信息

    :param level: 相对于调用者的栈帧层数
    :return:(方法名，文件行号，模块名)
    """
    frame = inspect.currentframe()

    for _ in range(level + 1):
        if frame.f_back:
            frame = frame.f_back

    return get_class_name(frame) + frame.f_code.co_name, frame.f_lineno, get_module_name(frame)


def get_class_name(frame, more_char='.'):
    try:
        return frame.f_locals['self'].__class__.__name__ + more_char
    except (KeyError, AttributeError):
        return ''


def get_module_name(frame):
    return inspect.getmodule(frame).__name__


class PidReplier(object):
    """PID 应答器"""

    @staticmethod
    def is_pid_exists(pid: int, timestamp: int) -> bool:
        try:
            return int(psutil.Process(pid).create_time()) == timestamp
        except Exception as e:
            _ = e  # 查询不到就意味着pid不存在
            return False

    @staticmethod
    def get_current_pid_and_create_timestamp() -> (int, int):
        pid = os.getpid()
        return pid, int(psutil.Process(pid).create_time())


class PathInMount(object):
    """路径与挂载目录"""

    NOT_IN_MOUNT = 0  # 文件不在mount目录下
    DIR_MOUNTED = 1  # 文件在mount目录下，且mount目录已经挂载
    DIR_NOT_MOUNT = 2  # 文件在mount目录下，但是mount目录未挂载

    MOUNT_ROOT = '/home/mnt/nodes/'  # 挂载点的根路径，所有挂载点都挂载到该目录下的目录中

    @staticmethod
    def query_status(file_path: str):
        """查询文件路径类型

        :return:
            NOT_IN_MOUNT, DIR_MOUNTED, DIR_NOT_MOUNT
        """

        if not file_path.startswith(PathInMount.MOUNT_ROOT):
            return PathInMount.NOT_IN_MOUNT

        split_path = pathlib.Path(file_path).parts
        if len(split_path) < 6:  # /, home, mnt, nodes, mount_point, more
            return PathInMount.NOT_IN_MOUNT

        mount_point_path = os.path.join(*split_path[0:5])
        if os.path.ismount(mount_point_path):
            return PathInMount.DIR_MOUNTED
        else:
            return PathInMount.DIR_NOT_MOUNT

    @staticmethod
    def is_in_not_mount(file_path: str):
        """判断给定路径是否在一个未挂载的目录中

        :return:
            True  DIR_NOT_MOUNT
            False NOT_IN_MOUNT, DIR_MOUNTED
        """
        return PathInMount.DIR_NOT_MOUNT == PathInMount.query_status(os.path.realpath(file_path))


def delete_file(file_path) -> bool:
    """删除文件，递归删除目录

    :return:
        True 文件/目录 删除成功
        False 文件/目录 未删除成功
    """

    if os.path.exists(file_path):
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)  # 递归删除目录
            else:
                os.remove(file_path)
        finally:
            return not os.path.exists(file_path)
    else:
        return True


def remove_glob(path_glob: str):
    """根据通配符删除文件"""

    for path in glob.iglob(path_glob):
        os.remove(path)


def remove_glob_list(path_list: list):
    """根据通配符删除文件（多个文件）"""

    for path in path_list:
        remove_glob(path)


class ContextGuard(object):
    """扩展上下文管理器

    :remark:
        将支持with的对象，扩展为支持显式__exit__的对象
        示例：

        with ContextGuard(locker) as c_locker:  # 等同于 with locker: 进入锁空间
            do_some()
            c_locker.exit() # 提前释放锁
            do_more()
    """

    def __init__(self, o):
        assert hasattr(o, '__enter__')
        assert hasattr(o, '__exit__')
        self._ = o
        self.o = None
        self.using = False

    def __enter__(self):
        self.o = self._.__enter__()
        self.using = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.using:
            return

        self.using = False
        self.o = None
        self._.__exit__(exc_type, exc_val, exc_tb)

    def exit(self):
        self.__exit__(None, None, None)


def LockDecorator(locker):
    def _real_decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kv):
            with locker:
                return fn(*args, **kv)

        return wrapper

    return _real_decorator

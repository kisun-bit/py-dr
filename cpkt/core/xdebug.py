import ast
import inspect
import os
import sys
import threading
import time
import traceback
from datetime import datetime

from cpkt.core import rt
from cpkt.core import xlogging as lg

_logger = lg.get_logger(__name__)

_flags = None  # type: list

XDEBUG_THREAD_NAME = 'xdebug'


def flag_on():
    """使用前缀比较，来判断对应调用者的调试开关是否存在（开启）"""
    flags = _flags
    if flags is None:
        return False

    caller = '{2}.{0}'.format(*rt.get_back_function_info(1))

    for flag in flags:
        if caller.startswith(flag):
            return True
    else:
        return False


def flag_exist():
    """判断对应调用者的调试开关是否存在（开启）"""
    flags = _flags
    if flags is None:
        return False

    caller = '{2}.{0}'.format(*rt.get_back_function_info(1))
    return caller in flags


def flag_name_exist(flag_name):
    flags = _flags
    if flags is None:
        return False
    return flag_name in flags


class XDebugHelper(threading.Thread):
    TIMER_INTERVAL_SECS = 10

    def __init__(self, dir_path):
        """
        :param dir_path: 调试辅助线程的目录，后续简称目录

        :remark:
            1. 死锁类现场的调试
                在目录下创建文件 dump_thread，开启记录线程调用栈的功能
                记录线程调用栈的文件 为 dump_thread.txt
            2. 更新调试开关
                在目录下创建文件 flags.txt
                在 flags.txt 文件中，每一行可记录一个调试开关；调试开关的格式 类似 a.b.c
                在 python 对应的文件或函数或类的方法中，调用 flag_on 方法可判断 flags.txt 文件中是否有对应的调试开关
        """

        threading.Thread.__init__(self, name=XDEBUG_THREAD_NAME, daemon=True)

        self.dir_path = dir_path
        self.dump_thread_flag_path = os.path.join(dir_path, 'dump_thread')
        self.dump_thread_file_path = self.dump_thread_flag_path + '.txt'

        self.flags_file_path = os.path.join(dir_path, 'flags.txt')

    def run(self):
        while True:
            try:
                time.sleep(self.TIMER_INTERVAL_SECS)
                self.load_flags()
                self.dump_thread_logic()
            except Exception as e:
                _logger.error('XDebugHelper thread Exception : {}\n{}'.format(e, lg.format_exception(e)))

    def load_flags(self):
        global _flags
        try:
            with open(self.flags_file_path) as f:
                new_flags = [l.strip() for l in f.readlines()]
                if new_flags:
                    _flags = new_flags
                else:
                    _flags = None
        except Exception as e:
            _ = e
            _flags = None

    def dump_thread_logic(self):
        if not os.path.exists(self.dump_thread_flag_path):
            return
        self.dump_all_thread_stack()

    def dump_all_thread_stack(self):
        with open(self.dump_thread_file_path, 'w') as w:
            w.write('=== begin {} ===\n'.format(datetime.now().strftime("%y-%m-%d (%H:%M:%S.%f)")))
            self.all_thread_stack(w)
            w.write('\n=== end {} ===')

    @staticmethod
    def all_thread_stack(w):
        current = threading.get_ident()
        id2name = dict((th.ident, th.name) for th in threading.enumerate())
        for thread_id, stack in sys._current_frames().items():
            if thread_id == current:
                continue
            w.write('  --------------------------------------\nThread {} - {}\n'.format(thread_id, id2name[thread_id]))
            w.write(format_stack(stack))


def format_stack(stack):
    frames = list()

    while stack:
        formatted, _ = format_frame(stack)

        # special case to ignore runcode() here.
        if not (os.path.basename(formatted[0]) == 'code.py' and formatted[2] == 'runcode'):
            frames.append(formatted)

        stack = stack.f_back

    lines = traceback.format_list(frames)

    return ''.join(lines)


def format_frame(frame):
    filename, lineno, function, source, relevant_values, f_locals = get_frame_information(frame)

    lines = lg.format_relevant_values(relevant_values, source)
    lines = lg.format_f_locals(lines, relevant_values, f_locals)

    formatted = '\n    '.join([lg.to_unicode(x) for x in lines])
    return (filename, lineno, function, formatted), source


def get_frame_information(frame):
    class_name = rt.get_class_name(frame)
    frame_info = inspect.getframeinfo(frame)
    filename, function, lineno, source = lg.get_frame_information(frame_info)
    f_locals = frame.f_locals

    try:
        tree = ast.parse(source, mode='exec')
        relevant_values = lg.get_relevant_values(frame, tree)
    except SyntaxError:
        relevant_values = []

    return filename, lineno, class_name + function, source, relevant_values, f_locals

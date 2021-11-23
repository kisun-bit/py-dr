import ast
import inspect
import locale
import logging
import os
import sys
import time
import traceback
from logging import config as logging_config

from cpkt.core import exc
from cpkt.core import rt


def set_logging_config(config_path: str):
    """设置调试日志配置

    :param config_path: 配置文件全路径
    :remark: 如果不设置配置文件，那么所有调试信息将输出到标准输出流
    """
    logging_config.fileConfig(config_path)


def get_logger(name: str):
    """获取调试日志输出对象

    :param name: 一般为 __name__
    """
    return logging.getLogger(name)


def log_with_limit(fn, msg, cache, limit=600, flag=None):
    """限制频次的输出日志
    对于相同flag的日志，限制输出频次低于limit秒

    :param fn: callable 输出日志的方法，接收msg参数
    :param msg: str 日志内容
    :param cache: dict 记录最后一次输出的缓存对象
    :param limit: int 限制的时长，单位秒
    :param flag: str or int or obj 限制频次的唯一标记。如果没有设置，那么就将日志内容作为标记进行限制
    """
    if flag is None:
        flag = msg

    now_t = time.time()
    last_t = cache.get(flag)
    if not last_t or abs(now_t - last_t) > limit:
        cache[flag] = now_t
        fn(msg)


######
# 格式化异常
######

PIPE_CHAR = '|'
CAP_CHAR = '->'

ENCODING = locale.getpreferredencoding()


def format_current_exception():
    """

    :remark: 只能在except语块中使用
    :return:
    """
    ___, exc_value___, exc_traceback___ = sys.exc_info()
    try:
        track = ''.join(_format_exception(exc_value___, exc_traceback___))
        if isinstance(exc_value___, exc.CpktException):
            track += ''  # TODO
            ## 什么模块（方法名:行号） 什么时候 ： ： trace_msg
        return track
    finally:
        del exc_traceback___


def format_exception(exc_value___: Exception):
    exc_traceback___ = exc_value___.__traceback__
    track = ''.join(_format_exception(exc_value___, exc_traceback___))
    if isinstance(exc_value___, exc.CpktException):
        track += ''  # TODO
        ## 什么模块（方法名:行号） 什么时候 ： ： trace_msg
    return track


def _format_exception(value, tb, seen=None):
    # Implemented from built-in traceback module:
    # https://github.com/python/cpython/blob/a5b76167dedf4d15211a216c3ca7b98e3cec33b8/Lib/traceback.py#L468

    exc_type, exc_value, exc_traceback = type(value), value, tb

    if seen is None:
        seen = set()

    seen.add(id(exc_value))

    if exc_value:
        if exc_value.__cause__ is not None and id(exc_value.__cause__) not in seen:
            for text in _format_exception(exc_value.__cause__, exc_value.__cause__.__traceback__, seen=seen):
                yield text
            yield "\nThe above exception was the direct cause of the following exception:\n\n"
        elif exc_value.__context__ is not None and id(
                exc_value.__context__) not in seen and not exc_value.__suppress_context__:
            for text in _format_exception(exc_value.__context__, exc_value.__context__.__traceback__, seen=seen):
                yield text
            yield "\nDuring handling of the above exception, another exception occurred:\n\n"

    if exc_traceback is not None:
        yield 'Traceback (most recent call last):\n'

    formatted, source = format_traceback(exc_traceback)

    yield formatted

    if not str(value) and exc_type is AssertionError:
        value.args = (source,)
    title = traceback.format_exception_only(exc_type, value)

    yield ''.join(title).strip() + '\n'


def format_traceback(tb=None):
    omit_last = False
    if not tb:
        try:
            raise Exception()
        except Exception as e_:
            _ = e_
            omit_last = True
            _, _, tb = sys.exc_info()
            assert tb is not None

    frames = []
    final_source = ''
    while tb:
        if omit_last and not tb.tb_next:
            break

        formatted, source = format_traceback_frame(tb)

        # special case to ignore runcode() here.
        if not (os.path.basename(formatted[0]) == 'code.py' and formatted[2] == 'runcode'):
            final_source = source
            frames.append(formatted)

        tb = tb.tb_next

    lines = traceback.format_list(frames)

    return ''.join(lines), final_source


def format_traceback_frame(tb):
    filename, lineno, function, source, relevant_values, f_locals = get_traceback_information(tb)

    lines = format_relevant_values(relevant_values, source)
    lines = format_f_locals(lines, relevant_values, f_locals)

    formatted = '\n    '.join([to_unicode(x) for x in lines])
    return (filename, lineno, function, formatted), source


def to_unicode(val):
    if isinstance(val, (bytearray, bytes)):
        v = val[:32]
        more = '' if len(val) < 32 else '...'
        try:
            return 'b[{}{}]'.format(v.decode(ENCODING), more)
        except Exception as e_:
            _ = e_
            return '{}{}'.format(v, more)

    return val


def format_f_locals(lines, relevant_values, f_locals):
    relevant_keys = [rv[0] for rv in relevant_values]

    for k in sorted(f_locals):
        if k in relevant_keys:
            continue
        if k[:2] == '__' and k[-2:] == '__':
            continue
        elif k[-3:] == '___':
            continue
        else:
            lines.append('- {} : {}'.format(k, to_unicode(f_locals[k])))

    return lines


def format_relevant_values(relevant_values, source):
    lines = [source]
    for i in reversed(range(len(relevant_values))):
        _, col, val = relevant_values[i]
        pipe_cols = [pcol for _, pcol, _ in relevant_values[:i]]
        line = ''
        index = 0
        for pc in pipe_cols:
            line += (' ' * (pc - index)) + PIPE_CHAR
            index = pc + 1

        line += '{}{} {}'.format((' ' * (col - index)), CAP_CHAR, val)
        lines.append(line)

    return lines


def get_traceback_information(tb):
    class_name = rt.get_class_name(tb.tb_frame)
    frame_info = inspect.getframeinfo(tb)
    filename, function, lineno, source = get_frame_information(frame_info)
    f_locals = tb.tb_frame.f_locals

    try:
        tree = ast.parse(source, mode='exec')
        relevant_values = get_relevant_values(tb.tb_frame, tree)
    except SyntaxError:
        relevant_values = []

    return filename, lineno, class_name + function, source, relevant_values, f_locals


def get_frame_information(frame_info):
    filename = frame_info.filename
    lineno = frame_info.lineno
    function = frame_info.function
    try:
        source = ''.join(frame_info.code_context)
    except Exception as e_:
        _ = e_
        source = 'fetch code failed:{}({})'.format(filename, lineno)
    source = source.strip()

    return filename, function, lineno, source


def get_relevant_values(frame, tree):
    names = get_relevant_names(tree)
    values = []

    for name in names:
        text = name.id
        col = name.col_offset
        if text in frame.f_locals:
            val = frame.f_locals.get(text, None)
            values.append((text, col, format_value(val)))
        elif text in frame.f_globals:
            val = frame.f_globals.get(text, None)
            values.append((text, col, format_value(val)))

    values.sort(key=lambda e_: e_[1])

    return values


def get_relevant_names(tree):
    return [node for node in ast.walk(tree) if isinstance(node, ast.Name)]


def format_value(v):
    try:
        v = to_unicode(v)
        v = repr(v)
    except KeyboardInterrupt:
        raise
    except BaseException as e_:
        _ = e_
        v = '<unprintable {} object>'.format(type(v).__name__)

    return v

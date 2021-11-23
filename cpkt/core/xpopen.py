import io
import locale
import os
import shlex
import subprocess
import sys
import threading

from cpkt.core import xlogging as lg
from cpkt.data import define

_logger = lg.get_logger(__name__)
_module_locker = threading.Lock()

if os.name == 'posix':
    import select

PREFERRED_ENCODING = locale.getpreferredencoding(False)

HIGH_OR_EQ_36 = sys.version_info[0] >= 3 and sys.version_info[1] >= 6
PY2 = sys.version_info[0] < 3


def delay_execute_cmd(delay: float, cmd, timeout=None, shell=True, **kwargs):
    kwargs['cmd'] = cmd
    kwargs['timeout'] = timeout
    kwargs['shell'] = shell

    # noinspection PyTypeChecker
    _timer = threading.Timer(interval=delay, function=execute_cmd, kwargs=kwargs)
    _timer.start()
    return _timer


def execute_cmd(cmd, timeout=None, shell=True, input_string=None,
                encoding=PREFERRED_ENCODING, errors='replace', **kwargs):
    """执行命令行

    :return (int, str, str) return_code, stdout, stderr
    """
    _popen = new_popen(cmd, shell, input_string is not None, encoding, errors, **kwargs)

    if input_string is not None and not input_string.endswith(os.linesep):
        input_string = '{}{}'.format(input_string, os.linesep)  # 换行

    if not HIGH_OR_EQ_36 and input_string is not None:
        input_string = input_string.encode(encoding=encoding)

    return_code, stdout, stderr = waite_process(_popen, timeout, input_string)
    if HIGH_OR_EQ_36:
        return return_code, stdout.rstrip(), stderr.rstrip()
    else:
        if PY2:
            return return_code, stdout.rstrip(), stderr.rstrip()
        else:
            return return_code, \
                   stdout.decode(encoding=encoding, errors=errors).rstrip(), \
                   stderr.decode(encoding=encoding, errors=errors).rstrip()


def execute_cmd_output_lines(cmd, timeout=None, shell=True, input_string=None,
                             encoding=PREFERRED_ENCODING, errors='replace', **kwargs):
    """执行命令行

    :return (int, list[str, ], list[str, ]) return_code, stdout, stderr

    备注：将execute_cmd返回的stdout与stderr使用splitlines进行分行处理
    """
    r, stdout, stderr = execute_cmd(
        cmd=cmd, timeout=timeout, shell=shell, input_string=input_string,
        encoding=encoding, errors=errors, **kwargs
    )
    return r, stdout.splitlines(), stderr.splitlines()


def waite_process(process, timeout=None, input_string=None):
    def kill():
        _logger.warning('waite_process timeout, begin os.kill({}, 9)'.format(process.pid))
        try:
            os.kill(process.pid, 9)  # windows has no signal.SIGKILL
        except Exception as e:
            _ = e  # 忽略所有异常
        _logger.warning('waite_process timeout, end os.kill({}, 9)'.format(process.pid))

    if PY2:
        _timer = None
        try:
            if isinstance(timeout, int) and timeout > 0:
                def _kill_delay():
                    if process.poll() is None:  # 超时
                        kill()
                    else:
                        pass  # 已经退出

                _timer = threading.Timer(interval=timeout, function=_kill_delay)
                _timer.start()

            stdout, stderr = process.communicate(input=input_string)
        finally:
            if _timer:
                _timer.cancel()

        return process.returncode, stdout, stderr
    else:
        with process:
            try:
                stdout, stderr = process.communicate(timeout=timeout, input=input_string)
            except subprocess.TimeoutExpired:
                kill()
                stdout, stderr = process.communicate()  # 需要再一次获取，防止进程变成 Z状态
        return process.returncode, stdout, stderr


def new_popen(cmd, shell=True, input_string=False, encoding=None, errors=None, **kwargs):
    def _calc_args():
        if shell and not isinstance(cmd, str):
            return subprocess.list2cmdline(cmd)
        if not shell and isinstance(cmd, str):
            return shlex.split(cmd)
        return cmd

    params = kwargs.copy()  # type: dict
    params['args'] = _calc_args()
    params['shell'] = shell
    params['stdout'] = subprocess.PIPE
    params['stderr'] = subprocess.PIPE

    if input_string:
        params['stdin'] = subprocess.PIPE

    if HIGH_OR_EQ_36:
        params['universal_newlines'] = True
        params['encoding'] = encoding
        params['errors'] = errors

    if sys.platform == 'win32':
        with _module_locker:  # windows multi thread new popen will hang
            return subprocess.Popen(**params)
    else:
        return subprocess.Popen(**params)


class Pipe4Process(object):
    def __init__(self, enable_in=False):
        if enable_in:
            self.pipe = {'out': os.pipe(), 'err': os.pipe(), 'in': os.pipe()}
        else:
            self.pipe = {'out': os.pipe(), 'err': os.pipe(), 'in': (None, None,)}

    def destroy(self):
        if not self.pipe:
            return

        for rw in self.pipe.values():
            self._close_pipe(rw[0])
            self._close_pipe(rw[1])
        self.pipe = None

    @staticmethod
    def _close_pipe(fd):
        if not fd:
            return
        try:
            os.close(fd)
        except Exception as e:
            _ = e  # do nothing

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _ = exc_type
        _ = exc_val
        _ = exc_tb
        self.destroy()


class Process(threading.Thread):
    """异步进程对象，仅支持linux"""

    def __init__(self, p4p: Pipe4Process, popen: subprocess.Popen, stdout: bool, stderr: bool, logger_fn):
        super(Process, self).__init__(name='[Process_{}]'.format(popen.pid), daemon=True)
        self._p4p = p4p
        self._popen = popen  # type: subprocess.Popen
        self._stdout = io.StringIO() if stdout else None
        self._stderr = io.StringIO() if stderr else None
        self.logger_fn = logger_fn

    def __getattr__(self, name):
        """
        支持 pid
        """
        assert name in ('pid',), '无效的方法名 {}'.format(name)
        return getattr(self._popen, name)

    def logger(self, more, msg):
        self.logger_fn('{}({}) {}'.format(self.name, more, msg))

    def write_stdin(self, input_str: str):
        """将字符串写入标准输入
        :param input_str: 需要调用者传入 \n
        """
        stdin = self._p4p.pipe['in'][1]
        assert stdin, '异步进程对象未启用stdin'
        self.logger('in', input_str)
        os.write(stdin, input_str.encode(encoding=PREFERRED_ENCODING))

    def read_stdout(self):
        """读取实时stdout，非阻塞
        注意：不保证一定是按行输出，可能在某行的中间截断
              如果确定进程是按行输出（有换行符号），那么使用 read_stdout_lines
        """
        assert self._stdout, '异步进程对象未启用stdout'
        return self._stdout.read()

    def read_stderr(self):
        """读取实时stderr，非阻塞
        注意：不保证一定是按行输出，可能在某行的中间截断
              如果确定进程是按行输出（有换行符号），那么使用 read_stderr_lines
        """
        assert self._stderr, '异步进程对象未启用stderr'
        return self._stderr.read()

    def _log_std_content(self, std, content):
        for line in content.splitlines():
            if not line:
                continue
            self.logger(std, line)

    def run(self):
        with self._p4p:
            try:
                self.logger('info', 'thread begin poll')
                self.run_()
                self.logger('info', 'thread end poll')
            except Exception as e:
                self.logger('err', 'thread poll failed {}'.format(e))

    def run_(self):
        pipes = [self._p4p.pipe['out'][0], self._p4p.pipe['err'][0], ]
        timeout = 1  # 每1秒判断一次进程是否已退出
        while self._popen.poll() is None:
            self.fetch_out_and_err(pipes, timeout)
        self._popen.wait()  # 等待命令执行结束
        self.fetch_out_and_err(pipes, 0)

    def fetch_out_and_err(self, pipes, timeout):
        for fd in select.select(pipes, [], [], timeout)[0]:
            buf = os.read(fd, 4096)
            if not len(buf):
                continue
            output_str = buf.decode(encoding=PREFERRED_ENCODING, errors='replace')
            if fd == pipes[0]:
                self._log_std_content('out', output_str)
                self._stdout.write(output_str) if self._stdout else None
            else:
                self._log_std_content('err', output_str)
                self._stderr.write(output_str) if self._stderr else None

    def communicate(self):
        """同步等待进程退出
        :return: returncode, stdout, stderr

        注意：如果有异步读取过 stdout 或 stderr，那么此时 stdout 与 stderr 返回的是还未读取过的值
        """
        self._popen.wait()
        self.join()
        stdout = self._stdout.read() if self._stdout else ''
        stderr = self._stderr.read() if self._stderr else ''
        return self._popen.returncode, stdout, stderr

    @property
    def return_code(self):
        self.join()
        return self._popen.returncode

    @staticmethod
    def create(cmd, shell=True, stdout=True, stderr=True, stdin=False, cwd=None, env=None,
               log_level=define.Base.LOG_LEVEL_DEBUG, logger=None):
        """创建 Process 对象，异步进程对象

        :param cmd: str     执行进程
        :param shell: bool  是否在shell中
        :param stdout: bool 是否启用 stdout 缓存
        :param stderr: bool 是否启用 stderr 缓存
        :param stdin: bool  是否支持 stdin
        :param cwd: str     工作目录
        :param env:         环境变量
        :param log_level:   调试日志等级
        :param logger:      调试日志对象，None为不打印日志；非None将使用该logger打印 stdout stderr stdin

        注意当不启用stdout缓存时，依然会打印调试日志
        """
        logger_fn = define.Base.logger_fn(log_level, [logger, _logger, ])
        p4p = Pipe4Process(stdin)

        try:
            popen = subprocess.Popen(cmd, shell=shell, cwd=cwd, env=env,
                                     stdout=p4p.pipe['out'][1], stderr=p4p.pipe['err'][1], stdin=p4p.pipe['in'][0], )
            logger_fn('popen new pid {} : {}'.format(popen.pid, cmd))
            process = Process(p4p, popen, stdout, stderr, logger_fn)
            process.start()
            return process
        except Exception as e:
            p4p.destroy()
            logger_fn('Process.create failed. {} - {}'.format(e, cmd), exc_info=True)
            raise e


def find_pid_grep_by_str(_str):
    """匹配字符串，查询进程号"""

    cmd = "ps -ef | grep '{}' | grep -v grep | ".format(_str) + "awk '{print $2}'"
    r, out, err = execute_cmd_output_lines(cmd)
    if not out or r != 0:  # 执行命令失败，或out为空list
        return None
    else:
        return [int(_) for _ in out]

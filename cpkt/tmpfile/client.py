import json
import mmap
import os
import time

from cpkt.core import rt
from cpkt.core import xlogging
from cpkt.tmpfile import common

_logger = xlogging.get_logger(__name__)

pid, pid_create_timestamp = rt.PidReplier.get_current_pid_and_create_timestamp()

delaydel_prx = None  # ice代理


def set_delaydel_prx(_delaydel_prx):
    """为client设置ice代理，初始化临时文件管理功能"""

    global delaydel_prx
    delaydel_prx = _delaydel_prx


class TmpFile(object):
    """客户端接口（对用户，对服务端），添加临时文件任务的接口，以及对临时文件任务的操作接口

    描述：
        1、工作原理：
            构造实例：构造该类的实例时，client将参数传给server，由server添加任务，并返回任务返回值（日志文件路径，记录
            的索引号）给client，通过返回值，client建立当前任务的mmap映射，通过mmap映射提供当前任务的操作接口

            临时文件任务的操作接口：
                1）设置删除 fn：set_delete
                2）取消删除 fn：cancel_delete
                3）设置删除时间 fn：set_delete_time

        2、client如何与server通信：
            client —> watch power —> server —> client
            通信流程：
                1）boxService启动server，并为client创建Powerpxy代理：set_delaydel_prx
                2）client将获取的参数转为json fn：__json_params
                3）client通过代理 Powerpxy 调用server创建任务的接口，并获取返回值 fn：__parse_server_return

        3、client建立任务日志文件的mmap映射
            1）获取server的返回值
            2）通过mmap与任务日志文件建立映射 fn：__get_mmap_handle

    属性:
        file_path：临时文件路径
        caller_msg：调用者信息（包含：创建"临时文件"的代码路径以及所在代码行号），可为空
    """

    def __init__(self, file_path: str, delay_delete_seconds: int, caller_msg=None):
        self.mmap_handle = None
        self.is_changed = False  # 当前任务默认未被操作

        self.file_path = os.path.realpath(file_path)  # 传入的临时文件路径一律转为真实路径
        assert len(self.file_path) <= common.FILE_PATH_MAX_LENGTH

        self.delay_delete_seconds = delay_delete_seconds  # 延迟删除时间(秒)

        if not caller_msg:
            self.caller_msg = '{2}.{0}({1})'.format(*rt.get_back_function_info(1))
        else:
            self.caller_msg = caller_msg

        self.index, self.logfile_path = self._parse_server_return(self.__json_params)  # 获取服务端返回值

        self.__create_mmap_handle()  # 获取mmap句柄

        self.record_manipulate = common.RecordManipulate()  # 实例:字段解析器

    def __del__(self):
        self.__destroy_mmap_handle()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """如果当前任务未作任何修改，则自动调用 set_delete() 走删除流程"""

        try:
            if not self.is_changed:
                self.__set_delete()
        finally:
            self.__destroy_mmap_handle()

    def __create_mmap_handle(self):
        """获取映射句柄"""

        assert not self.mmap_handle
        with open(self.logfile_path, "r+b") as f:
            mmap_handle = mmap.mmap(f.fileno(), 0)
            self.mmap_handle = mmap_handle

    def __destroy_mmap_handle(self):
        if self.mmap_handle:
            self.mmap_handle.close()
            self.mmap_handle = None

    def __set_changed(self):
        assert not self.is_changed
        self.is_changed = True

    def get_record_dict(self):
        """获取record，并解析为字典格式"""

        begin_offset, end_offset = common.calc_offset(self.index)
        return self.record_manipulate.record_parse(self.mmap_handle[begin_offset:end_offset])

    @property
    def __json_params(self) -> str:
        """参数组合为json字符串"""

        param_dict = {
            "pid": pid,
            "file_path": self.file_path,
            "caller_msg": self.caller_msg,
            "pid_create_timestamp": pid_create_timestamp,
            "delete_timestamp": common.EMPTY_TIMESTAMP_STR
        }
        return json.dumps(param_dict)

    @staticmethod
    def _parse_server_return(json_params: json):
        """解析服务端返回值"""

        server_return = delaydel_prx.addDelayDelItem(json_params)
        server_return = json.loads(server_return)
        index = server_return['index']
        logfile_path = server_return['logfile_path']
        _logger.debug("服务端返回值：index={}，logfile_path={}".format(index, logfile_path))
        return index, logfile_path

    def __write(self, new_record):
        """优先写入状态位(第0位字符)后面的字符"""

        begin_offset = common.RECORD_LENGTH * (self.index - 1)
        end_offset = begin_offset + common.RECORD_LENGTH

        self.mmap_handle[(begin_offset + 1):end_offset] = new_record[1:]
        self.mmap_handle.flush()
        self.mmap_handle[begin_offset] = new_record[0]
        self.mmap_handle.flush()

    def __set_delete(self):
        """自动设置删除状态（当前任务未作任何操作时调用该方法）：日志状态改为 STATUS_WAIT_DELETE"""

        # 确保未作修改
        assert not self.is_changed

        set_timestamp = int(time.time())  # 当前操作的时间戳
        record_dict = self.get_record_dict()
        record_dict['status'] = common.STATUS_WAIT_DELETE
        record_dict['change_timestamp'] = set_timestamp
        record_dict['delete_timestamp'] = set_timestamp + self.delay_delete_seconds  # 设置删除时间

        new_record = self.record_manipulate.dict2record(record_dict)
        self.__write(new_record)
        _logger.debug("文件(index{}):{}，已设置为删除状态".format(self.index, self.file_path))

    def cancel_delete(self):
        """取消删除：日志状态改为 STATUS_NOT_DELETE """

        self.__set_changed()  # 记录操作状态

        # 设置取消状态
        record_dict = self.get_record_dict()
        record_dict['status'] = common.STATUS_NOT_DELETE
        record_dict['change_timestamp'] = int(time.time())

        new_record = self.record_manipulate.dict2record(record_dict)
        self.__write(new_record)
        _logger.debug("文件(index{}):{}，已取消删除".format(self.index, self.file_path))

    def confirm_delete(self):
        """确认删除：日志状态改为 STATUS_WAIT_DELETE"""

        self.__set_delete()  # 设置删除状态
        self.__set_changed()  # 记录操作状态

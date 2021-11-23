# -*- coding: utf-8 -*-
import mmap
import os
import threading
import time

from cpkt.core import rt
from cpkt.core import xlogging as lg
from cpkt.tmpfile import common

_logger = lg.get_logger(__name__)

persistence_manager = None  # type: PersistenceManager
index_allocator = None  # type: IndexAllocator
background_thread = None  # type: DelayDelWorker


def init_server(persistence_file_path: str):
    """初始化服务端"""

    init_persistence(persistence_file_path)

    # 后台工作器
    global background_thread
    assert background_thread is None
    background_thread = DelayDelWorker(persistence_manager)
    background_thread.start()


def init_persistence(persistence_file_path):
    # 如果日志文件不存在,创建
    if not os.path.exists(persistence_file_path):
        _logger.info('persistence_file_path not exist : {}'.format(persistence_file_path))
        with open(persistence_file_path, 'a+b') as f:
            for i in range(common.MAX_INDEX):
                f.write(common.ERASE_STR.encode('utf-8'))
        os.system('sync')

    # 持久化管理器
    global persistence_manager
    assert persistence_manager is None
    persistence_manager = PersistenceManager(persistence_file_path)

    # 空间分配器
    global index_allocator
    assert index_allocator is None
    index_allocator = IndexAllocator(persistence_manager)


class PersistenceManager(object):
    """持久化管理器

    描述：
        1、全局唯一
        2、构造时与任务日志文件建立mmap映射
        3、对外提供以下三种操作：
            1、擦除记录 fn：erase(index)
            2、写入记录 fn：write(index)
            3、读取记录 fn：read(index)
    """

    def __init__(self, logfile_path):
        self.logfile_path = logfile_path
        self.mmap_handle = None
        self.__create_mmap_handle()  # 初始化mmap映射

    def __del__(self):
        self.__destroy_mmap_handle()

    def __destroy_mmap_handle(self):
        if self.mmap_handle:
            self.mmap_handle.close()
            self.mmap_handle = None

    def __create_mmap_handle(self):
        """获取mmap句柄"""

        with open(self.logfile_path, "r+b") as f:
            self.mmap_handle = mmap.mmap(f.fileno(), 0)

    def erase(self, index: int):
        """优先擦除状态位(第0位字符)"""

        begin_offset, end_offset = common.calc_offset(index)

        self.mmap_handle[begin_offset] = common.ERASE_BINARY[0]
        self.mmap_handle.flush()
        self.mmap_handle[(begin_offset + 1): end_offset] = common.ERASE_BINARY[1:]
        self.mmap_handle.flush()

    def write(self, index: int, new_record: bytes):
        """优先写入状态位(第0位字符)后面的字符"""

        begin_offset, end_offset = common.calc_offset(index)
        assert len(new_record) == common.RECORD_LENGTH

        self.mmap_handle[(begin_offset + 1):end_offset] = new_record[1:]
        self.mmap_handle.flush()
        self.mmap_handle[begin_offset] = new_record[0]
        self.mmap_handle.flush()

    def read(self, index: int) -> bytes:
        """读取index对应记录"""

        begin_offset, end_offset = common.calc_offset(index)
        return self.mmap_handle[begin_offset:end_offset]

    def is_empty(self, index: int) -> bool:
        """判断index对应记录是否为空。判断方式：首字符是否为空"""

        begin_offset, _ = common.calc_offset(index)
        return self.mmap_handle[begin_offset] == common.PLACE_HOLDER_BINARY

    def is_logfile_empty(self):
        """判断整个日志文件是否为空"""

        for idx in range(common.MIN_INDEX, common.MAX_INDEX + 1):
            if not self.is_empty(idx):
                return False
        else:
            return True


class IndexAllocator(object):
    """空间分配器,对外提供一个获取可用index的接口

    描述：
        1、对外接口 fn：get_available_index
        2、工作原理：
            当对外接口被调用，该空间分配器轮询任务日志表，直到获取到可用index，并返回该index
    """

    class NotFindAvailableIndex(Exception):
        pass

    def __init__(self, pm: PersistenceManager):
        self.persistence_manager = pm
        self.lock = threading.Lock()
        self.pointer = common.MIN_INDEX  # index指针

    def get_available_index(self) -> (int, PersistenceManager):
        """获取可用空间 index

        :raise:
            IndexAllocator.NotFindEmpty 当搜索完毕所有记录位都无法找到可用 index 时抛出
        :remark:
            index 的有效范围在 [MIN_INDEX, MAX_INDEX]
        """

        count = 0  # 轮询计数指针

        with self.lock:
            while True:
                # 限定index指针扫描范围
                if self.pointer > common.MAX_INDEX:
                    self.pointer = common.MIN_INDEX

                # 轮询计数器
                count = self.__check_counter(count)

                # 获取可用的index
                if self.persistence_manager.is_empty(self.pointer):  # 如果当前pointer所在记录为空
                    available_index = self.pointer
                    self.pointer = self.pointer + 1
                    _logger.debug("找到可用index: {}".format(available_index))
                    return available_index, self.persistence_manager
                else:
                    self.pointer = self.pointer + 1

    def __check_counter(self, count: int) -> int:
        """轮询计数器，轮询数超过 MAX_COUNT_TIMES，抛出异常"""

        max_scan_count_times = common.MAX_SCAN_TIMES * common.MAX_INDEX
        if count > max_scan_count_times:
            _logger.error('搜索完毕{}条记录位,没有找到可用 index'.format(max_scan_count_times))
            raise self.NotFindAvailableIndex
        else:
            return count + 1


class Worker(object):
    """日志处理器

    描述：
        1、工作原理：
            1）判断传入的记录record的操作条件，进行对应操作
            2）操作(文件操作、记录操作)：
                a.删除条件：删除文件，并且擦除记录
                b.取消条件：不删除文件，擦除记录
                c.不处理：不删除文件，也不擦除记录

    属性：
        idx：记录所在任务日志表的索引号
        record：任务记录（bytes格式）
    """

    def __init__(self, idx: int, record: bytes, pm: PersistenceManager):
        self.idx = idx
        self.record = record
        self.persistence_manager = pm

        self.record_dict = common.RecordManipulate.record_parse(self.record)
        self.pid = self.record_dict['pid']
        self.index = self.record_dict['index']
        self.status = self.record_dict['status']
        self.file_path = self.record_dict['file_path']
        self.delete_timestamp = self.record_dict['delete_timestamp']
        self.pid_create_timestamp = self.record_dict['pid_create_timestamp']

    def _del_file(self) -> bool:
        """文件删除:
            1、非挂载类型文件、挂载类型且已挂载文件，走删除流程
            2、挂载类型文件但未挂载文件，不做操作
        """

        if rt.PathInMount.is_in_not_mount(self.file_path):
            return False
        elif rt.delete_file(self.file_path):
            _logger.info("文件(index{}):{}已删除".format(self.index, self.file_path))
            return True
        else:
            _logger.warning("文件(index{}):{}删除失败".format(self.index, self.file_path))
            return False

    def __is_status_not_delete(self) -> bool:
        """是否满足条件：状态为 NOT_DELETE"""

        return self.status == common.STATUS_NOT_DELETE

    def __is_status_waite_del_and_time_to_delete(self) -> bool:
        """是否满足条件：状态为 WAIT_DELETE 且已设置删除时间时 且删除时间已到"""

        return (self.status == common.STATUS_WAIT_DELETE
                and isinstance(self.delete_timestamp, int)
                and int(time.time()) >= self.delete_timestamp)

    def __is_status_unknown_and_caller_pid_killed(self) -> bool:
        """是否满足条件：状态为 UNKNOWN 且调用者进程是否已死"""

        if self.status == common.STATUS_UNKNOWN:
            return not rt.PidReplier.is_pid_exists(self.pid, self.pid_create_timestamp)

    def _is_delete_condition(self) -> bool:
        """是否符合文件删除条件"""

        if self.__is_status_waite_del_and_time_to_delete():
            return True  # 确认删除状态，且删除时间已到
        elif self.__is_status_unknown_and_caller_pid_killed():
            return True  # UNKNOWN 状态，且调用者 PID 不存在
        else:
            return False

    def work(self):
        """执行任务"""

        # 符合文件删除条件：删除文件，擦除记录
        if self._is_delete_condition():
            _logger.info("文件(index{}):{}符合删除条件".format(self.index, self.file_path))
            if self._del_file():
                self.persistence_manager.erase(self.idx)
                _logger.debug("文件(index{}):{}的记录已擦除".format(self.index, self.file_path))

        # 符合取消条件，不删除文件，擦除记录
        if self.__is_status_not_delete():
            _logger.info("文件(index{}):{}为取消删除状态".format(self.index, self.file_path))
            self.persistence_manager.erase(self.idx)
            _logger.debug("文件(index{}):{}的记录已擦除".format(self.index, self.file_path))

        # other status 不处理
        pass


class ApiForClient(object):
    """对客户端的接口:添加日志

    描述：
        1、工作原理：
            1）获取可用的index（获取获取 index 的时间超出 WAITING_SECONDS 时，抛出异常）
            2）调用字段解析器，将client端的参数格式化为record固定格式
            3）在任务日志文件中写入record
            4）向client端return：index，logfile_path
    """

    @staticmethod
    def add(pid: int,
            file_path: str,
            caller_msg: str,
            delete_timestamp,
            pid_create_timestamp: int,
            status=common.STATUS_UNKNOWN,
            version=common.RECORD_VERSION,
            change_timestamp=common.EMPTY_TIMESTAMP_STR,
            ):
        """添加任务记录"""

        # 获取可用的index
        while True:
            try:
                available_index, pm = index_allocator.get_available_index()
                break
            except IndexAllocator.NotFindAvailableIndex:
                _logger.debug(r'will sleep {}s. because IndexAllocator.NotFindAvailableIndex'.format(common.SLEEP_TIME))
                time.sleep(common.SLEEP_TIME)

        # 格式化参数
        record = common.RecordManipulate.record_format(available_index, version, delete_timestamp,
                                                       int(time.time()), status, change_timestamp, pid,
                                                       pid_create_timestamp, file_path, caller_msg)
        # 写入
        pm.write(available_index, record)
        _logger.debug("添加临时文件:{}".format(file_path))

        return available_index, index_allocator.persistence_manager.logfile_path


class DelayDelWorker(threading.Thread):
    """后台工作器"""

    def __init__(self, pm: PersistenceManager):
        super(DelayDelWorker, self).__init__(name='DelayDelWorker', daemon=True)
        self.persistence_manager = pm

    def run(self):
        """轮询任务日志表，依次处理每一条记录，轮询周期:2分钟"""

        while True:
            _logger.debug("!!!!! {} 启动扫描!!!!!".format(self.name))

            for idx in range(common.MIN_INDEX, common.MAX_INDEX + 1):
                try:
                    record = self.persistence_manager.read(idx)
                    if record[0] != common.PLACE_HOLDER_BINARY:
                        Worker(idx, record, self.persistence_manager).work()
                except Exception as e:
                    _logger.error(lg.format_exception(e))  # 捕获所有异常，保证线程不会退出

            # 扫完一轮，休眠2分钟，重头开始扫
            _logger.debug("日志文件已扫描完一轮，扫描周期为{}秒".format(common.SLEEP_TIME))
            time.sleep(common.SLEEP_TIME)

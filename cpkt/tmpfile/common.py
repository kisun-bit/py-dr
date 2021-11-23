# -*- coding: utf-8 -*-

MIN_INDEX = 1  # 日志文件最小记录数
MAX_INDEX = 40960  # 日志文件最大记录数，20MBytes

PLACE_HOLDER_CHAR = " "  # 空字符
PLACE_HOLDER_BINARY = PLACE_HOLDER_CHAR.encode('utf-8')[0]

SLEEP_TIME = 120  # 日志扫描周期

RECORD_LENGTH = 512  # 每条记录长度

PID_LENGTH = 8
INDEX_LENGTH = 4
TIMESTAMP_LENGTH = 8  # 时间戳长度
RECORD_VERSION = "1"  # 记录版本号
STATUS = [  # 状态域
    'n',  # STATUS_NOT_DELETE
    'y',  # STATUS_WAIT_DELETE
    'u',  # STATUS_UNKNOWN
]
STATUS_NOT_DELETE = STATUS[0]
STATUS_WAIT_DELETE = STATUS[1]
STATUS_UNKNOWN = STATUS[2]
FILE_PATH_MAX_LENGTH = 255  # 临时文件绝对路径最大长度
CALLER_MSG_MAX_LENGTH = 201  # 调用者信息最大长度

ERASE_STR = PLACE_HOLDER_CHAR * (RECORD_LENGTH - 1) + "\n"  # 用于表示空记录
ERASE_BINARY = ERASE_STR.encode('utf-8')

FIXED_LENGTH = 56  # 参见 record字符总长度.JPG 固定长度

MAX_SCAN_TIMES = 2  # 空间分配器最大扫描次数

EMPTY_TIMESTAMP_STR = '0' * TIMESTAMP_LENGTH  # 空时间戳

PARAM_STR_LIST = ["index", "version", "delete_timestamp", "create_timestamp", "status", "change_timestamp", "pid",
                  "pid_create_timestamp", "file_path", "caller_msg"]


class RecordManipulate(object):
    """字段解析器"""

    @staticmethod
    def hex2int(hex_str: str):
        return int(hex_str, 16)

    @staticmethod
    def record_parse(record: bytes) -> dict:
        """将存储记录解析为字典格式"""

        record = record.decode('utf-8')
        str_list = record.split("|")
        assert len(str_list) == len(PARAM_STR_LIST)

        params_dict = {
            "status": str_list[PARAM_STR_LIST.index('status')],
            "version": str_list[PARAM_STR_LIST.index('version')],
            "pid": RecordManipulate.hex2int(str_list[PARAM_STR_LIST.index('pid')]),
            "index": RecordManipulate.hex2int(str_list[PARAM_STR_LIST.index('index')]),
            "create_timestamp": RecordManipulate.hex2int(str_list[PARAM_STR_LIST.index('create_timestamp')]),
            "file_path": str_list[PARAM_STR_LIST.index('file_path')].replace(" ", "").replace("\n", ""),
            "caller_msg": str_list[PARAM_STR_LIST.index('caller_msg')].replace(" ", "").replace("\n", ""),
            "pid_create_timestamp": RecordManipulate.hex2int(str_list[PARAM_STR_LIST.index('pid_create_timestamp')]),
            "delete_timestamp": (
                RecordManipulate.hex2int(str_list[PARAM_STR_LIST.index('delete_timestamp')])
                if str_list[PARAM_STR_LIST.index('delete_timestamp')] != EMPTY_TIMESTAMP_STR else EMPTY_TIMESTAMP_STR
            ),
            "change_timestamp": (
                RecordManipulate.hex2int(str_list[PARAM_STR_LIST.index('change_timestamp')])
                if str_list[PARAM_STR_LIST.index('change_timestamp')] != EMPTY_TIMESTAMP_STR else EMPTY_TIMESTAMP_STR
            ),
        }
        return params_dict

    @staticmethod
    def record_format(index, version, delete_timestamp, create_timestamp, status, change_timestamp, pid,
                      pid_create_timestamp, file_path, caller_msg) -> bytes:
        """将参数格式化为存储格式"""

        pid = hex(int(pid))[2:].zfill(PID_LENGTH)
        index = hex(int(index))[2:].zfill(INDEX_LENGTH)
        delete_timestamp = RecordManipulate.timestamp_format(delete_timestamp)
        create_timestamp = RecordManipulate.timestamp_format(create_timestamp)
        change_timestamp = RecordManipulate.timestamp_format(change_timestamp)
        pid_create_timestamp = RecordManipulate.timestamp_format(pid_create_timestamp)
        assert status in STATUS
        assert len(file_path) <= FILE_PATH_MAX_LENGTH

        result = "{}|{}|{}|{}|{}|{}|{}|{}|{}|{}".format(
            index, version, delete_timestamp, create_timestamp, status, change_timestamp,
            pid, pid_create_timestamp, file_path, caller_msg)

        if len(result) > RECORD_LENGTH - 1:
            result = result[:RECORD_LENGTH - 1] + '\n'
        else:
            result = result + (PLACE_HOLDER_CHAR * (RECORD_LENGTH - 1 - len(result))) + '\n'
        return result.encode('utf-8')

    @staticmethod
    def dict2record(record_dict):
        """参数字典格式化为 record"""

        assert set(PARAM_STR_LIST) == set(record_dict.keys())
        params = list()
        for i in PARAM_STR_LIST:
            params.append(record_dict[i])
        return RecordManipulate.record_format(*params)

    @staticmethod
    def timestamp_format(timestamp):
        """时间戳格式化，去掉16进制字符串 '0x' 字符"""

        if timestamp == EMPTY_TIMESTAMP_STR:
            return timestamp
        else:
            return hex(int(timestamp))[2:]  # 去掉16进制字符串 '0x' 字符


def calc_offset(index) -> (int, int):
    """计算index对应的字节偏移 [begin_offset, end_offset)"""
    assert MIN_INDEX <= index <= MAX_INDEX

    begin_offset = RECORD_LENGTH * (index - 1)
    end_offset = begin_offset + RECORD_LENGTH
    return begin_offset, end_offset

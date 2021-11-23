class Base(object):
    LOG_LEVEL_NONE = 'n'
    LOG_LEVEL_DEBUG = 'd'
    LOG_LEVEL_INFO = 'i'

    @staticmethod
    def log_none(*args, **kwargs):
        _ = args
        _ = kwargs
        pass  # do nothing

    @staticmethod
    def logger_fn(log_level, loggers: list):
        """得到调试日志方法

        :param log_level: 调试日志等级
        :param loggers: 复数个日志对象（可为None），按照优先级从头到尾进行查找
        :return: 打印调试日志的方法
        """
        if log_level == Base.LOG_LEVEL_NONE:
            return Base.log_none

        for logger in loggers:
            if logger:
                if log_level == Base.LOG_LEVEL_DEBUG:
                    return logger.debug
                elif log_level == Base.LOG_LEVEL_INFO:
                    return logger.info
                else:
                    pass
        else:
            return Base.log_none


class DiskSnapshotService(object):
    STORAGE_TYPE_QCOW = 'qcow'
    STORAGE_TYPE_CDP = 'cdp'

    CDP_TYPE_SYNC = 's'  # 同步CDP
    CDP_TYPE_ASYNC = 'a'  # 异步CDP

    DIFF_BITMAP_TYPE_NOT_SAME_CHAIN = 'not_same_chain'  # 不在一个快照链中
    DIFF_BITMAP_TYPE_FROM_BEFORE_TO = 'from_before_to'  # from 早于 to
    DIFF_BITMAP_TYPE_FROM_AFTER_TO = 'from_after_to'  # from 晚于 to
    DIFF_BITMAP_TYPE_SAME = 'same'  # from 与 to 是同一个点

    CLW_BOOT_REDIRECT_MBR_UUID = 'clwbootdisk'.ljust(32, '0')
    CLW_BOOT_REDIRECT_GPT_UUID = 'clwbootdisk'.ljust(31, '0') + '1'
    CLW_BOOT_REDIRECT_GPT_LINUX_UUID = 'clwbootdisk'.ljust(31, '0') + '2'

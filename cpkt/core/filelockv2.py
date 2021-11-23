import os
import copy
import fcntl
import time
import threading
import sys


'''不再使用。
# 这个类不是线程安全的，不能多线程使用同一个类。
# inherit表示是否继承，默认不继承。
class file_ex_lock(object):
    STATUS_TIMEOUT = -1
    STATUS_FREE = 1
    STATUS_ALIVE = 0
    def __init__(self, filename, inherit=False):
        self.__filename = copy.copy(filename)
        _open_flag = os.O_RDWR | os.O_CREAT
        if not inherit:
            _open_flag |= os.O_CLOEXEC
        self.__fd = os.open(self.__filename, _open_flag, 0o666)
        if self.__fd <= 0:
            raise SystemError("try_lock({}) os.open error!".format(self.__filename))

    @property
    def filename(self):
        return self.__filename

    def __del__(self):
        if self.__fd > 0:
            # print("unlock")
            os.close(self.__fd)
            self.__fd = 0

    def unlock(self):
        try:
            fcntl.flock(self.__fd, fcntl.LOCK_UN)
        except IOError as _e:
            raise SystemError("fcntl.flock({}) error:{}".format(self.__filename, _e))
        pass

    # 返回 False 表示未等到。返回True表示持有了锁。
    # 有2种方式来实现，一种是阻塞模式，用另外的线程发EINTR信号，一种是非阻塞自己的代码sleep.
    # 因为nfs的 unlock的信号返回非常慢。所以用sleep 的方式更快。
    def try_lock(self, timeout_ms: int =-1):
        timeout_ms = timeout_ms/1000
        if timeout_ms < 0:
            _wait_flag = fcntl.LOCK_EX
        else:
            _wait_flag = fcntl.LOCK_EX | fcntl.LOCK_NB

        while True:
            try:
                fcntl.flock(self.__fd, _wait_flag)
                return True
            except IOError as _e:
                if timeout_ms < 0:
                    # 应该是堵塞，不应该返回的，所以抛异常。
                    os.close(self.__fd)
                    self.__fd = 0
                    raise SystemError("fcntl.flock({}) error:{}".format(self.__filename, _e))
                elif timeout_ms == 0:
                    # 已经等待完成。
                    return False
                else:
                    # 至少是1，所以要等待重试一次。最差100HZ是0.01，所以等等0.02对性能影响应该很小。
                    _w = min(timeout_ms, 0.02)
                    time.sleep(_w)
                    timeout_ms -= _w

    # 检测是不是其他人锁住了。。
    def is_locked_by_others(self):
        if self.try_lock(timeout_ms=0):
            self.unlock()
            return False
        return True

    # 如是返回-1，表示超时，如果返回1，表示没有人持有锁。返回0，表示正常结束等待。
    def wait_keep_alive(self, wait_condition, keepalive_time: int, keepalive_count: int):
        total_time_ms = keepalive_time * keepalive_count * 1000

        for _i in range(keepalive_count):
            if not wait_condition:
                return 0

            _pre_wait = int(time.time())
            _locked = self.try_lock(total_time_ms)
            if not _locked:
                # 未锁住，超时了。
                return self.STATUS_TIMEOUT

            self.unlock()  # 锁住成功，要unlock。
            # 看看是不是很快返回，没有人持有锁。
            if int(time.time()) - _pre_wait <= 2:
                # 1秒内就返回，
                time.sleep(1)
                continue
            # 锁定成功，
            return self.STATUS_ALIVE
        # 很快锁成功的次数超过阀值。没人持有锁。
        return self.STATUS_FREE

    def take_keep_alive(self, take_condition: threading.Event, keepalive_time: int):
        while True:
            _locked = self.try_lock()
            if _locked:
                _status = take_condition.wait(keepalive_time)
                self.unlock()
                if _status:
                    return
            time.sleep(0.2)  # 100ms... 等等是 0.02，这里10倍于等待，应该能等成功？
'''


class FileExLockV2(object):
    def __init__(self, filename):
        self.__filename = copy.copy(filename)
        self.__fd = 0

    def __enter__(self):
        count = 0
        while True:
            count += 1
            if self.try_lock():
                break
            if count == 10:
                # _logger.warning('{} get lock failed, will retry'.format(self))
                count = 0
            time.sleep(1)
        # _logger.debug('{} get lock successful'.format(self))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def try_lock(self):
        mode = os.O_RDWR | os.O_CREAT
        self.__fd = os.open(self.__filename, mode, 0o666)
        if self.__fd <= 0:
            return False
        try:
            fcntl.flock(self.__fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except:
            pass
        os.close(self.__fd)
        self.__fd = 0
        return False

    def release(self):
        if self.__fd > 0:
            os.close(self.__fd)
            self.__fd = 0

    def __str__(self):
        return '<FileExLockV2 {} {}>'.format(self.__filename, self.__fd)


if __name__ == "__main__":
    #xlock = file_ex_lock(r'/run/clware_test_lock')
    #print("try_lock{}".format(xlock.try_lock()))
    #print("try_lock{}".format(xlock.try_lock()))
    with FileExLockV2('/run/test_v2_lock'):
        print('zzzz')
        with FileExLockV2('/run/test_v2_lock'):
            print('xxxx')

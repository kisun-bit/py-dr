import threading
import copy
import socket
import os
import time


class ProcessMonitorThread(threading.Thread):
    def __init__(self, unix_socket_filename: str, cmd_list: dict, daemon=False):
        threading.Thread.__init__(self, daemon=daemon)
        self.__server_address = copy.copy(unix_socket_filename)
        self.__sock = None
        self.__connection = None
        self.__cmd_list = cmd_list
        if 'help' not in self.__cmd_list:
            self.__cmd_list['help'] = self.help
        try:
            _dir_name, _file_name = os.path.split(self.__server_address)
            os.makedirs(_dir_name)
        except Exception as e:
            _ = e
            pass
        # Make sure the socket does not already exist
        try:
            os.unlink(self.__server_address)
        except OSError:
            if os.path.exists(self.__server_address):
                raise

        # Create a UDS socket
        self.__sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # Bind the socket to the address
        self.__sock.bind(self.__server_address)

        # Listen for incoming connections
        self.__sock.listen(1)

    def help(self, cmd_word: list, puts, gets):
        puts("help:\n{}\n".format(self.__cmd_list.keys()))

    def run(self):
        _last_cmd_word = ['help']
        while True:
            # Wait for a connection
            if self.__connection is None:
                self.__connection, client_address = self.__sock.accept()
                _last_cmd_word = ['help']
            try:
                _data = self.__connection.recv(1024)
                if not _data:
                    self.__connection.close()
                    self.__connection = None
                    continue
                _data = _data.decode(encoding='utf-8')
                _lines = _data.splitlines()
                for _cmd_line in _lines:
                    _cmd_word = _cmd_line.split()
                    if len(_cmd_word) <= 0:
                        _cmd_word = _last_cmd_word
                    else:
                        _last_cmd_word = _cmd_word

                    cmd_name = _cmd_word[0].lower()
                    if cmd_name not in self.__cmd_list:
                        cmd_name = 'help'
                    self.__cmd_list[cmd_name](_cmd_word, self.puts, self.gets)

            except Exception as e:
                self.puts("Exception:{}".format(e))
                self.__connection.close()
                self.__connection = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__connection:
            self.__connection.close()

    def puts(self, s):
        if self.__connection:
            try:
                self.__connection.sendall(s.encode(encoding='utf-8'))
            except Exception as e:
                _ = e
                self.__connection.close()
                self.__connection = None

    def gets(self):
        return self.__connection.recv(1024).decode(encoding='utf-8')


def monitor_test_cmd_exit(cmd_word: list, puts, gets):
    _ = cmd_word
    puts("input key:")
    _data = gets()
    _data = _data.strip()
    if _data == "yes":
        puts("exit Process!\n")
    else:
        puts("error key:{}\n".format(_data))

    return


if __name__ == '__main__':

    ProcessMonitorThread(
        r'/run/monitor/test_monitor',
        {'exit': monitor_test_cmd_exit},
        daemon=True).start()

    while True:
        time.sleep(1111)

    pass

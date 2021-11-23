import abc

import Ice

from cpkt.icehelper import application


class Communicator(abc.ABC):

    def __init__(self, logger):
        self._communicator = None
        self.logger = logger

    def start(self, args: list, config_file: str, init_data_list: list):
        """The main entry point for the Application class.

        :param args:
            The arguments are an argument list (such as sys.argv)， 最高优先级
        :param config_file:
            The file path of an Ice configuration file，次优先级
        :param init_data_list:
            InitializationData properties 参数，最低优先级
            [('Ice.Default.Host', '127.0.0.1'), ('Ice.Warn.Connections', '1'), ... ]
        """
        assert self._communicator is None

        py_logger = application.PyLoggerI(self.logger)
        init_data = application.Application.generate_init_data(config_file, init_data_list, args, py_logger)
        self._communicator = Ice.initialize(args, init_data)
        try:
            self.more_init(args)
        except Exception as e:
            self.logger.info('call Communicator.more_init failed. {}'.format(e))
            self.stop()
            self.wait_stop()
            self.destroy()
            raise e

    @abc.abstractmethod
    def more_init(self, args):
        raise RuntimeError('run() not implemented')

    def stop(self):
        if self._communicator:
            self._communicator.shutdown()

    def destroy(self):
        if self._communicator:
            self._communicator.destroy()
            self._communicator = None

    def wait_stop(self):
        if self._communicator:
            self._communicator.waitForShutdown()

    def communicator(self):
        return self._communicator  # type: Communicator

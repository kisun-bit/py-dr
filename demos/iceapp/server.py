import sys

from cpkt.core import xlogging as lg
from cpkt.icehelper import application

_logger = lg.get_logger(__name__)


class Server(application.Application):

    def __init__(self):
        super(Server, self).__init__()

    def run(self, args):
        _ = args

        adapter = self.communicator().createObjectAdapter("ApiAdapter")
        adapter.activate()

        endpoint = adapter.getEndpoints()  # IcePy.Endpoint (tcp -h 127.0.0.1 -p xxxxxx -t 60000,)
        print(endpoint[0])

        self.communicator().waitForShutdown()
        return 0

    def shutdown(self):
        _ = self
        _logger.info("shutdown called")
        self.communicator().shutdown()


app = Server()

app_default_properties = [
    (r'ApiAdapter.Endpoints', r'tcp -h 127.0.0.1 -p 0'),
]
app.main(sys.argv, '/etc/aio/iceapp.cfg', app_default_properties, _logger)

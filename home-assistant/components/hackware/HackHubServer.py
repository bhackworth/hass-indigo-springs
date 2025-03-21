"""Server to collect data from all Hackware devices."""

from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from threading import Thread
from typing import Any, override


class Sample:
    """A single measurement from one of the Hackware devices."""

    sensor: str
    temperature: float | None
    humidity: float | None
    moisture: float | None
    voltage: float | None

    def __init__(self, post_data: str) -> None:
        """Initialize a sample from JSON data."""

        # TODO: use pydantic instead
        sample_json = json.loads(post_data)
        self.sensor = sample_json["sensor"]
        self.temperature = (
            float(sample_json["temperature"]) if "temperature" in sample_json else None
        )
        self.humidity = (
            float(sample_json["humidity"]) if "humidity" in sample_json else None
        )
        self.moisture = (
            float(sample_json["moisture"]) if "moisture" in sample_json else None
        )
        self.voltage = (
            float(sample_json["voltage"]) if "voltage" in sample_json else None
        )

    @staticmethod
    def from_json_str(post_data: str):
        """Create a sample from a JSON string."""
        return Sample(post_data)

    def __str__(self):
        """Return a viewable version of the sample."""
        return f"Sensor {self.sensor}: temperature {self.temperature}, moisture {self.moisture}, voltage {self.voltage}"


class HackHubServer(Thread):
    """Handle interactions with custom-written sensors."""

    def __init__(self, port: int) -> None:
        """Create a new server instance."""
        super().__init__()
        self._port = port
        self._server = None
        self._callbacks = []

    # start() is provided by Thread

    @override
    def run(self):
        """Thread's main activity: start a web server and listen for requests."""
        self._server = HTTPServer(("", self._port), self.create_handler())
        self._server.serve_forever()

    def stop(self):
        """Stop the thread and shut down the web server."""
        self._server.shutdown()
        self.join()
        del self._server

    def add_callback(
        self, cb: Callable[[Sample, Any | None], None], cbdata: Any | None = None
    ):
        """Notify a caller when new data arrives."""
        self._callbacks.append((cb, cbdata))

    def remove_callback(self, cb, cbdata):
        """Remove a callback."""
        self._callbacks.remove((cb, cbdata))

    def call_callbacks(self, sample: Sample):
        """Call the callbacks, passing the new sample we received."""
        for cb in self._callbacks:
            cb[0](sample, cb[1])

    def create_handler(hub) -> BaseHTTPRequestHandler.__class__:  # noqa: N805
        """Generate an HTTP request handler class."""

        class RequestHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length).decode("utf8")

                if self.path == "/api/samples":
                    sample = Sample.from_json_str(post_data)
                    # Validate the sample

                    # Respond to the client
                    self.send_response(200)
                    self.send_header("Content-type", "text/json")
                    self.end_headers()

                    message = '{ "status": "OK" }\n'

                    self.wfile.write(bytes(message, "utf8"))

                    hub.call_callbacks(sample)

                else:
                    self.send_response(500)
                    self.end_headers()

        return RequestHandler

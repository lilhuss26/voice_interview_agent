import logging
import os

from src.api.app import create_app
from src.api.sockets.interview import socketio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = create_app()

if __name__ == "__main__":
    socketio.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "4567")),
        debug=os.getenv("DEBUG", "1") == "1",
        allow_unsafe_werkzeug=True,
    )

from src.api.app import create_app
from src.api.sockets.interview import socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=True, port=4567, allow_unsafe_werkzeug=True)

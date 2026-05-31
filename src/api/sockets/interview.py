from flask_socketio import SocketIO, emit
from langgraph.types import Command
from src.api.session_store import session_store
from src.api.services.voice import text_to_audio, audio_to_text

socketio = SocketIO(async_mode="threading")


@socketio.on("join")
def handle_join(data):
    try:
        session_id = data.get("session_id")
        session = session_store.get(session_id)
        if not session:
            emit("error", {"message": "session not found"})
            return
        state = session["graph"].get_state(session["config"])
        question = state.tasks[0].interrupts[0].value
        emit("question", {"audio": text_to_audio(question)})
    except Exception as e:
        emit("error", {"message": str(e)})


@socketio.on("answer")
def handle_answer(data):
    try:
        session_id = data.get("session_id")
        audio_bytes = data.get("audio")
        session = session_store.get(session_id)
        if not session:
            emit("error", {"message": "session not found"})
            return
        graph, config = session["graph"], session["config"]

        answer_text = audio_to_text(audio_bytes)
        graph.invoke(Command(resume=answer_text), config=config)

        state = graph.get_state(config)
        if not state.next:
            emit("finished", {})
        else:
            question = state.tasks[0].interrupts[0].value
            emit("question", {"audio": text_to_audio(question)})
    except Exception as e:
        emit("error", {"message": str(e)})

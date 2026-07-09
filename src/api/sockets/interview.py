import logging
import traceback

from flask_socketio import SocketIO, emit
from langgraph.types import Command
from src.api.session_store import session_store
from src.api.services.voice import text_to_audio, audio_to_text

logger = logging.getLogger("interview.socket")

socketio = SocketIO(async_mode="threading")


@socketio.on("join")
def handle_join(data):
    try:
        session_id = data.get("session_id")
        logger.info("JOIN session=%s", session_id)
        session = session_store.get(session_id)
        if not session:
            logger.warning("JOIN: session %s not found", session_id)
            emit("error", {"message": "session not found"})
            return
        state = session["graph"].get_state(session["config"])
        question = state.tasks[0].interrupts[0].value
        logger.info("JOIN: first question=%r", question[:120])
        emit("question", {"audio": text_to_audio(question)})
    except Exception as e:
        logger.error("JOIN failed: %s\n%s", e, traceback.format_exc())
        emit("error", {"message": str(e)})


@socketio.on("answer")
def handle_answer(data):
    try:
        session_id = data.get("session_id")
        audio_bytes = data.get("audio")
        size = len(audio_bytes) if audio_bytes else 0
        logger.info("ANSWER session=%s | received %d bytes of audio", session_id, size)

        session = session_store.get(session_id)
        if not session:
            logger.warning("ANSWER: session %s not found", session_id)
            emit("error", {"message": "session not found"})
            return
        graph, config = session["graph"], session["config"]

        answer_text = audio_to_text(audio_bytes)
        logger.info("ANSWER session=%s | transcript=%r", session_id, answer_text)

        graph.invoke(Command(resume=answer_text), config=config)

        state = graph.get_state(config)
        if not state.next:
            logger.info("ANSWER session=%s | interview FINISHED", session_id)
            emit("finished", {})
        else:
            question = state.tasks[0].interrupts[0].value
            logger.info("ANSWER session=%s | next question=%r", session_id, question[:120])
            emit("question", {"audio": text_to_audio(question)})
    except Exception as e:
        logger.error("ANSWER failed: %s\n%s", e, traceback.format_exc())
        emit("error", {"message": str(e)})

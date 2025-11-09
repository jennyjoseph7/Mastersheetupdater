"""Simple in-memory demo showing Input -> Agent -> Output flow."""
from queue import Queue
from voice.input_manager.manager import InputManager
from voice.agent.voice_agent import VoiceAgent
from voice.output_manager.manager import OutputManager


def run_demo(inputs=None):
    if inputs is None:
        inputs = ["Hello", "Pricing please"]

    req_q = Queue()
    resp_q = Queue()

    inp = InputManager(req_q)
    agent = VoiceAgent()

    response_ids = []
    # push inputs
    for t in inputs:
        rid = inp.push_input(t)
        response_ids.append((rid, t))
        # agent processes synchronously in this demo
        # generate response and put chunks on resp_q
        full = agent.generate(t)
        # split into simple chunks
        for i in range(0, len(full), 8):
            resp_q.put({"response_id": rid, "chunk": full[i : i + 8]})

    out = OutputManager(resp_q)
    assembled = {rid: out.collect_for_response(rid) for rid, _ in response_ids}
    return assembled


if __name__ == "__main__":
    print(run_demo())

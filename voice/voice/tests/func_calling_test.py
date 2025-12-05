import asyncio
from google import genai
from google.genai import types
from gryd_worker import gryd_helpers as hp
import pyaudio

pya = pyaudio.PyAudio()
logger = hp.get_logger(__name__)

def get_weather(location: str) -> dict:
    logger.info(f"[TOOL] get_weather({location})")
    result = {"temperature": "25°C", "condition": "Sunny", "location": location}
    logger.info(f"[RESULT] {result}\n")
    return result

def get_dealer_data(location: str) -> dict:
    logger.info(f"[TOOL] get_dealer_data({location})")
    result = {"name": "Dealer A", "location": location}
    logger.info(f"[RESULT] {result}\n")
    return result

# Mic configs
FORMAT = pyaudio.paInt16
CHANNELS = 1

RECEIVER_POLL_TIMEOUT = 600
RECIEVER_SHUTDOWN_DRAIN_TIMEOUT = 20 
SENDER_SHUTDOWN_TMEOUT=5

async def voice_agent_with_tools():
    """Voice agent with tools. Work in progress"""
    client = genai.Client()
    # Tool definitions
    tools = [
        {
            "function_declarations": [
                {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City name"}
                        },
                        "required": ["location"]
                    }
                },
                {
                    "name": "get_dealer_data",
                    "description": "Get dealer data for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City name"}
                        },
                        "required": ["location"]
                    }
                }
            ]
        }
    ]
    handlers = {"get_weather": get_weather, "get_dealer_data": get_dealer_data}
    config = {
    #     "tools_config": types.ToolConfig(
    #     function_calling_config=types.FunctionCallingConfig(
    #         # AUTO → model decides when to call tools
    #         mode="AUTO"
    #         # You can also use:
    #         # mode="ANY" → model may return multiple calls in one turn
    #         # mode="NONE" → disables tool usage
    #     )
    # ),
        "response_modalities": ["AUDIO"],
        "system_instruction": "You are a helpful assistant. Use tools when needed.",
        "tools": tools,
        "speech_config": types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        "input_audio_transcription": {},
        "output_audio_transcription": {},
    }
    pya = pyaudio.PyAudio()
    mic_stream = pya.open(format=pyaudio.paInt16,channels=1,rate=16000,input=True,frames_per_buffer=1024)
    speaker_stream = pya.open(format=pyaudio.paInt16,channels=1,rate=24000,output=True)
    input_queue = asyncio.Queue()
    output_queue = asyncio.Queue()
    
    print("Listening... Speak now!")
    print("="*60)

    conn = client.aio.live.connect(model="gemini-live-2.5-flash-preview", config=config)
    async with conn as session:
        async def sender():
            """Send audio continuously"""
            print("[SENDER] Started")
            try:
                while True:
                    audio_data = await input_queue.get()
                    if audio_data is None:
                        print("[SENDER] Stop signal received")
                        break
                    await session.send_realtime_input(audio={'data': audio_data, 'mime_type': 'audio/pcm;rate=16000'})
            except asyncio.CancelledError:
                print("[SENDER] Cancelled")
            except Exception as e:
                print(f"[SENDER] Error: {e}")
            finally:
                print("[SENDER] Stopped")

        import ast

        def execute_gemini_executable_code(code: str, handlers: dict):
            tree = ast.parse(code)
            if not isinstance(tree.body[0], ast.Expr):
                raise ValueError("Not an expression")

            print_call = tree.body[0].value
            tool_call = print_call.args[0]
            if isinstance(tool_call.func, ast.Attribute):
                function_name = tool_call.func.attr
            else:
                function_name = tool_call.func.id
            function_args = {kw.arg: ast.literal_eval(kw.value) for kw in tool_call.keywords}
            if function_name not in handlers:
                raise ValueError(f"Unknown tool: {function_name}")
            result = handlers[function_name](**function_args)
            return function_name, function_args, result


        async def receiver():
            """Receive responses and handle tools"""
            print("[RECEIVER] Started")
            user_transcript = []
            agent_transcript = []
            
            try:
                async for response in session.receive():
                    print(f"Response: {response}")
                    content = response.server_content
                    if response.tool_call:
                        print(f"Tool call: {response.tool_call}")
                    if not content:
                        continue
                    print(f"Content: {content}")    
        
                    if content.input_transcription and hasattr(content.input_transcription, 'text') and content.input_transcription.text:
                        text = content.input_transcription.text
                        user_transcript.append(text)
                        print(f"👤 YOU: {text}")
                    
                    if content.output_transcription and hasattr(content.output_transcription, 'text') and content.output_transcription.text:
                        text = content.output_transcription.text
                        agent_transcript.append(text)
                        print(f"🤖 AGENT: {text}")
                    
                    # Handle model turn (tools + audio)
                    if content.model_turn and content.model_turn.parts:
                        for part in content.model_turn.parts:
                            if hasattr(part, "executable_code") and part.executable_code is not None:
                                code = part.executable_code.code
                                # function_call = part.executable_code.function_call
                                # function_call_id = function_call.id
                                # function_name = function_call.name
                                # function_args = dict(function_call.args)
                                # print(f"Function call: {function_call}")
                                # print(f"Function name: {function_name}")
                                # print(f"Function args: {function_args}")
                                # print(f"Function call id: {function_call_id}")


                                print(f"\n🔧 EXECUTABLE CODE RECEIVED:\n{code}")
                                function_name, function_args, result = execute_gemini_executable_code(code = code, handlers = handlers)
                                print(f"Function name: {function_name}")
                                print(f"Function args: {function_args}")
                                print(f"Function result: {result}")
                                await session.send_tool_response(function_responses=[types.FunctionResponse(name=function_name,response=result)])
                                # await session.

                            
                            if part.code_execution_result is not None:
                                print(part.code_execution_result.output)
                            if hasattr(part, "inline_data") and part.inline_data:
                                if hasattr(part.inline_data, "data"):
                                    await output_queue.put(part.inline_data.data)

                    
                    # Generation complete
                    if content.generation_complete:
                        print("-" * 60)
                        full_user = ''.join(user_transcript).strip()
                        full_agent = ''.join(agent_transcript).strip()
                        if full_user:
                            print(f"[USER SAID]: {full_user}")
                        if full_agent:
                            print(f"[AGENT SAID]: {full_agent}")
                        print("🎤 Ready for next question...")
                        print("-" * 60)
                        user_transcript = []
                        agent_transcript = []
                        
            except asyncio.CancelledError:
                print("[RECEIVER] Cancelled")
            except Exception as e:
                print(f"[RECEIVER] Error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                print("[RECEIVER] Stopped")
        
        async def mic_capture():
            """Capture from microphone"""
            print("[MIC] Started")
            try:
                loop = asyncio.get_event_loop()
                while True:
                    audio = await loop.run_in_executor(
                        None, mic_stream.read, 1024, False
                    )
                    await input_queue.put(audio)
            except asyncio.CancelledError:
                print("[MIC] Cancelled")
            finally:
                print("[MIC] Stopped")
        
        async def speaker_playback():
            """Play audio to speaker"""
            print("[SPEAKER] Started")
            try:
                loop = asyncio.get_event_loop()
                while True:
                    audio = await output_queue.get()
                    await loop.run_in_executor(None, speaker_stream.write, audio)
            except asyncio.CancelledError:
                print("[SPEAKER] Cancelled")
            finally:
                print("[SPEAKER] Stopped")
        
        # Run all tasks
        try:
            await asyncio.gather(
                sender(),
                receiver(),
                mic_capture(),
                speaker_playback()
            )
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            mic_stream.stop_stream()
            speaker_stream.stop_stream()
            mic_stream.close()
            speaker_stream.close()
            pya.terminate()


if __name__ == '__main__':
    asyncio.run(voice_agent_with_tools())



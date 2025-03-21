import time
import sounddevice
import dashscope
from dashscope.api_entities.dashscope_response import SpeechSynthesisResponse
from dashscope.audio.tts_v2 import *
from datetime import datetime
import numpy as np

def get_timestamp():
    now = datetime.now()
    formatted_timestamp = now.strftime("[%Y-%m-%d %H:%M:%S.%f]")
    return formatted_timestamp

# 若没有将API Key配置到环境变量中，需将your-api-key替换为自己的API Key
dashscope.api_key = "sk-6a259a1064144086be0e11e5903c1d49"

model = "cosyvoice-v1"
voice = "longxiaochun"

llm_basechat = [
            {"role": "system", "content": "你是一位情感陪伴专家，你的任务是陪伴一位盲人聊天，在聊天中，你需要关注用户的情感需要，不要反复提及用户残疾的情况。"},
        ]
class Callback(ResultCallback):
    _player = None
    _stream = None

    def on_open(self):
        print("websocket is open.")
        self._stream = sounddevice.OutputStream(
            samplerate=22050,
            channels=1,
            dtype='int16',
            blocksize=1024
        )
        self._stream.start()

    def on_complete(self):
        print(get_timestamp() + " speech synthesis task complete successfully.")

    def on_error(self, message: str):
        print(f"speech synthesis task failed, {message}")

    def on_close(self):
        print(get_timestamp() + " websocket is closed.")
        # 停止播放器
        self._stream.stop_stream()
        self._stream.close()
        self._player.terminate()

    def on_event(self, message):
        pass

    def on_data(self, data: bytes) -> None:
        print(get_timestamp() + " audio result length: " + str(len(data)))
        self._stream.write(np.frombuffer(data, dtype='int16'))


callback = Callback()


synthesizer = SpeechSynthesizer(
    model=model,
    voice=voice,
    format=AudioFormat.PCM_22050HZ_MONO_16BIT,  
    callback=callback,
)
usrmsg = input("请输入您的问题：")
llm_basechat.append({"role": "user", "content": usrmsg})
completion = dashscope.Generation.call(
                    model="qwen-plus",
                    messages=llm_basechat,
                    temperature=0.35,
                    extra_body={
                        "enable_search": True
                    },
                    result_format='message',
                    stream=True,
                    # 增量式流式输出
                    incremental_output=True
                )
for chunk in completion:
    try:
        text_content = chunk.output.choices[0].message.content
        if text_content:
            print(f"{text_content}")
            synthesizer.streaming_call(text_content)
    except Exception as e:
        print(f"处理流式输出块错误: {str(e)}")
        continue
print()
synthesizer.streaming_complete()  # 完成合成后，一定要主动关闭连接

print('[Metric] requestId: {}, first package delay ms: {}'.format(
    synthesizer.get_last_request_id(),
    synthesizer.get_first_package_delay()))
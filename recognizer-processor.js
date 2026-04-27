class RecognizerAudioProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super(options);
    this.port.onmessage = (event) => {
      if (event.data.action === "init") {
        this._recognizerId = event.data.recognizerId;
        this._recognizerPort = event.ports[0];
      }
    };
  }

  process(inputs) {
    const data = inputs[0][0];
    if (this._recognizerPort && data) {
      const audioArray = data.map((value) => value * 0x8000);
      this._recognizerPort.postMessage(
        {
          action: "audioChunk",
          data: audioArray,
          recognizerId: this._recognizerId,
          sampleRate,
        },
        { transfer: [audioArray.buffer] }
      );
    }
    return true;
  }
}

registerProcessor("recognizer-processor", RecognizerAudioProcessor);

import whisper

def transcribe_audio(audio_file_path):
    """Transcribe an audio file using Whisper."""
    # Load the Whisper model
    model = whisper.load_model("tiny")  # You can use "base", "small", "medium", or "large"
    
    # Transcribe the audio
    result = model.transcribe(audio_file_path, batch_size=1)
    
    # Combine the text from all segments
    transcription = result.get("text", "")
    return transcription

# import whisperx

# def transcribe_audio(audio_file_path):
#     """Transcribe an audio file using WhisperX."""
#     model = whisperx.load_model("large-v2", device="cpu", compute_type="int8")  # Use CPU
#     audio = whisperx.load_audio(audio_file_path)
#     result = model.transcribe(audio)
#     return " ".join([segment["text"] for segment in result["segments"]])

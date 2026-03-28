Speech Synthesis
MOSS-TTS
POST
https://studio.mosi.cn/api/v1/audio/speech
MOSS-TTS is a powerful TTS (Text-to-Speech) model. It takes text and a reference audio to synthesize high-quality speech that mimics the voice characteristics of the reference.

Model Highlights
SOTA
State-of-the-art on Seed-TTS-Eval, Seed-TTS-Eval Hard, CV3, and self-built arena.
Token-level duration control
Scalable bitrate (adjustable RVQ layers)
Ultra-short: single word generation
Ultra-long: up to 1 hour audio
Accurate rare word pronunciation
Multi-language support
Chinese-English code-switching
Phoneme-level pronunciation control
Pinyin / IPA / mixed input support
Request Parameters
Header
Parameter	Type	Required	Description
Authorization	String	Yes	Bearer <YOUR_API_KEY>
Body
Parameter	Type	Required	Description
model	String	Yes	Model name, use moss-tts
text	String	Yes	Text to synthesize.
voice_id	String	Yes	Reference voice ID that determines the voice style. Use an ID from the public voice library, or create a custom voice via Voice Clone.
👉 View Public Voice Library
🎙 Create Voice
expected_duration_sec	Float	No	Expected output audio duration in seconds (optional). Best practice: set to 0.5x - 1.5x of the normal reading time of the text. Values outside this range may reduce quality.
sampling_params	Object	No	Sampling configuration.
- max_new_tokens: Max tokens (default 512)
- temperature: Sampling temperature (default 1.7)
- top_p: Nucleus sampling (default 0.8)
- top_k: Top-K sampling (default 25)
meta_info	Boolean	No	Whether to return performance metrics, default false
Sampling Parameters
These parameters are in the sampling_params object.

Important
Default values work well for most cases. Adjust temperature for more or less variation.
Recommended parameters: Chinese temperature=1.7, top_p=0.8, top_k=25; English temperature=1.5, top_p=0.8, top_k=50.
Parameter	Type	Default	Description & Tips
max_new_tokens	Int	512	Maximum tokens to generate. Controls output audio length.
temperature	Float	1.7	Sampling temperature. Higher values increase output diversity.
top_p	Float	0.8	Nucleus sampling probability threshold. Recommended 0.8.
top_k	Int	25	Top-K sampling. Limits candidate tokens per step.
Examples
Python Example
Python

Copy
import requests
import base64

url = "https://studio.mosi.cn/api/v1/audio/speech"

payload = {
    "model": "moss-tts",
    "text": "Hello, the weather is great today.",
    "voice_id": "2001257729754140672",
    "expected_duration_sec": 3.2,
    "meta_info": True,
    "sampling_params": {
        "max_new_tokens": 512,
        "temperature": 1.7,
        "top_p": 0.8,
        "top_k": 25
    }
}

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_API_KEY"
}

response = requests.post(url, json=payload, headers=headers)
result = response.json()

audio_b64 = result.get("audio_data")
if audio_b64:
    with open("output.wav", "wb") as f:
        f.write(base64.b64decode(audio_b64))
    print("Audio saved to output.wav")
cURL Example
cURL

Copy
curl -X POST "https://studio.mosi.cn/api/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "moss-tts",
    "text": "Hello, great weather today",
    "voice_id": "2001257729754140672",
    "expected_duration_sec": 3.2,
    "meta_info": true,
    "sampling_params": {
      "max_new_tokens": 256,
      "temperature": 1.7,
      "top_p": 0.8,
      "top_k": 25
    }
  }' | jq -r '.audio_data' | base64 -d -i > output.wav

# macOS users should use:
# ... | jq -r '.audio_data' | base64 -d > output.wav
Response Parameters
Returns JSON with Base64 audio data, duration, and usage statistics.

Parameter	Type	Description
audio_data	String	Base64 encoded audio data.
duration_s	Float	Duration of generated audio in seconds.
usage	Object	Usage statistics.
- prompt_tokens: Input token count
- completion_tokens: Output token count
- total_tokens: Total token count
- credit_cost: Credits consumed
meta_info	Object	Performance metrics (returned when request parameter meta_info=true).
- request_id: Unique request ID
- latency_ms: Inference latency (milliseconds)
- e2e_latency_sec: End-to-end latency (seconds)
- prompt_tokens: Prompt tokens
- completion_tokens: Completion tokens
- total_tokens: Total tokens
- cost: Credits consumed
Response Example
JSON

Copy
{
  "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8A...",
  "duration_s": 0.72,
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 6,
    "credit_cost": 6
  },
  "meta_info": {
    "request_id": "uuid",
    "latency_ms": 1234.5,
    "e2e_latency_sec": 1.23,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 6,
    "cost": 6
  }
}
Status Codes & Errors
HTTP 200 indicates success. Errors return 4xx/5xx with code in JSON body.

Error Code	Description	Solution
4000	Invalid Request
Invalid request format	Check if request parameters are correct
4002	Invalid Audio
Invalid reference audio format	Check reference audio format, supports 16-48kHz WAV
4010	Unauthorized
Unauthorized access	Check if API Key is added to request header
4011	Invalid API Key
Invalid API Key	Check if API Key is correct
4020	Insufficient Credits
Insufficient balance	Please recharge and try again
4029	Rate Limit
Rate limit exceeded	Reduce request frequency or implement backoff retry
5000	Internal Error
Internal server error	Retry later, contact support if persists
5002	Voice Not Found
Voice audio unavailable	Verify the Voice status is ACTIVE for the given voice_id
5004	Timeout
Request timeout	Check text length, reduce content per request
Performance & Quotas
RPM
5
Requests Per Minute Limit
Max requests per minute per account. Exceeding returns 429.

OUTPUT
24kHz
Output Audio Quality
24kHz WAV format output audio.

TIMEOUT
600s
Request Timeout
Default 600 seconds, configurable via API settings.

Contact Us
Email: mosi@mosi.cn

Snapshots
Quickly identify model versions for consistent API calls. Below are all available snapshots and versions for MOSS-TTS.

moss-tts
moss-tts-20260207
moss-tts-20260207
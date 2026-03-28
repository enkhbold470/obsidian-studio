Multi-Speaker Dialogue TTS
MOSS-TTSD
Overview
MOSS-TTSD is a multi-speaker dialogue TTS service that generates dialogue audio with two speakers.

Model Highlights
Voice ID required: voice_id and voice_id2 are both required, status must be ACTIVE
Strict text format: Must use [S1] and [S2] tags
Voice ID mapping: voice_id maps to [S1], voice_id2 maps to [S2]
Audio format: Returns Base64 encoded WAV, needs decoding
Billing: Billed by tokens, ~text length×2
Generate Dialogue Audio
POST
https://studio.mosi.cn/api/v1/audio/speech
Generate dialogue audio based on dialogue text and two voice IDs.

Request Headers
Parameter	Type	Required	Description
Authorization	String	Yes	Bearer {api_key}
Content-Type	String	Yes	application/json
Text Format Requirements
Important
Text must use [S1] and [S2] tags to mark speakers!
Correct Format
Text

Copy
[S1]你好，今天天气真好。[S2]是的，很适合出去走走。[S1]我们去公园吧。
Format Rules
Use [S1] to mark speaker 1 content
Use [S2] to mark speaker 2 content
Tags must be uppercase
Tags should be immediately followed by text, no spaces
Can switch speakers multiple times
Incorrect Format Examples
Wrong Example	Reason
你好。你好。	No speaker tags
[s1]你好[s2]你好	Tags are lowercase
[S1] 你好	Space after tag
[说话人1]你好	Using Chinese tags
Request Parameters
Parameter	Type	Required	Default	Description
model	String	Yes	-	Model name. Use moss-ttsd or a specific snapshot version.
text	String	Yes	-	Dialogue text (must contain [S1][S2] tags)
voice_id	String	Yes	-	Voice ID for speaker 1
👉 View Public Voice Library
🎙 Create Voice
voice_id2	String	Yes	-	Voice ID for speaker 2
👉 View Public Voice Library
🎙 Create Voice
meta_info	Boolean	No	false	Whether to return meta info (for debugging)
sampling_params	Object	No	-	Sampling parameters, see table below
Sampling Parameters
Parameter	Type	Default	Description
max_new_tokens	Integer	20000	Maximum tokens to generate
temperature	Float	0.8	Sampling temperature (not recommended to adjust, use default)
top_p	Float	0.95	Nucleus sampling threshold
top_k	Integer	50	Top-K sampling
audio_presence_penalty	Float	0.0	Audio channel presence penalty to suppress blank audio. Higher values suppress blank audio more aggressively
Request Examples
Basic Request
JSON

Copy
{
  "model": "moss-ttsd",
  "text": "[S1]你好，今天天气真好。[S2]是的，很适合出去走走。",
  "voice_id": "08219ad1",
  "voice_id2": "a0fafa9b"
}
Complete Request (with all parameters)
JSON

Copy
{
  "model": "moss-ttsd",
  "text": "[S1]诶，我最近看了一篇讲人工智能的文章，还挺有意思的。[S2]哦？是吗，关于啥的啊？",
  "voice_id": "08219ad1",
  "voice_id2": "a0fafa9b",
  "meta_info": false,
  "sampling_params": {
    "max_new_tokens": 20000,
    "top_p": 0.95,
    "top_k": 50
  }
}
Python Example
Python

Copy
import base64
import json
import requests

api_base = "https://studio.mosi.cn"
api_key = "YOUR_API_KEY"

payload = {
    "model": "moss-ttsd",
    "text": "[S1]你好，今天天气真好。[S2]是的，很适合出去走走。",
    "voice_id": "08219ad1",
    "voice_id2": "a0fafa9b",
    "sampling_params": {
        "max_new_tokens": 20000,
        "temperature": 0.8,
        "top_p": 0.95,
        "top_k": 50
    },
    "meta_info": True
}

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

resp = requests.post(
    f"{api_base}/api/v1/audio/speech",
    headers=headers,
    data=json.dumps(payload),
    timeout=180
)
resp.raise_for_status()

data = resp.json()
audio_base64 = data["audio_data"]
audio_bytes = base64.b64decode(audio_base64)

with open("moss_ttsd_output.wav", "wb") as f:
    f.write(audio_bytes)

print("saved:", "moss_ttsd_output.wav")
Response Format
Success Response (200 OK)
JSON

Copy
{
  "audio_data": "UklGRi4AAABXQVZF...",
  "usage": {
    "total_tokens": 216,
    "credit_cost": 216
  }
}
Response Fields
Field	Type	Description
audio_data	String	Base64 encoded audio data (WAV format)
usage	Object	Usage statistics
usage.total_tokens	Integer	Number of tokens consumed
usage.credit_cost	Float	Credits/cost consumed
Audio Data Information
Format: WAV
Encoding: Base64
Sample rate: 32kHz
Bit depth: 16-bit
Channels: Mono
Parameters Guide
temperature (Sampling Temperature)
Not recommended to adjust this parameter. Use default value 0.8 for best results.
Controls randomness and diversity of generation. Default value 0.8 is optimized for good balance between stability and naturalness.

Error Responses
Error Format
JSON

Copy
{
  "code": 5000,
  "error": "Internal Error: failed to get voice1"
}
Common Errors
Status	code	Error Message	Cause	Solution
400	4001	Invalid request	Missing required parameters	Check text, voice_id, voice_id2
400	4001	text is required	Missing text parameter	Add dialogue text
400	4001	voice_id is required	Missing voice_id	Add speaker 1 voice ID
400	4001	voice_id2 is required	Missing voice_id2	Add speaker 2 voice ID
401	4010	Unauthorized	Invalid API key	Check Authorization header
404	4004	voice not found	Voice not found	Verify voice_id is correct
500	5002	failed to get voice audio	Voice audio unavailable	Verify the Voice status is ACTIVE for the given voice_id
503	5003	TTSD service not configured	Service not configured	Contact administrator
Usage Limits
Item	Limit	Description
Text length	Recommend < 500 chars	Long text increases generation time
Request timeout	120 s	Returns 503 on timeout
Concurrency	5 /user	Excess requests will queue
RPM	5	Requests per minute limit
Voice requirement	Must be ACTIVE	Status must be ACTIVE
Complete Workflow
1. Prepare two Voice IDs
   ↓
2. Build dialogue text (with [S1][S2] tags)
   ↓
3. Call TTSD API
   ↓
4. Get Base64 audio data
   ↓
5. Decode and play/save
Performance Metrics
Metric	Typical Value
Response time	3-10 s
Audio quality	16kHz / 16bit
Token consumption	~text length×2
Audio size	~32KB/second
Contact Us
Email：mosi@mosi.cn

Snapshots
Quickly identify model versions for consistent API calls. Below are all available snapshots and versions for MOSS-TTSD.

moss-ttsd
moss-ttsd-20260320
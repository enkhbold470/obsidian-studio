> ## Documentation Index
> Fetch the complete documentation index at: https://docs.fish.audio/llms.txt
> Use this file to discover all available pages before exploring further.

# Overview

> The official Python library for the Fish Audio API

export const AudioTranscript = ({voices = []}) => {
  const [selectedVoice, setSelectedVoice] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const audioRef = useRef(null);
  const dropdownRef = useRef(null);
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const updateTime = () => setCurrentTime(audio.currentTime);
    const updateDuration = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);
    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('ended', handleEnded);
    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('ended', handleEnded);
    };
  }, []);
  useEffect(() => {
    const handleClickOutside = event => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDropdownOpen]);
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.load();
      setIsPlaying(false);
      setCurrentTime(0);
    }
  }, [selectedVoice]);
  const togglePlay = () => {
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };
  const handleProgressChange = e => {
    const newTime = parseFloat(e.target.value);
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };
  const formatTime = time => {
    if (isNaN(time)) return '0:00';
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };
  const currentVoice = voices[selectedVoice];
  return <div className="border rounded-lg bg-card border-gray-200 dark:border-gray-800">
      {}
      <div className="grid grid-cols-3 items-center px-3 py-1.5 bg-muted border-b border-gray-200 dark:border-gray-800">
        <span className="text-xs font-medium">Listen to Page</span>

        <span className="text-xs font-semibold text-muted-foreground text-center">Powered by Fish Audio S2 Pro</span>

        {voices.length > 1 ? <div className="relative justify-self-end" ref={dropdownRef}>
            <button onClick={() => setIsDropdownOpen(!isDropdownOpen)} className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-muted hover:bg-gray-200 dark:hover:bg-gray-700 transition-all duration-200 cursor-pointer text-xs">
              <span className="text-muted-foreground">Voice:</span>
              <span className="font-medium">{voices[selectedVoice]?.name}</span>
              <svg className={`w-3 h-3 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {isDropdownOpen && <div className="absolute right-0 mt-1 w-auto bg-white dark:bg-black border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden z-50">
                {voices.map((voice, index) => <button key={index} onClick={() => {
    setSelectedVoice(index);
    setIsDropdownOpen(false);
  }} className={`w-full px-3 py-1.5 text-left text-xs hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center gap-2 ${index === selectedVoice ? 'bg-gray-100 dark:bg-gray-800 font-medium' : ''}`}>
                    {voice.id && <img src={`https://public-platform.r2.fish.audio/coverimage/${voice.id}`} alt={voice.name} className="w-5 h-5 rounded-full m-0 flex-shrink-0 object-cover" />}
                    <span className="flex-1 whitespace-nowrap">{voice.name}</span>
                  </button>)}
              </div>}
          </div> : <div className="justify-self-end" />}
      </div>

      {}
      <div className="px-3 py-1.5 bg-card">
        <audio ref={audioRef} src={currentVoice?.url} preload="metadata" />

        <div className="flex items-center gap-2">
          {}
          <button onClick={togglePlay} className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-gray-200 rounded-full hover:opacity-80 transition-opacity relative overflow-hidden" aria-label={isPlaying ? 'Pause' : 'Play'}>
            <div className="transition-transform duration-300 ease-in-out" style={{
    transform: isPlaying ? 'rotate(180deg)' : 'rotate(0deg)'
  }}>
              {isPlaying ? <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                </svg> : <svg className="w-3 h-3 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>}
            </div>
          </button>

          {}
          <div className="flex-1 flex items-center gap-2">
            <span className="text-xs font-mono text-gray-500 dark:text-gray-400 min-w-[35px]">
              {formatTime(currentTime)}
            </span>

            <div className="flex-1 relative h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div className="absolute top-0 left-0 h-full bg-gray-400 dark:bg-gray-500 transition-all duration-100" style={{
    width: `${duration ? currentTime / duration * 100 : 0}%`
  }} />
              <input type="range" min="0" max={duration || 0} value={currentTime} onChange={handleProgressChange} className="absolute top-0 left-0 w-full h-full opacity-0 cursor-pointer" />
            </div>
            <span className="text-xs font-mono text-gray-500 dark:text-gray-400 min-w-[35px]">
              {formatTime(duration)}
            </span>
          </div>
        </div>
      </div>
    </div>;
};

<AudioTranscript
  voices={[
  {
    "id": "8ef4a238714b45718ce04243307c57a7",
    "name": "E-girl",
    "url": "https://pub-b995142090474379a930b856ab79b4d4.r2.dev/audio/python-overview/8ef4a238714b45718ce04243307c57a7.mp3"
  },
  {
    "id": "802e3bc2b27e49c2995d23ef70e6ac89",
    "name": "Energetic Male",
    "url": "https://pub-b995142090474379a930b856ab79b4d4.r2.dev/audio/python-overview/802e3bc2b27e49c2995d23ef70e6ac89.mp3"
  },
  {
    "id": "933563129e564b19a115bedd57b7406a",
    "name": "Sarah",
    "url": "https://pub-b995142090474379a930b856ab79b4d4.r2.dev/audio/python-overview/933563129e564b19a115bedd57b7406a.mp3"
  },
  {
    "id": "bf322df2096a46f18c579d0baa36f41d",
    "name": "Adrian",
    "url": "https://pub-b995142090474379a930b856ab79b4d4.r2.dev/audio/python-overview/bf322df2096a46f18c579d0baa36f41d.mp3"
  },
  {
    "id": "b347db033a6549378b48d00acb0d06cd",
    "name": "Selene",
    "url": "https://pub-b995142090474379a930b856ab79b4d4.r2.dev/audio/python-overview/b347db033a6549378b48d00acb0d06cd.mp3"
  },
  {
    "id": "536d3a5e000945adb7038665781a4aca",
    "name": "Ethan",
    "url": "https://pub-b995142090474379a930b856ab79b4d4.r2.dev/audio/python-overview/536d3a5e000945adb7038665781a4aca.mp3"
  }
]}
/>

This guide will walk you through installation, authentication, and core features.

<Note>
  If you're using the legacy Session-based API (`fish_audio_sdk`), see the [migration guide](/archive/python-sdk-legacy/migration-guide) to upgrade to the new SDK.
</Note>

## Installation

<Steps>
  <Step title="Install the SDK">
    Install via uv (Python 3.9 or higher required):

    ```bash  theme={null}
    uv add fish-audio-sdk
    ```

    For audio playback utilities, install with the `utils` extra:

    ```bash  theme={null}
    uv add "fish-audio-sdk[utils]"
    ```
  </Step>

  <Step title="Get your API key">
    <AccordionGroup>
      <Accordion icon="user-plus" title="Create a Fish Audio account">
        Sign up for a free Fish Audio account to get started with our API.

        1. Go to [fish.audio/auth/signup](https://fish.audio/auth/signup)
        2. Fill in your details to create an account, complete steps to verify your account.
        3. Log in to your account and navigate to the [API section](https://fish.audio/app/api-keys)
      </Accordion>

      <Accordion icon="key" title="Get your API key">
        Once you have an account, you'll need an API key to authenticate your requests.

        1. Log in to your [Fish Audio Dashboard](https://fish.audio/app/api-keys/)
        2. Navigate to the API Keys section
        3. Click "Create New Key" and give it a descriptive name, set a expiration if desired
        4. Copy your key and store it securely

        <Warning>Keep your API key secret! Never commit it to version control or share it publicly.</Warning>
      </Accordion>
    </AccordionGroup>
  </Step>

  <Step title="Set up authentication">
    Configure your API key using environment variables:

    ```bash  theme={null}
    export FISH_API_KEY=your_api_key_here
    ```

    Or create a `.env` file in your project root:

    ```bash  theme={null}
    FISH_API_KEY=your_api_key_here
    ```
  </Step>
</Steps>

## Quick Start

Get started with the [`FishAudio`](/api-reference/sdk/python/client#fishaudio-objects) client in less than a minute:

<CodeGroup>
  ```python Synchronous theme={null}
  from fishaudio import FishAudio
  from fishaudio.utils import play, save

  # Initialize client (reads from FISH_API_KEY environment variable)
  client = FishAudio()

  # Generate and play audio
  audio = client.tts.convert(text="Hello, playing from Fish Audio!")
  play(audio)

  # Generate and save audio
  audio = client.tts.convert(text="Saving this audio to a file!")
  save(audio, "output.mp3")
  ```

  ```python Asynchronous theme={null}
  import asyncio
  from fishaudio import AsyncFishAudio
  from fishaudio.utils import play, save

  async def main():
      # Initialize async client
      client = AsyncFishAudio()

      # Generate and play audio
      audio = await client.tts.convert(text="Hello, playing from Fish Audio!")
      play(audio)

      # Generate and save audio
      audio = await client.tts.convert(text="Saving this audio to a file!")
      save(audio, "output.mp3")

  asyncio.run(main())
  ```
</CodeGroup>

## Core Features

### Text-to-Speech

Fully customizable text-to-speech generation:

<CodeGroup>
  ```python Synchronous focus={6-10} theme={null}
  from fishaudio import FishAudio
  from fishaudio.utils import play

  client = FishAudio()

  # With a specific voice
  audio = client.tts.convert(
      text="Custom voice",
      reference_id="bf322df2096a46f18c579d0baa36f41d" # Adrian
  )
  play(audio)
  ```

  ```python Asynchronous focus={8-12} theme={null}
  import asyncio
  from fishaudio import AsyncFishAudio
  from fishaudio.utils import play

  async def main():
      client = AsyncFishAudio()

      # With a specific voice
      audio = await client.tts.convert(
          text="Custom voice",
          reference_id="bf322df2096a46f18c579d0baa36f41d" # Adrian
      )
      play(audio)

  asyncio.run(main())
  ```
</CodeGroup>

<CodeGroup>
  ```python Synchronous focus={6-10} theme={null}
  from fishaudio import FishAudio
  from fishaudio.utils import play

  client = FishAudio()

  # With speed control
  audio = client.tts.convert(
      text="I'm talking pretty fast, is this still too slow?",
      speed=1.5  # 1.5x speed
  )
  play(audio)
  ```

  ```python Asynchronous focus={8-12} theme={null}
  import asyncio
  from fishaudio import AsyncFishAudio
  from fishaudio.utils import play

  async def main():
      client = AsyncFishAudio()

      # With speed control
      audio = await client.tts.convert(
          text="I'm talking pretty fast, is this still too slow?",
          speed=1.5  # 1.5x speed
      )
      play(audio)

  asyncio.run(main())
  ```
</CodeGroup>

Create reusable configurations with [`TTSConfig`](/api-reference/sdk/python/types#ttsconfig-objects). [`Prosody`](/api-reference/sdk/python/types#prosody-objects) controls speech characteristics like speed and volume:

<CodeGroup>
  ```python Synchronous focus={7-18} theme={null}
  from fishaudio import FishAudio
  from fishaudio.types import TTSConfig, Prosody
  from fishaudio.utils import play

  client = FishAudio()

  # Define config once
  my_config = TTSConfig(
      prosody=Prosody(speed=1.2, volume=-5),
      reference_id="933563129e564b19a115bedd57b7406a", # Sarah
      format="wav",
      latency="balanced"
  )

  # Reuse across multiple generations
  audio1 = client.tts.convert(text="Welcome to our product demonstration.", config=my_config)
  audio2 = client.tts.convert(text="Let me show you the key features.", config=my_config)
  audio3 = client.tts.convert(text="Thank you for watching this tutorial.", config=my_config)

  play(audio1)
  play(audio2)
  play(audio3)
  ```

  ```python Asynchronous focus={9-20} theme={null}
  import asyncio
  from fishaudio import AsyncFishAudio
  from fishaudio.types import TTSConfig, Prosody
  from fishaudio.utils import play

  async def main():
      client = AsyncFishAudio()

      # Define config once
      my_config = TTSConfig(
          prosody=Prosody(speed=1.2, volume=-5),
          reference_id="933563129e564b19a115bedd57b7406a", # Sarah
          format="wav",
          latency="balanced"
      )

      # Reuse across multiple generations
      audio1 = await client.tts.convert(text="Welcome to our product demonstration.", config=my_config)
      audio2 = await client.tts.convert(text="Let me show you the key features.", config=my_config)
      audio3 = await client.tts.convert(text="Thank you for watching this tutorial.", config=my_config)

      play(audio1)
      play(audio2)
      play(audio3)

  asyncio.run(main())
  ```
</CodeGroup>

<Tip>
  For chunk-by-chunk processing, use [`stream()`](/api-reference/sdk/python/resources#stream) which returns an `AudioStream` (iterable). For real-time streaming with dynamic text, see [Real-time Streaming](#real-time-streaming) below.
</Tip>

Learn more in the [Text-to-Speech guide](/developer-guide/sdk-guide/python/text-to-speech).

### Speech-to-Text

Transcribe audio to text for various use cases:

<CodeGroup>
  ```python Synchronous focus={5-16} theme={null}
  from fishaudio import FishAudio

  client = FishAudio()

  # Transcribe audio
  with open("audio.wav", "rb") as f:
      result = client.asr.transcribe(
          audio=f.read(),
          language="en"  # Optional: specify language
      )

  print(result.text)

  # Access segments
  for segment in result.segments:
      print(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
  ```

  ```python Asynchronous focus={7-18} theme={null}
  import asyncio
  from fishaudio import AsyncFishAudio

  async def main():
      client = AsyncFishAudio()

      # Transcribe audio
      with open("audio.wav", "rb") as f:
          result = await client.asr.transcribe(
              audio=f.read(),
              language="en"  # Optional: specify language
          )

      print(result.text)

      # Access segments
      for segment in result.segments:
          print(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")

  asyncio.run(main())
  ```
</CodeGroup>

Learn more in the [Speech-to-Text guide](/developer-guide/sdk-guide/python/speech-to-text).

### Real-time Streaming

Stream dynamically generated text for conversational AI and live applications. Perfect for integrating with LLM streaming responses, live captions, and chatbot interactions:

<CodeGroup>
  ```python Synchronous focus={7-15} theme={null}
  from fishaudio import FishAudio
  from fishaudio.utils import play

  client = FishAudio()

  # Stream dynamically generated text (e.g., from LLM)
  def text_chunks():
      yield "Hello, "
      yield "this is "
      yield "streaming text!"

  audio_stream = client.tts.stream_websocket(
      text_chunks(),
      latency="balanced"
  )

  play(audio_stream)
  ```

  ```python Asynchronous focus={9-17} theme={null}
  import asyncio
  from fishaudio import AsyncFishAudio
  from fishaudio.utils import play

  async def main():
      client = AsyncFishAudio()

      # Stream dynamically generated text
      async def text_chunks():
          yield "Hello, "
          yield "this is "
          yield "streaming text!"

      audio_stream = await client.tts.stream_websocket(
          text_chunks(),
          latency="balanced"
      )

      play(audio_stream)

  asyncio.run(main())
  ```
</CodeGroup>

Learn more in the [WebSocket Streaming guide](/developer-guide/sdk-guide/python/websocket).

### Voice Cloning

**Instant voice cloning** - Clone a voice on-the-fly using [`ReferenceAudio`](/api-reference/sdk/python/types#referenceaudio-objects):

<CodeGroup>
  ```python Synchronous focus={6-12} theme={null}
  from fishaudio import FishAudio
  from fishaudio.types import ReferenceAudio

  client = FishAudio()

  # Instant voice cloning
  with open("reference.wav", "rb") as f:
      audio = client.tts.convert(
          text="This will sound like the reference voice",
          references=[ReferenceAudio(
              audio=f.read(),
              text="Text spoken in the reference audio"
          )]
      )
  ```

  ```python Asynchronous focus={8-14} theme={null}
  import asyncio
  from fishaudio import AsyncFishAudio
  from fishaudio.types import ReferenceAudio

  async def main():
      client = AsyncFishAudio()

      # Instant voice cloning
      with open("reference.wav", "rb") as f:
          audio = await client.tts.convert(
              text="This will sound like the reference voice",
              references=[ReferenceAudio(
                  audio=f.read(),
                  text="Text spoken in the reference audio"
              )]
          )

  asyncio.run(main())
  ```
</CodeGroup>

**Voice models** - Create persistent voice models for repeated use:

<CodeGroup>
  ```python Synchronous focus={6-11} theme={null}
  from fishaudio import FishAudio

  client = FishAudio()

  # Create persistent voice model
  with open("voice_sample.wav", "rb") as f:
      voice = client.voices.create(
          title="My Custom Voice",
          voices=[f.read()],
          description="Custom voice clone"
      )
  print(f"Created voice: {voice.id}")
  ```

  ```python Asynchronous focus={8-13} theme={null}
  import asyncio
  from fishaudio import AsyncFishAudio

  async def main():
      client = AsyncFishAudio()

      # Create persistent voice model
      with open("voice_sample.wav", "rb") as f:
          voice = await client.voices.create(
              title="My Custom Voice",
              voices=[f.read()],
              description="Custom voice clone"
          )
      print(f"Created voice: {voice.id}")

  asyncio.run(main())
  ```
</CodeGroup>

Learn more in the [Voice Cloning guide](/developer-guide/sdk-guide/python/voice-cloning).

## Client Initialization

<Tabs>
  <Tab title="Environment Variable">
    The recommended approach using environment variables:

    ```python  theme={null}
    from fishaudio import FishAudio

    # Automatically reads from FISH_API_KEY environment variable
    client = FishAudio()
    ```
  </Tab>

  <Tab title="Direct API Key">
    Provide the API key directly:

    ```python  theme={null}
    from fishaudio import FishAudio

    client = FishAudio(api_key="your_api_key")
    ```

    <Warning>
      Never commit API keys to version control. Use environment variables or secret management systems.
    </Warning>
  </Tab>

  <Tab title="Custom Endpoint">
    Configure a custom base URL:

    ```python  theme={null}
    from fishaudio import FishAudio

    client = FishAudio(
        api_key="your_api_key",
        base_url="https://your-proxy-domain.com"
    )
    ```
  </Tab>
</Tabs>

## Sync vs Async

The SDK provides both synchronous and asynchronous clients:

<CodeGroup>
  ```python Synchronous theme={null}
  from fishaudio import FishAudio

  # For typical applications
  client = FishAudio()
  audio = client.tts.convert(text="Hello!")
  ```

  ```python Asynchronous theme={null}
  import asyncio
  from fishaudio import AsyncFishAudio

  async def main():
      # For async applications (web servers, concurrent tasks)
      client = AsyncFishAudio()
      audio = await client.tts.convert(text="Hello!")

  asyncio.run(main())
  ```
</CodeGroup>

<Tip>
  Use [`AsyncFishAudio`](/api-reference/sdk/python/client#asyncfishaudio-objects) when:

  * Building async web applications (FastAPI, Sanic, etc.)
  * Processing multiple requests concurrently
  * Integrating with other async libraries
  * You need maximum performance
</Tip>

## Resource Clients

The SDK organizes functionality into resource clients:

| Resource                                                                      | Description        | Key Methods                                           |
| ----------------------------------------------------------------------------- | ------------------ | ----------------------------------------------------- |
| [`client.tts`](/api-reference/sdk/python/resources#ttsclient-objects)         | Text-to-speech     | `convert()`, `stream()`, `stream_websocket()`         |
| [`client.asr`](/api-reference/sdk/python/resources#asrclient-objects)         | Speech recognition | `transcribe()`                                        |
| [`client.voices`](/api-reference/sdk/python/resources#voicesclient-objects)   | Voice management   | `list()`, `get()`, `create()`, `update()`, `delete()` |
| [`client.account`](/api-reference/sdk/python/resources#accountclient-objects) | Account info       | `get_credits()`, `get_package()`                      |

## Utility Functions

The SDK includes helpful utilities (requires `utils` extra):

```python  theme={null}
from fishaudio.utils import save, play, stream

# Save audio to file
save(audio, "output.mp3")

# Play audio (automatically detects environment)
play(audio)  # Works in Jupyter, regular Python, etc.

# Stream audio in real-time (requires mpv)
stream(audio_iterator)
```

Use [`play()`](/api-reference/sdk/python/utils#play) for playback and [`save()`](/api-reference/sdk/python/utils#save) for writing audio files.

Learn more in the [API Reference - Utils](/api-reference/sdk/python/utils).

## Error Handling

The SDK provides a comprehensive exception hierarchy:

```python  theme={null}
from fishaudio import FishAudio
from fishaudio.exceptions import (
    FishAudioError,
    AuthenticationError,
    RateLimitError,
    ValidationError
)

client = FishAudio()

try:
    audio = client.tts.convert(text="Hello!")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError:
    print("Rate limit exceeded. Please wait before retrying.")
except ValidationError as e:
    print(f"Invalid request: {e}")
except FishAudioError as e:
    print(f"API error: {e}")
```

The SDK includes exceptions for [`AuthenticationError`](/api-reference/sdk/python/exceptions#authenticationerror-objects), [`RateLimitError`](/api-reference/sdk/python/exceptions#ratelimiterror-objects), [`ValidationError`](/api-reference/sdk/python/exceptions#validationerror-objects), and [`FishAudioError`](/api-reference/sdk/python/exceptions#fishaudioerror-objects) for common error scenarios.

Learn more in the [API Reference - Exceptions](/api-reference/sdk/python/exceptions).

## Next Steps

<CardGroup cols={2}>
  <Card title="Authentication" icon="key" href="/developer-guide/sdk-guide/python/authentication">
    Set up API keys and client configuration
  </Card>

  <Card title="Text-to-Speech" icon="microphone" href="/developer-guide/sdk-guide/python/text-to-speech">
    Generate natural-sounding speech
  </Card>

  <Card title="Voice Cloning" icon="clone" href="/developer-guide/sdk-guide/python/voice-cloning">
    Clone voices and manage voice models
  </Card>

  <Card title="Speech-to-Text" icon="waveform" href="/developer-guide/sdk-guide/python/speech-to-text">
    Transcribe audio to text
  </Card>

  <Card title="WebSocket Streaming" icon="bolt" href="/developer-guide/sdk-guide/python/websocket">
    Real-time audio streaming
  </Card>

  <Card title="API Reference" icon="book-open" href="/api-reference/sdk/python/overview">
    Complete API documentation
  </Card>
</CardGroup>

## Resources

* [GitHub Repository](https://github.com/fishaudio/fish-audio-python)
* [PyPI Package](https://pypi.org/project/fish-audio-sdk/)
* [Migration Guide](/archive/python-sdk-legacy/migration-guide) - Upgrade from legacy SDK
* [Best Practices](/developer-guide/best-practices/) - Production-ready tips
* [API Reference](/api-reference/sdk/python/) - Detailed documentation


Built with [Mintlify](https://mintlify.com).
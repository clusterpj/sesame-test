# Sesame Voice Chat Client

A robust Python client for interacting with Sesame's voice AI characters (Maya and Miles) using the unofficial SesameAI Python client.

## Features

- **Interactive Voice Conversations**: Have real-time voice conversations with Maya or Miles
- **Microphone Selection**: Choose from available microphones at startup
- **Visual Audio Feedback**: See real-time audio levels when speaking
- **Automatic Connection Management**: Monitors and maintains the WebSocket connection
- **Comprehensive Logging**: Detailed logs for troubleshooting
- **Robust Error Handling**: Gracefully handles connection and audio issues
- **Status Indicators**: Clear indicators when the AI character is speaking

## Prerequisites

- Python 3.7+
- Windows, macOS, or Linux
- Microphone and speakers/headphones
- Internet connection

## Installation

1. **Create and activate a virtual environment** (recommended):
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate on Windows
   venv\Scripts\activate
   
   # Activate on macOS/Linux
   source venv/bin/activate
   ```

2. **Install the unofficial SesameAI client**:
   ```bash
   # Clone the repository
   git clone https://github.com/ijub/sesame_ai.git
   
   # Navigate to the directory
   cd sesame_ai
   
   # Install in development mode
   pip install -e .
   ```

3. **Install dependencies**:
   ```bash
   pip install requests websocket-client numpy PyAudio
   ```

   **Note for Windows users**: If you have issues installing PyAudio, try using a pre-built wheel:
   ```bash
   # Remove any failed PyAudio installation
   pip uninstall pyaudio
   
   # Install using a pre-built wheel (check for the version matching your Python)
   pip install https://files.pythonhosted.org/packages/0c/1c/fb826d6ddb5d7aeb743baa7df5e5db1f99ef87afaa1b81a443196b30c3e8/PyAudio-0.2.11-cp38-cp38-win_amd64.whl
   ```

   **Note for Linux users**: You may need to install PortAudio first:
   ```bash
   # For Ubuntu/Debian
   sudo apt-get install portaudio19-dev
   
   # For Fedora/RHEL
   sudo dnf install portaudio-devel
   ```

4. **Save the Sesame Voice Chat client script**:
   - Save the `sesame_voice_chat.py` file to your project directory

## Usage

1. **Run the script**:
   ```bash
   python sesame_voice_chat.py
   ```

2. **Select your microphone**:
   - The script will display a list of available microphones
   - Enter the number corresponding to your preferred microphone

3. **Start the conversation**:
   - The script will connect to the selected character (Maya by default)
   - Start speaking when you see "Connected to [Character]! Start speaking..."
   - You'll see real-time audio level indicators when speaking
   - The character's responses will play through your speakers
   - Look for "→ Receiving audio from character..." and "← Character finished speaking" indicators

4. **Exit the application**:
   - Press Ctrl+C to stop the application
   - The script will clean up all resources and disconnect gracefully

## Configuration

You can modify these variables at the top of the script:

- **CHARACTER**: Change to "Miles" or "Maya" to select different characters
- **CHUNK**: Adjust audio chunk size (default: 1024)
- **RATE**: Adjust sample rate (default: 16000)
- **stream_reset_interval**: Interval in seconds between audio stream resets (default: 180)

## Troubleshooting

1. **Check the logs**:
   - Log files are created in the `logs` directory
   - The script creates a new log file each time it runs
   - Check logs for errors or warnings

2. **Connection issues**:
   - Ensure you have a stable internet connection
   - The script will automatically try to reconnect if the connection drops

3. **Audio issues**:
   - Check your microphone settings in your operating system
   - Ensure your microphone has permission to be accessed
   - Try selecting a different microphone if available

4. **Error: "No available input devices"**:
   - Ensure your microphone is connected and recognized by your OS
   - Check microphone permissions

5. **Character doesn't respond**:
   - Check your audio levels to ensure your voice is being detected
   - Speak clearly and at a moderate volume
   - Wait for the character to finish speaking before continuing

## Extending the Client

Here are some ideas for extending this client:

1. **Add a GUI**: Create a graphical interface using Tkinter or PyQt
2. **Speech-to-Text**: Add transcription to see what the character is saying
3. **Recording**: Add functionality to record conversations
4. **Multiple Characters**: Add an option to switch between characters more easily
5. **Custom Prompts**: Add the ability to set initial conversation prompts

## License

This client uses the unofficial SesameAI Python client, which is subject to its own licensing terms. Please use responsibly and in accordance with Sesame's terms of service.

## Acknowledgments

- This client utilizes the unofficial SesameAI Python client by ijub
- Special thanks to the developers of PyAudio, NumPy, and WebSocket-client libraries
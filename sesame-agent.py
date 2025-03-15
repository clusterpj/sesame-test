import time
import threading
import pyaudio
import numpy as np
import logging
import os
import traceback
from datetime import datetime
from sesame_ai import SesameAI, TokenManager, SesameWebSocket

# Set up logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_filename = os.path.join(log_dir, f"sesame_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("sesame_voice")

logger.info("Starting Sesame Voice Client")

# Initialize the client and get a token
try:
    client = SesameAI()
    token_manager = TokenManager(client, token_file="token.json")
    id_token = token_manager.get_valid_token()
    logger.info("Successfully obtained authentication token")
except Exception as e:
    logger.error(f"Failed to initialize Sesame client: {e}")
    logger.debug(traceback.format_exc())
    raise

# Choose character: "Miles" or "Maya"
CHARACTER = "Maya"  # Change to "Miles" if you prefer
logger.info(f"Selected character: {CHARACTER}")

# Global variables
connection_active = True
current_ws = None
reconnect_count = 0
audio_reset_count = 0

# Function to create and set up a new websocket connection
def setup_connection():
    global current_ws, reconnect_count
    
    logger.info("Setting up new WebSocket connection")
    
    # Set up WebSocket connection
    ws = SesameWebSocket(id_token=id_token, character=CHARACTER)
    
    # Connection callbacks
    def on_connect():
        logger.info(f"Connected to {CHARACTER}! Start speaking...")

    def on_disconnect():
        logger.info(f"Disconnected from {CHARACTER}")
        
    ws.set_connect_callback(on_connect)
    ws.set_disconnect_callback(on_disconnect)
    
    # Connect to the server
    logger.info(f"Connecting to {CHARACTER}...")
    try:
        ws.connect()
    except Exception as e:
        logger.error(f"Connection error: {e}")
        logger.debug(traceback.format_exc())
        return None
    
    # Wait for connection to establish
    time.sleep(2)
    
    if ws.is_connected():
        logger.info(f"Successfully connected to {CHARACTER}")
        current_ws = ws
        reconnect_count += 1
        logger.info(f"Connection established. Reconnect count: {reconnect_count}")
        return ws
    else:
        logger.error("Failed to connect. Will retry...")
        return None

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Initialize PyAudio
p = pyaudio.PyAudio()

# Function to list and select audio devices
def select_microphone():
    # Get a list of all input devices
    input_devices = []
    info = p.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')
    
    logger.info("\nAVAILABLE MICROPHONES:")
    
    for i in range(0, num_devices):
        device_info = p.get_device_info_by_host_api_device_index(0, i)
        if device_info.get('maxInputChannels') > 0:
            input_devices.append((i, device_info.get('name')))
            logger.info(f"{len(input_devices)}. Device id {i} - {device_info.get('name')}")
    
    if not input_devices:
        logger.error("No input devices found!")
        return None
    
    # Let user select a device
    choice = None
    while choice is None:
        try:
            selection = input("\nSelect microphone number (1-" + str(len(input_devices)) + "): ")
            idx = int(selection) - 1
            if 0 <= idx < len(input_devices):
                choice = input_devices[idx]
                logger.info(f"Selected: {choice[1]} (Device ID: {choice[0]})")
            else:
                logger.warning("Invalid selection. Please try again.")
        except ValueError:
            logger.warning("Please enter a number.")
    
    return choice[0]  # Return the device ID

# Select microphone
selected_mic_id = select_microphone()

# Open microphone stream with selected device
try:
    mic_stream = p.open(format=FORMAT,
                      channels=CHANNELS,
                      rate=RATE,
                      input=True,
                      input_device_index=selected_mic_id,
                      frames_per_buffer=CHUNK)
    logger.info(f"Successfully connected to selected microphone (Device ID: {selected_mic_id})")
except Exception as e:
    logger.error(f"Error connecting to selected microphone: {e}")
    logger.debug(traceback.format_exc())
    logger.info("Falling back to default microphone...")
    try:
        mic_stream = p.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          frames_per_buffer=CHUNK)
        logger.info("Connected to default microphone")
    except Exception as e:
        logger.critical(f"Failed to open any microphone: {e}")
        logger.debug(traceback.format_exc())
        raise

# Open speaker stream
try:
    speaker_stream = p.open(format=FORMAT,
                           channels=CHANNELS,
                           rate=16000,
                           output=True)
    logger.info("Speaker stream opened successfully")
except Exception as e:
    logger.critical(f"Failed to open speaker: {e}")
    logger.debug(traceback.format_exc())
    raise

# Function to calculate audio energy - with proper error handling
def calculate_energy(audio_data):
    try:
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        # Check if array is empty or all zeros
        if len(audio_array) == 0 or np.all(audio_array == 0):
            return 0.0
        
        # Calculate energy safely
        return float(np.sqrt(np.mean(np.square(audio_array.astype(float)))))
    except Exception as e:
        logger.warning(f"Error calculating audio energy: {e}")
        return 0.0

# Function to reset audio streams - more gentle approach
def reset_audio_streams():
    global mic_stream, speaker_stream, audio_reset_count
    
    logger.info("Performing gentle audio stream reset...")
    audio_reset_count += 1
    
    # Save current speaker rate
    current_speaker_rate = None
    if hasattr(speaker_stream, '_rate'):
        current_speaker_rate = speaker_stream._rate
    elif current_ws and hasattr(current_ws, 'server_sample_rate'):
        current_speaker_rate = current_ws.server_sample_rate
    
    # Reset microphone first, then speaker to minimize disruption
    try:
        # Close and reopen microphone
        mic_stream.stop_stream()
        mic_stream.close()
        logger.info("Microphone stream closed")
        
        # Brief pause
        time.sleep(0.1)
        
        # Reopen microphone
        mic_stream = p.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          input_device_index=selected_mic_id,
                          frames_per_buffer=CHUNK)
        logger.info("Microphone stream reset successfully")
        
        # Now handle speaker
        speaker_stream.stop_stream()
        speaker_stream.close()
        logger.info("Speaker stream closed")
        
        # Brief pause
        time.sleep(0.1)
        
        # Determine correct rate for speaker
        rate = 16000  # Default
        if current_speaker_rate:
            rate = current_speaker_rate
        elif current_ws and hasattr(current_ws, 'server_sample_rate'):
            rate = current_ws.server_sample_rate
        
        logger.info(f"Using sample rate for speaker: {rate}")
        
        # Reopen speaker
        speaker_stream = p.open(format=FORMAT,
                               channels=CHANNELS,
                               rate=rate,
                               output=True)
        logger.info("Speaker stream reset successfully")
        
    except Exception as e:
        logger.error(f"Error during gentle audio reset: {e}")
        logger.debug(traceback.format_exc())
        # Try a more aggressive reset as fallback
        try:
            # Close everything
            if hasattr(mic_stream, 'close'):
                mic_stream.close()
            if hasattr(speaker_stream, 'close'):
                speaker_stream.close()
            
            # Reopen with defaults
            mic_stream = p.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=RATE,
                              input=True,
                              input_device_index=selected_mic_id,
                              frames_per_buffer=CHUNK)
            
            rate = 16000
            if current_ws and hasattr(current_ws, 'server_sample_rate'):
                rate = current_ws.server_sample_rate
            
            speaker_stream = p.open(format=FORMAT,
                                   channels=CHANNELS,
                                   rate=rate,
                                   output=True)
            logger.info("Audio reset completed via fallback method")
        except Exception as e2:
            logger.critical(f"Critical error during audio reset: {e2}")
            raise
    
    logger.info(f"Audio reset completed. Total resets: {audio_reset_count}")

# Function to capture and send microphone audio
def capture_microphone():
    logger.info("Microphone capture thread started")
    
    # Variables for voice activity visualization
    audio_levels = []
    max_level_history = 5
    silent_frames = 0
    speaking_frames = 0
    
    # Variables for connection management
    last_activity_time = time.time()
    stream_reset_interval = 180  # Reset audio streams every 3 minutes
    last_stream_reset = time.time()
    last_heartbeat = time.time()
    
    try:
        while connection_active:
            if current_ws and current_ws.is_connected():
                try:
                    # Read audio data with error handling
                    try:
                        data = mic_stream.read(CHUNK, exception_on_overflow=False)
                    except Exception as e:
                        logger.warning(f"Error reading from microphone: {e}")
                        time.sleep(0.1)
                        continue
                    
                    # Calculate energy for activity detection
                    energy = calculate_energy(data)
                    
                    # Track audio levels for better visualization
                    audio_levels.append(energy)
                    if len(audio_levels) > max_level_history:
                        audio_levels.pop(0)
                    
                    # Update activity time if there's significant audio
                    if energy > 500:
                        last_activity_time = time.time()
                        speaking_frames += 1
                        silent_frames = 0
                        
                        # Only log occasionally to avoid flooding
                        if speaking_frames % 10 == 0:
                            logger.debug(f"Speaking detected. Energy level: {energy:.1f}")
                        
                        # Visual representation of audio level
                        avg_level = sum(audio_levels) / len(audio_levels) if audio_levels else 0
                        bars = int(min(avg_level / 100, 20))
                        print(f"\rMic: {'|' * bars}{' ' * (20-bars)} Level: {energy:.0f}", end='')
                    else:
                        silent_frames += 1
                        speaking_frames = 0
                        
                        # Log silence periods (occasionally)
                        if silent_frames % 100 == 0 and silent_frames > 0:
                            logger.debug(f"Silence continues. Frames: {silent_frames}")
                    
                    # Send audio data with error handling
                    try:
                        current_ws.send_audio_data(data)
                    except Exception as e:
                        logger.error(f"Error sending audio data: {e}")
                        logger.debug(traceback.format_exc())
                        # Don't continue to avoid excessive error logging
                        time.sleep(0.5)
                        continue
                    
                    # Check if we need to reset the audio streams
                    current_time = time.time()
                    if current_time - last_stream_reset > stream_reset_interval:
                        logger.info(f"Performing scheduled audio stream reset after {stream_reset_interval} seconds")
                        reset_audio_streams()
                        last_stream_reset = current_time
                    
                    # Send a heartbeat ping if there's been no activity
                    if current_time - last_heartbeat > 5:  # Heartbeat every 5 seconds
                        logger.debug("Sending regular heartbeat ping")
                        last_heartbeat = current_time
                        
                        # If there's been no activity for a while, log it
                        if current_time - last_activity_time > 10:
                            logger.info("No audio activity detected for 10+ seconds")
                        
                except Exception as e:
                    logger.error(f"Error in microphone capture loop: {e}")
                    logger.debug(traceback.format_exc())
                    time.sleep(1)
            else:
                logger.warning("Not connected in microphone thread. Waiting...")
                time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Microphone capture stopped by user")
    except Exception as e:
        logger.error(f"Microphone thread crashed: {e}")
        logger.debug(traceback.format_exc())
    finally:
        logger.info("Microphone capture thread ending")

# Function to play received audio
def play_audio():
    logger.info("Audio playback thread started")
    receiving_audio = False
    silent_frames = 0
    
    try:
        while connection_active:
            if current_ws and current_ws.is_connected():
                try:
                    # Get audio with timeout and error handling
                    try:
                        audio_chunk = current_ws.get_next_audio_chunk(timeout=0.01)
                    except Exception as e:
                        if "timeout" not in str(e).lower():
                            logger.warning(f"Error getting audio chunk: {e}")
                        time.sleep(0.01)
                        continue
                    
                    if audio_chunk:
                        # Reset silent frame counter when we get audio
                        silent_frames = 0
                        
                        if not receiving_audio:
                            logger.info("Character started speaking")
                            print("\n→ Receiving audio from character...")
                            receiving_audio = True
                        
                        # Play audio with error handling
                        try:
                            speaker_stream.write(audio_chunk)
                        except Exception as e:
                            logger.error(f"Error playing audio: {e}")
                    else:
                        silent_frames += 1
                        
                        # If we've been receiving audio but now got silence for a while
                        if receiving_audio and silent_frames > 100:  # About 1 second of silence
                            logger.info("Character finished speaking")
                            print("← Character finished speaking")
                            receiving_audio = False
                            
                except Exception as e:
                    if "timeout" not in str(e).lower():  # Ignore timeout exceptions
                        logger.error(f"Error in audio playback loop: {e}")
                        logger.debug(traceback.format_exc())
                    time.sleep(0.1)
            else:
                logger.warning("Not connected in playback thread. Waiting...")
                time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Audio playback stopped by user")
    except Exception as e:
        logger.error(f"Playback thread crashed: {e}")
        logger.debug(traceback.format_exc())
    finally:
        logger.info("Audio playback thread ending")

# Function to periodically check and maintain the connection
def connection_monitor():
    global current_ws
    
    reconnection_attempts = 0
    logger.info("Connection monitor thread started")
    
    while connection_active:
        try:
            # Check if connection is still active
            if current_ws is None or not current_ws.is_connected():
                reconnection_attempts += 1
                logger.warning(f"Connection lost or not established. Reconnection attempt {reconnection_attempts}...")
                
                # Try to disconnect cleanly if there's an existing connection
                if current_ws:
                    try:
                        current_ws.disconnect()
                        logger.info("Successfully disconnected old connection")
                    except Exception as e:
                        logger.warning(f"Error disconnecting: {e}")
                
                # Create a new connection
                current_ws = setup_connection()
                
                # If successfully reconnected, reset speaker stream to match server sample rate
                if current_ws and current_ws.is_connected() and hasattr(current_ws, 'server_sample_rate'):
                    try:
                        logger.info(f"Adjusting speaker to server sample rate: {current_ws.server_sample_rate}Hz")
                        speaker_stream.close()
                        speaker_stream = p.open(format=FORMAT,
                                               channels=CHANNELS,
                                               rate=current_ws.server_sample_rate,
                                               output=True)
                    except Exception as e:
                        logger.error(f"Error adjusting speaker rate: {e}")
            else:
                # Connection is good, log status occasionally
                if reconnection_attempts > 0:
                    logger.info(f"Connection stable after {reconnection_attempts} reconnection attempts")
                    reconnection_attempts = 0
        except Exception as e:
            logger.error(f"Error in connection monitor: {e}")
            logger.debug(traceback.format_exc())
        
        # Check every 10 seconds
        time.sleep(10)

# Function to periodically check for system health and log statistics
def system_monitor():
    logger.info("System monitor thread started")
    
    # Track statistics
    start_time = time.time()
    last_stats_time = start_time
    
    while connection_active:
        try:
            current_time = time.time()
            # Log stats every minute
            if current_time - last_stats_time >= 60:
                uptime = current_time - start_time
                logger.info(f"System statistics - Uptime: {uptime:.1f}s, Reconnects: {reconnect_count}, Audio resets: {audio_reset_count}")
                last_stats_time = current_time
                
                # Check if websocket is connected
                if current_ws:
                    logger.info(f"WebSocket connected: {current_ws.is_connected()}")
                else:
                    logger.warning("WebSocket not initialized")
                
                # Check audio streams
                try:
                    mic_active = mic_stream.is_active()
                    speaker_active = speaker_stream.is_active()
                    logger.info(f"Audio streams - Mic active: {mic_active}, Speaker active: {speaker_active}")
                except:
                    logger.warning("Could not check audio stream status")
        except Exception as e:
            logger.error(f"Error in system monitor: {e}")
        
        # Check every 15 seconds
        time.sleep(15)

# Initial connection
logger.info("Establishing initial connection...")
current_ws = setup_connection()

# Update speaker sample rate after connection is established
if current_ws and current_ws.is_connected() and hasattr(current_ws, 'server_sample_rate'):
    logger.info(f"Adjusting to server sample rate: {current_ws.server_sample_rate}Hz")
    speaker_stream.close()
    speaker_stream = p.open(format=FORMAT,
                           channels=CHANNELS,
                           rate=current_ws.server_sample_rate,
                           output=True)

# Start threads
logger.info("Starting worker threads...")

mic_thread = threading.Thread(target=capture_microphone)
mic_thread.daemon = True
mic_thread.start()

playback_thread = threading.Thread(target=play_audio)
playback_thread.daemon = True
playback_thread.start()

monitor_thread = threading.Thread(target=connection_monitor)
monitor_thread.daemon = True
monitor_thread.start()

stats_thread = threading.Thread(target=system_monitor)
stats_thread.daemon = True
stats_thread.start()

# Initial instructions for the users 
logger.info("All systems initialized")
print("\n" + "="*50)
print(f"You are now connected to {CHARACTER}!")
print("HOW TO USE:")
print("1. Speak clearly into your selected microphone")
print("2. You'll see a visual audio level indicator when speaking")
print("3. The system will automatically maintain the connection")
print("4. Press Ctrl+C to exit")
print("5. Log file is being created at: " + log_filename)
print("="*50 + "\n")

# Keep the main thread alive
try:
    print("Session active. Press Ctrl+C to exit")
    while connection_active:
        time.sleep(1)
except KeyboardInterrupt:
    logger.info("Shutdown initiated by user (Ctrl+C)")
    print("\nShutting down...")
except Exception as e:
    logger.critical(f"Critical error in main thread: {e}")
    logger.debug(traceback.format_exc())
finally:
    # Clean up
    connection_active = False
    logger.info("Cleaning up resources...")
    
    if current_ws:
        try:
            current_ws.disconnect()
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")
    
    try:
        mic_stream.stop_stream()
        mic_stream.close()
        logger.info("Microphone stream closed")
    except Exception as e:
        logger.error(f"Error closing microphone stream: {e}")
    
    try:
        speaker_stream.stop_stream()
        speaker_stream.close()
        logger.info("Speaker stream closed")
    except Exception as e:
        logger.error(f"Error closing speaker stream: {e}")
    
    try:
        p.terminate()
        logger.info("PyAudio terminated")
    except Exception as e:
        logger.error(f"Error terminating PyAudio: {e}")
    
    logger.info("All resources cleaned up. Session ended.")
    print("Resources cleaned up. Check the log file for details.")
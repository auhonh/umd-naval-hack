import asyncio
import json
import overshoot
import cv2
import os
from dotenv import load_dotenv
from collections import deque
import time
import zmq
import zmq.asyncio

''' running this on the pi, so we need to open a port and send info to the terminal when needed.'''

load_dotenv()
LAPTOP_IP = "192.168.6.218" # gonna have to change this when we move over to the hotspot IP
API_KEY = os.getenv("OVERSHOOT_API_KEY")
BUFFER_LENGTH_SECONDS = 3.0
FPS = 15
frame_buffer = deque(maxlen=int(BUFFER_LENGTH_SECONDS * FPS)) # Assuming 5 FPS max

async def create_and_send_clip(frames_to_save, alert_text, current_target, push_socket, loop):
    """Compiles the mp4 and fires it over the network."""
    if not frames_to_save:
        return
        
    temp_filename = "/tmp/temp_anomaly.mp4" # Store temporarily in Pi's RAM/disk
    height, width, _ = frames_to_save[0].shape
    
    # Write frames to the temporary file
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(temp_filename, fourcc, FPS, (width, height))
    for frame in frames_to_save:
        out.write(frame)
    out.release()
    
    # Read the raw binary data
    with open(temp_filename, "rb") as f:
        video_bytes = f.read()
        
    # Prepare the JSON metadata
    metadata = {
        "message": alert_text,
        "fps": FPS,
        "duration": BUFFER_LENGTH_SECONDS,
        "current_target": current_target
    }
    metadata_bytes = json.dumps(metadata).encode('utf-8')
    
    # Fire the multipart message safely from the async loop
    await push_socket.send_multipart([metadata_bytes, video_bytes])
    print("[+] Video sent.")

def handle_overshoot_result(response, current_target, loop, push_socket):
    try:
        # The result is now guaranteed to be a JSON string
        data = json.loads(response.result)
        # Check the strict boolean
        if data.get("detected") is True and current_target.lower() in data.get("description").lower():
            # Lock in the current buffer
            print(f"\n[Found]: {data.get('description')}")
            captured_clip = list(frame_buffer)            
            # Send the video and the AI's detailed explanation over the network
            description = data.get("description", "Target detected")
            await create_and_send_clip(captured_clip, description, current_target, push_socket, loop)
        else:
            # Print what the AI sees when the water is clear
            print(f"[Clear] AI sees: {data.get('description')}")
            
    except json.JSONDecodeError:
        print(f"[-] AI returned invalid JSON: {response.result}")

async def run_camera_loop(client, sub_socket, push_socket):
    # Make sure you are using the for await calls
    source = overshoot.FrameSource(width=640, height=480)
    loop = asyncio.get_running_loop()

    poller = zmq.asyncio.Poller()
    poller.register(sub_socket, zmq.POLLIN)
    
    current_target = "boat"

    print("Connecting to Overshoot...")

    DETECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "detected": {
            "type": "boolean",
            "description": "True if the requested target object is confidently and clearly visible, otherwise false."
        },
        "description": {
            "type": "string",
            "description": "A short, 1-sentence description of what you currently see. 15 words max."
        }
    },
    "required": ["detected", "description"]
    }
    stream = await client.streams.create(
        source=source,
        prompt=f"Analyze the scene. You are strictly looking for a {current_target}. Respond True ONLY if the {current_target} is clearly visible. If you only see people, rooms, or empty water, respond False.",
        model="Qwen/Qwen3.5-4B",
        on_result=lambda r: handle_overshoot_result(r, current_target, loop, push_socket),
        max_output_tokens=50,
        output_schema=DETECTION_SCHEMA,
        #  3 FPS for a 1-second clip = 3 frames sent to the model per analysis
        target_fps=3,
        clip_length_seconds=1.0, 
        delay_seconds=0.5,
        interval_seconds=2.0 # Ask for analysis every 2 seconds
    )

    cap = cv2.VideoCapture(0)
    print("Streaming frames... Press Ctrl+C in the terminal to stop.")
    
    try:
        while True:
            # Check if any messages are waiting. Timeout=0 means "don't wait, just check"
            events = dict(poller.poll(timeout=0))
            
            # If our sub_socket is in the events dictionary, a message is waiting!
            if sub_socket in events:
                # We can safely call recv_string() without it blocking or throwing an error
                msg = sub_socket.recv_string() 
                if msg == "stop":
                    print("\n[!] Stop command received. Halting camera.")
                    break
                elif msg.startswith("TARGET:"):
                    # Extract the new target and update the stream live
                    current_target = msg.split("TARGET:")[1]
                    print(f"\n[!] Now looking for '{current_target}'")
                    
                    new_prompt = f"Analyze the scene. You are strictly looking for a {current_target}. Respond True ONLY if the {current_target} is clearly visible. If you only see rooms or empty water, respond False."
                    await stream.update_prompt(new_prompt)

            ret, bgr = cap.read()
            if not ret:
                print("Camera feed lost.")
                break
                
            frame_buffer.append(bgr)
            
            rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
            rgba = cv2.resize(rgba, (640, 480))
            source.push_frame(rgba) 
            
            await asyncio.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping stream...")
        
    finally:
        cap.release()
        await stream.close()
        await client.close()
        print("Cleanup complete.")

async def main():
    ctx = zmq.asyncio.Context()

    # Connect to Command Center (Commands In)
    print(f"[*] Linking to Command Center at {LAPTOP_IP}...")
    sub_socket = ctx.socket(zmq.SUB)
    sub_socket.connect(f"tcp://{LAPTOP_IP}:5555")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "") # Subscribe to all messages

    # Connect to Command Center (Alerts Out)
    push_socket = ctx.socket(zmq.PUSH)
    push_socket.connect(f"tcp://{LAPTOP_IP}:5556")
    
    client = overshoot.Overshoot(api_key=API_KEY) 
    print("[+] Pi ready :)")

    try:
        while True:
            # Wait idle here until a command arrives
            msg = await sub_socket.recv_string()
            if msg == "start":
                print("\n[!] Start command received.")
                await run_camera_loop(client, sub_socket, push_socket)
    except KeyboardInterrupt:
        pass
    finally:
        await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # Catch the interrupt at the top level to hide the ugly traceback


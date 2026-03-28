import asyncio
import zmq
import zmq.asyncio
import json
import time

''' my laptop basically just listens for alerts from the Pi and prints them to the terminal.'''

async def listen_for_alerts(pull_socket):
    """Constantly listens for messages from the Pi."""
    print("[*] Listening for incoming alerts on port 5556...")
    while True:
        # This waits silently until a message arrives
        parts = await pull_socket.recv_multipart()
        
        # 2. Unpack the JSON metadata and the binary video
        metadata = json.loads(parts[0].decode('utf-8'))
        video_bytes = parts[1]
        
        # 3. Save the video to your laptop's hard drive
        filename = f"anomaly_capture_{int(time.time())}.mp4"
        with open(filename, "wb") as f:
            f.write(video_bytes)
            
        print(f"\n[🚨 ALERT]: {metadata['message']}")
        print(f"[📁 VIDEO SAVED]: {filename}")
        print("Command (start/stop): ", end="", flush=True)

async def get_user_commands(pub_socket):
    """Waits for you to type 'start' or 'stop' and broadcasts it."""
    loop = asyncio.get_running_loop()
    print("[*] Command broadcaster ready on port 5555.")
    
    while True:
        # run_in_executor prevents input() from freezing the incoming alerts
        cmd = await loop.run_in_executor(None, input, "Command (start/stop): ")
        cmd = cmd.strip().lower()
        
        if cmd in ['start', 'stop']:
            await pub_socket.send_string(cmd)
            print(f"[+] Broadcasted: {cmd}")
        else:
            print("[-] Invalid command. Use 'start' or 'stop'.")

async def main():
    ctx = zmq.asyncio.Context()

    # Setup the Publisher socket (Commands out)
    pub_socket = ctx.socket(zmq.PUB)
    pub_socket.bind("tcp://*:5555")

    # Setup the Pull socket (Alerts in)
    pull_socket = ctx.socket(zmq.PULL)
    pull_socket.bind("tcp://*:5556")

    # Run both tasks concurrently
    await asyncio.gather(
        listen_for_alerts(pull_socket),
        get_user_commands(pub_socket)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down Command Center.")
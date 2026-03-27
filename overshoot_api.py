API_KEY = "ovs_3ee750f415615cf3e4be01c6b997f58f"
import asyncio
import overshoot


async def main():
    client = overshoot.Overshoot(api_key=API_KEY)

    stream = await client.streams.create(
        source=overshoot.FileSource(path="C:\\Users\\mateo\\OneDrive\\Mateo\\umd-naval-hack\\YTDown.com_YouTube_Markiplier-Punches-You_Media_teYFeGD6Ilc_001_1080p.mp4", loop=True),
        prompt="Describe what you see",
        model="Qwen/Qwen3.5-9B",
        on_result=lambda r: print(r.result),
    )
    await asyncio.sleep(5)
    await stream.close()
    await client.close()

asyncio.run(main())


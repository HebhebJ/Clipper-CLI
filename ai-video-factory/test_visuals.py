import httpx
import json

SCRIPT = {
  "topic": "Elon musk and going to mars",
  "duration_seconds": 45.926,
  "tone": "Informational",
  "language": "en",
  "title": "",
  "hook": "",
  "scenes": [
    {
      "id": 1,
      "start": 0.0,
      "end": 7.037,
      "voice_text": "As we look up at the night sky, our eyes are drawn to a distant red planet - Mars.",
      "visual_tags": [
        "night sky",
        "Mars planet"
      ],
      "on_screen_text": "Mars in Sight"
    },
    {
      "id": 2,
      "start": 7.037,
      "end": 16.296,
      "voice_text": "And for Elon Musk, that's not just a dream, it's a mission. With his company SpaceX, he's working tirelessly to make humanity a multi-planetary species.",
      "visual_tags": [
        "SpaceX logo",
        "mission control room",
        "Elon Musk"
      ],
      "on_screen_text": "Making it Happen"
    },
    # ... add other scenes if you want
  ],
}

async def main():
    video_id = "test-elon"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://127.0.0.1:8004/generate-visuals",
            json={
                "video_id": video_id,
                "script": SCRIPT,
                "resolution": "1080x1920",
                "fps": 30,
            },
        )
    print("Status:", resp.status_code)
    print(resp.json())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    
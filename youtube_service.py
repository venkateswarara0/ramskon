import os
import requests
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


def search_youtube_videos(query, max_results=3):
    if not YOUTUBE_API_KEY:
        return []

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY
    }

    response = requests.get(url, params=params, timeout=20)
    data = response.json()

    videos = []

    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        videos.append({
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "thumbnail": snippet["thumbnails"]["medium"]["url"],
            "youtube_link": f"https://www.youtube.com/watch?v={video_id}"
        })

    return videos
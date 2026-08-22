"""
YouTube data/transcript module.

This file contains YouTube logic only.
The GUI and __main__ entry point were moved to main.py.
"""

# import os
import re
# import json
# import requests
# import pandas as pd
# from datetime import datetime, timezone
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (    TranscriptsDisabled,    NoTranscriptFound,    VideoUnavailable,)


# BASE_URL = "https://www.googleapis.com/youtube/v3"
# CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".yt_research_config.json")
# GLOBAL_API_KEY = [""]




def extract_video_id(url_or_id: str):
    url_or_id = url_or_id.strip()

    patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        m = re.search(pattern, url_or_id)
        if m:
            return m.group(1)

    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url_or_id):
        return url_or_id

    return None


def fetch_transcript_text(video_id: str):
    """Return (text, language), or raise if transcript is unavailable."""
    ytt_api = YouTubeTranscriptApi()

    try:
        fetched = ytt_api.fetch(
            video_id,
            languages=["vi", "en"],
        )
        lang = getattr(fetched, "language", None) or "vi/en"

    except NoTranscriptFound:
        transcript_list = ytt_api.list(video_id)
        transcript = next(iter(transcript_list))
        fetched = transcript.fetch()
        lang = transcript.language

    raw = fetched.to_raw_data()

    text = "\n".join(
        f"[{int(item['start'])}s] {item['text']}"
        for item in raw
    )
    text = clean_transcript(text)
    return text, lang



def clean_transcript(text):
    # 1. Xóa timestamp như [7s], [10s]...
    text = re.sub(r'\[\d+s\]\s*', '', text)

    # 2. Marker như [âm nhạc], [tiếng cười]...
    # được coi là điểm ngắt đoạn
    text = re.sub(r'\[[^\]]*\]\s*', '\n\n', text)

    # 3. Tách thành các đoạn văn dựa trên marker
    raw_paragraphs = re.split(r'\n\s*\n', text)

    paragraphs = []

    for paragraph in raw_paragraphs:
        # Chuẩn hóa khoảng trắng trong từng đoạn
        paragraph = re.sub(r'\s+', ' ', paragraph).strip()

        if paragraph:
            paragraphs.append(paragraph)

    # 4. Ghép lại thành các đoạn văn
    return '\n\n'.join(paragraphs)


#
# def extract_handle_or_id(url: str):
#     url = url.strip()
#     patterns = [
#         (r"youtube\.com/channel/([a-zA-Z0-9_-]+)", "id"),
#         (r"youtube\.com/@([a-zA-Z0-9_.-]+)", "handle"),
#         (r"youtube\.com/c/([a-zA-Z0-9_.-]+)", "custom"),
#         (r"youtube\.com/user/([a-zA-Z0-9_.-]+)", "username"),
#     ]
#     for pattern, kind in patterns:
#         m = re.search(pattern, url)
#         if m:
#             return kind, m.group(1)
#     if url.startswith("@"):
#         return "handle", url[1:]
#     return "search", url
#
#
# def get_channel_id(kind, value, api_key):
#     if kind == "id":
#         return value
#     if kind == "handle":
#         r = requests.get(
#             f"{BASE_URL}/channels",
#             params={"part": "id", "forHandle": value, "key": api_key},
#         ).json()
#     elif kind == "username":
#         r = requests.get(
#             f"{BASE_URL}/channels",
#             params={"part": "id", "forUsername": value, "key": api_key},
#         ).json()
#     else:
#         r = requests.get(
#             f"{BASE_URL}/search",
#             params={
#                 "part": "snippet",
#                 "q": value,
#                 "type": "channel",
#                 "maxResults": 1,
#                 "key": api_key,
#             },
#         ).json()
#         items = r.get("items", [])
#         return items[0]["snippet"]["channelId"] if items else None
#
#     items = r.get("items", [])
#     return items[0]["id"] if items else None
#
#
# def get_uploads_playlist_id(channel_id, api_key):
#     r = requests.get(
#         f"{BASE_URL}/channels",
#         params={
#             "part": "contentDetails,snippet",
#             "id": channel_id,
#             "key": api_key,
#         },
#     ).json()
#
#     items = r.get("items", [])
#     if not items:
#         return None, None
#
#     playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
#     channel_name = items[0]["snippet"]["title"]
#     return playlist_id, channel_name
#
#
# def get_video_ids(playlist_id, max_videos, api_key):
#     video_ids = []
#     next_page = None
#
#     while len(video_ids) < max_videos:
#         params = {
#             "part": "contentDetails",
#             "playlistId": playlist_id,
#             "maxResults": min(50, max_videos - len(video_ids)),
#             "key": api_key,
#         }
#
#         if next_page:
#             params["pageToken"] = next_page
#
#         r = requests.get(
#             f"{BASE_URL}/playlistItems",
#             params=params,
#         ).json()
#
#         for item in r.get("items", []):
#             video_ids.append(item["contentDetails"]["videoId"])
#
#         next_page = r.get("nextPageToken")
#         if not next_page:
#             break
#
#     return video_ids
#
#
# def get_video_details(video_ids, channel_name, api_key):
#     rows = []
#
#     for i in range(0, len(video_ids), 50):
#         chunk = video_ids[i:i + 50]
#
#         r = requests.get(
#             f"{BASE_URL}/videos",
#             params={
#                 "part": "snippet,statistics",
#                 "id": ",".join(chunk),
#                 "key": api_key,
#             },
#         ).json()
#
#         for item in r.get("items", []):
#             snippet = item["snippet"]
#             stats = item.get("statistics", {})
#
#             published = datetime.fromisoformat(
#                 snippet["publishedAt"].replace("Z", "+00:00")
#             )
#
#             days_since = (
#                 datetime.now(timezone.utc) - published
#             ).days or 1
#
#             views = int(stats.get("viewCount", 0))
#
#             rows.append({
#                 "Kênh": channel_name,
#                 "Tiêu đề": snippet["title"],
#                 "Ngày đăng": published.strftime("%Y-%m-%d"),
#                 "Số ngày đã đăng": days_since,
#                 "Lượt xem": views,
#                 "Lượt xem/ngày": round(views / days_since, 1),
#                 "Lượt thích": int(stats.get("likeCount", 0)),
#                 "Bình luận": int(stats.get("commentCount", 0)),
#                 "Tags": ", ".join(snippet.get("tags", [])[:10]),
#                 "Link video": f"https://www.youtube.com/watch?v={item['id']}",
#             })
#
#     return rows
#
#
# def process_channel(url, api_key, top_n, log_fn):
#     kind, value = extract_handle_or_id(url)
#
#     channel_id = get_channel_id(kind, value, api_key)
#     if not channel_id:
#         log_fn(f"⚠️  Không tìm thấy kênh từ link: {url}")
#         return []
#
#     playlist_id, channel_name = get_uploads_playlist_id(
#         channel_id,
#         api_key,
#     )
#
#     if not playlist_id:
#         log_fn(f"⚠️  Không lấy được video của kênh: {url}")
#         return []
#
#     # Giữ nguyên logic cũ: quét tối đa 50 video gần nhất.
#     video_ids = get_video_ids(playlist_id, 50, api_key)
#     all_videos = get_video_details(
#         video_ids,
#         channel_name,
#         api_key,
#     )
#
#     all_videos.sort(
#         key=lambda r: r["Lượt xem"],
#         reverse=True,
#     )
#
#     top_videos = all_videos[:top_n]
#
#     log_fn(
#         f"✅ {channel_name}: {len(top_videos)} video view cao "
#         f"(trong tổng {len(all_videos)} video đã quét)"
#     )
#
#     return top_videos

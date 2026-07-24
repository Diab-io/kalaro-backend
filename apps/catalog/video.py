import requests
from django.conf import settings


class VideoUploadError(Exception):
    pass


def create_stream_upload(title: str) -> dict:
    if settings.DEBUG:
        import uuid
        return {"video_id": f"fake-{uuid.uuid4().hex[:8]}", "upload_url": "http://localhost/fake-upload"}

    resp = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.CLOUDFLARE_ACCOUNT_ID}/stream/direct_upload",
        headers={"Authorization": f"Bearer {settings.CLOUDFLARE_STREAM_API_TOKEN}"},
        json={
            "maxDurationSeconds": 3600,
            "meta": {"name": title},
        },
        timeout=10,
    )
    if not resp.ok:
        raise VideoUploadError(f"{resp.status_code}: {resp.text}")

    data = resp.json()
    if not data.get("success"):
        raise VideoUploadError(data.get("errors"))

    result = data["result"]
    return {"video_id": result["uid"], "upload_url": result["uploadURL"]}


def get_playback_info(video_id: str) -> dict:
    """
    Used later in module 4 to check a video is ready and fetch its
    HLS/DASH manifest URLs for gated playback.
    """
    resp = requests.get(
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.CLOUDFLARE_ACCOUNT_ID}/stream/{video_id}",
        headers={"Authorization": f"Bearer {settings.CLOUDFLARE_STREAM_API_TOKEN}"},
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()["result"]
    return {
        "ready": result["readyToStream"],
        "hls_url": result["playback"]["hls"],
        "dash_url": result["playback"]["dash"],
        "duration": result.get("duration"),
    }
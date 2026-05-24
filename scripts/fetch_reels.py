import json
import os
import instaloader

def fetch_reels():
    TARGET_ACCOUNT = "prof_ds_"
    MAX_REELS = 10
    DATA_PATH = os.path.join("users", "default", "data", "gallery.json")

    print(f"Fetching latest reels for {TARGET_ACCOUNT}...")

    # Load existing gallery data
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        gallery_data = json.load(f)

    L = instaloader.Instaloader(
        download_pictures=False,
        download_video_thumbnails=False,
        download_videos=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
    )

    try:
        profile = instaloader.Profile.from_username(L.context, TARGET_ACCOUNT)
    except Exception as e:
        print(f"Error accessing profile: {e}")
        return

    # Filter for reels
    reels = []
    for post in profile.get_posts():
        if post.is_video:
            # Generate a title from the caption
            title = post.caption[:40] + "..." if post.caption else f"Reel #{len(reels)+1}"
            title = title.split("\n")[0] # keep it to one line

            reels.append({
                "title": title,
                "reel_url": f"https://www.instagram.com/reel/{post.shortcode}/",
                "reel_id": post.shortcode
            })
            
            if len(reels) >= MAX_REELS:
                break

    if reels:
        gallery_data["reels"] = reels
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(gallery_data, f, indent=4, ensure_ascii=False)
        print(f"Successfully updated gallery.json with {len(reels)} reels.")
    else:
        print("No reels found or failed to fetch.")

if __name__ == "__main__":
    fetch_reels()

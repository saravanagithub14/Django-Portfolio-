import json
import os
import instaloader
import requests

def fetch_reels():
    TARGET_ACCOUNT = "prof_ds_"
    MAX_REELS = 10
    DATA_PATH = os.path.join("users", "default", "data", "gallery.json")
    IMG_DIR = os.path.join("static", "images", "reels")
    
    os.makedirs(IMG_DIR, exist_ok=True)

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
            
            # Download Thumbnail
            img_filename = f"{post.shortcode}.jpg"
            img_path = os.path.join(IMG_DIR, img_filename)
            rel_img_path = f"static/images/reels/{img_filename}"
            
            if not os.path.exists(img_path):
                print(f"Downloading thumbnail for {post.shortcode}...")
                try:
                    response = requests.get(post.url)
                    if response.status_code == 200:
                        with open(img_path, 'wb') as f:
                            f.write(response.content)
                except Exception as e:
                    print(f"Failed to download thumbnail: {e}")

            reels.append({
                "title": title,
                "reel_url": f"https://www.instagram.com/reel/{post.shortcode}/",
                "reel_id": post.shortcode,
                "thumbnail": rel_img_path
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

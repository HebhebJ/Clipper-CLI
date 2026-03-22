import os
import yt_dlp
import sys

def download_video(url, download_path="./downloads", quality='best'):
    """
    Download YouTube video using yt-dlp
    
    Args:
        url (str): YouTube video URL
        download_path (str): Directory to save the video
        quality (str): Video quality ('best', 'worst', 'mp4', '720p', etc.)
    """
    
    # Create download directory if it doesn't exist
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    
    # Configure yt-dlp options
    ydl_opts = {
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'format': quality,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(url, download=False)
            print(f"Title: {info.get('title', 'Unknown')}")
            print(f"Duration: {info.get('duration', 'Unknown')} seconds")
            print(f"Uploader: {info.get('uploader', 'Unknown')}")
            print(f"Views: {info.get('view_count', 'Unknown')}")
            print("-" * 50)
            
            # Ask for confirmation
            confirm = input("Do you want to download this video? (y/n): ").lower()
            if confirm == 'y':
                print("Downloading...")
                ydl.download([url])
                print("Download completed successfully!")
            else:
                print("Download cancelled.")
                
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def download_audio_only(url, download_path="./downloads"):
    """
    Download only audio from YouTube video
    """
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    
    ydl_opts = {
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("Downloading audio...")
            ydl.download([url])
            print("Audio download completed!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def show_available_formats(url):
    """
    Show all available formats for a video
    """
    ydl_opts = {
        'listformats': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def main():
    print("YouTube Video Downloader")
    print("=" * 30)
    
    while True:
        print("\nOptions:")
        print("1. Download video")
        print("2. Download audio only (MP3)")
        print("3. Show available formats")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            url = input("Enter YouTube URL: ").strip()
            quality = input("Enter quality (best/worst/720p/480p/etc) or press Enter for 'best': ").strip()
            if not quality:
                quality = 'best'
            download_path = input("Enter download path (press Enter for './downloads'): ").strip()
            if not download_path:
                download_path = "./downloads"
            
            download_video(url, download_path, quality)
            
        elif choice == '2':
            url = input("Enter YouTube URL: ").strip()
            download_path = input("Enter download path (press Enter for './downloads'): ").strip()
            if not download_path:
                download_path = "./downloads"
            
            download_audio_only(url, download_path)
            
        elif choice == '3':
            url = input("Enter YouTube URL: ").strip()
            show_available_formats(url)
            
        elif choice == '4':
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
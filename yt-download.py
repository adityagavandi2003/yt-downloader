import yt_dlp
import os
import re
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from queue import Queue
import webbrowser
import json
from datetime import datetime

# FFmpeg path configuration
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE_PATH = r"C:\ffmpeg\bin\ffprobe.exe"

# Theme configurations
LIGHT_THEME = {
    'bg': '#ffffff',
    'fg': '#000000',
    'select_bg': '#0078d7',
    'select_fg': '#ffffff',
    'button_bg': '#f0f0f0',
    'button_fg': '#000000',
    'frame_bg': '#f0f0f0',
    'entry_bg': '#ffffff',
    'entry_fg': '#000000',
    'hover_bg': '#e0e0e0',
    'active_bg': '#d0d0d0'
}

DARK_THEME = {
    'bg': '#2d2d2d',
    'fg': '#ffffff',
    'select_bg': '#0078d7',
    'select_fg': '#ffffff',
    'button_bg': '#3d3d3d',
    'button_fg': '#ffffff',
    'frame_bg': '#3d3d3d',
    'entry_bg': '#2d2d2d',
    'entry_fg': '#ffffff',
    'hover_bg': '#4d4d4d',
    'active_bg': '#5d5d5d'
}

class ModernButton(ttk.Button):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        
    def on_enter(self, e):
        self.state(['active'])
        
    def on_leave(self, e):
        self.state(['!active'])

class YouTubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader Pro")
        self.root.geometry("1000x800")
        self.root.resizable(True, True)
        
        # Initialize variables
        self.current_theme = 'light'
        self.download_history = []
        self.current_video_number = 0
        self.total_playlist_videos = 0
        self.load_history()
        
        # Initialize style
        self.style = ttk.Style()
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Create main container
        self.main_container = ttk.Frame(root)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Create menu bar
        self.create_menu()
        
        # Create main sections
        self.create_url_section()
        self.create_options_section()
        self.create_progress_section()
        self.create_history_section()
        
        # Check FFmpeg installation
        self.check_ffmpeg_installation()
        
        # Queue for thread communication
        self.queue = Queue()
        
        # Apply initial theme
        self.apply_theme(self.current_theme)
        
        # Create tooltips
        self.create_tooltips()
        
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Clear History", command=self.clear_history)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Light Theme", command=lambda: self.apply_theme('light'))
        view_menu.add_command(label="Dark Theme", command=lambda: self.apply_theme('dark'))
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Check FFmpeg", command=self.check_ffmpeg_installation)
        
    def create_url_section(self):
        url_frame = ttk.LabelFrame(self.main_container, text="Video URL", padding="10")
        url_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        url_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(url_frame, text="YouTube URL:").grid(row=0, column=0, sticky="w", padx=5)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Add paste button
        paste_btn = ModernButton(url_frame, text="Paste", command=self.paste_url)
        paste_btn.grid(row=0, column=2, padx=5)
        
    def create_options_section(self):
        options_frame = ttk.LabelFrame(self.main_container, text="Download Options", padding="10")
        options_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        options_frame.grid_columnconfigure(1, weight=1)
        
        # Playlist Options
        playlist_frame = ttk.Frame(options_frame)
        playlist_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=5)
        
        self.playlist_var = tk.BooleanVar(value=False)
        self.playlist_check = ttk.Checkbutton(playlist_frame, text="Download as Playlist", 
                                            variable=self.playlist_var)
        self.playlist_check.grid(row=0, column=0, sticky="w")
        
        self.start_var = tk.StringVar(value="1")
        ttk.Label(playlist_frame, text="Start:").grid(row=0, column=1, sticky="w", padx=5)
        self.start_entry = ttk.Entry(playlist_frame, textvariable=self.start_var, width=5)
        self.start_entry.grid(row=0, column=2, sticky="w")
        
        self.end_var = tk.StringVar(value="")
        ttk.Label(playlist_frame, text="End:").grid(row=0, column=3, sticky="w", padx=5)
        self.end_entry = ttk.Entry(playlist_frame, textvariable=self.end_var, width=5)
        self.end_entry.grid(row=0, column=4, sticky="w")
        
        # Format and Quality
        ttk.Label(options_frame, text="Format:").grid(row=1, column=0, sticky="w", pady=5)
        self.format_var = tk.StringVar(value="mp4")
        self.format_combo = ttk.Combobox(options_frame, textvariable=self.format_var, 
                                       values=["mp4", "mp3"], state="readonly")
        self.format_combo.grid(row=1, column=1, sticky="ew", pady=5)
        
        ttk.Label(options_frame, text="Quality:").grid(row=2, column=0, sticky="w", pady=5)
        self.quality_var = tk.StringVar(value="best")
        self.quality_combo = ttk.Combobox(options_frame, textvariable=self.quality_var, 
                                        state="readonly")
        self.quality_combo.grid(row=2, column=1, sticky="ew", pady=5)
        
        # Filename Template
        ttk.Label(options_frame, text="Filename Template:").grid(row=3, column=0, sticky="w", pady=5)
        self.template_var = tk.StringVar(value="%(title)s.%(ext)s")
        self.template_entry = ttk.Entry(options_frame, textvariable=self.template_var)
        self.template_entry.grid(row=3, column=1, sticky="ew", pady=5)
        
        # Template Help
        template_help = ttk.Label(options_frame, 
                                text="Available variables: %(title)s, %(ext)s, %(id)s, %(uploader)s",
                                foreground="gray")
        template_help.grid(row=4, column=0, columnspan=2, sticky="w", pady=2)
        
        # Output Directory
        ttk.Label(options_frame, text="Output Directory:").grid(row=5, column=0, sticky="w", pady=5)
        self.output_var = tk.StringVar(value=r"D:\youtube")
        self.output_entry = ttk.Entry(options_frame, textvariable=self.output_var)
        self.output_entry.grid(row=5, column=1, sticky="ew", pady=5)
        self.browse_btn = ModernButton(options_frame, text="Browse", command=self.browse_directory)
        self.browse_btn.grid(row=5, column=2, padx=5, pady=5)
        
        # Download Button
        self.download_btn = ModernButton(options_frame, text="Download", command=self.start_download)
        self.download_btn.grid(row=6, column=0, columnspan=3, pady=10)
        
        # Bind format change event
        self.format_combo.bind('<<ComboboxSelected>>', self.update_quality_options)
        
        # Initialize quality options
        self.update_quality_options()
        
    def create_progress_section(self):
        progress_frame = ttk.LabelFrame(self.main_container, text="Download Progress", padding="10")
        progress_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Video Info
        self.info_frame = ttk.Frame(progress_frame)
        self.info_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        self.title_label = ttk.Label(self.info_frame, text="Title: ")
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.duration_label = ttk.Label(self.info_frame, text="Duration: ")
        self.duration_label.grid(row=1, column=0, sticky="w")
        
        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.grid(row=2, column=0, sticky="w", pady=5)
        
    def create_history_section(self):
        history_frame = ttk.LabelFrame(self.main_container, text="Download History", padding="10")
        history_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        history_frame.grid_columnconfigure(0, weight=1)
        history_frame.grid_rowconfigure(0, weight=1)
        
        # Create Treeview with scrollbars
        self.history_tree = ttk.Treeview(history_frame, 
                                       columns=("Date", "Title", "Format", "Quality"),
                                       show="headings",
                                       selectmode="browse")
        
        # Configure columns
        self.history_tree.heading("Date", text="Date")
        self.history_tree.heading("Title", text="Title")
        self.history_tree.heading("Format", text="Format")
        self.history_tree.heading("Quality", text="Quality")
        
        self.history_tree.column("Date", width=150)
        self.history_tree.column("Title", width=400)
        self.history_tree.column("Format", width=100)
        self.history_tree.column("Quality", width=100)
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        x_scrollbar = ttk.Scrollbar(history_frame, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Grid layout
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Load history
        self.load_history_to_tree()
        
    def create_tooltips(self):
        # Create tooltips for various widgets
        self.create_tooltip(self.url_entry, "Enter the YouTube video or playlist URL")
        self.create_tooltip(self.playlist_check, "Check this to download an entire playlist")
        self.create_tooltip(self.start_entry, "Starting video number for playlist download")
        self.create_tooltip(self.end_entry, "Ending video number for playlist download (leave empty for all)")
        self.create_tooltip(self.format_combo, "Select the output format (MP4 for video, MP3 for audio)")
        self.create_tooltip(self.quality_combo, "Select the quality of the download")
        self.create_tooltip(self.template_entry, "Customize the output filename format")
        self.create_tooltip(self.output_entry, "Select where to save the downloaded files")
        
    def create_tooltip(self, widget, text):
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
            label.pack()
            
            def hide_tooltip(event):
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.bind('<Leave>', hide_tooltip)
            
        widget.bind('<Enter>', show_tooltip)
        
    def paste_url(self):
        try:
            self.url_var.set(self.root.clipboard_get())
        except:
            pass
            
    def show_about(self):
        about_text = """YouTube Downloader Pro Version 1.0

                        A modern YouTube video downloader with playlist support,
                        format conversion, and download history.

                        Features:
                        • Download videos in MP4 or MP3 format
                        • Support for playlists and channels
                        • Custom filename templates
                        • Download history tracking
                        • Dark/Light theme support
                        • Progress tracking
                        • High-quality downloads

                        © 2024 yt-downloader by @aditya"""
                        
        messagebox.showinfo("About", about_text)
        
    def apply_theme(self, theme):
        self.current_theme = theme
        theme_config = LIGHT_THEME if theme == 'light' else DARK_THEME
        
        # Configure root window
        self.root.configure(bg=theme_config['bg'])
        
        # Configure main container
        self.main_container.configure(style=f'Main.TFrame')
        self.style.configure('Main.TFrame', background=theme_config['bg'])
        
        # Configure labels
        for widget in self.main_container.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                widget.configure(style=f'Frame.TLabelframe')
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label):
                        child.configure(style=f'Label.TLabel')
        
        self.style.configure('Label.TLabel', 
                           background=theme_config['bg'], 
                           foreground=theme_config['fg'])
        
        # Configure entries
        for widget in self.main_container.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Entry):
                        child.configure(style=f'Entry.TEntry')
        
        self.style.configure('Entry.TEntry', 
                           fieldbackground=theme_config['entry_bg'],
                           foreground=theme_config['entry_fg'])
        
        # Configure buttons
        for widget in self.main_container.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ModernButton):
                        child.configure(style=f'Button.TButton')
        
        self.style.configure('Button.TButton',
                           background=theme_config['button_bg'],
                           foreground=theme_config['button_fg'])
        
        # Configure frames
        self.style.configure('Frame.TLabelframe',
                           background=theme_config['frame_bg'],
                           foreground=theme_config['fg'])
        
        # Configure treeview
        self.style.configure('Treeview',
                           background=theme_config['entry_bg'],
                           foreground=theme_config['entry_fg'],
                           fieldbackground=theme_config['entry_bg'])
        self.style.configure('Treeview.Heading',
                           background=theme_config['button_bg'],
                           foreground=theme_config['button_fg'])
        
    def load_history(self):
        try:
            if os.path.exists('download_history.json'):
                with open('download_history.json', 'r') as f:
                    self.download_history = json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            self.download_history = []
            
    def save_history(self):
        try:
            with open('download_history.json', 'w') as f:
                json.dump(self.download_history, f)
        except Exception as e:
            print(f"Error saving history: {e}")
            
    def load_history_to_tree(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for entry in self.download_history:
            self.history_tree.insert('', 'end', values=(
                entry['date'],
                entry['title'],
                entry['format'],
                entry['quality']
            ))
            
    def clear_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to clear the download history?"):
            self.download_history = []
            self.save_history()
            self.load_history_to_tree()
            
    def add_to_history(self, title, format_type, quality):
        entry = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'title': title,
            'format': format_type,
            'quality': quality
        }
        self.download_history.append(entry)
        self.save_history()
        self.load_history_to_tree()
        
    def check_ffmpeg_installation(self):
        """Check if FFmpeg is installed and accessible"""
        if not os.path.exists(FFMPEG_PATH):
            response = messagebox.askyesno(
                "FFmpeg Not Found",
                "FFmpeg is not installed. This is required for high-quality downloads and MP3 conversion.\n\n"
                "Would you like to download FFmpeg now?",
                icon='warning'
            )
            if response:
                webbrowser.open('https://github.com/BtbN/FFmpeg-Builds/releases')
                messagebox.showinfo(
                    "Installation Instructions",
                    "1. Download the latest 'ffmpeg-master-latest-win64-gpl.zip'\n"
                    "2. Extract the ZIP file\n"
                    "3. Copy the contents of the 'bin' folder to 'C:\\ffmpeg\\bin\\'\n"
                    "4. Restart this application\n\n"
                    "Would you like to continue without FFmpeg? (Some features may be limited)"
                )
            else:
                messagebox.showwarning(
                    "Limited Functionality",
                    "Some features may be limited without FFmpeg:\n"
                    "- MP3 downloads\n"
                    "- High-quality MP4 downloads\n"
                    "- Video format conversion"
                )
        
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_var.set(directory)
            
    def update_quality_options(self, event=None):
        if self.format_var.get() == "mp4":
            self.quality_combo['values'] = ["best", "1080p", "720p", "480p"]
            self.quality_var.set("best")
        else:
            self.quality_combo['values'] = ["320kbps", "192kbps", "128kbps", "64kbps"]
            self.quality_var.set("192kbps")
            
    def get_video_info(self, url):
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0)
                }
        except Exception as e:
            self.queue.put(('error', str(e)))
            return None
            
    def format_duration(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    def download_video(self):
        url = self.url_var.get()
        if not url:
            self.queue.put(('error', "Please enter a YouTube URL"))
            return
            
        # Reset playlist counters
        self.current_video_number = 0
        self.total_playlist_videos = 0
            
        # Get video information
        video_info = self.get_video_info(url)
        if not video_info:
            return
            
        # Update video information
        self.queue.put(('info', video_info))
        
        # Configure yt-dlp options
        output_dir = self.output_var.get()
        
        # If playlist download is enabled, create a playlist folder
        if self.playlist_var.get():
            try:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    playlist_info = ydl.extract_info(url, download=False)
                    if 'entries' in playlist_info:
                        playlist_title = playlist_info.get('title', 'Playlist')
                        # Clean the playlist title to make it a valid folder name
                        playlist_title = re.sub(r'[<>:"/\\|?*]', '_', playlist_title)
                        playlist_dir = os.path.join(output_dir, playlist_title)
                        os.makedirs(playlist_dir, exist_ok=True)
                        output_dir = playlist_dir
                        
                        # Get playlist information
                        total_videos = len(playlist_info['entries'])
                        self.total_playlist_videos = total_videos
                        start_idx = int(self.start_var.get()) - 1 if self.start_var.get() else 0
                        end_idx = int(self.end_var.get()) - 1 if self.end_var.get() else total_videos
                        
                        # Update status with playlist information
                        self.queue.put(('info', {
                            'title': f"Playlist: {playlist_title}",
                            'duration': 0,
                            'total_videos': total_videos,
                            'start_idx': start_idx + 1,
                            'end_idx': end_idx,
                            'current_video': start_idx + 1
                        }))
                        
                        # Modify template to include video number for playlists
                        template = self.template_var.get()
                        if '%(playlist_index)s' not in template:
                            # Add playlist index at the start of the filename
                            template = '%(playlist_index)s. ' + template
                            self.template_var.set(template)
            except Exception as e:
                self.queue.put(('error', f"Error getting playlist info: {str(e)}"))
                return
        
        ydl_opts = {
            'outtmpl': os.path.join(output_dir, self.template_var.get()),
            'quiet': True,
            'progress': True,
            'progress_hooks': [self.progress_hook],
            # Add retry options
            'retries': 10,  # Number of retries for network errors
            'fragment_retries': 10,  # Number of retries for fragment downloads
            'retry_sleep': 5,  # Sleep time between retries
            'retry_sleep_functions': {'fragment': lambda n: 5 * (n + 1)},  # Exponential backoff
            'socket_timeout': 30,  # Socket timeout in seconds
            'extractor_retries': 3,  # Number of retries for extractor errors
            'ignoreerrors': True,  # Continue on download errors
            'no_warnings': False,  # Show warnings for debugging
            'verbose': True,  # Show verbose output for debugging
            'no_check_certificates': True,  # Skip HTTPS certificate validation
            'prefer_insecure': True,  # Prefer insecure connections if available
            'sleep_interval': 5,  # Sleep between requests
            'max_sleep_interval': 30,  # Maximum sleep interval
            'throttledratelimit': 100000,  # Rate limit for throttled requests
            'concurrent_fragments': 3,  # Number of fragments to download concurrently
        }
        
        # Add FFmpeg options if available
        if os.path.exists(FFMPEG_PATH):
            ydl_opts.update({
                'ffmpeg_location': FFMPEG_PATH,
                'ffprobe_location': FFPROBE_PATH,
            })
        
        # Add playlist options if enabled
        if self.playlist_var.get():
            ydl_opts.update({
                'playliststart': int(self.start_var.get()) if self.start_var.get() else 1,
                'playlistend': int(self.end_var.get()) if self.end_var.get() else None,
                'playlist_items': f"{self.start_var.get()}-{self.end_var.get()}" if self.end_var.get() else None,
            })
        
        if self.format_var.get() == "mp3":
            if not os.path.exists(FFMPEG_PATH):
                self.queue.put(('error', "FFmpeg is required for MP3 downloads. Please install FFmpeg first."))
                return
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': self.quality_var.get().replace('kbps', ''),
                }],
            })
        else:
            quality = self.quality_var.get()
            if quality == "best":
                format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                height = quality.replace('p', '')
                format_str = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best[ext=mp4]'
            ydl_opts['format'] = format_str
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.queue.put(('complete', "Download completed successfully!"))
            self.add_to_history(video_info['title'], self.format_var.get(), self.quality_var.get())
        except Exception as e:
            self.queue.put(('error', str(e)))
            
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                total = d.get('total_bytes', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    progress = (downloaded / total) * 100
                    # Add playlist index to progress message if available
                    if 'playlist_index' in d:
                        # Update current video number
                        current_video = d['playlist_index']
                        if current_video != self.current_video_number:
                            self.current_video_number = current_video
                        self.queue.put(('progress', {
                            'progress': progress,
                            'playlist_index': current_video,
                            'title': d.get('filename', ''),
                            'total_videos': self.total_playlist_videos
                        }))
                    else:
                        self.queue.put(('progress', progress))
            except:
                pass
        elif d['status'] == 'finished':
            # Video finished downloading
            if 'playlist_index' in d:
                self.queue.put(('video_complete', {
                    'playlist_index': d['playlist_index'],
                    'total_videos': self.total_playlist_videos
                }))
                
    def update_gui(self):
        try:
            while True:
                msg_type, msg = self.queue.get_nowait()
                if msg_type == 'error':
                    messagebox.showerror("Error", msg)
                    self.download_btn['state'] = 'normal'
                elif msg_type == 'info':
                    if isinstance(msg, dict) and 'total_videos' in msg:
                        # Update status for playlist download
                        self.title_label['text'] = f"Playlist: {msg['title']}"
                        self.duration_label['text'] = f"Videos: {msg['start_idx']} to {msg['end_idx']} of {msg['total_videos']}"
                        if 'current_video' in msg:
                            self.status_label['text'] = f"Downloading video {msg['current_video']} of {msg['total_videos']}"
                    else:
                        self.title_label['text'] = f"Title: {msg['title']}"
                        self.duration_label['text'] = f"Duration: {self.format_duration(msg['duration'])}"
                elif msg_type == 'progress':
                    if isinstance(msg, dict):
                        self.progress_var.set(msg['progress'])
                        self.status_label['text'] = f"Downloading video {msg['playlist_index']} of {msg['total_videos']}"
                    else:
                        self.progress_var.set(msg)
                elif msg_type == 'video_complete':
                    # Update status when a video in playlist is complete
                    if isinstance(msg, dict):
                        current = msg['playlist_index']
                        total = msg['total_videos']
                        if current < total:
                            self.status_label['text'] = f"Completed video {current} of {total}. Starting next video..."
                elif msg_type == 'complete':
                    self.status_label['text'] = msg
                    self.download_btn['state'] = 'normal'
                    messagebox.showinfo("Success", msg)
        except:
            pass
        finally:
            self.root.after(100, self.update_gui)
            
    def start_download(self):
        self.download_btn['state'] = 'disabled'
        self.progress_var.set(0)
        self.status_label['text'] = "Starting download..."
        threading.Thread(target=self.download_video, daemon=True).start()
        self.update_gui()

def main():
    root = tk.Tk()
    app = YouTubeDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()


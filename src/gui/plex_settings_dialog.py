"""
Plex settings dialog for entering connection details
"""
import tkinter as tk
from tkinter import ttk, messagebox

class PlexSettingsDialog:
    """Dialog for configuring Plex connection settings"""
    
    def __init__(self, parent, config_manager):
        """Initialize settings dialog"""
        self.config_manager = config_manager
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Plex Connection Settings")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        
        # Make it modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._setup_ui()
        
        # Load existing settings
        self._load_settings()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _setup_ui(self):
        """Setup dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        ttk.Label(
            main_frame,
            text="Plex Connection Settings",
            font=("Arial", 14, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Plex URL
        ttk.Label(main_frame, text="Plex Server URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(main_frame, width=40)
        self.url_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(
            main_frame, 
            text="Example: http://192.168.1.100:32400",
            font=("Arial", 8),
            foreground="gray"
        ).grid(row=2, column=1, sticky=tk.W)
        
        # Plex Token
        ttk.Label(main_frame, text="Plex Token:").grid(row=3, column=0, sticky=tk.W, pady=(15, 5))
        self.token_entry = ttk.Entry(main_frame, width=40, show="*")
        self.token_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(15, 5))
        
        # Show token checkbox
        self.show_token_var = tk.BooleanVar()
        ttk.Checkbutton(
            main_frame,
            text="Show token",
            variable=self.show_token_var,
            command=self._toggle_token_visibility
        ).grid(row=4, column=1, sticky=tk.W)
        
        # Help for finding token
        help_frame = ttk.LabelFrame(main_frame, text="How to find your Plex Token", padding="10")
        help_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15)
        
        help_text = (
            "1. Open Plex Web App in your browser\n"
            "2. Play any media item\n"
            "3. Click the more (...) button\n"
            "4. Select 'Get Info' > 'View XML'\n"
            "5. Look for 'X-Plex-Token=' in the URL"
        )
        ttk.Label(help_frame, text=help_text, justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)
        
        # Library name
        ttk.Label(main_frame, text="Library Name:").grid(row=6, column=0, sticky=tk.W, pady=(15, 5))
        self.library_entry = ttk.Entry(main_frame, width=40)
        self.library_entry.grid(row=6, column=1, sticky=(tk.W, tk.E), pady=(15, 5))
        self.library_entry.insert(0, "Audiobooks")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame,
            text="Test Connection",
            command=self._test_connection
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self._save
        ).grid(row=0, column=1, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy
        ).grid(row=0, column=2, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
    
    def _load_settings(self):
        """Load existing settings from config"""
        url = self.config_manager.get('plex.url', '')
        token = self.config_manager.get('plex.token', '')
        library = self.config_manager.get('plex.library_name', 'Audiobooks')
        
        if url:
            self.url_entry.insert(0, url)
        if token:
            self.token_entry.insert(0, token)
        if library:
            self.library_entry.delete(0, tk.END)
            self.library_entry.insert(0, library)
    
    def _toggle_token_visibility(self):
        """Toggle token visibility"""
        if self.show_token_var.get():
            self.token_entry.config(show="")
        else:
            self.token_entry.config(show="*")
    
    def _test_connection(self):
        """Test connection to Plex"""
        url = self.url_entry.get().strip()
        token = self.token_entry.get().strip()
        
        if not url or not token:
            messagebox.showwarning("Missing Information", "Please enter both URL and token")
            return
        
        try:
            from plex.plex_client import PlexClient
            client = PlexClient()
            client.connect(url, token)
            
            messagebox.showinfo("Success", f"Connected to Plex server:\n{client.server.friendlyName}")
            
        except Exception as e:
            messagebox.showerror("Connection Failed", f"Failed to connect to Plex:\n{str(e)}")
    
    def _save(self):
        """Save settings and close dialog"""
        url = self.url_entry.get().strip()
        token = self.token_entry.get().strip()
        library = self.library_entry.get().strip()
        
        if not url or not token:
            messagebox.showwarning("Missing Information", "Please enter both URL and token")
            return
        
        # Save to config
        self.config_manager.update_plex_config(url, token, library)
        
        # Return result
        self.result = {
            'url': url,
            'token': token,
            'library': library
        }
        
        self.dialog.destroy()

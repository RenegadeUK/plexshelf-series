"""
Main GUI window for PlexShelf Series Manager
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from gui.plex_settings_dialog import PlexSettingsDialog
from gui.series_review_panel import SeriesReviewPanel
from database.db_manager import DatabaseManager
from config.config_manager import ConfigManager
from plex.plex_client import PlexClient
from matching.series_matcher import SeriesMatcher

logger = logging.getLogger(__name__)

class MainWindow:
    """Main application window"""
    
    def __init__(self, root):
        """Initialize main window"""
        self.root = root
        self.root.title("PlexShelf Series Manager")
        self.root.geometry("1200x800")
        
        # Initialize managers
        self.config_manager = ConfigManager()
        self.config_manager.load()
        
        self.db_manager = DatabaseManager()
        self.db_manager.initialize()
        
        self.plex_client = PlexClient()
        self.series_matcher = None
        
        # Connection status
        self.connected = False
        
        # Setup UI
        self._setup_ui()
        
        # Try to auto-connect if credentials exist
        self._try_auto_connect()
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self._show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Actions menu
        actions_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Actions", menu=actions_menu)
        actions_menu.add_command(label="Scan Plex Library", command=self._scan_library)
        actions_menu.add_command(label="Match Series", command=self._match_series)
        actions_menu.add_command(label="Review Matches", command=self._review_matches)
        actions_menu.add_command(label="Apply to Plex", command=self._apply_to_plex)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # Status bar at top
        self._setup_status_bar(main_container)
        
        # Notebook for different panels
        self.notebook = ttk.Notebook(main_container)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Overview tab
        self._setup_overview_tab()
        
        # Series review tab
        self._setup_series_review_tab()
        
        # Log tab
        self._setup_log_tab()
    
    def _setup_status_bar(self, parent):
        """Setup status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Connection status
        ttk.Label(status_frame, text="Plex Status:").grid(row=0, column=0, padx=5)
        self.status_label = ttk.Label(status_frame, text="Not Connected", foreground="red")
        self.status_label.grid(row=0, column=1, padx=5)
        
        # Connect button
        self.connect_button = ttk.Button(
            status_frame, 
            text="Connect to Plex", 
            command=self._show_settings
        )
        self.connect_button.grid(row=0, column=2, padx=5)
        
        # Stats
        self.stats_label = ttk.Label(status_frame, text="Books: 0 | Series: 0 | Matches: 0")
        self.stats_label.grid(row=0, column=3, padx=20)
    
    def _setup_overview_tab(self):
        """Setup overview tab"""
        overview_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(overview_frame, text="Overview")
        
        # Welcome message
        ttk.Label(
            overview_frame,
            text="PlexShelf Series Manager",
            font=("Arial", 16, "bold")
        ).grid(row=0, column=0, pady=10)
        
        ttk.Label(
            overview_frame,
            text="Organize your Plex audiobooks into series collections",
            font=("Arial", 10)
        ).grid(row=1, column=0, pady=5)
        
        # Action buttons
        button_frame = ttk.Frame(overview_frame)
        button_frame.grid(row=2, column=0, pady=20)
        
        ttk.Button(
            button_frame,
            text="1. Scan Plex Library",
            command=self._scan_library,
            width=25
        ).grid(row=0, column=0, padx=10, pady=5)
        
        ttk.Button(
            button_frame,
            text="2. Match Series",
            command=self._match_series,
            width=25
        ).grid(row=1, column=0, padx=10, pady=5)
        
        ttk.Button(
            button_frame,
            text="3. Review & Approve",
            command=self._review_matches,
            width=25
        ).grid(row=2, column=0, padx=10, pady=5)
        
        ttk.Button(
            button_frame,
            text="4. Apply to Plex",
            command=self._apply_to_plex,
            width=25
        ).grid(row=3, column=0, padx=10, pady=5)
        
        # Statistics display
        stats_frame = ttk.LabelFrame(overview_frame, text="Statistics", padding="10")
        stats_frame.grid(row=3, column=0, pady=20, sticky=(tk.W, tk.E))
        
        self.overview_stats = scrolledtext.ScrolledText(
            stats_frame, 
            height=10, 
            width=60,
            state='disabled'
        )
        self.overview_stats.grid(row=0, column=0, sticky=(tk.W, tk.E))
    
    def _setup_series_review_tab(self):
        """Setup series review tab"""
        self.review_panel = SeriesReviewPanel(self.notebook, self.db_manager)
        self.notebook.add(self.review_panel.frame, text="Review Matches")
    
    def _setup_log_tab(self):
        """Setup log tab"""
        log_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(log_frame, text="Logs")
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=30,
            width=100,
            state='disabled'
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Add clear button
        ttk.Button(
            log_frame,
            text="Clear Logs",
            command=self._clear_logs
        ).grid(row=1, column=0, pady=5)
    
    def _try_auto_connect(self):
        """Try to automatically connect using saved credentials"""
        plex_url = self.config_manager.get('plex.url')
        plex_token = self.config_manager.get('plex.token')
        
        if plex_url and plex_token:
            try:
                self.plex_client.connect(plex_url, plex_token)
                self._update_connection_status(True)
                self.log("Auto-connected to Plex")
            except Exception as e:
                logger.warning(f"Auto-connect failed: {e}")
    
    def _show_settings(self):
        """Show Plex settings dialog"""
        dialog = PlexSettingsDialog(self.root, self.config_manager)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            # Try to connect
            try:
                self.plex_client.connect(dialog.result['url'], dialog.result['token'])
                self._update_connection_status(True)
                self.log("Connected to Plex successfully")
                messagebox.showinfo("Success", "Connected to Plex successfully!")
            except Exception as e:
                self._update_connection_status(False)
                self.log(f"Failed to connect: {e}")
                messagebox.showerror("Connection Failed", str(e))
    
    def _update_connection_status(self, connected):
        """Update connection status display"""
        self.connected = connected
        if connected:
            self.status_label.config(text="Connected", foreground="green")
            self.connect_button.config(text="Settings")
        else:
            self.status_label.config(text="Not Connected", foreground="red")
            self.connect_button.config(text="Connect to Plex")
    
    def _scan_library(self):
        """Scan Plex library for audiobooks"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to Plex first")
            return
        
        try:
            self.log("Starting library scan...")
            
            # Get library
            library_name = self.config_manager.get('plex.library_name', 'Audiobooks')
            self.plex_client.get_library(library_name)
            
            # Get all audiobooks
            audiobooks = self.plex_client.get_all_audiobooks()
            self.log(f"Found {len(audiobooks)} audiobooks")
            
            # Store in database
            session = self.db_manager.get_session()
            from database.models import AudiobookItem
            
            added = 0
            updated = 0
            
            for book in audiobooks:
                metadata = self.plex_client.get_audiobook_metadata(book)
                
                # Check if exists
                existing = session.query(AudiobookItem).filter_by(
                    plex_id=metadata['plex_id']
                ).first()
                
                if existing:
                    # Update
                    for key, value in metadata.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    # Add new
                    new_book = AudiobookItem(**metadata)
                    session.add(new_book)
                    added += 1
            
            session.commit()
            session.close()
            
            self.log(f"Scan complete: {added} added, {updated} updated")
            self._update_stats()
            messagebox.showinfo("Scan Complete", 
                              f"Added {added} new audiobooks\nUpdated {updated} existing audiobooks")
            
        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            self.log(f"ERROR: {e}")
            messagebox.showerror("Scan Failed", str(e))
    
    def _match_series(self):
        """Run series matching algorithm"""
        try:
            self.log("Starting series matching...")
            
            session = self.db_manager.get_session()
            matcher = SeriesMatcher(session)
            
            matches_found = matcher.match_all_audiobooks()
            session.close()
            
            self.log(f"Matching complete: {matches_found} matches found")
            self._update_stats()
            
            messagebox.showinfo("Matching Complete", 
                              f"Found {matches_found} series matches\nPlease review in the 'Review Matches' tab")
            
            # Switch to review tab
            self.notebook.select(1)
            self.review_panel.load_matches()
            
        except Exception as e:
            logger.error(f"Matching failed: {e}", exc_info=True)
            self.log(f"ERROR: {e}")
            messagebox.showerror("Matching Failed", str(e))
    
    def _review_matches(self):
        """Open review matches tab"""
        self.notebook.select(1)
        self.review_panel.load_matches()
    
    def _apply_to_plex(self):
        """Apply approved matches to Plex"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to Plex first")
            return
        
        # Confirm with user
        if not messagebox.askyesno("Confirm", 
                                    "This will create collections in Plex for all approved matches.\nContinue?"):
            return
        
        try:
            self.log("Applying changes to Plex...")
            
            session = self.db_manager.get_session()
            from database.models import SeriesMatch, Series
            
            # Get all approved matches
            approved = session.query(SeriesMatch).filter_by(user_approved=True).all()
            
            if not approved:
                messagebox.showinfo("No Changes", "No approved matches to apply")
                return
            
            # Group by series
            series_dict = {}
            for match in approved:
                if match.series_id not in series_dict:
                    series_dict[match.series_id] = []
                series_dict[match.series_id].append(match.audiobook.plex_id)
            
            # Create collections
            created = 0
            for series_id, book_ids in series_dict.items():
                series = session.query(Series).get(series_id)
                collection_name = f"{series.series_name} Series"
                
                try:
                    self.plex_client.create_collection(collection_name, book_ids)
                    self.log(f"Created collection: {collection_name}")
                    created += 1
                except Exception as e:
                    self.log(f"Failed to create {collection_name}: {e}")
            
            session.close()
            
            self.log(f"Applied {created} collections to Plex")
            messagebox.showinfo("Complete", f"Created {created} collections in Plex!")
            
        except Exception as e:
            logger.error(f"Apply failed: {e}", exc_info=True)
            self.log(f"ERROR: {e}")
            messagebox.showerror("Apply Failed", str(e))
    
    def _update_stats(self):
        """Update statistics display"""
        try:
            session = self.db_manager.get_session()
            from database.models import AudiobookItem, Series, SeriesMatch
            
            book_count = session.query(AudiobookItem).count()
            series_count = session.query(Series).count()
            match_count = session.query(SeriesMatch).count()
            approved_count = session.query(SeriesMatch).filter_by(user_approved=True).count()
            
            session.close()
            
            self.stats_label.config(
                text=f"Books: {book_count} | Series: {series_count} | Matches: {match_count} | Approved: {approved_count}"
            )
            
        except Exception as e:
            logger.error(f"Failed to update stats: {e}")
    
    def log(self, message):
        """Add message to log display"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
    
    def _clear_logs(self):
        """Clear log display"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
    
    def _show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About",
            "PlexShelf Series Manager\n\n"
            "Organize your Plex audiobooks into series collections\n\n"
            "Version 1.0.0"
        )

"""
Series review panel for approving/rejecting matches
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging

logger = logging.getLogger(__name__)

class SeriesReviewPanel:
    """Panel for reviewing and approving series matches"""
    
    def __init__(self, parent, db_manager):
        """Initialize review panel"""
        self.db_manager = db_manager
        self.current_matches = []
        
        # Create main frame
        self.frame = ttk.Frame(parent, padding="10")
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup panel UI"""
        # Top controls
        control_frame = ttk.Frame(self.frame)
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(
            control_frame,
            text="Refresh",
            command=self.load_matches
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            control_frame,
            text="Approve All High Confidence",
            command=self._approve_high_confidence
        ).grid(row=0, column=1, padx=5)
        
        ttk.Button(
            control_frame,
            text="Manual Match",
            command=self._manual_match
        ).grid(row=0, column=2, padx=5)
        
        # Filter options
        ttk.Label(control_frame, text="Filter:").grid(row=0, column=3, padx=(20, 5))
        self.filter_var = tk.StringVar(value="pending")
        filter_combo = ttk.Combobox(
            control_frame,
            textvariable=self.filter_var,
            values=["all", "pending", "approved", "rejected"],
            state="readonly",
            width=15
        )
        filter_combo.grid(row=0, column=4, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.load_matches())
        
        # Treeview for matches
        tree_frame = ttk.Frame(self.frame)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Create treeview
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("audiobook", "author", "series", "confidence", "method", "status"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configure columns
        self.tree.heading("audiobook", text="Audiobook")
        self.tree.heading("author", text="Author")
        self.tree.heading("series", text="Series")
        self.tree.heading("confidence", text="Confidence")
        self.tree.heading("method", text="Method")
        self.tree.heading("status", text="Status")
        
        self.tree.column("audiobook", width=300)
        self.tree.column("author", width=150)
        self.tree.column("series", width=200)
        self.tree.column("confidence", width=80)
        self.tree.column("method", width=100)
        self.tree.column("status", width=80)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Action buttons
        action_frame = ttk.Frame(self.frame)
        action_frame.grid(row=2, column=0, pady=10)
        
        ttk.Button(
            action_frame,
            text="Approve Selected",
            command=self._approve_selected
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            action_frame,
            text="Reject Selected",
            command=self._reject_selected
        ).grid(row=0, column=1, padx=5)
        
        ttk.Button(
            action_frame,
            text="Edit Match",
            command=self._edit_match
        ).grid(row=0, column=2, padx=5)
        
        ttk.Button(
            action_frame,
            text="Remove Match",
            command=self._remove_match
        ).grid(row=0, column=3, padx=5)
        
        # Configure grid weights
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
    
    def load_matches(self):
        """Load matches from database"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            session = self.db_manager.get_session()
            from database.models import SeriesMatch
            
            # Get matches based on filter
            query = session.query(SeriesMatch)
            
            filter_value = self.filter_var.get()
            if filter_value == "pending":
                query = query.filter_by(user_approved=False, user_rejected=False)
            elif filter_value == "approved":
                query = query.filter_by(user_approved=True)
            elif filter_value == "rejected":
                query = query.filter_by(user_rejected=True)
            
            matches = query.all()
            self.current_matches = matches
            
            # Populate tree
            for match in matches:
                status = "Approved" if match.user_approved else "Rejected" if match.user_rejected else "Pending"
                
                self.tree.insert("", tk.END, values=(
                    match.audiobook.title,
                    match.audiobook.author or "Unknown",
                    match.series.series_name,
                    f"{match.confidence_score}%",
                    match.match_method,
                    status
                ), tags=(str(match.id),))
            
            session.close()
            logger.info(f"Loaded {len(matches)} matches")
            
        except Exception as e:
            logger.error(f"Failed to load matches: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to load matches:\n{str(e)}")
    
    def _approve_selected(self):
        """Approve selected matches"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select matches to approve")
            return
        
        try:
            session = self.db_manager.get_session()
            from database.models import SeriesMatch
            
            for item in selected:
                match_id = int(self.tree.item(item)['tags'][0])
                match = session.query(SeriesMatch).get(match_id)
                if match:
                    match.user_approved = True
                    match.user_rejected = False
            
            session.commit()
            session.close()
            
            self.load_matches()
            messagebox.showinfo("Success", f"Approved {len(selected)} matches")
            
        except Exception as e:
            logger.error(f"Failed to approve matches: {e}", exc_info=True)
            messagebox.showerror("Error", str(e))
    
    def _reject_selected(self):
        """Reject selected matches"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select matches to reject")
            return
        
        try:
            session = self.db_manager.get_session()
            from database.models import SeriesMatch
            
            for item in selected:
                match_id = int(self.tree.item(item)['tags'][0])
                match = session.query(SeriesMatch).get(match_id)
                if match:
                    match.user_approved = False
                    match.user_rejected = True
            
            session.commit()
            session.close()
            
            self.load_matches()
            messagebox.showinfo("Success", f"Rejected {len(selected)} matches")
            
        except Exception as e:
            logger.error(f"Failed to reject matches: {e}", exc_info=True)
            messagebox.showerror("Error", str(e))
    
    def _approve_high_confidence(self):
        """Automatically approve high confidence matches"""
        try:
            session = self.db_manager.get_session()
            from database.models import SeriesMatch
            
            high_confidence = session.query(SeriesMatch).filter(
                SeriesMatch.confidence_score >= 90,
                SeriesMatch.user_approved == False,
                SeriesMatch.user_rejected == False
            ).all()
            
            for match in high_confidence:
                match.user_approved = True
            
            session.commit()
            count = len(high_confidence)
            session.close()
            
            self.load_matches()
            messagebox.showinfo("Success", f"Auto-approved {count} high confidence matches")
            
        except Exception as e:
            logger.error(f"Failed to auto-approve: {e}", exc_info=True)
            messagebox.showerror("Error", str(e))
    
    def _edit_match(self):
        """Edit selected match"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a match to edit")
            return
        
        if len(selected) > 1:
            messagebox.showinfo("Multiple Selection", "Please select only one match to edit")
            return
        
        # TODO: Implement edit dialog
        messagebox.showinfo("Not Implemented", "Edit functionality coming soon")
    
    def _remove_match(self):
        """Remove selected match"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select matches to remove")
            return
        
        if not messagebox.askyesno("Confirm", f"Remove {len(selected)} match(es)?"):
            return
        
        try:
            session = self.db_manager.get_session()
            from database.models import SeriesMatch
            
            for item in selected:
                match_id = int(self.tree.item(item)['tags'][0])
                match = session.query(SeriesMatch).get(match_id)
                if match:
                    session.delete(match)
            
            session.commit()
            session.close()
            
            self.load_matches()
            messagebox.showinfo("Success", f"Removed {len(selected)} matches")
            
        except Exception as e:
            logger.error(f"Failed to remove matches: {e}", exc_info=True)
            messagebox.showerror("Error", str(e))
    
    def _manual_match(self):
        """Open manual match dialog"""
        # TODO: Implement manual match dialog
        messagebox.showinfo("Not Implemented", "Manual match functionality coming soon")

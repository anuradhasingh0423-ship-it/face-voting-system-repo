import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from tkinter import Tk, Label, Button, Frame, CENTER, messagebox, filedialog
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Votes file
VOTES_FILE = "Votes.csv"

LABELS = {
    "english": {
        "title": "Live Voting Dashboard",
        "MOBILE": "Mobile",
        "NAME": "Name",
        "ELECTION": "Election",
        "PARTY": "Party",
        "DATE": "Date",
        "TIME": "Time",
        "votes": "Votes",
        "vote_count": "Vote Count by Party",
        "refresh": "🔄 Refresh",
        "export": "⬇ Export CSV",
        "no_data": "No votes recorded yet.",
    },
    "hindi": {
        "title": "लाइव वोटिंग डैशबोर्ड",
        "MOBILE": "मोबाइल",
        "NAME": "नाम",
        "ELECTION": "चुनाव",
        "PARTY": "पार्टी",
        "DATE": "तारीख",
        "TIME": "समय",
        "votes": "वोट",
        "vote_count": "पार्टी के अनुसार वोटों की संख्या",
        "refresh": "🔄 ताज़ा करें",
        "export": "⬇ एक्सपोर्ट CSV",
        "no_data": "अभी तक कोई वोट नहीं डाला गया है।",
    }
}

THEMES = {
    "light": {
        "bg": "white",
        "fg": "black",
        "bar_colors": ['orange', 'blue', 'green', 'red', 'purple', 'cyan', 'magenta']
    },
    "dark": {
        "bg": "#2b2b2b",
        "fg": "white",
        "bar_colors": ['#f39c12', '#3498db', '#2ecc71', '#e74c3c', '#9b59b6', '#1abc9c', '#e67e22']
    }
}

def load_votes():
    """Load Votes.csv and add DATE/TIME columns dynamically."""
    expected_cols = ["MOBILE", "NAME", "ELECTION", "PARTY"]
    df = pd.DataFrame(columns=expected_cols + ["DATE", "TIME"])
    
    if os.path.exists(VOTES_FILE):
        try:
            df = pd.read_csv(VOTES_FILE)
            # Ensure expected columns exist
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
            df = df.fillna("").astype(str)
            # Add DATE and TIME columns dynamically if missing
            if "DATE" not in df.columns:
                df["DATE"] = datetime.now().strftime("%Y-%m-%d")
            if "TIME" not in df.columns:
                df["TIME"] = datetime.now().strftime("%H:%M:%S")
            df = df[expected_cols + ["DATE", "TIME"]]
        except Exception as e:
            print("Error reading Votes.csv:", e)
            df = pd.DataFrame(columns=expected_cols + ["DATE", "TIME"])
    return df

class VoteDashboard:
    def __init__(self, root):
        self.root = root
        self.current_language = "english"
        self.labels = LABELS[self.current_language]
        self.theme = THEMES["light"]
        self.columns = ["MOBILE", "NAME", "ELECTION", "PARTY", "DATE", "TIME"]
        self.data_df = pd.DataFrame(columns=self.columns)
        self._setup_ui()
        self.auto_refresh_interval = 3000  # milliseconds (3 seconds)
        self.refresh_table()  # initial load
        self.schedule_auto_refresh()  # start auto-refresh

    def _setup_ui(self):
        self.root.title("🗳️ Voting Dashboard")
        self.root.geometry("1000x650")
        self.root.configure(bg=self.theme["bg"])

        self.title_label = Label(self.root, text=self.labels['title'], font=("Arial", 20, "bold"),
                                 bg=self.theme['bg'], fg=self.theme['fg'])
        self.title_label.pack(pady=8)

        toolbar = Frame(self.root, bg=self.theme['bg'])
        toolbar.pack(fill="x", padx=10, pady=5)
        
        refresh_btn = Button(toolbar, text=self.labels['refresh'], bg="#4CAF50", fg="white",
                             command=self.refresh_table)
        refresh_btn.pack(side="left", padx=5)
        
        export_btn = Button(toolbar, text=self.labels['export'], bg="#607D8B", fg="white",
                            command=self.export_to_csv)
        export_btn.pack(side="left", padx=5)
        
        # Delete all votes button
        delete_btn = Button(toolbar, text="❌ Delete All Votes", bg="#f44336", fg="white",
                            command=self.delete_all_votes)
        delete_btn.pack(side="left", padx=5)

        # Table
        table_frame = Frame(self.root)
        table_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.tree = ttk.Treeview(table_frame, columns=self.columns, show='headings')
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        self.tree.pack(fill="both", expand=True, side="left")

        for col in self.columns:
            self.tree.heading(col, text=self.labels.get(col, col))
            self.tree.column(col, width=140, anchor=CENTER)

        # Chart
        self.fig = Figure(figsize=(6,3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(pady=10)

    def refresh_table(self):
        df = load_votes()
        self.data_df = df
        for r in self.tree.get_children():
            self.tree.delete(r)
        if df.empty:
            self.tree.insert("", "end", values=[""]*len(self.columns))
        else:
            for _, row in df.iterrows():
                self.tree.insert("", "end", values=[row.get(c,"") for c in self.columns])
        self.plot_votes(df)

    def schedule_auto_refresh(self):
        """Schedule table and chart to refresh automatically."""
        self.refresh_table()
        self.root.after(self.auto_refresh_interval, self.schedule_auto_refresh)

    def plot_votes(self, df):
        self.ax.clear()
        if df.empty or df['PARTY'].dropna().empty:
            self.ax.set_title(self.labels['vote_count'], color=self.theme['fg'])
            self.canvas.draw()
            return

        vote_counts = df.groupby('PARTY').size().sort_values(ascending=False)
        colors = (self.theme['bar_colors'] * (len(vote_counts) // len(self.theme['bar_colors']) + 1))[:len(vote_counts)]
        bars = self.ax.bar(vote_counts.index, vote_counts.values, color=colors)

        for bar, cnt in zip(bars, vote_counts.values):
            x = bar.get_x() + bar.get_width()/2
            self.ax.text(x, bar.get_height()+0.3, str(int(cnt)), ha='center')

        self.ax.set_title(self.labels['vote_count'])
        self.ax.set_xlabel('Party')
        self.ax.set_ylabel('Votes')

        self.canvas.draw()

    def export_to_csv(self):
        if self.data_df.empty:
            messagebox.showinfo("No data", "No data to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if path:
            self.data_df.to_csv(path, index=False)
            messagebox.showinfo("Exported", f"Exported to {path}")

    def delete_all_votes(self):
        """Delete all votes from Votes.csv after confirmation."""
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete ALL votes?")
        if confirm:
            try:
                # Overwrite the file with an empty DataFrame with headers only
                pd.DataFrame(columns=self.columns).to_csv(VOTES_FILE, index=False)
                self.refresh_table()  # Refresh table and chart
                messagebox.showinfo("Deleted", "All votes have been deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete votes: {e}")


def launch_dashboard():
    root = Tk()
    app = VoteDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    launch_dashboard()


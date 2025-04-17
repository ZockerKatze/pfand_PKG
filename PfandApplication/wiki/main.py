import csv
import os
import re
import tkinter as tk
from tkinter import ttk


def select_file(callback=None):
    def set_choice(choice):
        select_window.destroy()
        if choice == "Wiki":
            open_wiki()
        else:
            filename = os.path.join("PfandApplication/wiki", "listeSPAR.csv" if choice == "SPAR" else "listeHOFER.csv")
            if callback:
                callback(filename)
            else:
                start_app(filename)

    select_window = tk.Tk()
    select_window.title("Wähle eine Liste")
    select_window.geometry("300x200")

    label = tk.Label(select_window, text="Bitte eine Liste wählen:", font=("Arial", 12))
    label.pack(pady=10)

    spar_button = tk.Button(select_window, text="SPAR", command=lambda: set_choice("SPAR"), width=15)
    spar_button.pack(pady=5)

    hofer_button = tk.Button(select_window, text="HOFER", command=lambda: set_choice("HOFER"), width=15)
    hofer_button.pack(pady=5)

    wiki_button = tk.Button(select_window, text="Wiki", command=lambda: set_choice("Wiki"), width=15)
    wiki_button.pack(pady=5)

    select_window.mainloop()

class CSVViewerApp:
    def __init__(self, root, filename):
        self.root = root
        title = "PFANDLISTE - SPAR" if "SPAR" in filename else "PFANDLISTE - HOFER"
        self.root.title(title)
        self.root.geometry("800x600")

        self.label = tk.Label(root, text=title, font=("Arial", 16, "bold"))
        self.label.pack(pady=10)

        self.frame = tk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(self.frame, show="headings")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.configure(yscroll=self.scrollbar.set)

        # Create a frame for search functionality and style it
        search_frame = tk.Frame(root, pady=10, padx=20)
        search_frame.pack(fill=tk.X)

        self.search_label = tk.Label(search_frame, text="Search:", font=("Arial", 12), anchor="w")
        self.search_label.pack(side=tk.LEFT)

        self.search_entry = tk.Entry(search_frame, font=("Arial", 12), relief="solid", borderwidth=2)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.search_entry.bind("<KeyRelease>", self.search)

        self.load_csv(filename)

    def search(self, event):
        search_term = self.search_entry.get().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.load_csv(self.filename, search_term)

    def load_csv(self, filename, search_term=""):
        self.filename = filename
        try:
            with open(filename, newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                headers = next(reader, None)

                self.tree["columns"] = headers
                self.tree.heading("#0", text="#")  # First column for index
                self.tree.column("#0", width=50, anchor="center")

                for header in headers:
                    self.tree.heading(header, text=header)
                    self.tree.column(header, anchor="center")

                for i, row in enumerate(reader, start=1):
                    if any(search_term.lower() in str(cell).lower() for cell in row):
                        self.tree.insert("", "end", text=i, values=row)
        except FileNotFoundError:
            print(f"Error: {filename} not found!")
        except Exception as e:
            print(f"Error loading CSV: {e}")

    def sort_column(self, col):
        data = [(self.tree.item(item)["values"], item) for item in self.tree.get_children("")]
        data.sort(key=lambda x: x[0][col])
        for idx, item in enumerate(data):
            self.tree.move(item[1], '', idx)

    def right_click_menu(self, event):
        selected_item = self.tree.selection()
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Copy", command=lambda: self.copy_cell(selected_item))
        menu.post(event.x_root, event.y_root)

    def copy_cell(self, selected_item):
        # Copy data from the selected row to clipboard
        if selected_item:
            row_values = self.tree.item(selected_item[0])["values"]
            self.root.clipboard_clear()
            self.root.clipboard_append(' | '.join(row_values))

def open_wiki():
    wiki_window = tk.Tk()
    wiki_window.title("Wiki")
    wiki_window.geometry("500x400")

    text_area = tk.Text(wiki_window, wrap=tk.WORD)
    text_area.pack(expand=True, fill=tk.BOTH)

    filename = os.path.join("PfandApplication/wiki", "wiki.md")

    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()
            format_markdown(text_area, content)
    except FileNotFoundError:
        text_area.insert(tk.END, f"Fehler: '{filename}' nicht gefunden!")

    wiki_window.mainloop()

def format_markdown(text_area, text):
    text_area.tag_configure("bold", font=("Arial", 10, "bold"))
    text_area.tag_configure("center", justify="center")

    text_area.delete("1.0", tk.END)

    segments = []
    last_end = 0

    for match in re.finditer(r'<p align="center">(.*?)</p>|\*\*(.*?)\*\*', text, re.DOTALL):
        segments.append((text[last_end:match.start()], None))

        if match.group(1):  # Centered text
            segments.append((match.group(1), "center"))
        elif match.group(2):  # Bold text
            segments.append((match.group(2), "bold"))

        last_end = match.end()

    segments.append((text[last_end:], None))

    for segment, tag in segments:
        text_area.insert(tk.END, segment, tag if tag else "")

def start_app(filename):
    root = tk.Tk()
    app = CSVViewerApp(root, filename)
    root.mainloop()

if __name__ == "__main__": select_file()
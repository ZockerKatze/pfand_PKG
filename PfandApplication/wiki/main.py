import tkinter as tk
from tkinter import ttk
import csv
import os
import re

def select_file(callback=None):
    def set_choice(choice):
        select_window.destroy()
        if choice == "Wiki":
            open_wiki()
        else:
            filename = os.path.join("wiki", "listeSPAR.csv" if choice == "SPAR" else "listeHOFER.csv")
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
        self.root.geometry("600x400")
        
        self.label = tk.Label(root, text=title, font=("Arial", 16, "bold"))
        self.label.pack(pady=10)
        
        self.frame = tk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(self.frame)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.configure(yscroll=self.scrollbar.set)
        
        self.load_csv(filename)
        
    def load_csv(self, filename):
        try:
            with open(filename, newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                headers = next(reader, None)
                
                self.tree['columns'] = headers
                self.tree.heading("#0", text="#")  # First column for index
                self.tree.column("#0", width=50)
                
                for header in headers:
                    self.tree.heading(header, text=header)
                    self.tree.column(header, anchor="center")
                
                for i, row in enumerate(reader, start=1):
                    self.tree.insert("", "end", text=i, values=row)
        except FileNotFoundError:
            print(f"Error: {filename} not found!")
        except Exception as e:
            print(f"Error loading CSV: {e}")

## Doesnt really work yet
## In the Future maybe
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

def open_wiki():
    wiki_window = tk.Tk()
    wiki_window.title("Wiki")
    wiki_window.geometry("500x400")
    
    text_area = tk.Text(wiki_window, wrap=tk.WORD)
    text_area.pack(expand=True, fill=tk.BOTH)
    
    filename = os.path.join("wiki", "wiki.md")
    
    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()
            format_markdown(text_area, content)
    except FileNotFoundError:
        text_area.insert(tk.END, f"Fehler: '{filename}' nicht gefunden!")
    
    wiki_window.mainloop()

def start_app(filename):
    root = tk.Tk()
    app = CSVViewerApp(root, filename)
    root.mainloop()

if __name__ == "__main__":
    select_file()


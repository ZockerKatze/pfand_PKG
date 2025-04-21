import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
import json
from PIL import Image, ImageTk
import os
import subprocess
from datetime import datetime
from tkcalendar import DateEntry
import csv
import cv2
from pyzbar.pyzbar import decode
import threading
import queue
import numpy as np
import shutil

# Local Dependencies
from PfandApplication.wiki import main as wiki
from PfandApplication.pfand_scanner import launch_pfand_scanner
from PfandApplication.updater import open_updater as open_updater, run_silent_update
from PfandApplication.tgtg_orderchecker import main as tgtg
from PfandApplication.tgtg_orderchecker import setupkey as tgtg_kt

class Achievement:
    def __init__(self, title, description, condition_type, condition_value):
        self.title = title
        self.description = description
        self.condition_type = condition_type
        self.condition_value = condition_value
        self.unlocked = False
        self.unlock_date = None

class PfandCalculator:
    def __init__(self, root):
        self.achievement_image_gray = None
        self.root = root
        self.root.title("Österreichischer Pfandrechner")
        
        # Load products and prices from JSON
        self.load_products()
        
        self.quantities = {}
        self.images = {}
        self.spinboxes = {}  # Store spinbox references
        self.deposit_history = self.load_deposit_history()
        self.scanned_barcodes = set()
        self.barcode_history = []  # Store barcode scan history
        
        self.achievements = self.initialize_achievements()
        self.load_achievements()
        
        if not os.path.exists('PfandApplication/images'):
            os.makedirs('images')
            
        self.create_menu()
        self.load_quantities()
        self.create_widgets()
        
        # Scanner window
        self.scanner_window = None
        self.cap = None
        self.scanning = False
        
        self.achievement_image = self.load_achievement_image()

    @staticmethod
    def load_image(product_name):
        try:
            # Use Flaschen icon for Bierflasche
            if product_name == "Bierflasche":
                product_name = "Flaschen"
                
            image_path = f"PfandApplication/images/{product_name.lower()}.png"
            if os.path.exists(image_path):
                try:
                    image = Image.open(image_path)
                    image = image.resize((100, 100), Image.Resampling.LANCZOS)
                    return ImageTk.PhotoImage(image)
                except Exception as e:
                    print(f"Error processing image {image_path}: {e}")
                    return None
            else:
                print(f"Image not found: {image_path}")
                return None
        except Exception as e:
            print(f"Error loading image for {product_name}: {e}")
            return None
    
    def load_achievement_image(self):
        try:
            image_path = "PfandApplication/images/auszeichnung.png"
            if os.path.exists(image_path):
                try:
                    image = Image.open(image_path)
                    image = image.resize((50, 50), Image.Resampling.LANCZOS)
                    # Store both normal and gray versions
                    self.achievement_image = ImageTk.PhotoImage(image)
                    # Create grayscale version while preserving transparency
                    gray_image = Image.new('RGBA', image.size)
                    for x in range(image.width):
                        for y in range(image.height):
                            r, g, b, a = image.getpixel((x, y))
                            # Convert to grayscale while preserving alpha
                            gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                            # Make it lighter
                            gray = min(255, gray + 100)
                            gray_image.putpixel((x, y), (gray, gray, gray, a))
                    self.achievement_image_gray = ImageTk.PhotoImage(gray_image)
                    return self.achievement_image
                except Exception as e:
                    print(f"Error processing achievement image: {e}")
                    return None
            print(f"Achievement image not found: {image_path}")
            return None
        except Exception as e:
            print(f"Error loading achievement image: {e}")
            return None

    @staticmethod
    def initialize_achievements():
        return {
            "each_100": Achievement("Krass, Weiter So!", "Du hast bis jetzt 100 von jedem Element gesammelt!", "each_element", 100),
            "each_500": Achievement("Adlersson wäre neidisch!", "Adlersson wäre neidisch auf dich! Du hast 500 von jedem Element gesammelt!", "each_element", 500),
            "each_1000": Achievement("Arbeitslos I", "Arbeitsamt hat angerufen! Du hast 1000 von jedem Element gesammelt!", "each_element", 1000),
            "total_2000": Achievement("Arbeitslos II", "Das Arbeitsamt hat angst vor dir! Du hast 2000 totale Elemente gesammelt!", "total_elements", 2000),
            "total_3000": Achievement("Arbeitslos III", "Drachenlord hat angst vor dir! Du hast mehr wie 3000 Elemente gesammelt!", "total_elements", 3000),
            "total_over_3000": Achievement("Krankhafte Sucht!", "Du hast echt einen Vogel! Pfandangel #1! Du hast >3000 gesammelt!", "total_elements", 3001),
            "first_deposit": Achievement("Depositer!", "Guter Anfang!", "deposits", 1),
            "deposits_10": Achievement("Depositer I", "Cool, Weiter So!", "deposits", 10),
            "deposits_50": Achievement("Depositer II", "WoW, Echt viele Abgaben!", "deposits", 50),
            "deposits_100": Achievement("Depositer III", "Du bist der Meister der Abgaben!", "deposits", 100),
            "deposits_150": Achievement("Meister Depositer", "Der Pfandautomat hat Angst vor dir, so viel wie du Abgegeben hast müsstest du eine Villa besitzen!", "deposits", 150),
            # New scanner achievements
            "first_scan": Achievement("Scanner Neuling", "Du hast deinen ersten Barcode gescannt!", "scans", 1),
            "scans_50": Achievement("Scanner Pro", "50 Barcodes gescannt - du kennst dich aus!", "scans", 50),
            "scans_100": Achievement("Scanner Meister", "100 Barcodes gescannt - der Profi ist da!", "scans", 100),
            "scans_500": Achievement("Scanner Legende", "500 Barcodes gescannt - legendärer Scanner Status erreicht!", "scans", 500),
            "daily_10": Achievement("Tages Champion", "10 Barcodes an einem Tag gescannt!", "daily_scans", 10),
            "daily_25": Achievement("Tages Meister", "25 Barcodes an einem Tag gescannt - sehr fleißig!", "daily_scans", 25)
        }

    def load_achievements(self):
        try:
            with open('achievements.json', 'r') as f:
                data = json.load(f)
                for key, achievement_data in data.items():
                    if key in self.achievements:
                        self.achievements[key].unlocked = achievement_data['unlocked']
                        self.achievements[key].unlock_date = achievement_data['unlock_date']
        except FileNotFoundError:
            pass

    def save_achievements(self):
        data = {
            key: {
                'unlocked': achievement.unlocked,
                'unlock_date': achievement.unlock_date
            }
            for key, achievement in self.achievements.items()
        }
        with open('achievements.json', 'w') as f:
            json.dump(data, f)

    def check_achievements(self):
        total_elements = sum(self.deposit_history[-1]['quantities'].values()) if self.deposit_history else 0
        all_time_total = sum(sum(d['quantities'].values()) for d in self.deposit_history)
        deposits_count = len(self.deposit_history)
        
        for achievement in ["each_100", "each_500", "each_1000"]:
            if not self.achievements[achievement].unlocked:
                if all(self.deposit_history[-1]['quantities'][product] >= self.achievements[achievement].condition_value 
                      for product in self.products):
                    self.unlock_achievement(achievement)

        for achievement in ["total_2000", "total_3000", "total_over_3000"]:
            if not self.achievements[achievement].unlocked and all_time_total >= self.achievements[achievement].condition_value:
                self.unlock_achievement(achievement)

        deposit_achievements = {
            1: "first_deposit",
            10: "deposits_10",
            50: "deposits_50",
            100: "deposits_100",
            150: "deposits_150"
        }
        
        for count, achievement_key in deposit_achievements.items():
            if not self.achievements[achievement_key].unlocked and deposits_count >= count:
                self.unlock_achievement(achievement_key)

    def unlock_achievement(self, achievement_key):
        achievement = self.achievements[achievement_key]
        if not achievement.unlocked:
            achievement.unlocked = True
            achievement.unlock_date = datetime.now().strftime("%d.%m.%Y")
            self.save_achievements()
            messagebox.showinfo("Auszeichnung freigeschaltet!", 
                              f"Neue Auszeichnung: {achievement.title}\n\n{achievement.description}")

    def show_achievements(self):
        achievements_window = tk.Toplevel(self.root)
        achievements_window.title("Auszeichnungen")
        achievements_window.geometry("800x600")

        notebook = ttk.Notebook(achievements_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        all_frame = ttk.Frame(notebook)
        notebook.add(all_frame, text="Alle Auszeichnungen")

        unlocked_frame = ttk.Frame(notebook)
        notebook.add(unlocked_frame, text="Freigeschaltete")

        self._create_achievements_view(all_frame, show_all=True)
        self._create_achievements_view(unlocked_frame, show_all=False)

    def _create_achievements_view(self, parent_frame, show_all=True):
        canvas = tk.Canvas(parent_frame)
        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(widget):
            widget.bind('<MouseWheel>', _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel(child)

        canvas.bind('<MouseWheel>', _on_mousewheel)
        _bind_mousewheel(scrollable_frame)

        sammeln_achievements = {
            "each_100": self.achievements["each_100"],
            "each_500": self.achievements["each_500"],
            "each_1000": self.achievements["each_1000"],
            "total_2000": self.achievements["total_2000"],
            "total_3000": self.achievements["total_3000"],
            "total_over_3000": self.achievements["total_over_3000"]
        }

        abgeben_achievements = {
            "first_deposit": self.achievements["first_deposit"],
            "deposits_10": self.achievements["deposits_10"],
            "deposits_50": self.achievements["deposits_50"],
            "deposits_100": self.achievements["deposits_100"],
            "deposits_150": self.achievements["deposits_150"]
        }

        scanner_achievements = {
            "first_scan": self.achievements["first_scan"],
            "scans_50": self.achievements["scans_50"],
            "scans_100": self.achievements["scans_100"],
            "scans_500": self.achievements["scans_500"],
            "daily_10": self.achievements["daily_10"],
            "daily_25": self.achievements["daily_25"]
        }

        row = 0

        def add_group_header(title):
            nonlocal row
            header_frame = ttk.Frame(scrollable_frame)
            header_frame.grid(row=row, column=0, sticky='ew', padx=5, pady=(15, 5))
            
            header_label = ttk.Label(header_frame, text=title, 
                                   font=('TkDefaultFont', 12, 'bold'))
            header_label.pack(anchor='w')
            
            separator = ttk.Separator(scrollable_frame, orient='horizontal')
            row += 1
            separator.grid(row=row, column=0, sticky='ew', pady=2)
            row += 1

        def add_achievement(key, achievement):
            nonlocal row
            if not show_all and not achievement.unlocked:
                return

            frame = ttk.Frame(scrollable_frame)
            frame.grid(row=row, column=0, sticky='ew', padx=5, pady=5)

            if self.achievement_image:
                if achievement.unlocked:
                    image_label = ttk.Label(frame, image=self.achievement_image)
                else:
                    image_label = ttk.Label(frame, image=self.achievement_image_gray)
                image_label.grid(row=0, column=0, rowspan=2, padx=(5, 10), pady=5)

            content_frame = ttk.Frame(frame)
            content_frame.grid(row=0, column=1, sticky='nsew', pady=5)

            title_label = ttk.Label(content_frame, text=achievement.title, 
                                  font=('TkDefaultFont', 10, 'bold'))
            title_label.grid(row=0, column=0, sticky='w')

            if achievement.unlocked:
                date_label = ttk.Label(content_frame, 
                                     text=f"Freigeschaltet am: {achievement.unlock_date}",
                                     font=('TkDefaultFont', 8))
                date_label.grid(row=0, column=1, padx=(20, 0))

            desc_label = ttk.Label(content_frame, text=achievement.description, 
                                 wraplength=600)
            desc_label.grid(row=1, column=0, columnspan=2, sticky='w', pady=(2, 0))

            content_frame.grid_columnconfigure(0, weight=1)
            content_frame.grid_columnconfigure(1, weight=0)

            separator = ttk.Separator(scrollable_frame, orient='horizontal')
            row += 1
            separator.grid(row=row, column=0, sticky='ew', pady=5)
            row += 1

            _bind_mousewheel(frame)

        add_group_header("Sammeln")
        for key, achievement in sammeln_achievements.items():
            add_achievement(key, achievement)

        add_group_header("Abgeben")
        for key, achievement in abgeben_achievements.items():
            add_achievement(key, achievement)

        add_group_header("Scanner")
        for key, achievement in scanner_achievements.items():
            add_achievement(key, achievement)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    """
    About / Information Section
    
    Structure:
    Main Credits    
    TGTG Credits    
    Updater Credits 
    µScan Credits   
    
    QuickInfo:
        Basically create Toplevel Windows which display Details about each "Integration"
        Use a image for each one (path -> images/versions)
    """
    def create_credits(self, future_icons):
        about_window = tk.Toplevel(self.root)
        about_window.title("Über Programm")
        about_window.resizable(True, True)

        # Grid configuration
        about_window.grid_columnconfigure(0, weight=1)
        about_window.grid_columnconfigure(1, weight=1)
        about_window.grid_rowconfigure(0, weight=1)

        image_path = os.path.join(os.getcwd(), "PfandApplication", "images", "versions", "pineapple.png")

        try:
            img = Image.open(image_path).convert("RGBA")

            bg_color_hex = about_window.cget("bg")
            bg_color_rgb = about_window.winfo_rgb(bg_color_hex)
            bg_color_rgba = tuple(c // 256 for c in bg_color_rgb) + (255,)

            background = Image.new("RGBA", img.size, bg_color_rgba)
            img = Image.alpha_composite(background, img)
            img = img.resize((100, 100), Image.Resampling.LANCZOS)
            pineapple_img = ImageTk.PhotoImage(img)

            img_label = tk.Label(about_window, image=pineapple_img)
            img_label.image = pineapple_img
            img_label.grid(row=0, column=0, columnspan=2, pady=(15, 5))
        except Exception as e:
            print(f"Fehler beim Laden des Bildes: {e}")

        # Info label
        label = tk.Label(
            about_window,
            text=(
                "PfandApp V.8.15.200 - 'Pineapple'\n"
                "PaketVersion 1.2  ( PKG1.2 )\n\n"
                "Erstellt mit TKinter, CV2, Numpy, PyZbar, TGTG-API, TKCalendar, Datetime\n"
            ),
            padx=10,
            pady=10,
            justify="center",
            anchor="center"
        )
        label.grid(row=1, column=0, columnspan=2, pady=0, sticky="nsew")

        url = "https://zockerkatze.github.io/ZockerKatze/"
        url_future_icons = "https://www.svgrepo.com/svg/266606/watermelon"

        # Website button
        website_button = tk.Button(about_window, text="Webseite", command=lambda: webbrowser.open(url))
        website_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        if future_icons:
            future_icon_button = tk.Button(about_window, text="Futur-Icons", command=lambda: webbrowser.open(url_future_icons))
            future_icon_button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        else:
            future_icon_button = None

        # Close button
        close_button = tk.Button(about_window, text="Schließen", command=about_window.destroy)
        close_button.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

    # TGTG Credits
    def TGTG_credits(self):
        about_tgtg = tk.Toplevel(self.root)
        about_tgtg.title("Über TGTG-OrderChecker")
        about_tgtg.resizable(True, True)

        for col in range(2):
            about_tgtg.grid_columnconfigure(col, weight=1)
        about_tgtg.grid_rowconfigure(0, weight=1)

        image_path = os.path.join(os.getcwd(), "PfandApplication", "images", "versions", "tgtg.png")

        try:
            img = Image.open(image_path).convert("RGBA")
            bg_color_hex = about_tgtg.cget("bg")
            bg_color_rgb = about_tgtg.winfo_rgb(bg_color_hex)
            bg_color_rgba = tuple(c // 256 for c in bg_color_rgb) + (255,)

            blended = Image.new("RGBA", img.size, bg_color_rgba)
            img = Image.alpha_composite(blended, img)
            img = img.resize((100, 100), Image.Resampling.LANCZOS)

            tgtg_img = ImageTk.PhotoImage(img)

            # Prevent Garbage Collection ( WHY PYTHON, WHY? )
            about_tgtg.tgtg_img = tgtg_img

            img_label = tk.Label(about_tgtg, image=tgtg_img)
            img_label.grid(row=0, column=0, columnspan=2, pady=(15, 5), sticky='n')
        except Exception as e:
            print(f"Fehler beim Laden des Bildes: {e}")

        label_TGTG = tk.Label(
            about_tgtg,
            text=(
                "PV2-PKG1 - ( PfandVersion 2 - Package 1 )\n"
                "\nTooGoodToGo OrderChecker"
            ),
            padx=10,
            pady=10,
            justify="center",
            anchor="center"
        )
        label_TGTG.grid(row=1, column=0, columnspan=2, sticky="nsew")

        url_TGTG = "https://github.com/ZockerKatze/tgtg_orderchecker"

        website_button = tk.Button(about_tgtg, text="Öffne Repository im Browser", command=lambda: webbrowser.open(url_TGTG))
        website_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        close_button = tk.Button(about_tgtg, text="Schließen", command=about_tgtg.destroy)
        close_button.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

    def update_credits(self):
        about_update = tk.Toplevel(self.root)
        about_update.title("Über UpdaterApp")
        about_update.geometry("650x350")

        # Grid configuration for responsiveness
        about_update.grid_columnconfigure(0, weight=1)
        about_update.grid_columnconfigure(1, weight=1)
        about_update.grid_rowconfigure(0, weight=1)
        about_update.grid_rowconfigure(1, weight=1)
        about_update.grid_rowconfigure(2, weight=0)

        # Load and process image
        image_path = os.path.join(os.getcwd(), "PfandApplication", "images", "versions", "updates.png")

        try:
            img = Image.open(image_path).convert("RGBA")

            bg_color_hex = about_update.cget("bg")
            bg_color_rgb = about_update.winfo_rgb(bg_color_hex)
            bg_color_rgba = tuple(c // 256 for c in bg_color_rgb) + (255,)

            background = Image.new("RGBA", img.size, bg_color_rgba)
            img = Image.alpha_composite(background, img)
            img = img.resize((100, 100), Image.Resampling.LANCZOS)
            update_img = ImageTk.PhotoImage(img)

            # Garbage Collection
            about_update.update_img = update_img

            img_label = tk.Label(about_update, image=update_img)
            img_label.grid(row=0, column=0, columnspan=2, pady=(15, 5), sticky='n')
        except Exception as e:
            print(f"Fehler beim Laden des Bildes: {e}")

        label_update_app = tk.Label(
            about_update,
            text=(
                "Updater App für PfandApp - (PKG1)\n"
                "Version 1.200.000\n"
                "Diese Updater App nutzt das GitHub Repository, um die App zu updaten.\n"
                "Nach Updates sollte die App neugestartet (oder reloaded, bei UI) werden.\n"
                "Beim Starten der App wird nach Updates gesucht!"
            ),
            justify="left",
            anchor="center",
            wraplength=600
        )
        label_update_app.grid(row=1, column=0, columnspan=2, sticky='nsew', padx=10, pady=10)

        # Buttons
        url = "https://github.com/ZockerKatze/pfand_PKG"

        close_button = tk.Button(about_update, text="Schließen", command=about_update.destroy)
        close_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        open_repo_button = tk.Button(about_update, text="Öffne Update-Repository", command=lambda: webbrowser.open(url))
        open_repo_button.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

    def uscan_credits(self):
        about_uscan = tk.Toplevel(self.root)
        about_uscan.title("Über µScan")
        about_uscan.geometry("650x290")

        about_uscan.grid_columnconfigure(0, weight=1)
        about_uscan.grid_rowconfigure(0, weight=1)
        about_uscan.grid_rowconfigure(1, weight=0)

        image_path = os.path.join(os.getcwd(), "PfandApplication", "images", "versions", "uscan.png")

        try:
            img = Image.open(image_path).convert("RGBA")

            bg_color_hex = about_uscan.cget("bg")
            bg_color_rgb = about_uscan.winfo_rgb(bg_color_hex)
            bg_color_rgba = tuple(c // 256 for c in bg_color_rgb) + (255,)

            background = Image.new("RGBA", img.size, bg_color_rgba)
            img = Image.alpha_composite(background, img)
            img = img.resize((300, 100), Image.Resampling.LANCZOS)

            uscan_img = ImageTk.PhotoImage(img)

            # Garbage Collection Prevention
            about_uscan.uscan_img = uscan_img

            img_label = tk.Label(about_uscan, image=uscan_img)
            img_label.grid(row=0, column=0, columnspan=2, pady=(15, 5), sticky='n')

        except Exception as e:
            print(f"Fehler beim Laden des Bildes: {e}")

        label_uscan_app = tk.Label(
            about_uscan,
            text=(
                "µScan - Der bessere Barcode Scanner\n"
                "Version 2.2.2\n"
                "µScan erfordert einen UI Reload (Strg+R) in der Root Anwendung\n"
                "µScan ist für mehrere Barcodes gemacht, die in einer kurzen Zeit gescannt werden sollten\n"
                "Beachte das µScan eine Kamera benötigt die mindestens 30FPS aufnehmen kann (Process-FPS können eingestellt werden!)"
            ),
            justify="left",
            anchor="center"
        )
        label_uscan_app.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        close_button = tk.Button(about_uscan, text="Schließen", command=about_uscan.destroy)
        close_button.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 10))

    def create_menu(self):
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # "Datei" Menu

        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(label="Speichern", command=self.save_quantities, accelerator="Strg+S")
        file_menu.add_command(label="Ordner öffnen", command=self.open_file_location, accelerator="Strg+O")
        file_menu.add_command(label="Speicherdatei löschen", command=self.remove_save_file, accelerator="Strg+Shift+F1")
        file_menu.add_separator()
        file_menu.add_command(label="Neulanden der UI", command=self.recreate_widgets, accelerator="Strg+R")
        file_menu.add_command(label="Updater", command=open_updater, accelerator="Strg+U") # Added this to the File Menu too!
        file_menu.add_separator()
        file_menu.add_command(label="Öffne PfandListe", command=wiki.select_file, accelerator="Strg+L")
        file_menu.add_command(label="Beenden", command=self.root.quit, accelerator="Strg+Q")
        file_menu.add_separator()
        file_menu.add_command(label="Über Programm", command=lambda: self.create_credits(False), accelerator="Strg+F10") # Else this will autolaunch (wo lambda)

        # Deposit Menu

        deposit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Pfand", menu=deposit_menu)
        deposit_menu.add_command(label="Pfand Abgeben", command=self.quick_deposit, accelerator="Strg+D")
        deposit_menu.add_command(label="Abgabe Historie", command=self.show_deposit_history, accelerator="Strg+H")
        deposit_menu.add_separator()
        deposit_menu.add_command(label="Historie Exportieren (CSV)", command=self.export_history_csv, accelerator="Strg+E")
        deposit_menu.add_command(label="Historie Löschen", command=self.clear_deposit_history, accelerator="Strg+Shift+F2")

        # Scanner Menu

        scanner_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Scanner", menu=scanner_menu)
        scanner_menu.add_command(label="Scanner öffnen", command=self.open_scanner_window, accelerator="Strg+B")
        scanner_menu.add_separator()
        scanner_menu.add_command(label="Öffne µScan", command=launch_pfand_scanner, accelerator="Strg+Shift+B") #µScan
        scanner_menu.add_command(label="Über µScan", command=self.uscan_credits) #µScan credits
        scanner_menu.add_separator()
        scanner_menu.add_command(label="Barcodes Exportieren (CSV)", command=self.export_barcodes_csv, accelerator="Strg+Shift+E")

        # Achivements Menu

        achievements_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Auszeichnungen", menu=achievements_menu)
        achievements_menu.add_command(label="Auszeichnungen anzeigen", command=self.show_achievements, accelerator="Strg+F6")
        achievements_menu.add_command(label="Auszeichnungen löschen", command=self.delete_achievements, accelerator="Strg+F7")
        
        # Add custom products menu

        products_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Produkte", menu=products_menu)
        products_menu.add_command(label="Produkt hinzufügen", command=self.show_add_product_window, accelerator="Strg+P")
        products_menu.add_command(label="Produkte verwalten", command=self.show_manage_products_window, accelerator="Strg+Shift+P")

        # TGTG Menu (used to not exist)
        
        tgtg_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="TGTG", menu=tgtg_menu)
        tgtg_menu.add_command(label="Öffne TGTG-OC", command=tgtg.start_tgtg, accelerator="Strg+F12")
        tgtg_menu.add_command(label="Öffne KeyTool", command=tgtg_kt.ask_for_tokens, accelerator="Strg+F11")
        tgtg_menu.add_separator()
        tgtg_menu.add_command(label="Über TGTG", command=self.TGTG_credits) # No keybind , why tf would you need one anyway

        update_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Updater", menu=update_menu)
        update_menu.add_command(label="Öffne Updater", command=open_updater, accelerator="Strg+U") # Version (7.4.000 Updater Version)
        update_menu.add_separator()
        update_menu.add_command(label="Über Updater", command=self.update_credits) # Also no keybind here, same reason as the tgtg one #V7.4.001

        # Manage Keybinds
        self.root.bind('<Control-s>', lambda e: self.save_quantities())
        self.root.bind('<Control-o>', lambda e: self.open_file_location())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<Control-d>', lambda e: self.quick_deposit())
        self.root.bind('<Control-h>', lambda e: self.show_deposit_history())
        self.root.bind('<Control-e>', lambda e: self.export_history_csv())
        self.root.bind('<Control-b>', lambda e: self.open_scanner_window())
        self.root.bind('<Control-Shift-B>', lambda e: launch_pfand_scanner()) #µScan
        self.root.bind('<Control-F1>', lambda e: self.handle_shift_f1(e))
        self.root.bind('<Control-F2>', lambda e: self.handle_shift_f2(e))
        self.root.bind('<Control-F6>', lambda e: self.show_achievements())
        self.root.bind('<Control-F7>', lambda e: self.delete_achievements())
        self.root.bind('<Control-F12>', lambda e: tgtg.start_tgtg(self.root))
        self.root.bind('<Control-F11>', lambda e: tgtg_kt.ask_for_tokens())
        self.root.bind('<Control-Shift-C>', lambda e: self.create_credits(False)) # True this will show future Icons
        self.root.bind('<Control-E>', lambda e: self.export_barcodes_csv() if e.state & 0x1 else self.export_history_csv())
        self.root.bind('<Control-p>', lambda e: self.show_add_product_window())
        self.root.bind('<Control-P>', lambda e: self.show_manage_products_window() if e.state & 0x1 else self.show_add_product_window())
        self.root.bind('<Control-l>', lambda e: wiki.select_file())
        self.root.bind('<Control-r>', lambda e: self.recreate_widgets())
        self.root.bind('<Control-u>', lambda e: open_updater()) # New Update Feature (Version 7.4.000 UPDATER)

    def open_file_location(self):
        current_dir = os.getcwd()
        if os.name == 'nt':  # Windows
            os.startfile(current_dir)
        else:  # Linux/Mac
            try:
                subprocess.run(['xdg-open', current_dir])
            except:
                subprocess.run(['open', current_dir])

    def remove_save_file(self):
        if os.path.exists('quantities.json'):
            if messagebox.askyesno("Löschen bestätigen", "Sind Sie sicher, dass Sie die Speicherdatei löschen möchten?"):
                try:
                    os.remove('quantities.json')
                    messagebox.showinfo("Erfolg", "Speicherdatei wurde erfolgreich gelöscht!")
                    self.quantities = {product: 0 for product in self.products}
                    self.update_total()
                    for widget in self.root.winfo_children():
                        if isinstance(widget, ttk.Frame):
                            for child in widget.winfo_children():
                                if isinstance(child, ttk.Frame):
                                    for grandchild in child.winfo_children():
                                        if isinstance(grandchild, ttk.Spinbox):
                                            grandchild.set("0")
                except Exception as e:
                    messagebox.showerror("Fehler", f"Datei konnte nicht gelöscht werden: {str(e)}")
        else:
            messagebox.showinfo("Info", "Keine Speicherdatei vorhanden.")

    def load_quantities(self):
        try:
            with open('quantities.json', 'r') as f:
                self.quantities = json.load(f)
        except FileNotFoundError:
            self.quantities = {product: 0 for product in self.products}
    
    def save_quantities(self):
        try:
            with open('quantities.json', 'w') as f:
                json.dump(self.quantities, f)
            messagebox.showinfo("Erfolg", "Mengen wurden erfolgreich gespeichert!")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern der Mengen: {str(e)}")
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        for i, product in enumerate(self.products):
            frame = ttk.Frame(main_frame)
            frame.grid(row=0, column=i, padx=10, pady=5)
            
            image = self.load_image(product)
            if image:
                self.images[product] = image  
                label = ttk.Label(frame, image=self.images[product])
                label.grid(row=0, column=0, pady=5)
            else:
                canvas = tk.Canvas(frame, width=100, height=100, bg='white')
                canvas.grid(row=0, column=0, pady=5)
                canvas.create_text(50, 50, text=f"Kein {product}\nBild gefunden")
            
            ttk.Label(frame, text=product).grid(row=1, column=0, pady=2)
            ttk.Label(frame, text=f"€{self.PRICES[product]:.2f}").grid(row=2, column=0, pady=2)
            
            quantity_var = tk.StringVar(value=str(self.quantities.get(product, 0)))
            spinbox = ttk.Spinbox(
                frame,
                from_=0,
                to=100,
                width=5,
                textvariable=quantity_var,
                command=lambda p=product, v=quantity_var: self.update_quantity(p, v)
            )
            spinbox.grid(row=3, column=0, pady=5)
            
            # Store spinbox reference
            self.spinboxes[product] = spinbox
            
            spinbox.bind('<Return>', lambda event, p=product, v=quantity_var: self.update_quantity(p, v))
            spinbox.bind('<FocusOut>', lambda event, p=product, v=quantity_var: self.update_quantity(p, v))
        
        self.total_label = ttk.Label(main_frame, text="Gesamt: €0.00", font=('TkDefaultFont', 10, 'bold'))
        self.total_label.grid(row=1, column=0, columnspan=len(self.products), pady=10)
        
        self.update_total()
    
    def update_quantity(self, product, var, event=None):
        try:
            quantity = int(var.get())
            self.quantities[product] = quantity
            self.update_total()
        except ValueError:
            var.set(str(self.quantities.get(product, 0)))
    
    def update_total(self):
        total = sum(self.quantities[product] * self.PRICES[product] for product in self.products) # get total
        self.total_label.config(text=f"Gesamt: €{total:.2f}")

    @staticmethod
    def load_deposit_history():
        try:
            with open('deposit_history.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save_deposit_history(self):
        try:
            with open('deposit_history.json', 'w') as f:
                json.dump(self.deposit_history, f)
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern der Historie: {str(e)}")

    # Changed in Version 7.4.101
    def show_deposit_history(self):
        try:
            with open("deposit_history.json", "r", encoding="utf-8") as file:
                deposit_history = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print("error while loading file")
            return

        history_window = tk.Toplevel(self.root)
        history_window.title("Pfand Abgabe Historie")
        history_window.geometry("900x500")

        main_frame = ttk.Frame(history_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        all_items = set()
        for deposit in deposit_history:
            all_items.update(deposit['quantities'].keys())

        item_columns = sorted(all_items)
        columns = ['Datum'] + item_columns + ['Gesamt']

        tree = ttk.Treeview(main_frame, columns=columns, show='headings')

        for col in columns:
            tree.heading(col, text=col, anchor='center')
            width = 100 if col == 'Datum' else 80
            tree.column(col, width=width, anchor='center' if col != 'Gesamt' else 'e')

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        totals = {item: 0 for item in item_columns}
        total_amount = 0

        for deposit in deposit_history:
            quantities = deposit.get('quantities', {})
            row = [deposit.get('date', '')]
            for item in item_columns:
                count = quantities.get(item, 0)
                row.append(count)
                totals[item] += count
            amount = deposit.get('total', 0.0)
            row.append(f"{amount:.2f}")
            total_amount += amount
            tree.insert('', tk.END, values=row)

        totals_frame = ttk.Frame(main_frame)
        totals_frame.grid(row=1, column=0, sticky='ew', pady=(5, 0))

        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.grid(row=2, column=0, sticky='ew', pady=2)

        bold_font = ('TkDefaultFont', 9, 'bold')

        row = ["Gesamt:"]
        for item in item_columns:
            row.append(f"{totals[item]} {item}")  
        row.append(f"€{total_amount:.2f}")  
        for idx, value in enumerate(row):
            ttk.Label(totals_frame, text=value, font=bold_font).grid(row=0, column=idx, sticky='w', padx=5)

        separator.grid(row=3, column=0, sticky='ew', pady=5)

    def make_deposit(self):
        deposit_dialog = tk.Toplevel(self.root)
        deposit_dialog.title("Pfand Abgeben")
        deposit_dialog.geometry("300x150")
        deposit_dialog.transient(self.root)
        deposit_dialog.grab_set()

        ttk.Label(deposit_dialog, text="Abgabe Datum:").pack(pady=5)
        date_picker = DateEntry(deposit_dialog, width=12, background='darkblue',
                              foreground='white', borderwidth=2, locale='de_DE')
        date_picker.pack(pady=5)

        def confirm_deposit():
            date = date_picker.get_date().strftime("%d.%m.%Y")
            current_total = sum(self.quantities[product] * self.PRICES[product]
                              for product in self.products)
            
            deposit_record = {
                'date': date,
                'quantities': dict(self.quantities),
                'total': current_total
            }
            self.deposit_history.append(deposit_record)
            self.save_deposit_history()

            self.quantities = {product: 0 for product in self.products}
            self.save_quantities()
            self.update_total()

            for widget in self.root.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Frame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.Spinbox):
                                    grandchild.set("0")

            messagebox.showinfo("Erfolg", "Pfand wurde erfolgreich abgegeben!")
            deposit_dialog.destroy()

        button_frame = ttk.Frame(deposit_dialog)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="Abgeben", command=confirm_deposit).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=deposit_dialog.destroy).pack(side=tk.LEFT, padx=5)

    def quick_deposit(self):
        if sum(self.quantities.values()) == 0:
            messagebox.showinfo("Info", "Keine Mengen zum Abgeben vorhanden.")
            return

        if messagebox.askyesno("Pfand Abgeben", "Möchten Sie den Pfand mit dem heutigen Datum abgeben?"):
            current_date = datetime.now().strftime("%d.%m.%Y")
            current_total = sum(self.quantities[product] * self.PRICES[product] 
                            for product in self.products)
            
            deposit_record = {
                'date': current_date,
                'quantities': dict(self.quantities),
                'total': current_total
            }
            self.deposit_history.append(deposit_record)
            self.save_deposit_history()
            
            self.check_achievements()

            self.quantities = {product: 0 for product in self.products}
            self.save_quantities()
            self.update_total()

            for widget in self.root.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Frame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.Spinbox):
                                    grandchild.set("0")

            messagebox.showinfo("Erfolg", "Pfand wurde erfolgreich abgegeben!")
        else:
            self.make_deposit()

    def export_history_csv(self):
        if not self.deposit_history:
            messagebox.showinfo("Info", "Keine Historie zum Exportieren vorhanden.")
            return

        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Dateien", "*.csv")],
                initialfile="pfand_historie.csv"
            )
            
            if not file_path:
                return

            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # Create header with all products
                header = ['Datum'] + self.products + ['Gesamt (€)']
                writer.writerow(header)
                
                for deposit in self.deposit_history:
                    # Create row with all products
                    row = [deposit['date']]
                    for product in self.products:
                        row.append(deposit['quantities'].get(product, 0))
                    row.append(f"{deposit['total']:.2f}")
                    writer.writerow(row)
            
            messagebox.showinfo("Erfolg", "Historie wurde erfolgreich exportiert!")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Exportieren: {str(e)}")

    def clear_deposit_history(self):
        if not self.deposit_history:
            messagebox.showinfo("Info", "Keine Historie zum Löschen vorhanden.")
            return

        if messagebox.askyesno("Löschen bestätigen", 
                              "Sind Sie sicher, dass Sie die gesamte Abgabe-Historie löschen möchten?\n"
                              "Dieser Vorgang kann nicht rückgängig gemacht werden!"):
            try:
                self.deposit_history = []
                if os.path.exists('deposit_history.json'):
                    os.remove('deposit_history.json')
                messagebox.showinfo("Erfolg", "Abgabe-Historie wurde erfolgreich gelöscht!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Löschen der Historie: {str(e)}")

    def handle_shift_f1(self, event):
        if event.state & 0x1:
            self.remove_save_file()

    def handle_shift_f2(self, event):
        if event.state & 0x1:
            self.clear_deposit_history()

    def delete_achievements(self):
        if not any(achievement.unlocked for achievement in self.achievements.values()):
            messagebox.showinfo("Info", "Keine Auszeichnungen zum Löschen vorhanden.")
            return

        if messagebox.askyesno("Löschen bestätigen", 
                              "Sind Sie sicher, dass Sie alle Auszeichnungen löschen möchten?\n"
                              "Dieser Vorgang kann nicht rückgängig gemacht werden!"):
            try:
                for achievement in self.achievements.values():
                    achievement.unlocked = False
                    achievement.unlock_date = None
                
                if os.path.exists('achievements.json'):
                    os.remove('achievements.json')
                messagebox.showinfo("Erfolg", "Alle Auszeichnungen wurden erfolgreich gelöscht!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Löschen der Auszeichnungen: {str(e)}")

    def open_scanner_window(self):
        if self.scanner_window is None or not self.scanner_window.winfo_exists():
            self.scanner_window = tk.Toplevel(self.root)
            self.scanner_window.title("Pfand Scanner")
            self.scanner_window.protocol("WM_DELETE_WINDOW", self.close_scanner_window)
            
            # Create frames for scanner layout
            self.camera_frame = ttk.Frame(self.scanner_window)
            self.camera_frame.pack(side="left", padx=10, pady=5)
            
            self.scanner_control_frame = ttk.Frame(self.scanner_window)
            self.scanner_control_frame.pack(side="left", padx=10, pady=5, fill="y")
            
            # Create camera label
            self.camera_label = ttk.Label(self.camera_frame)
            self.camera_label.pack()
            
            # Create focus control
            focus_frame = ttk.LabelFrame(self.scanner_control_frame, text="Kamera Einstellungen")
            focus_frame.pack(pady=5, padx=5, fill="x")
            
            ttk.Label(focus_frame, text="Fokus:").pack(pady=2)
            self.focus_slider = ttk.Scale(focus_frame, from_=0, to=255, orient="horizontal")
            self.focus_slider.set(0)
            self.focus_slider.pack(pady=2, padx=5, fill="x")
            
            self.autofocus_var = tk.BooleanVar(value=True)
            self.autofocus_check = ttk.Checkbutton(
                focus_frame,
                text="Autofokus",
                variable=self.autofocus_var,
                command=self.toggle_autofocus
            )
            self.autofocus_check.pack(pady=2)
            
            # Create image processing controls
            process_frame = ttk.LabelFrame(self.scanner_control_frame, text="Bildverarbeitung")
            process_frame.pack(pady=5, padx=5, fill="x")
            
            ttk.Label(process_frame, text="Helligkeit:").pack(pady=2)
            self.brightness_slider = ttk.Scale(process_frame, from_=0, to=100, orient="horizontal")
            self.brightness_slider.set(50)
            self.brightness_slider.pack(pady=2, padx=5, fill="x")
            
            ttk.Label(process_frame, text="Kontrast:").pack(pady=2)
            self.contrast_slider = ttk.Scale(process_frame, from_=0, to=100, orient="horizontal")
            self.contrast_slider.set(50)
            self.contrast_slider.pack(pady=2, padx=5, fill="x")
            
            # Start/Stop button
            self.scan_button = ttk.Button(
                self.scanner_control_frame,
                text="Scannen Starten",
                command=self.toggle_scanning
            )
            self.scan_button.pack(pady=10)
            
            # Initialize scan counter for achievements
            self.daily_scans = 0
            self.total_scans = 0
            self.last_scan_date = None
            
            # Queue for thread-safe communication
            self.queue = queue.Queue()
            
            # Set window size to match camera resolution
            self.scanner_window.geometry("1600x800")

    def close_scanner_window(self):
        if self.scanning:
            self.toggle_scanning()
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.scanner_window:
            self.scanner_window.destroy()
            self.scanner_window = None

    def toggle_scanning(self):
        if not self.scanning:
            self.cap = cv2.VideoCapture(0)
            
            # Set optimal camera properties for performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)  # Request 30 FPS
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer delay
            
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            self.cap.set(cv2.CAP_PROP_FOCUS, 0)
            
            self.scanning = True
            self.scan_button.configure(text="Scannen Stoppen")
            self.process_video()
        else:
            self.scanning = False
            if self.cap:
                self.cap.release()
            self.cap = None
            self.scan_button.configure(text="Scannen Starten")
            self.camera_label.configure(image='')

    def toggle_autofocus(self):
        if self.cap:
            if self.autofocus_var.get():
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                self.focus_slider.state(['disabled'])
            else:
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                self.focus_slider.state(['!disabled'])
                self.cap.set(cv2.CAP_PROP_FOCUS, self.focus_slider.get())

    def adjust_image(self, frame):
        # This method is now only used for preview adjustments
        brightness = self.brightness_slider.get() / 50.0 - 1.0
        contrast = self.contrast_slider.get() / 50.0
        
        adjusted = cv2.convertScaleAbs(frame, alpha=contrast, beta=brightness * 127)
        return adjusted

    def process_video(self):
        if not self.scanning:
            return
            
        try:
            ret, frame = self.cap.read()
            if ret:
                if not self.autofocus_var.get():
                    self.cap.set(cv2.CAP_PROP_FOCUS, self.focus_slider.get())
                
                # Resize frame for faster processing (720p is plenty for barcode detection)
                frame = cv2.resize(frame, (1280, 720))
                
                # Only process every 3rd frame for barcode detection
                if hasattr(self, 'frame_count'):
                    self.frame_count += 1
                else:
                    self.frame_count = 0
                
                if self.frame_count % 3 == 0:  # Process every 3rd frame
                    # Process in grayscale for better performance
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    barcodes = decode(gray)
                    
                    for barcode in barcodes:
                        points = barcode.polygon
                        if len(points) == 4:
                            pts = np.array([(p.x, p.y) for p in points])
                            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
                    
                        barcode_data = barcode.data.decode('utf-8')
                        if barcode_data not in self.scanned_barcodes:
                            self.scanned_barcodes.add(barcode_data)
                            self.scanner_window.after(0, lambda d=barcode_data: self.handle_barcode(d))
                
                # Convert and display frame
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                img = Image.fromarray(cv2image)
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_label.imgtk = imgtk
                self.camera_label.configure(image=imgtk)
            
            if self.scanning:
                # Use a shorter delay for higher frame rate
                self.scanner_window.after(5, self.process_video)
        except Exception as e:
            print(f"Error in process_video: {e}")
            if self.scanning:
                self.scanner_window.after(5, self.process_video)

    def handle_barcode(self, barcode_data):
        # First dialog for Pfand symbol verification
        verify_dialog = tk.Toplevel(self.scanner_window)
        verify_dialog.title("Pfand Symbol Überprüfung")
        verify_dialog.transient(self.scanner_window)
        verify_dialog.grab_set()
        
        ttk.Label(verify_dialog, text="Ist ein Pfand Symbol auf dem Produkt?").pack(pady=10)
        
        def handle_verification(has_pfand):
            verify_dialog.destroy()
            if has_pfand:
                # Add barcode to history with timestamp and Pfand status
                self.barcode_history.append({
                    'timestamp': datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    'barcode': barcode_data,
                    'has_pfand': True
                })
                self.show_product_selection_dialog(barcode_data)
            else:
                # Add barcode to history with timestamp and Pfand status
                self.barcode_history.append({
                    'timestamp': datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    'barcode': barcode_data,
                    'has_pfand': False
                })
                self.scanned_barcodes.remove(barcode_data)
                messagebox.showinfo("Kein Pfand", "Dieses Produkt hat kein Pfand Symbol.")
        
        button_frame = ttk.Frame(verify_dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Ja", command=lambda: handle_verification(True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Nein", command=lambda: handle_verification(False)).pack(side=tk.LEFT, padx=5)

    def show_product_selection_dialog(self, barcode_data):
        dialog = tk.Toplevel(self.scanner_window)
        dialog.title("Barcode Erkannt")
        dialog.transient(self.scanner_window)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Barcode erkannt: {barcode_data}").pack(pady=10)
        ttk.Label(dialog, text="Produkttyp auswählen:").pack(pady=5)
        
        product_var = tk.StringVar()
        for product in self.products:
            ttk.Radiobutton(dialog, text=product, variable=product_var, value=product).pack()
        
        def confirm():
            selected_product = product_var.get()
            if selected_product:
                print(f"Erhöhe {selected_product}")  # Debug print
                # Update quantity
                current_qty = self.quantities.get(selected_product, 0)
                self.quantities[selected_product] = current_qty + 1
                print(f"Neue Menge für {selected_product}: {self.quantities[selected_product]}")  # Debug print
                
                # Update scan counters and check achievements
                self.update_scan_achievements()
                
                # Force immediate UI update
                def do_update():
                    try:
                        # Directly update the spinbox
                        spinbox = self.spinboxes[selected_product]
                        spinbox.set(str(self.quantities[selected_product]))
                        spinbox.update()  # Force the spinbox to update
                        
                        # Update the total
                        self.update_total()
                        self.root.update_idletasks()  # Force the entire UI to update
                        
                        # Save the quantities
                        self.save_quantities()
                        print("UI Update und Speicherung abgeschlossen")  # Debug print
                    except Exception as e:
                        print(f"Fehler beim UI Update: {e}")
                
                # Schedule the update for the next event loop iteration
                self.root.after(1, do_update)
                dialog.destroy()
        
        def skip():
            self.scanned_barcodes.remove(barcode_data)
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Hinzufügen", command=confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Überspringen", command=skip).pack(side=tk.LEFT, padx=5)

    def update_scan_achievements(self):
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Update daily scan counter
        if self.last_scan_date != current_date:
            self.daily_scans = 1
            self.last_scan_date = current_date
        else:
            self.daily_scans += 1
        
        # Update total scan counter
        self.total_scans += 1
        
        # Check scan-related achievements
        achievements_to_check = {
            1: "first_scan",
            50: "scans_50",
            100: "scans_100",
            500: "scans_500"
        }
        
        # Check total scans achievements
        for count, achievement_key in achievements_to_check.items():
            if self.total_scans == count and not self.achievements[achievement_key].unlocked:
                self.unlock_achievement(achievement_key)
                self.save_achievements()
        
        # Check daily scan achievements
        daily_achievements = {
            10: "daily_10",
            25: "daily_25"
        }
        
        for count, achievement_key in daily_achievements.items():
            if self.daily_scans == count and not self.achievements[achievement_key].unlocked:
                self.unlock_achievement(achievement_key)
                self.save_achievements()
        
        # Save the updated scan counts
        self.save_quantities()  # This ensures we don't lose progress

    def update_ui(self):
        def update_spinboxes():
            try:
                # Update all spinboxes to match quantities
                main_frame = self.root.winfo_children()[0]  # Get the main frame
                for frame in main_frame.winfo_children():
                    if isinstance(frame, ttk.Frame):
                        # Find the product this frame represents
                        for widget in frame.winfo_children():
                            if isinstance(widget, ttk.Label) and widget.cget('text') in self.products:
                                product = widget.cget('text')
                                current_qty = self.quantities.get(product, 0)
                                # Find and update the spinbox
                                for w in frame.winfo_children():
                                    if isinstance(w, ttk.Spinbox):
                                        w.set(str(current_qty))
                                        w.update()
                                        break
                
                # Update the total
                self.update_total()
            except Exception as e:
                print(f"Error updating UI: {e}")
        
        # Ensure updates happen in the main thread
        if threading.current_thread() is threading.main_thread():
            update_spinboxes()
        else:
            self.root.after(0, update_spinboxes)

    def on_closing(self):
        if self.scanner_window and self.scanner_window.winfo_exists():
            self.close_scanner_window()
        self.root.destroy()

    def export_barcodes_csv(self):
        if not self.barcode_history:
            messagebox.showinfo("Info", "Keine Barcodes zum Exportieren vorhanden.")
            return

        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Dateien", "*.csv")],
                initialfile="barcode_historie.csv"
            )
            
            if not file_path:
                return

            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # Write header
                writer.writerow(['Datum', 'Barcode', 'Hat Pfand'])
                
                # Write barcode history
                for entry in self.barcode_history:
                    writer.writerow([
                        entry['timestamp'],
                        entry['barcode'],
                        'Ja' if entry['has_pfand'] else 'Nein'
                    ])
            
            messagebox.showinfo("Erfolg", "Barcode Historie wurde erfolgreich exportiert!")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Exportieren: {str(e)}")

    def load_products(self):
        try:
            with open('products.json', 'r') as f:
                data = json.load(f)
                self.products = data.get('products', [])
                self.PRICES = data.get('prices', {})
        except FileNotFoundError:
            # Default products if no JSON exists
            self.products = ["Flaschen", "Bierflasche", "Kasten", "Dose", "Plastikflasche", "Monster", "Joghurt Glas"]
            self.PRICES = {
                "Flaschen": 0.25,
                "Bierflasche": 0.20,
                "Kasten": 3.00,
                "Dose": 0.25,
                "Plastikflasche": 0.25,
                "Monster": 0.25,
                "Joghurt Glas": 0.17,
            }
            self.save_products()

    def save_products(self):
        try:
            data = {
                'products': self.products,
                'prices': self.PRICES
            }
            with open('products.json', 'w') as f:
                json.dump(data, f)
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern der Produkte: {str(e)}")

    def show_add_product_window(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Neues Produkt hinzufügen")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Product name
        name_frame = ttk.Frame(dialog)
        name_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(name_frame, text="Produktname:").pack(side='left')
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var)
        name_entry.pack(side='left', fill='x', expand=True, padx=5)

        # Deposit amount
        deposit_frame = ttk.Frame(dialog)
        deposit_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(deposit_frame, text="Pfandbetrag (€):").pack(side='left')
        deposit_var = tk.StringVar()
        deposit_entry = ttk.Entry(deposit_frame, textvariable=deposit_var)
        deposit_entry.pack(side='left', fill='x', expand=True, padx=5)

        # Image selection
        image_frame = ttk.Frame(dialog)
        image_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(image_frame, text="Bild:").pack(side='left')
        image_path_var = tk.StringVar()
        image_entry = ttk.Entry(image_frame, textvariable=image_path_var)
        image_entry.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(image_frame, text="Durchsuchen", command=lambda: self.select_image(image_path_var)).pack(side='left')

        def add_product():
            name = name_var.get().strip()
            try:
                deposit = float(deposit_var.get().replace(',', '.'))
            except ValueError:
                messagebox.showerror("Fehler", "Bitte geben Sie einen gültigen Pfandbetrag ein.")
                return

            if not name:
                messagebox.showerror("Fehler", "Bitte geben Sie einen Produktnamen ein.")
                return

            if name in self.products:
                messagebox.showerror("Fehler", "Ein Produkt mit diesem Namen existiert bereits.")
                return

            image_path = image_path_var.get()
            if image_path:
                try:
                    # Create images directory if it doesn't exist
                    if not os.path.exists('PfandApplication/images'):
                        os.makedirs('images')

                    # Copy and rename the image
                    new_image_path = f"PfandApplication/images/{name.lower()}.png"
                    shutil.copy2(image_path, new_image_path)
                except Exception as e:
                    messagebox.showerror("Fehler", f"Fehler beim Kopieren des Bildes: {str(e)}")
                    return

            # Add the new product
            self.products.append(name)
            self.PRICES[name] = deposit
            self.save_products()

            # Update the UI
            self.recreate_widgets()
            dialog.destroy()

        ttk.Button(dialog, text="Hinzufügen", command=add_product).pack(pady=10)

    def select_image(self, image_path_var, preview_label=None):
        file_path = filedialog.askopenfilename(
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if file_path:
            image_path_var.set(file_path)
            if preview_label:
                try:
                    image = Image.open(file_path)
                    # Resize image to fit preview (100x100)
                    image.thumbnail((100, 100), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    preview_label.configure(image=photo)
                    preview_label.image = photo  # Keep a reference
                except Exception as e:
                    print(f"Error loading preview: {e}")

    def show_manage_products_window(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Produkte verwalten")
        dialog.geometry("1200x600")
        dialog.transient(self.root)
        dialog.grab_set()

        # Create main container with two columns
        main_container = ttk.Frame(dialog)
        main_container.pack(fill='both', expand=True, padx=10, pady=5)

        # Left column for product list
        left_frame = ttk.Frame(main_container)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))

        # Right column for add/edit product
        right_frame = ttk.LabelFrame(main_container, text="Produkt hinzufügen")
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))

        # Create treeview in left frame
        tree = ttk.Treeview(left_frame, columns=('Name', 'Pfand'), show='headings')
        tree.heading('Name', text='Name')
        tree.heading('Pfand', text='Pfand (€)')
        tree.pack(fill='both', expand=True)

        # Add scrollbar for treeview
        scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)

        # Populate treeview
        for product in self.products:
            tree.insert('', 'end', values=(product, f"{self.PRICES[product]:.2f}"))

        # Add product form in right frame
        # Product name
        name_frame = ttk.Frame(right_frame)
        name_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(name_frame, text="Produktname:").pack(side='left')
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var)
        name_entry.pack(side='left', fill='x', expand=True, padx=5)

        # Deposit amount
        deposit_frame = ttk.Frame(right_frame)
        deposit_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(deposit_frame, text="Pfandbetrag (€):").pack(side='left')
        deposit_var = tk.StringVar()
        deposit_entry = ttk.Entry(deposit_frame, textvariable=deposit_var)
        deposit_entry.pack(side='left', fill='x', expand=True, padx=5)

        # Image selection with preview
        image_frame = ttk.Frame(right_frame)
        image_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(image_frame, text="Bild:").pack(side='left')
        image_path_var = tk.StringVar()
        image_entry = ttk.Entry(image_frame, textvariable=image_path_var)
        image_entry.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(image_frame, text="Durchsuchen", command=lambda: self.select_image(image_path_var, preview_label)).pack(side='left')

        # Image preview
        preview_frame = ttk.Frame(right_frame)
        preview_frame.pack(fill='x', padx=10, pady=5)
        preview_label = ttk.Label(preview_frame)
        preview_label.pack()

        def update_preview(image_path):
            if image_path and os.path.exists(image_path):
                try:
                    image = Image.open(image_path)
                    # Resize image to fit preview (100x100)
                    image.thumbnail((100, 100), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    preview_label.configure(image=photo)
                    preview_label.image = photo  # Keep a reference
                except Exception as e:
                    print(f"Error loading preview: {e}")

        def select_image_with_preview(image_path_var, preview_label):
            file_path = filedialog.askopenfilename(
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
            )
            if file_path:
                image_path_var.set(file_path)
                update_preview(file_path)

        def add_product():
            name = name_var.get().strip()
            try:
                deposit = float(deposit_var.get().replace(',', '.'))
            except ValueError:
                messagebox.showerror("Fehler", "Bitte geben Sie einen gültigen Pfandbetrag ein.")
                return

            if not name:
                messagebox.showerror("Fehler", "Bitte geben Sie einen Produktnamen ein.")
                return

            if name in self.products:
                messagebox.showerror("Fehler", "Ein Produkt mit diesem Namen existiert bereits.")
                return

            image_path = image_path_var.get()
            if image_path:
                try:
                    # Create images directory if it doesn't exist
                    if not os.path.exists('PfandApplication/images'):
                        os.makedirs('images')

                    # Copy and rename the image
                    new_image_path = f"PfandApplication/images/{name.lower()}.png"
                    shutil.copy2(image_path, new_image_path)
                except Exception as e:
                    messagebox.showerror("Fehler", f"Fehler beim Kopieren des Bildes: {str(e)}")
                    return

            # Add the new product
            self.products.append(name)
            self.PRICES[name] = deposit
            self.save_products()

            # Update treeview
            tree.insert('', 'end', values=(name, f"{deposit:.2f}"))
            tree.yview_moveto(1)  # Scroll to the bottom to show the new item

            # Clear form
            name_var.set("")
            deposit_var.set("")
            image_path_var.set("")
            preview_label.configure(image='')

            # Update the main window UI
            self.recreate_widgets()

        def delete_product():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warnung", "Bitte wählen Sie ein Produkt aus.")
                return

            if messagebox.askyesno("Bestätigen", "Möchten Sie das ausgewählte Produkt wirklich löschen?"):
                item = tree.item(selected[0])
                product_name = item['values'][0]
                
                # Remove from lists
                self.products.remove(product_name)
                del self.PRICES[product_name]
                
                # Delete image if exists
                image_path = f"PfandApplication/images/{product_name.lower()}.png"
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        print(f"Fehler beim Löschen des Bildes: {e}")

                # Save changes and update UI
                self.save_products()
                self.recreate_widgets()
                dialog.destroy()

        # Add buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill='x', padx=10, pady=10)
        ttk.Button(button_frame, text="Hinzufügen", command=add_product).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Löschen", command=delete_product).pack(side='left', padx=5)

        # Bind image selection to preview update
        image_path_var.trace_add('write', lambda *args: update_preview(image_path_var.get()))

    def recreate_widgets(self):
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Recreate menu
        self.create_menu()
        
        # Reload quantities
        self.load_quantities()
        
        # Recreate main widgets
        self.create_widgets()

    @staticmethod
    def launch(check_for_update) -> None:
     root = tk.Tk()
     app = PfandCalculator(root)

     #Icon (Version Pineapple | not really sure if this works yet!)
     #TODO: Check if this shit works (On Windows and Linux)
     icon_path = os.path.join(os.getcwd(), "PfandApplication", "images", "versions", "pineapple.png")
     ico = Image.open(icon_path)
     photo = ImageTk.PhotoImage(ico)
     root.iconphoto(False, photo)


     if check_for_update is None: # If it's None then also pass (acts like False)
         pass

     elif not check_for_update: # If it isn't True pass
         pass

     else: # If is True then call the silent updater
         root.after(1, run_silent_update)

     root.mainloop()

if __name__ == "__main__": PfandCalculator.launch(True)

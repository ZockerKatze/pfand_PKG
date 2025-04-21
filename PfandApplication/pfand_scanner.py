# µScan V2.2.2
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import cv2
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode
from datetime import datetime, timedelta
import threading
import queue
import json
import os
import time

class PfandScanner:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.window.geometry("1920x1080")
        self.window.minsize(960, 540)
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        self.data_file = "quantities.json"
        self.load_json()

        self.barcode_times = {}
        self.prompted_barcodes = set()

        self.selected_device_index = tk.IntVar(value=0)
        self.last_process_time = time.time()

        # FPS Einstellung ist hier!
        # FPS Setting is here!
        self.process_interval = 0.30 # 30 FPS

        self.init_gui()
        self.init_camera()

        self.queue = queue.Queue()
        self.pfand_values = {
            "EINWEG": 0.25,
            "MEHRWEG": 0.15,
            "DOSE": 0.25,
        }

        self.update_preview()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queue()

    def init_gui(self):
        self.main_frame = ttk.Frame(self.window)
        self.main_frame.grid(sticky="nsew")
        self.main_frame.columnconfigure(0, weight=3)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=3)
        self.main_frame.rowconfigure(0, weight=1)

        self.camera_frame = ttk.Frame(self.main_frame)
        self.camera_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.info_frame = ttk.Frame(self.main_frame)
        self.info_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

        self.camera_label = ttk.Label(self.camera_frame)
        self.camera_label.pack(expand=True, fill="both")

        self.init_device_selector()
        self.init_controls()
        self.init_treeview()

    def init_device_selector(self):
        device_frame = ttk.LabelFrame(self.control_frame, text="Video Device")
        device_frame.pack(pady=5, padx=5, fill="x")

        ttk.Label(device_frame, text="Choose Camera:").pack(anchor="w", padx=5)

        self.device_combo = ttk.Combobox(device_frame, state="readonly")
        self.device_combo.pack(fill="x", padx=5)

        available_devices = self.list_video_devices()
        self.device_combo['values'] = [f"Camera {i}" for i in available_devices]
        self.device_combo.current(0)
        self.device_combo.bind("<<ComboboxSelected>>", self.change_camera)

    def list_video_devices(self, max_devices=10):
        available = []
        for i in range(max_devices):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available

    def change_camera(self, event=None):
        index = self.device_combo.current()
        self.selected_device_index.set(index)
        self.init_camera()

    def init_controls(self):
        focus_frame = ttk.LabelFrame(self.control_frame, text="Camera Controls")
        focus_frame.pack(pady=5, padx=5, fill="x")

        ttk.Label(focus_frame, text="Focus:").pack(pady=2)
        self.focus_slider = ttk.Scale(focus_frame, from_=0, to=255, orient="horizontal")
        self.focus_slider.set(0)
        self.focus_slider.pack(pady=2, padx=5, fill="x")

        self.autofocus_var = tk.BooleanVar(value=True)
        self.autofocus_check = ttk.Checkbutton(
            focus_frame, text="Autofocus", variable=self.autofocus_var, command=self.toggle_autofocus)
        self.autofocus_check.pack(pady=2)

        process_frame = ttk.LabelFrame(self.control_frame, text="Image Processing")
        process_frame.pack(pady=5, padx=5, fill="x")

        ttk.Label(process_frame, text="Brightness:").pack(pady=2)
        self.brightness_slider = ttk.Scale(process_frame, from_=0, to=100, orient="horizontal")
        self.brightness_slider.set(50)
        self.brightness_slider.pack(pady=2, padx=5, fill="x")

        ttk.Label(process_frame, text="Contrast:").pack(pady=2)
        self.contrast_slider = ttk.Scale(process_frame, from_=0, to=100, orient="horizontal")
        self.contrast_slider.set(50)
        self.contrast_slider.pack(pady=2, padx=5, fill="x")

    def init_treeview(self):
        self.tree = ttk.Treeview(self.info_frame, columns=("Time", "Barcode", "Type", "Deposit"), show="headings")
        for col in ["Time", "Barcode", "Type", "Deposit"]:
            self.tree.heading(col, text=col)
        self.tree.column("Time", width=150)
        self.tree.column("Barcode", width=200)
        self.tree.column("Type", width=100)
        self.tree.column("Deposit", width=100)
        self.tree.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.info_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
    def init_camera(self):
        if hasattr(self, 'cap') and self.cap and self.cap.isOpened():
            self.cap.release()
        device_index = self.selected_device_index.get()
        self.cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW if os.name == 'nt' else 0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.toggle_autofocus()

    def load_json(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                self.quantities = json.load(f)
        else:
            self.quantities = {}

    def save_json(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.quantities, f, indent=4)

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
        brightness = self.brightness_slider.get() / 50.0 - 1.0
        contrast = self.contrast_slider.get() / 50.0
        adjusted = cv2.convertScaleAbs(frame, alpha=contrast, beta=brightness * 127)
        gray = cv2.cvtColor(adjusted, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        return cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 11, 2)

    def update_preview(self):
        try:
            ret, frame = self.cap.read()
            if ret:
                if not self.autofocus_var.get():
                    self.cap.set(cv2.CAP_PROP_FOCUS, self.focus_slider.get())

                current_time = time.time()
                if current_time - self.last_process_time >= self.process_interval:
                    processed_frame = self.adjust_image(frame)
                    barcodes = decode(processed_frame) or decode(frame)
                    for barcode in barcodes:
                        barcode_data = barcode.data.decode('utf-8')
                        self.queue.put(barcode_data)
                    self.last_process_time = current_time

                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                img = Image.fromarray(cv2image)
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_label.imgtk = imgtk
                self.camera_label.configure(image=imgtk)
        except Exception as e:
            print(f"Error in video preview: {e}")

        self.window.after(10, self.update_preview)  # ~100 FPS preview

    def show_product_selection(self, barcode_data):
        if hasattr(self, 'product_win') and self.product_win.winfo_exists():
            return

        self.product_win = tk.Toplevel(self.window)
        self.product_win.title("Produktwahl")

        ttk.Label(self.product_win, text=f"Welches Produkt soll dem Barcode '{barcode_data}' zugeordnet werden?").pack(pady=5)

        selected_product = tk.StringVar()
        for prod in self.quantities:
            ttk.Radiobutton(self.product_win, text=prod, variable=selected_product, value=prod).pack(anchor='w')

        def confirm():
            prod = selected_product.get()
            if prod:
                self.quantities[prod] = self.quantities.get(prod, 0) + 1
                self.save_json()
                self.product_win.destroy()
            else:
                messagebox.showwarning("Keine Auswahl", "Bitte ein Produkt auswählen.")

        ttk.Button(self.product_win, text="Bestätigen", command=confirm).pack(pady=5)

    def process_queue(self):
        try:
            barcode_data = self.queue.get(timeout=0.1)
            now = datetime.now()

            timestamps = self.barcode_times.get(barcode_data, [])
            timestamps = [t for t in timestamps if now - t <= timedelta(seconds=5)]
            if len(timestamps) >= 3:
                return
            timestamps.append(now)
            self.barcode_times[barcode_data] = timestamps

            current_time = now.strftime("%Y-%m-%d %H:%M:%S")
            pfand_type = "EINWEG" if len(barcode_data) == 13 else "MEHRWEG" if len(barcode_data) == 8 else "DOSE"
            deposit = self.pfand_values.get(pfand_type, 0.00)

            self.tree.insert("", 0, values=(current_time, barcode_data, pfand_type, f"{deposit:.2f}"))

            if barcode_data not in self.prompted_barcodes:
                self.prompted_barcodes.add(barcode_data)
                self.window.after(0, self.show_product_selection, barcode_data)

        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error in queue processing: {e}")
        finally:
            self.window.after(100, self.process_queue)

    def on_closing(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.window.destroy()

if __name__ != "__main__":
    def launch_pfand_scanner():
        scanner_window = tk.Toplevel()
        PfandScanner(scanner_window, "µScan V2.2.2")

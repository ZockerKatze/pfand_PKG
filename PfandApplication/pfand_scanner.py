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

class PfandScanner:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)

        self.data_file = "quantities.json"
        self.load_json()

        self.barcode_times = {}
        self.prompted_barcodes = set()

        self.camera_frame = ttk.Frame(window)
        self.camera_frame.pack(side="left", padx=10, pady=5)

        self.control_frame = ttk.Frame(window)
        self.control_frame.pack(side="left", padx=10, pady=5, fill="y")

        self.info_frame = ttk.Frame(window)
        self.info_frame.pack(side="right", padx=10, pady=5, fill="both", expand=True)

        self.camera_label = ttk.Label(self.camera_frame)
        self.camera_label.pack()

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

        self.tree = ttk.Treeview(self.info_frame, columns=("Time", "Barcode", "Type", "Deposit"), show="headings")
        self.tree.heading("Time", text="Time")
        self.tree.heading("Barcode", text="Barcode")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Deposit", text="Deposit (€)")

        self.tree.column("Time", width=150)
        self.tree.column("Barcode", width=200)
        self.tree.column("Type", width=100)
        self.tree.column("Deposit", width=100)

        self.tree.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.info_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.cap.set(cv2.CAP_PROP_FOCUS, 0)

        self.queue = queue.Queue()

        self.pfand_values = {
            "EINWEG": 0.25,
            "MEHRWEG": 0.15,
            "DOSE": 0.25,
        }

        self.process_video()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queue()

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
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        return binary

    def process_video(self):
        ret, frame = self.cap.read()
        if ret:
            if not self.autofocus_var.get():
                self.cap.set(cv2.CAP_PROP_FOCUS, self.focus_slider.get())

            processed_frame = self.adjust_image(frame)
            barcodes = decode(processed_frame) or decode(frame)

            for barcode in barcodes:
                points = barcode.polygon
                if len(points) == 4:
                    pts = [(p.x, p.y) for p in points]
                    cv2.polylines(frame, [cv2.convexHull(cv2.UMat(cv2.Mat(pts))).get()], True, (0, 255, 0), 2)
                barcode_data = barcode.data.decode('utf-8')
                self.queue.put(barcode_data)

            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.imgtk = imgtk
            self.camera_label.configure(image=imgtk)

        self.window.after(10, self.process_video)

    def show_product_selection(self, barcode_data):
        if hasattr(self, 'product_win') and self.product_win.winfo_exists():
            return  # prevent multiple dialogs

        self.product_win = tk.Toplevel(self.window)
        self.product_win.title("Produktwahl")

        ttk.Label(self.product_win, text=f"Welches Produkt soll dem Barcode '{barcode_data}' zugeordnet werden?").pack(pady=5)

        selected_product = tk.StringVar()
        for prod in self.quantities:
            ttk.Radiobutton(self.product_win, text=prod, variable=selected_product, value=prod).pack(anchor='w')

        def confirm():
            prod = selected_product.get()
            if prod:
                self.quantities[prod] += 1
                self.save_json()
                self.product_win.destroy()
            else:
                messagebox.showwarning("Keine Auswahl", "Bitte ein Produkt auswählen.")

        ttk.Button(self.product_win, text="Bestätigen", command=confirm).pack(pady=5)

    def process_queue(self):
        try:
            while True:
                barcode_data = self.queue.get_nowait()
                now = datetime.now()

                if barcode_data in self.barcode_times:
                    timestamps = self.barcode_times[barcode_data]
                    timestamps = [t for t in timestamps if now - t <= timedelta(seconds=20)]
                    if len(timestamps) >= 10:
                        continue
                    timestamps.append(now)
                    self.barcode_times[barcode_data] = timestamps
                else:
                    self.barcode_times[barcode_data] = [now]

                current_time = now.strftime("%Y-%m-%d %H:%M:%S")
                if len(barcode_data) == 13:
                    pfand_type = "EINWEG"
                elif len(barcode_data) == 8:
                    pfand_type = "MEHRWEG"
                else:
                    pfand_type = "DOSE"
                deposit = self.pfand_values.get(pfand_type, 0.00)
                self.tree.insert("", 0, values=(current_time, barcode_data, pfand_type, f"{deposit:.2f}"))

                if barcode_data not in self.prompted_barcodes:
                    self.prompted_barcodes.add(barcode_data)
                    self.window.after(0, self.show_product_selection, barcode_data)

        except queue.Empty:
            pass
        finally:
            self.window.after(100, self.process_queue)

    def on_closing(self):
        if self.cap.isOpened():
            self.cap.release()
        self.window.destroy()

if __name__ != "__main__":
    def launch_pfand_scanner():
        scanner_window = tk.Toplevel()
        PfandScanner(scanner_window, "µScan V1.1.0")

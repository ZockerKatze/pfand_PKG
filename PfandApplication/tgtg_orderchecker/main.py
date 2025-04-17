import tkinter as tk
from io import BytesIO
from tkinter import messagebox, ttk, Menu
from datetime import datetime
import requests
from PIL import Image, ImageTk
from .key import *

class TGTGOrdersApp:
    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(self.parent, bg="#ffffff")
        self.frame.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill="both", expand=True)

        self.orders_tab = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.orders_tab, text="Bestellungen")

        self.log_tab = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.log_tab, text="Protokoll")

        self.log_text = tk.Text(self.log_tab, wrap=tk.WORD, height=15, font=("Arial", 10), bg="#f0f0f0")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

        self.order_frame = tk.Frame(self.orders_tab, bg="#ffffff")
        self.order_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.menu = Menu(self.parent)
        self.parent.config(menu=self.menu)
        self.filemenu = Menu(self.menu)
        self.menu.add_cascade(label="Datei", menu=self.filemenu)
        self.filemenu.add_command(label="Beenden", command=self.exit_applet)
        self.filemenu.add_command(label="Aktualisieren", command=self.display_orders)
        self.filemenu.add_command(label="Protokoll speichern", command=self.save_log)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Über", command=self.about)

        self.parent.after(1000, self.on_startup)

    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"{timestamp} - {message}\n")
        self.log_text.yview(tk.END)

    @staticmethod
    def format_time(iso_time):
        try:
            dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
            local_time = dt.astimezone()
            return local_time.strftime("%H:%M")
        except ValueError:
            return "Unbekannter Fehler!"

    def fetch_orders(self):
        self.log_message("[ INFO ]: Bestellungen werden abgerufen...")
        try:
            active_orders = client.get_active()
            if not isinstance(active_orders, dict) or "orders" not in active_orders:
                raise ValueError("Unerwartetes API-Antwortformat.")
            orders_list = active_orders.get("orders", [])
        except Exception as e:
            self.log_message(f"[ FEHLER ]: Fehler beim Abrufen aktiver Bestellungen: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Abrufen aktiver Bestellungen: {e}")
            return []

        orders_data = []
        for order in orders_list:
            try:
                order_info = {
                    "name": order.get("item_name", "Unbekannt"),
                    "store_name": order.get("store_name", "Unbekannt"),
                    "address": order.get("pickup_location", {}).get("address", {}).get("address_line", "Unbekannt"),
                    "quantity": order.get("quantity", 1),
                    "price": order.get("total_price", {}).get("minor_units", 0) / (10 ** order.get("total_price", {}).get("decimals", 2)),
                    "currency": order.get("total_price", {}).get("code", "Unbekannt"),
                    "payment_method": order.get("payment_method_display_name", "Unbekannt"),
                    "pickup_window": {
                        "start": self.format_time(order.get("pickup_interval", {}).get("start", "Unbekannt")),
                        "end": self.format_time(order.get("pickup_interval", {}).get("end", "Unbekannt"))
                    },
                    "image_url": order.get("item_cover_image", {}).get("current_url", "")
                }
                orders_data.append(order_info)
            except Exception as e:
                self.log_message(f"[ KRITISCHER FEHLER ]: Eine Bestellung wird übersprungen: {e}")
        return orders_data

    def display_orders(self):
        self.log_message("[ INFO ]: Bestellungen werden angezeigt...")
        orders = self.fetch_orders()
        if not orders:
            messagebox.showinfo("Info", "Keine aktiven Bestellungen gefunden.")
            self.log_message("[ FEHLER ]: Keine aktiven Bestellungen gefunden.")
            return

        for widget in self.order_frame.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(self.order_frame, bg="#ffffff")
        scroll_frame = tk.Frame(canvas, bg="#ffffff")
        scrollbar = tk.Scrollbar(self.order_frame, orient="vertical", command=canvas.yview)

        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        image_refs = []

        for order in orders:
            text = (f"{order['name']} - {order['store_name']}\n"
                    f"Adresse: {order['address']}\n"
                    f"Menge: {order['quantity']}\n"
                    f"Preis: {order['price']} {order['currency']}\n"
                    f"Zahlung: {order['payment_method']}\n"
                    f"Abholung: {order['pickup_window']['start']} bis {order['pickup_window']['end']}\n")

            label = tk.Label(scroll_frame, text=text, justify="left", padx=10, pady=5, anchor="w", font=("Arial", 10),
                             bg="#f0f0f0", relief="ridge")
            label.pack(fill="x", pady=5)

            if order["image_url"]:
                try:
                    response = requests.get(order["image_url"])
                    img_data = BytesIO(response.content)
                    img = Image.open(img_data)
                    img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(img)

                    img_label = tk.Label(scroll_frame, image=img_tk)
                    img_label.image = img_tk
                    image_refs.append(img_tk)
                    img_label.pack(pady=5)
                except Exception as e:
                    self.log_message(f"[ FEHLER ]: Bild konnte nicht geladen werden: {e}")

        scroll_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        def on_mouse_wheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

        canvas.bind_all("<MouseWheel>", on_mouse_wheel)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    def on_startup(self):
        self.log_message("[ INFO ]: Anwendung gestartet.")
        self.display_orders()

    def exit_applet(self):
        self.log_message("[ INFO ]: Anwendung wird beendet.")
        self.parent.quit()

    @staticmethod
    def about():
        messagebox.showinfo("Über", "TGTG OrderChecker PV2-PKG1\n PfandApplication ©")

    def save_log(self):
        try:
            log_content = self.log_text.get("1.0", tk.END)
            with open("protokoll_datei.log", "w") as log_file:
                log_file.write(log_content)
            self.log_message("[ INFO ]: Protokolldatei erfolgreich gespeichert.")
        except Exception as e:
            self.log_message(f"[ FEHLER ]: Fehler beim Speichern des Protokolls: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Speichern des Protokolls: {e}")

def start_tgtg(parent=None):
    new_window = tk.Toplevel(parent)
    new_window.title("TGTG Orders")
    new_window.geometry("500x600")

    app = TGTGOrdersApp(new_window)

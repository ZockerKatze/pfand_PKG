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
        self.notebook.add(self.orders_tab, text="Orders")
        
        self.log_tab = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.log_tab, text="Log")
        
        self.log_text = tk.Text(self.log_tab, wrap=tk.WORD, height=15, font=("Arial", 10), bg="#f0f0f0")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.order_frame = tk.Frame(self.orders_tab, bg="#ffffff")
        self.order_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.menu = Menu(self.parent)
        self.parent.config(menu=self.menu)
        self.filemenu = Menu(self.menu)
        self.menu.add_cascade(label="File", menu=self.filemenu)
        self.filemenu.add_command(label="Exit", command=self.exit_applet)
        self.filemenu.add_command(label="Refetch", command=self.display_orders)
        self.filemenu.add_command(label="Save Log", command=self.save_log)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="About", command=self.about)
        
        self.parent.after(1000, self.on_startup)
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"{timestamp} - {message}\n")
        self.log_text.yview(tk.END)
    
    def format_time(self, iso_time):
        try:
            dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
            local_time = dt.astimezone()
            return local_time.strftime("%H:%M")
        except ValueError:
            return "Unknown Error!"
    
    def fetch_orders(self):
        self.log_message("[ INFO ]: Fetching orders...")
        try:
            active_orders = client.get_active()
            if not isinstance(active_orders, dict) or "orders" not in active_orders:
                raise ValueError("Unexpected API response format.")
            orders_list = active_orders.get("orders", [])
        except Exception as e:
            self.log_message(f"[ ERROR ]: Error fetching active orders: {e}")
            messagebox.showerror("Error", f"Error fetching active orders: {e}")
            return []
        
        orders_data = []
        for order in orders_list:
            try:
                order_info = {
                    "name": order.get("item_name", "Unknown"),
                    "store_name": order.get("store_name", "Unknown"),
                    "address": order.get("pickup_location", {}).get("address", {}).get("address_line", "Unknown"),
                    "quantity": order.get("quantity", 1),
                    "price": order.get("total_price", {}).get("minor_units", 0) / (10 ** order.get("total_price", {}).get("decimals", 2)),
                    "currency": order.get("total_price", {}).get("code", "Unknown"),
                    "payment_method": order.get("payment_method_display_name", "Unknown"),
                    "pickup_window": {
                        "start": self.format_time(order.get("pickup_interval", {}).get("start", "Unknown")),
                        "end": self.format_time(order.get("pickup_interval", {}).get("end", "Unknown"))
                    },
                    "image_url": order.get("item_cover_image", {}).get("current_url", "")
                }
                orders_data.append(order_info)
            except Exception as e:
                self.log_message(f"[ FATAL ERROR ]: Skipping an order due to an error: {e}")
        return orders_data
    
    
    def display_orders(self):
        self.log_message("[ INFO ]: Displaying orders...")
        orders = self.fetch_orders()
        if not orders:
            messagebox.showinfo("Info", "No active orders found.")
            self.log_message("[ ERROR ]: No active orders found.")
            return

        # Clear existing widgets
        for widget in self.order_frame.winfo_children():
            widget.destroy()

        # Create a scrollable frame inside a Canvas
        canvas = tk.Canvas(self.order_frame, bg="#ffffff")
        scroll_frame = tk.Frame(canvas, bg="#ffffff")
        scrollbar = tk.Scrollbar(self.order_frame, orient="vertical", command=canvas.yview)

        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        # Store image references to prevent garbage collection
        image_refs = []

        for order in orders:
            text = (f"{order['name']} - {order['store_name']}\n"
                    f"Address: {order['address']}\n"
                    f"Quantity: {order['quantity']}\n"
                    f"Price: {order['price']} {order['currency']}\n"
                    f"Payment: {order['payment_method']}\n"
                    f"Pickup: {order['pickup_window']['start']} to {order['pickup_window']['end']}\n")

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
                    img_label.image = img_tk  # Store reference
                    image_refs.append(img_tk)  # Prevent garbage collection
                    img_label.pack(pady=5)
                except Exception as e:
                    self.log_message(f"[ ERROR ]: Failed to load image: {e}")

        # Update scroll region
        scroll_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        # Enable scrolling with the mouse wheel
        def on_mouse_wheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

        canvas.bind_all("<MouseWheel>", on_mouse_wheel)  # Windows & MacOS
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux Scroll Up
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))  # Linux Scroll Down
    
    def on_startup(self):
        self.log_message("[ INFO ]: Application started.")
        self.display_orders()
    
    def exit_applet(self):
        self.log_message("[ INFO ]: Exiting Applet")
        self.parent.quit()
    
    def about(self):
        messagebox.showinfo("About", "PythonTGTG Script for fetching Orders on Desktop")
    
    def save_log(self):
        try:
            log_content = self.log_text.get("1.0", tk.END)
            with open("log_file.log", "w") as log_file:
                log_file.write(log_content)
            self.log_message("[ INFO ]: Log file saved successfully.")
        except Exception as e:
            self.log_message(f"[ ERROR ]: Error saving log file: {e}")
            messagebox.showerror("Error", f"Error saving log file: {e}")

def start_tgtg(parent=None):
    new_window = tk.Toplevel(parent)  # Create a new window
    new_window.title("TGTG Bestellungen")
    new_window.geometry("500x600")

    # Start the TGTGOrdersApp inside this new window
    app = TGTGOrdersApp(new_window)


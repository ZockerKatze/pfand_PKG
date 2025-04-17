# ♻️ Pfandrechner – Python Package

**Version:** V.8.04.301-PKG1
**License:**[MIT]()

> ⚠️ **Note:** This package is based on the original [`pfand`](https://github.com/ZockerKatze/pfand) application, which has now been **archived**.
> This repo (`pfand_PKG`) continues the project in a modular and importable format, ideal for integration into your own Python workflows.

Welcome to the **Pfandrechner Package** – a modular and importable version of Austria’s beloved container deposit ("Pfand") calculator. This package allows developers to seamlessly integrate Pfand logic into their own Python projects.

---

## 📦 What’s Inside

This package retains the core functionalities of the original application, including:

* 🔢 **Deposit Calculator** – Compute the total value of returned bottles and cans.
* 🏆 **Achievements** – Monitor progress and unlock rewards for deposit milestones.
* 📜 **History & Exports** – Access past returns and export data.
* 📦 **TGTG Integration** – Connect with "Too Good To Go" orders (API key setup required).
* ⚙️ **Smart Updater** – Ensure the package stays updated with the latest features and fixes.

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ZockerKatze/pfand_PKG.git
cd pfand_PKG
```

### 2. Create and Activate a Virtual Environment (Recommended)

#### On macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

#### On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Launch or Integrate

You can now use the package by importing it into your own Python projects, or run the provided entry script if applicable:

```bash
python run.py
```

---

## 🧮 Usage

You have two options for counting:

* ✍️ **Manual Entry** – Input container numbers directly.
* 🔬 **µScan** – Utilize the enhanced scanner with barcode recognition powered by `pyzbar`.

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Commit your changes.
4. Submit a pull request for review.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE]() file for details.

---

Made with 💚 for recycling and a cleaner future.

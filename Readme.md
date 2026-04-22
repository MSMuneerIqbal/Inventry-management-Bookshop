# BABA BANGLES AND GENERAL STORE — POS & Inventory Management System

A full-featured **Point of Sale (POS) and Inventory Management System** built with Python and Flask. Designed to run as a native desktop application (no browser required) using PyWebView — perfect for small retail shops that need a fast, offline-capable POS without internet dependency.

> **Author:** Muneer Iqbal &nbsp;|&nbsp; **Email:** [muneeriqbal729@gmail.com](mailto:muneeriqbal729@gmail.com)

---

## Screenshots

| Point of Sale (POS) | Admin Dashboard |
|---|---|
| ![POS Screen](pos%20pic.png) | ![Admin Panel](admin%20picture.png) |

---

## Table of Contents

- [What Is This?](#what-is-this)
- [Who Can Use This?](#who-can-use-this)
- [Features](#features)
  - [Point of Sale (POS)](#point-of-sale-pos)
  - [Admin Panel](#admin-panel)
  - [Reports](#reports)
  - [Settings](#settings)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [Building the Desktop EXE](#building-the-desktop-exe)
- [Admin Login](#admin-login)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)

---

## What Is This?

This is a **desktop POS and inventory management system** built for small retail shops — originally developed for *BABA BANGLES AND GENERAL STORE*, Madina Bazar Dunyapur. It runs entirely offline on any Windows PC and opens in a native window (not a browser tab).

It handles the complete daily workflow of a retail shop:

- Cashier scans/searches products and adds them to a cart
- Applies per-item discounts at checkout
- Prints a thermal receipt automatically
- Admin tracks all sales, profit, stock levels, and generates Excel reports

All data is stored locally in a **SQLite database** — no internet, no server, no monthly fees.

---

## Who Can Use This?

This system is ideal for:

| Business Type | Why It Fits |
|---|---|
| General stores / kiryana shops | Tracks mixed inventory across many categories |
| Bangles & jewellery shops | Per-product low stock alerts, category filtering |
| Garment / textile shops | Product descriptions, category-wise stock reports |
| Stationery / bookshops | Fast search by name or description |
| Any small retail shop | Thermal printer support, offline-first, easy to use |

**Requirements on the shop PC:**
- Windows 10 or 11
- Python 3.10+ (for development mode) OR just the built `.exe` file
- A thermal receipt printer (80mm roll — standard in Pakistan)

---

## Features

### Point of Sale (POS)

![POS Screen](pos%20pic.png)

- **Product browsing** — grid view with category filter bar and search
- **Smart search** — searches both product name and description
- **Stock indicators** — green dot (in stock), yellow (low), red (out of stock)
- **Shopping cart** — add multiple items, adjust quantity per item
- **Per-item discount** — apply a rupee discount on any cart item
- **Checkout** — deducts stock, records sale, prints receipt
- **Thermal receipt** — auto-prints on 80mm paper with shop name, address, phone, itemised bill, discount, net total, and footer note
- **Return processing** — return a product by name, restocks quantity, logs as return

### Admin Panel

![Admin Panel](admin%20picture.png)

Accessible at `/admin` with password protection. Features a persistent sidebar with collapsible section groups (Products, Categories, Reports) that auto-expand for the current page.

**Three color themes** selectable from Settings:
- Classic Blue
- Crimson Gold
- Forest Green

#### Dashboard
- **Period quick-filter buttons** — Today / This Week / This Month / Custom Date Range
- **4 stat cards** — Total Sales, Total Profit, Items Sold, Low Stock count (for selected period)
- **4 overview cards** — Total Products, Categories, Out of Stock, Total Stock Value
- **Hot Selling Items** — top 10 products by quantity sold in the selected period (with gold/silver/bronze medals)
- **Stock Distribution** — category-wise progress bars showing product count and low-stock warnings

#### Products
- **All Products** — paginated table (50 per page) with inline search, stock status badge, low stock limit, price, purchase price, edit and delete buttons
- **Add Product** — name, description, category, quantity, sale price, purchase price, low stock alert limit
- **Edit Product** — same fields, tracks stock increases as Stock In entries automatically
- **Delete Product** — blocked if the product has any sale history (to protect accounting records)

#### Categories
- Add, edit, and delete product categories
- Delete is blocked if the category still has products

### Reports

All report pages show a **total record count**, support **pagination** (50 rows/page), and include an **Export Excel** button.

| Report | What It Shows |
|---|---|
| **Sales Report** | All transactions in a date range — revenue, profit, items sold, daily bar chart, full transaction table with discount and profit per line |
| **Stock In Report** | Every stock replenishment entry — date, product, category, quantity added, purchase value |
| **Stock Out Report** | All sold items (non-return sales) — date, product, quantity, sale price, discount, total value |
| **Stock Report** | Current stock snapshot by category with bar chart — filter by category or max stock level |
| **Low Stock Alert** | All products currently below their individual low stock limit — sorted by quantity ascending |

Every report exports to a formatted `.xlsx` Excel file named with the date range (e.g. `sales_2026-04-01_to_2026-04-23.xlsx`).

### Settings

- **Shop Identity** — shop name, address (shown on POS header and all bills)
- **Contact Information** — two contact persons with name and phone (printed on receipts)
- **Bill Footer Note** — custom message at the bottom of every receipt
- **Color Scheme** — visual card selector for Blue, Crimson, or Green admin theme
- **Live Bill Preview** — see how the receipt header and bill will look before saving

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask 3.1 |
| Database | SQLite 3 (via SQLAlchemy 2.0) |
| ORM | Flask-SQLAlchemy 3.1 |
| Desktop window | PyWebView (Chromium-based, no browser needed) |
| Frontend | Bootstrap 5.3, Font Awesome 6, Chart.js 4.4 |
| Excel export | Pandas 3.0 + openpyxl 3.1 |
| EXE packaging | PyInstaller |

---

## Project Structure

```
Inventry-management-Bookshop/
│
├── exe.py                        # Single-file application (all routes, models, logic)
├── run.py                        # Development entry point (python run.py)
├── requirements.txt              # Python dependencies
├── bookshop.db                   # SQLite database (auto-created on first run)
│
├── static/
│   ├── images/
│   │   └── logo.jpeg             # Shop logo (shown in header, admin sidebar, receipt)
│   └── css/
│       └── styles.css            # Minimal global CSS
│
└── templates/
    ├── home.html                 # POS product grid
    ├── cart.html                 # Shopping cart
    ├── receipt.html              # Thermal printer receipt (80mm)
    ├── return.html               # Product return form
    └── admin/
        ├── base.html             # Shared admin layout (sidebar, topbar, color theme)
        ├── login.html            # Admin login page
        ├── dashboard.html        # Dashboard with stats and charts
        ├── products.html         # All products (paginated + search)
        ├── add.html              # Add product form
        ├── update.html           # Edit product form
        ├── categories.html       # All categories
        ├── add_category.html     # Add category form
        ├── update_category.html  # Edit category form
        ├── sales.html            # Sales report + chart + export
        ├── stock_in.html         # Stock In report + export
        ├── stock_out.html        # Stock Out report + export
        ├── stock_report.html     # Stock by category + chart
        ├── lowstock.html         # Low stock alert + export
        └── settings.html        # Shop settings + color scheme
```

---

## Installation & Setup

### Step 1 — Install Python

Download and install **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/).

During installation, check **"Add Python to PATH"**.

### Step 2 — Get the Project

Clone or download this repository to your PC:

```cmd
git clone https://github.com/your-username/your-repo.git
cd Inventry-management-Bookshop
```

Or simply extract the ZIP to a folder like `C:\BabaBangles\`.

### Step 3 — Create a Virtual Environment

Open Command Prompt in the project folder:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

### Step 4 — Install Dependencies

```cmd
pip install -r requirements.txt
```

This installs:

| Package | Version | Purpose |
|---|---|---|
| Flask | 3.1.3 | Web framework |
| Flask-SQLAlchemy | 3.1.1 | Database ORM |
| SQLAlchemy | 2.0.49 | SQL engine |
| Werkzeug | 3.1.8 | WSGI utilities |
| Jinja2 | 3.1.6 | HTML templating |
| pandas | 3.0.2 | Excel data processing |
| openpyxl | 3.1.5 | Excel file writer |
| pywebview | latest | Native desktop window |
| pyinstaller | latest | EXE builder |

---

## Running the Application

### Development Mode (with browser, for testing)

```cmd
python run.py
```

Then open `http://127.0.0.1:5000` in your browser.

### Desktop App Mode (native window, no browser)

```cmd
python exe.py
```

This opens the application in its own native window using PyWebView — exactly how the final EXE will look and behave.

---

## Building the Desktop EXE

To distribute the application as a standalone `.exe` (no Python installation required on the target PC):

### Step 1 — Prepare the icon (optional)

Convert `static/images/logo.jpeg` to `bookshop.ico` using any online converter or:

```cmd
pip install pillow
python -c "from PIL import Image; img=Image.open('static/images/logo.jpeg'); img.save('bookshop.ico')"
```

### Step 2 — Build

```cmd
pyinstaller --onedir --windowed --icon=bookshop.ico ^
  --add-data="templates;templates" ^
  --add-data="static;static" ^
  --name=BabaBangles exe.py
```

### Step 3 — Run

The output is in `dist\BabaBangles\`. Double-click `BabaBangles.exe` to launch.

> **Important:** The database file (`bookshop.db`) is saved next to the `.exe`, not inside it — so your data is preserved when you update the application.

---

## Admin Login

| Field | Value |
|---|---|
| URL | `http://127.0.0.1:5000/admin` |
| Password | `admin@321` |

To change the password, edit line 454 in `exe.py`:
```python
if request.form['password'] == 'admin@321':
```

---

## Performance

This system is built to handle **millions of records** without slowdown:

- **8 database indexes** on all frequently queried columns (sale date, product ID, return flag, category, quantity, stock-in date)
- **Composite index** on `(sale_date, is_return)` — the most common filter combination
- **SQLite WAL mode** — allows concurrent reads while writing
- **64 MB page cache** + **256 MB memory-mapped I/O** configured at connection level
- **All dashboard stats computed in SQL** — zero Python loops over large tables
- **SQL GROUP BY** for all chart data and aggregations
- **Paginated tables** — 50 rows per page, never loads the full dataset into memory
- **Eager JOIN loading** — no N+1 queries on relationship traversal
- **Excel exports via `pd.read_sql`** — streams directly from SQLite, handles millions of rows without memory issues

---

## Troubleshooting

### "ModuleNotFoundError" on startup
Make sure the virtual environment is activated:
```cmd
.venv\Scripts\activate
python exe.py
```

### "Port 5000 already in use"
Another instance is running. Close it or restart the PC, then try again.

### Receipt does not auto-print
Your browser's popup blocker may have stopped the print dialog. Click "Print Receipt" manually, or allow popups from `127.0.0.1` in your browser settings. In the EXE version (PyWebView) this works automatically.

### Thermal printer cuts off text
Confirm your printer is set to **80mm paper width** in Windows printer settings. The receipt CSS uses `@page { size: 80mm auto }`.

### Cannot delete a product
Products with sale history cannot be deleted to protect accounting records. Instead, set the product's **quantity to 0** so it shows as "Out of Stock" on the POS.

### EXE crashes on start
Ensure the `templates` and `static` folders are in the same directory as the `.exe` (inside `dist\BabaBangles\`). Do not move the `.exe` out of its folder.

### Database not found after update
The `bookshop.db` file stays next to the `.exe`. If you replaced the `.exe` but moved the database, copy `bookshop.db` back into the same folder as `BabaBangles.exe`.

---

## License

This project was developed for **BABA BANGLES AND GENERAL STORE**, Madina Bazar Dunyapur. Free to use and modify for personal or small business purposes.

---

## Author

| | |
|---|---|
| **Name** | Muneer Iqbal |
| **Email** | [muneeriqbal729@gmail.com](mailto:muneeriqbal729@gmail.com) |

---

*Built with Python, Flask, and SQLite — runs entirely offline on any Windows PC.*

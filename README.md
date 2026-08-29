# Sweet Scoop 🍨

Sweet Scoop is a Flask-based artisanal ice cream shop web application for browsing products, placing orders, tracking deliveries, and managing the store from an admin dashboard.

## Features Overview

- **Customer Storefront**: Interactive menu with instant filtering by categories, search, and detailed product views.
- **Cart & Checkout**: Real-time cart offcanvas & dedicated page, customizable sizes, coupon validation (`SCOOP10`, `FIRST20`, `SUMMER15`), and order placement (COD / Card / UPI).
- **Order Tracking**: Order tracking system with real-time status timelines (`Pending` ➔ `Preparing` ➔ `Out for Delivery` ➔ `Delivered`).
- **Customer Accounts**: User registration, login, profile view, and order history receipts.
- **Admin Control Portal**:
  - Dashboard with sales revenue analytics, orders counter, and inventory stats.
  - Flavour Management (Add, Edit, Upload Image, and Delete flavours).
  - Order Management (Live status updates).
  - Customer Inquiry Messaging Inbox.
  - Admin Security Settings (Change Administrator Password).

## Project Structure

```text
Sweet Scoop/
├── .gitignore                           # Git ignore rules for virtual env, cache, and editor files
├── .venv/                               # Local Python virtual environment
├── app.py                               # Flask application: Models, routes, auth, seeding, APIs
├── README.md                            # Documentation & project structure guide
├── requirements.txt                     # Python dependencies
├── instance/
│   └── sweet_scoop.db                   # SQLite database (auto-created on first run)
├── static/                              # Static frontend assets
│   ├── css/
│   │   └── style.css                    # Main design system, typography, colors, animations
│   ├── images/
│   │   ├── uploads/                     # Admin uploaded flavour images
│   │   └── *.jpg                        # Core storefront flavour and hero visuals
│   └── js/
│       ├── admin.js                     # Admin dashboard AJAX interactions
│       ├── cart.js                      # Shopping cart management and checkout helpers
│       └── main.js                      # Storefront interactivity and menu filtering
├── templates/                           # Jinja2 HTML templates
│   ├── admin/
│   │   ├── change_password.html         # Admin password change page
│   │   ├── dashboard.html               # Admin dashboard & key metrics
│   │   ├── messages.html                # Customer contact inquiries
│   │   ├── orders.html                  # Order timeline & status management
│   │   └── products.html                # Product catalog inventory manager
│   ├── about.html                       # Brand story & store info
│   ├── base.html                        # Global layout, header navigation, cart offcanvas, footer
│   ├── cart.html                        # Dedicated cart page
│   ├── checkout.html                    # Checkout & address details form
│   ├── contact.html                     # Contact us inquiry form
│   ├── index.html                       # Landing page with hero, specials, and reviews
│   ├── login.html                       # User authentication sign-in
│   ├── menu.html                        # Complete interactive menu catalog
│   ├── order_success.html               # Order confirmation receipt
│   ├── product_detail.html              # Flavour detail & customer reviews
│   ├── profile.html                     # User profile & past order history
│   ├── register.html                    # Customer account registration
│   └── track.html                       # Real-time order tracker
└── tests/                               # Automated unit and integration tests
    ├── test_admin_change_password.py    # Test suite for admin password security
    └── test_admin_product_update.py     # Test suite for admin products & ordering
```

## Quickstart & Setup

### 1. Prerequisites
- Python 3.10+
- Terminal / PowerShell

### 2. Environment Setup
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Run the Application
```powershell
python app.py
```

Open `http://127.0.0.1:5000` in your web browser.

### Default Credentials
- **Admin Account**: `admin@sweetscoop.com` / `admin123`
- **Customer Account**: `customer@example.com` / `customer123`

### 4. Running Automated Tests
```powershell
python -m unittest discover -s tests
```

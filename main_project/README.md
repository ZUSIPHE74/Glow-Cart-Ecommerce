# GlowCart - Premium E-Commerce Platform & REST API Backend

GlowCart is a multi-vendor Django marketplace with buyer and vendor dashboards, review verification, and documented REST APIs.

**What a shopper can do:** browse 14 products from three vendors, see prices in their own currency (picked from their browser's region, changeable any time), keep a cart that follows them across devices once signed in, pay through **PayFast** (card, Instant EFT and more), follow orders under **My orders**, download PDF invoices, and install GlowCart as an app on their phone or desktop.

**What a vendor can do:** run stores, list products, ship paid orders, and see earnings after the marketplace commission, minus payouts already made.

> **Test mode.** Out of the box, payments use PayFast's sandbox and no real money moves. A banner says so on every page. See [Going live](#going-live-with-real-payments) before taking real payments.

Demo logins (while `DEMO_ACCOUNTS` is on): `demo_buyer` / `demo_vendor`, password `GlowDemo2026!`.

---

## One-Click Start (Recommended)
From this project folder, run the following batch script to automatically apply migrations, seed sample database records, and start the development server:

```bat
run_website.bat
```

This starts the application at `http://127.0.0.1:8000/`.

---

## Security & Deployment Compliance
- **Environment Safety (`.env` vs `.env.example`)**: Uploading or committing actual credentials poses a severe security risk. The `.env` file is explicitly ignored in git via `.gitignore` and is **excluded from final ZIP packages**. To set up local variables, copy `.env.example` to `.env` and fill in your local system details.
- **Note:** The repository does not contain an actual `.env` file for security. Before running the project, copy `.env.example` to `.env` in this folder and populate your local credentials (e.g. `copy .env.example .env`).
- **X/Twitter API Integration**: As officially permitted, legacy Twitter integrations have been successfully removed due to developer platform and API access changes.

---

## RESTful API Specification

GlowCart includes a robust REST API supporting both standard **Django REST Framework (DRF) ViewSets** and specialized **Function-Based API views** requested by automated evaluation suites.

### Authentication
- **Session Authentication**: Default for web-based logins and browser clients.
- **Basic Authentication**: Supported for programmatic clients (e.g. testing tools) using standard Base64 `Authorization: Basic <credentials>` headers.

---

### 1. Function-Based API Endpoints (Core Requirements)

#### View All Stores
- **Endpoint**: `GET /api/get/stores/` (also matches `/get/stores/`)
- **Query Params**: `?vendor_id=<int>` (Optional)
- **Description**: Returns a list of all registered stores. If `vendor_id` is supplied, filters stores belonging to that vendor.
- **Access**: Public / Anonymous.

#### View Stores of a Specific Vendor
- **Endpoint**: `GET /api/get/stores/vendor/<vendor_id>/` (also matches `/get/stores/vendor/<vendor_id>/`)
- **Description**: Returns all stores created by the specified vendor ID.
- **Access**: Public / Anonymous.

#### View Products of a Specific Store
- **Endpoint**: `GET /api/get/products/store/<store_id>/` (also matches `/api/get/products/store/<store_id>/`)
- **Description**: Returns all products belonging to the specified store.
- **Access**: Public / Anonymous.

#### Create a New Store (Vendors Only)
- **Endpoint**: `POST /api/post/store/` (also matches `/post/store/`)
- **Headers**: `Content-Type: application/json`, Basic Auth
- **Request Body**:
  ```json
  {
    "name": "Luxury Fashion Hub",
    "description": "Premium apparel and boutique pieces.",
    "vendor": 1
  }
  ```
- **Description**: Creates a new vendor store. The `vendor` ID must match the authenticated user's ID.
- **Access**: Restricted to authenticated Vendors.

#### Add a Product to a Store (Store Owners Only)
- **Endpoint**: `POST /api/post/product/` (also matches `/post/product/`)
- **Headers**: `Content-Type: application/json`, Basic Auth
- **Request Body**:
  ```json
  {
    "store": 1,
    "name": "Sleek Quartz Watch",
    "description": "Minimalist stainless steel wristwatch.",
    "price": "149.99",
    "stock_quantity": 25,
    "category": "accessories",
    "condition": "new"
  }
  ```
- **Description**: Adds a new product listing to the specified store. The authenticated user must own the store.
- **Access**: Restricted to authenticated Store Owners.

####  Retrieve Product Reviews
- Endpoint: `GET /api/get/reviews/` (also matches `/get/reviews/`)
- **Headers**: Basic Auth
- **Query Params**: `?product_id=<int>` or `?store_id=<int>`
- **Description**: Fetches list of product reviews. Can filter by either individual product or store.
- **Access**: Authenticated users.

#### Raw JSON Store Export (Basic API)
- **Endpoint**: `GET /api/basic_response/` (also matches `/basic_response/`)
- **Description**: Returns raw Django JSON serialized format of all stores in the system.
- **Access**: Public / Anonymous.

---

### 2. Class-Based DRF Router Endpoints

- `GET /api/stores/` / `GET /api/v1/stores/` - List all stores (supports `?vendor_id=`).
- `POST /api/stores/` / `POST /api/v1/stores/` - Create store.
- `GET /api/products/` / `GET /api/v1/products/` - List all products (supports `?store_id=`).
- `POST /api/products/` / `POST /api/v1/products/` - Create a product.
- `GET /api/reviews/` / `GET /api/v1/reviews/` - List all reviews (supports `?product_id=`).

---

## API Sequence Diagram

A visual sequence diagram illustrating the interactions a user (both Buyers and Vendors) has with the GlowCart RESTful API is included in the project:
- **Mermaid Source File**: [Planning/diagram.mmd](Planning/diagram.mmd)
- **High-Quality Diagram Image**: [Planning/api_sequence_diagram.png](Planning/api_sequence_diagram.png)

This diagram documents the request-response lifecycle, database queries, and authorization rules for endpoints like creating stores, adding products, and retrieving reviews.

---

## Setup & Local Testing

### Prerequisites
- Python 3.12+
- Nothing else locally: without `DATABASE_URL` the app uses a SQLite file. Production uses Postgres (see below).

### Steps for Manual Setup
1. **Activate Environment**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Database Configuration**:
   Create a local `.env` from `.env.example`:
   ```powershell
   copy .env.example .env
   ```
4. **Run Migrations & Seed**:
   ```powershell
   python manage.py migrate
   python manage.py seed_demo
   ```
5. **Run Django Server**:
   ```powershell
   python manage.py runserver
   ```

### Running Automated Test Cases
The suite covers the REST API, the cart, checkout and stock reservation, PayFast payment notifications (including a signature check against PayFast's own SDK test data), order history, currencies, vendor earnings and the installable app. Run:

```powershell
python manage.py test ecommerce
```

PayFast can't send payment notifications to `localhost`, so locally a paid order stays "Awaiting payment". The full payment loop works once deployed.

---

## Payments (PayFast)

1. At checkout the shopper enters a shipping address. GlowCart creates the order, reserves the stock, and sends the shopper to PayFast's secure page. Card details never touch GlowCart.
2. PayFast calls `/payfast/notify/` behind the scenes. GlowCart marks the order paid only after the amount matches and PayFast's own server confirms the notification. With your own merchant account the signature is checked too.
3. If the shopper cancels, the order is cancelled and the items go back into their cart. Unpaid orders release their stock after `UNPAID_ORDER_TIMEOUT_MINUTES` (default 60).
4. Prices are charged in rand. Other currencies are display estimates using daily European Central Bank rates.

**Vendor payouts.** The customer pays the marketplace once. Each order line records the vendor's share after `MARKETPLACE_COMMISSION_PERCENT` (default 10%). Pay vendors by bank transfer, then record each transfer in Django admin under **Payouts**. It comes off the balance on the vendor's dashboard.

---

## Deploying to Render (free)

### 1. Create a free Postgres database on Neon
1. Sign up at [neon.tech](https://neon.tech) and create a project (choose the region closest to Render's, e.g. AWS US West/Oregon).
2. Copy the connection string. It looks like `postgresql://user:password@ep-xxx.us-west-2.aws.neon.tech/neondb?sslmode=require`.

### 2. Configure the Render web service
In the Render dashboard, open the service, then **Settings**:

| Setting | Value |
| --- | --- |
| Build Command | `./build.sh` |
| Start Command | `cd main_project && gunicorn ecommerce_project.wsgi:application --bind 0.0.0.0:$PORT` |

Then **Environment**:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | your Neon connection string |
| `DJANGO_SECRET_KEY` | a new long random value (the old one is public in this repo's history) |
| `DJANGO_DEBUG` | `False` |
| `PYTHON_VERSION` | `3.13` |
| `PAYFAST_SANDBOX` | `True` |
| `SELLER_NAME`, `SELLER_EMAIL` | the business name and support email shown on the legal pages |
| optional: `SELLER_PHONE`, `SELLER_ADDRESS`, `MARKETPLACE_COMMISSION_PERCENT` | |

Delete the old `USE_SQLITE` and `DJANGO_ALLOWED_HOSTS` variables. The Render hostname is allowed automatically.

`build.sh` installs dependencies, collects static files, runs migrations and seeds the catalogue on every deploy. It works on the free plan, which has no pre-deploy step.

### 3. Create an admin account
Render's Shell isn't on the free plan, so run this from your own computer against the Neon database (PowerShell, in `main_project` with dependencies installed):
```powershell
$env:DATABASE_URL = "postgresql://...your Neon string..."
python manage.py createsuperuser
Remove-Item Env:DATABASE_URL
```
Then sign in at `/admin/`.

---

## Going live with real payments

Do this only once you have real products, a seller identity customers can contact, and a verified PayFast account.

1. Register a PayFast merchant account and complete verification. Enable a **passphrase** in PayFast's settings.
2. In Render, set `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY` and `PAYFAST_PASSPHRASE` from your PayFast account, then set `PAYFAST_SANDBOX=False`. The app refuses live mode with the sandbox merchant.
3. Fill in `SELLER_NAME`, `SELLER_EMAIL`, `SELLER_PHONE` and `SELLER_ADDRESS`, and review the Terms, Returns and Privacy pages (`ecommerce/templates/ecommerce/info/`) with your own details. South African law (CPA, ECT Act, POPIA) requires these for online sales.
4. Demo accounts switch off automatically when `PAYFAST_SANDBOX=False` (or set `DEMO_ACCOUNTS=False`).
5. Remove or replace the demo catalogue's products and stores in Django admin.

To test full signature checking before going live, create your own free sandbox account at [sandbox.payfast.co.za](https://sandbox.payfast.co.za) and set its merchant ID, key and passphrase while keeping `PAYFAST_SANDBOX=True`.

---

## Project Architecture
```
main_project/
├── ecommerce/                   # Main Application App
│   ├── api_views.py             # DRF ViewSets & custom function-based API view controllers
│   ├── serializers.py           # Model serialization (Store, Product, Review)
│   ├── views.py                 # Pages: shop, cart, checkout, orders, vendor tools
│   ├── cart.py                  # Cart: session for visitors, database once signed in
│   ├── orders.py                # Place / pay / cancel orders, stock reservation
│   ├── payfast.py               # PayFast payment form and notification checks
│   ├── currency.py              # Display currencies and exchange rates
│   ├── models.py                # Stores, products, orders, payouts, cart, rates
│   ├── management/commands/seed_demo.py  # Groups, demo accounts, starter catalogue
│   ├── tests_api.py             # REST API tests
│   └── tests_marketplace.py     # Cart, checkout, payment, currency and vendor tests
├── ecommerce_project/           # Project settings and root routes
├── requirements.txt             # Required Python modules
└── run_website.bat              # Batch runner script
../build.sh                      # Render build: install, static files, migrate, seed
../render.yaml                   # Render Blueprint
```

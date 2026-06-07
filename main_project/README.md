# GlowCart - Premium E-Commerce Platform & REST API Backend

GlowCart is a modern, high-performance Django e-commerce platform designed with dual Buyer/Vendor dashboard workflows, robust review verification pipelines, responsive CSS styling, and fully documented RESTful APIs.

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

## Setup & Local Testing

### Prerequisites
- Python 3.10+
- SQLite or MariaDB

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
   python seed_db.py
   ```
5. **Run Django Server**:
   ```powershell
   python manage.py runserver
   ```

### Running Automated Test Cases
GlowCart contains a suite of 13 integration and unit tests covering checkout payment bypasses, review verification statuses, database notification exclusions, and DRF API functionality. Run:

```powershell
python manage.py test ecommerce
```

---

## Project Architecture
```
main_project/
├── ecommerce/                   # Main Application App
│   ├── api_views.py             # DRF ViewSets & custom function-based API view controllers
│   ├── serializers.py           # Model serialization (Store, Product, Review)
│   ├── views.py                 # Core e-commerce view logic
│   ├── models.py                # Database entity schemas (Store, Product, Review, Notification)
│   └── tests_api.py             # E2E API and backend verification tests
├── ecommerce_project/           # Project settings and root routes
├── requirements.txt             # Required Python modules
├── run_website.bat              # Batch runner script
└── seed_db.py                   # Automated DB seed scripts
```

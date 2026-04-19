# GlowCart - Premium E-Commerce Platform

GlowCart is a Django e-commerce application featuring user registration/login, shopping cart, checkout, vendor stores, product reviews with verified purchase badges, and secure image uploads.

## Key Features
- **User Authentication**: Secure registration and login with security questions for password recovery
- **Vendor Stores**: Multi-vendor system allowing vendors to create and manage stores and products
- **Product Management**: Full CRUD operations with image uploads (both direct upload and URL)
- **Shopping Cart**: Session-based cart with persistent product management
- **Checkout & Orders**: Order placement with automatic invoice generation
- **Reviews System**: User reviews with automatic verification badge for verified purchases
- **Role-Based Access**: Separate permissions for Buyers and Vendors
- **Image Handling**: Proper image uploads with permanent storage and responsive display
- **Security**: PEP 8 compliant code, secure session handling, CSRF protection

## Important Setup Notes
- Database: MariaDB by default. SQLite only if `USE_SQLITE=1`
- Virtual environment required
- All dependencies in `requirements.txt` (including Pillow for image processing and xhtml2pdf for invoices)

## Correct Project Folder
Run Django commands from the folder that contains `manage.py`:

`<this project folder>`

## One-Click Start (Recommended)
From this project folder, run:

```bat
run_website.bat
```

This script:
1. Runs migrations
2. Starts Django on `127.0.0.1:8000`
3. Keeps the server running in that window

## Manual Setup

### 1. Open the Django folder
```powershell
cd <path-to-this-project-folder>
```

### 2. Create and activate virtual environment
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure MariaDB (default backend)
Create database:
```sql
CREATE DATABASE ecommerce_db;
```

Set environment variables (PowerShell example):
```powershell
$env:DB_NAME="ecommerce_db"
$env:DB_USER="root"
$env:DB_PASSWORD="your_password"
$env:DB_HOST="127.0.0.1"
$env:DB_PORT="3307"
```

### 5. Run migrations
```powershell
python manage.py migrate
```

### 6. Seed sample data (optional)
```powershell
python seed_db.py
```

### 7. Start the server
```powershell
python manage.py runserver 127.0.0.1:8000
```

## Key URLs
- Home/Browse Products: `http://127.0.0.1:8000/`
- Register: `http://127.0.0.1:8000/register/`
- Login: `http://127.0.0.1:8000/login/`
- Cart: `http://127.0.0.1:8000/cart/`
- Vendor Dashboard: `http://127.0.0.1:8000/vendor/dashboard/` (vendors only)

## Testing the Application

### As a Buyer
1. Register at `/register/` and select "Buyer" account type
2. Browse products on the home page
3. Add products to cart
4. Proceed to checkout
5. Leave reviews on purchased products (will be marked as "VERIFIED PURCHASE")

### As a Vendor
1. Register at `/register/` and select "Vendor" account type
2. Access vendor dashboard at `/vendor/dashboard/`
3. Create a store
4. Add products with images or image URLs
5. Manage product inventory and orders
6. Update order status (pending → shipped → delivered)

## Features Explained

### Verified Purchase Reviews
- Reviews can only be submitted after the product has been purchased
- Reviews are marked as verified for any non-cancelled purchase
- If an order is cancelled, the review status is updated accordingly
- The review form is available from the order confirmation workflow and on product pages after purchase

### Image Upload System
- Products can have images uploaded directly or linked via URL
- Uploaded images are stored permanently in `media/products/`
- Images display at full size without cropping (object-fit: contain)
- Image upload UI hides upload prompt after selection, shows preview with filename

### Security Features
- Session expires when browser closes
- CSRF protection on all forms
- Password recovery via security questions
- Role-based access control (Vendors vs Buyers)
- Secure cookie handling in production
- PEP 8 compliant code with proper spacing

## Troubleshooting

### "Can't reach this page"
The server is not running. Start it with `run_website.bat` or:
```powershell
python manage.py runserver 127.0.0.1:8000
```

### "ModuleNotFoundError: No module named 'ecommerce_project'"
You're in the wrong folder. Navigate to the folder containing `manage.py`:
```powershell
python manage.py check
python manage.py migrate
```

### Database connection refused
Ensure MariaDB is running on the configured port (default 3307):
- Check your DB_PORT environment variable
- Verify MariaDB credentials in settings.py
- Test connection manually if needed

### Images not showing
Ensure:
- Image files exist in `media/products/`
- Django static/media serving is enabled (`DEBUG=True` for development)
- File paths are correct in the database

### "No such table" errors
Run migrations:
```powershell
python manage.py migrate
```

## Admin Access
To access the Django admin at `http://127.0.0.1:8000/admin/`:
```powershell
python manage.py createsuperuser
```

## Environment Variables (Optional)
```powershell
# Database
$env:DB_NAME="ecommerce_db"
$env:DB_USER="root"
$env:DB_PASSWORD="your_password"
$env:DB_HOST="127.0.0.1"
$env:DB_PORT="3307"

# Django
$env:DJANGO_DEBUG="True"           # Set to False for production
$env:DJANGO_SECRET_KEY="your_key"  # Custom secret key
$env:DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1"

# SQLite fallback
$env:USE_SQLITE="1"  # Only use this for local testing
```

## Project Structure
```
ecommerce_project/
├── ecommerce/                   # Main app
│   ├── models.py                # Product, Order, Review, Store models
│   ├── views.py                 # All view logic
│   ├── forms.py                 # Registration, product, checkout forms
│   ├── urls.py                  # URL routing
│   ├── templates/ecommerce/     # HTML templates
│   │   ├── home.html            # Product listing
│   │   ├── product_detail.html  # Single product + reviews
│   │   ├── cart.html            # Shopping cart
│   │   ├── checkout.html        # Order confirmation
│   │   └── vendor/              # Vendor-only pages
│   └── migrations/              # Database migrations
├── ecommerce_project/           # Django config
│   ├── settings.py              # Database, security, apps config
│   ├── urls.py                  # Root URL config
│   └── wsgi.py                  # WSGI application
├── media/                       # User-uploaded files (images)
├── requirements.txt             # Python dependencies
├── manage.py                    # Django CLI
└── seed_db.py                   # Sample data script
```

## Code Standards
- Django and PEP 8 compliant
- Two blank lines between top-level classes and functions
- Proper permission decorators on restricted views
- Clean separation of concerns

## Production Deployment
Before deploying to production:
1. Set `DEBUG=False` in environment variables
2. Generate a new `SECRET_KEY` and set via environment
3. Configure `ALLOWED_HOSTS` appropriately
4. Use a production-grade database server
5. Collect static files: `python manage.py collectstatic`
6. Use a WSGI server (Gunicorn, uWSGI, etc.) instead of the development server
7. Enable SSL/TLS (HTTPS)


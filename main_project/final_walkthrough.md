# Final Walkthrough

This document summarizes the features and fixes implemented in the GlowCart e-commerce application.

## What is included
The application supports buyers, vendors, product management, orders, reviews, and image uploads. It is built with Django and includes the logic needed to handle user roles, secure form submission, and review verification.

## Features

### Product management
Vendors can create a store and add products. Each product can use an uploaded image or an image URL. Product availability updates automatically based on stock quantity, and products with no stock are hidden from the buyer listing.

### Shopping cart and checkout
A session-based shopping cart keeps products while the user browses. Buyers can update cart items, remove them, and proceed through checkout. Orders are created with status tracking, and stock is reduced after a successful purchase.

### Order management
Buyers can see their order history. Vendors can view orders that contain their products and update status from pending to shipped to delivered. Order status changes are tied to review verification.

### Reviews
Reviews can only be submitted after the product has been purchased. Reviews are marked as verified for any non-cancelled order. If an order is cancelled, the related reviews lose the verified label. Non-purchased reviews are still visible but marked as unverified.

### Authentication and authorization
Users can register as buyers or vendors. The registration flow includes required name fields and email validation. Security questions are available for password recovery. The application assigns users to Buyer or Vendor groups and protects vendor views with permission checks.

### Image handling
Images are stored in the `media/products/` directory. The upload interface hides the prompt after selection, shows a preview, and displays the file name below the image. Product images are displayed fully using `object-fit: contain` so they are not cropped.

### Code quality and security
The code is organized according to Django conventions and follows PEP 8 style guidelines. Forms use CSRF protection, permissions are enforced on restricted views, and the Django ORM protects against SQL injection.

## Environment and dependencies
The project uses Django 4.2+, Pillow for image uploads, and xhtml2pdf for invoice generation. MariaDB is the default database backend, with SQLite available as a fallback via `USE_SQLITE=1`.

## Recent fixes
- Fixed stock availability so products with quantity still show as available
- Updated image upload UX to remove confusing labels and show previews correctly
- Changed image display to use `object-fit: contain` so product images are not cropped
- Synchronized review verification when order status changes

## How to test key functionality

### Verified review workflow
1. Register as a buyer.
2. Purchase a product.
3. Leave a review for that product.
4. Confirm the review is labeled as a verified purchase.

### Vendor order flow
1. Register as a vendor.
2. Create a store and add a product.
3. Purchase that product as a buyer.
4. Update the order status in the vendor dashboard.
5. Confirm review verification updates accordingly.

### Image upload
1. Add a product with an uploaded image.
2. Confirm the upload prompt disappears after selecting an image.
3. Confirm the image preview appears and the product shows correctly on the home and product pages.

### Stock behavior
1. Create a product with positive stock.
2. Confirm it appears as available.
3. Reduce stock to zero.
4. Confirm it appears as out of stock and is removed from the buyer listing.

## Notes
This application is ready for final review. It includes the main features requested for vendor and buyer workflows, product management, review verification, and image handling.


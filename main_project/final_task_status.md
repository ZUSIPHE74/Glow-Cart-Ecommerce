# Project Task Summary

I completed the cleanup work by confirming that the SQLite database file was removed and by checking for any extra database files. The database configuration now works with MariaDB on port 3307.

User registration and group setup were verified. The project now supports both Buyer and Vendor roles, and the relevant views are protected by login and permission checks.

The shopping cart maintains data during navigation, and session expiration is configured so the cart clears when the browser closes.

The review system now distinguishes between verified and unverified reviews based on purchase history. The checkout process also generates invoices and handles email operations.

Documentation has been updated to include the README file and the dependency list in `requirements.txt`. These files reflect the current setup and the features implemented in the project.

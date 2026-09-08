# AR Drips

A Flask e-commerce website for an Indian streetwear store, with a branded customer storefront and a separately protected administrator workspace. Orders use cash on delivery; no online payment gateway is enabled.

## Features

- Browse and search products and categories without signing in.
- Add products directly from cards, with separate colour/size selection and quantities.
- Product galleries support front, back, side and size-chart images, including full-size viewing.
- Guest bags merge into customer accounts when signing in for checkout.
- COD checkout, order tracking, owner confirmation and stock-aware fulfilment.
- Separate `/admin/login` and dashboard for products, categories, orders, customers, inventory, coupon configuration, reviews, analytics and settings.
- Click-to-add sizes, automatic SKU generation and stock per size/colour.
- Product removal preserves historical orders and inventory while removing archived products from the catalogue.
- Server-side roles/permissions, CSRF, rate limiting, hashed passwords and revocable admin sessions.

## Technology

Python 3.13+ (tested locally with 3.14), Flask, Jinja templates, SQLAlchemy, MySQL, Flask-Migrate/Alembic, Flask-Login, Flask-WTF, Flask-Limiter, Pillow, CSS and vanilla JavaScript. Automated tests use an isolated SQLite database.

## Local setup on Windows

Install Python and a local MySQL server, then open a terminal in this project directory.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Run the copy command only on a fresh checkout: do not overwrite an existing `.env`.

1. Create a MySQL database named `ar_drips` and a dedicated database user with access to it.
2. Edit `.env` locally. Set `DATABASE_URL` to that user's MySQL connection URL. URL-encode special characters in credentials.
3. Generate a secret with `.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"` and put it in `SECRET_KEY`.
4. Keep `FLASK_CONFIG=development` and `SESSION_COOKIE_SECURE=false` for local HTTP.
5. Apply the migrations already included in this repository:

```powershell
.\.venv\Scripts\python.exe -m flask --app run.py db upgrade
```

Do **not** run `db init` or generate another initial migration: the project already includes its migration history.

For a new database only, create an administrator:

```powershell
.\.venv\Scripts\python.exe -m scripts.create_admin
```

This securely prompts for credentials. Existing administrators should keep their existing account. Optional starter categories can be created with `python -m scripts.seed_categories`, or directly in the dashboard.

Start the site:

```powershell
.\.venv\Scripts\python.exe run.py
```

- Storefront: http://127.0.0.1:5000/
- Administration: http://127.0.0.1:5000/admin/login

## Managing the store

Open **Admin > Products > Add product**, upload photos and save. In its editor, select size buttons, enter colour and stock per size, then click **Add sizes**. SKUs are automatic. Use **Admin > Categories > Add category** to create categories; change a product's Category field to move it.

Use 1200 x 1500 or 1080 x 1350 portrait product photos. Square size charts are supported without cropping. JPG/WEBP are recommended; PNG is accepted. Maximum 10 images per product and under 8 MB combined per upload. Aim for 200-500 KB per image.

Orders are initially Pending. Confirm them in admin, then mark shipped/delivered as appropriate. Record COD receipts only after verifying the payment. Cancellation before shipment restores stock. No live payment/refund processing is provided.

## Email and WhatsApp alerts

Alert configuration is optional for local shopping. Configure SMTP using the `MAIL_*` variables and owner recipients using `ORDER_ALERT_EMAIL` / `ORDER_ALERT_WHATSAPP`. Public confirmation links require `PUBLIC_BASE_URL`; WhatsApp delivery additionally requires a configured Meta Business API sender/template. A normal WhatsApp number alone cannot send automated API alerts.

Missing alert configuration does not erase a saved order. See [Store operations](STORE_OPERATIONS.md) for setup and retry details. Never put real credentials in tracked files.

## Files included in GitHub

Source code, templates, CSS/JavaScript, the logo, migrations, tests, scripts, documentation, configuration examples and uploaded JPG/PNG/WEBP product photographs are included by the Git rules. The photos are in `instance/uploads/products/` and keep their existing paths.

Excluded deliberately: `.env`, passwords/keys, `.venv`, generated caches, machine-specific files, logs, database dumps and local database files. These are not required source files and may contain private customer or authentication data.

**GitHub is not a database backup.** Your MySQL database contains products, category assignments, photo references, users, sizes, stock and orders. Photos alone do not recreate those records on a fresh checkout. Keep an encrypted/private MySQL backup outside Git and restore it separately when moving the existing store. A new database starts empty after migrations.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pip check
node --check app/static/js/app.js
node --check app/static/js/admin.js
```

The tests cover checkout, guest carts, stock, order lifecycle, admin sessions/permissions, image uploads, sizes, category management and product removal. They do not send live order alerts. Browser layout review is separate from server-side automated tests.

## Optional container files

Docker/Gunicorn/Nginx configuration is supplied as a starting point, not a verified hosting deployment. Docker requires explicit `DOCKER_DATABASE_URL`, `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD`; there are no usable default passwords. Database and uploads use persistent storage. `.dockerignore` prevents local secrets and environment files from being copied into the image. Hosting is outside the current project work.

## Current limitations

- Coupon configuration and review moderation exist in admin; customer coupon redemption/review submission are not wired into the storefront.
- Manual refunds are not processed or reconciled automatically.
- Automated public alert links and WhatsApp require external setup.
- Use production settings, HTTPS and a shared rate-limiter store before any real deployment; consider administrator MFA.

See [Admin workspace](ADMIN_WORKSPACE.md), [Store operations](STORE_OPERATIONS.md), [Local status](LOCAL_STATUS.md) and [Repository review](REPOSITORY_REVIEW.md).

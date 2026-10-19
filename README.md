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

Use 1200 x 1500 or 1080 x 1350 portrait product photos. Square size charts are supported without cropping. JPG/WEBP are recommended; PNG and MP4 video are accepted. Maximum 10 media files per product; photos up to 8 MB each, videos up to 25 MB each, and under 100 MB combined per upload. Aim for 200-500 KB per image.

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

For local Docker use, install and start Docker Desktop. Set the three Docker variables in `.env`; the database URL must use `db:3306` as its host and port, with the same password as `MYSQL_PASSWORD` (URL-encoded in the URL). Then run:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose logs --tail=100 web
```

Open http://localhost:8000. Compose sets Gunicorn to listen on all container interfaces, uses the mounted uploads directory, and runs the included database migrations before starting the web server. The Docker database is separate from your existing local MySQL database and initially contains no store records. For local HTTP keep `FLASK_CONFIG=development`. Before public hosting, configure production settings, HTTPS and shared rate-limit storage.

MySQL initialization passwords apply only to a new database volume; changing `.env` does not change passwords in an existing database. Keep `PUBLIC_BASE_URL` empty until you have a real public HTTPS address. Local shopping works without it, but owner notification links and their delivery remain unavailable until configured.

## Current limitations

- Coupon configuration and review moderation exist in admin; customer coupon redemption/review submission are not wired into the storefront.
- Manual refunds are not processed or reconciled automatically.
- Automated public alert links and WhatsApp require external setup.
- Use production settings, HTTPS and a shared rate-limiter store before any real deployment; consider administrator MFA.

See [Admin workspace](ADMIN_WORKSPACE.md), [Store operations](STORE_OPERATIONS.md), [Local status](LOCAL_STATUS.md) and [Repository review](REPOSITORY_REVIEW.md).


### Email password recovery

On `/admin/login`, choose **Forgot your password?**, enter the administrator's
account email, and open **Reset password** in the email. Enter and confirm a new
password (12-1024 characters), then sign in again. No terminal commands are needed.
The email link expires after 30 minutes and becomes invalid after the password
changes. Existing admin sessions are revoked. Customers use the same recovery
flow from `/auth/forgot-password`.

Configure `PUBLIC_BASE_URL=https://your-store-domain.com` together with the existing
`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`,
`MAIL_USE_TLS`, and `MAIL_USE_SSL` settings in `.env`, then restart the application.
For local development, `http://127.0.0.1:5000` is an example base URL; use the port
your server actually uses. A local URL only opens on the computer running the app.
Production reset emails require a configured HTTPS public URL. No database
migration or new dependency is required for this recovery flow.

The confirmation intentionally does not reveal whether an email has an account.
If no message arrives, check spam, SMTP settings and application logs for
`Password reset email could not be sent`. Do not share reset links or passwords.

## Product videos

Product uploads accept JPG/PNG/WEBP photos and MP4 videos, up to 10 files per product. Photos are limited to 8 MB each, videos to 25 MB each, and combined requests to 100 MB. MP4 containers must contain a video track; H.264 video with AAC audio is recommended for browser playback. Videos appear with playback controls below the product photo gallery. Photos remain the catalogue cover; add at least one photo for a cover image.

When deploying, update the existing server environment to `MAX_CONTENT_LENGTH=104857600`, set the active Nginx server's `client_max_body_size 100M;`, validate/reload Nginx, and restart the application. Existing environment values override the new default. No database migration is needed.

## Coming-soon pricing

In Add/Edit product, choose Coming soon and check **Price not announced yet** to leave pricing blank and hide it on the homepage, shop and product page. Uncheck it to announce a price. Other availability states still require a price. Existing products keep their prices visible. Apply the new migration with `python -m flask --app wsgi:app db upgrade` during deployment before starting the updated app.

Home/shop cards retain image hover/swipe behavior while their photo navigation and thumbnails are shown only on the product detail page.

## Customer account

Signed-in customers can open `/account/` from the header account icon. The dashboard shows total/in-progress/delivered order counts, the latest four orders, links to paginated order history and support, editable name/phone details, and a saved delivery address for future checkout. Existing order address snapshots are unchanged. Email is read-only; password reset uses the existing email reset flow. The default sign-in destination is the dashboard, while an explicit checkout destination is preserved. Account pages require authentication, changes require CSRF tokens, and private responses use no-store headers. This dashboard uses existing tables and needs no additional database migration.

## Worn by you

`/worn-by-you` is a public, paginated customer photo gallery. A signed-in customer can submit JPG/PNG/WEBP photos (up to 8 MB and 20 megapixels) only for an item from their own **Delivered** order. Product identity comes from the verified order item, never a customer-supplied product ID. Each purchased item allows up to five submissions. Customers give publication permission for their first name, caption and photo, can see their submission status, and can withdraw a photo at any time.

Photos start private and pending. Admin **Worn by you** uses the existing `reviews.manage` permission to approve or reject photos. Moderators must check that the photo depicts the purchased AURK product and is suitable for publication. Purchase verification alone does not identify what appears in a photo. Withdrawn photos cannot be republished by admin. Unapproved images are accessible only to their owner and an authenticated admin moderator.

Uploads are decoded and re-encoded to JPEG, resized to at most 1800 ? 2400, and have original metadata removed. Customer photos are stored under `UPLOAD_DIR/customer-photos` and excluded from Git. Keep this directory on persistent storage and include it in private backups. Do not configure a public static alias for the upload directory: serve images through the app's access checks. Photo responses use no-store headers.

Apply the new database migration before running this version: `python -m flask --app wsgi:app db upgrade`. The migration has been applied to the local database; AWS still needs it when deploying. No automatic customer emails are sent by this feature.

## Customer order email templates (preview stage)

Generate sample-only previews with `.\.venv\Scripts\python.exe -m scripts.preview_customer_emails` and open `instance/email-previews/index.html` in a browser. Preview output is private/ignored by Git. No real orders are read and no emails are sent.

`app/services/customer_email_templates.py` renders `order_received` and `order_confirmed` messages using the shared HTML/plain-text templates in `app/templates/emails/`. Each result provides a subject, HTML body, text body, AURK sender name, sender address and Reply-To address (both default to `support@aurk.in`). These are rendering metadata until integrated with the sending service; the existing SMTP sender is unchanged. The renderer accepts the saved order and its item snapshots, and requires a public HTTPS origin for the authenticated order link. It renders outside website context processors so scheduled sending can use it with an application context.

Next steps: review the samples, finish Brevo sender/domain verification, connect the sender and Reply-To headers, add durable customer notification events/retries, then test actual delivery, replies and email-client layouts. Customer order emails are not yet triggered automatically by this template-only change.

### Welcome email preview

The same preview command also generates `welcome.html`, `welcome.txt` and sample headers. The welcome email uses `no-reply@aurk.in` as the proposed unmonitored sender, and directs questions to `support@aurk.in`. It contains collection/account links and no password or verification claim. The intended trigger is a successfully committed new customer registration, once Brevo sending and the durable notification workflow are integrated. Failed or duplicate signups must not trigger it. This template change does not yet send welcome emails automatically.

## Brevo customer email automation

Welcome, order-received and order-confirmed events are now saved in `customer_emails` in the same transaction as the successful signup/order/status change. Default: `CUSTOMER_EMAILS_ENABLED=false`. No existing customers or orders are backfilled when enabled. Welcome uses `CUSTOMER_NOREPLY_EMAIL=no-reply@aurk.in`; order emails use `CUSTOMER_SUPPORT_EMAIL=support@aurk.in` as sender and Reply-To. The SMTP transport uses per-message sender/Reply-To overrides for these templates.

Use Brevo SMTP Login and an SMTP key (not your Hostinger password or a Brevo API key) in the private environment:

```dotenv
MAIL_SERVER=smtp-relay.brevo.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_FROM=support@aurk.in
PUBLIC_BASE_URL=https://aurk.in
CUSTOMER_SUPPORT_EMAIL=support@aurk.in
CUSTOMER_NOREPLY_EMAIL=no-reply@aurk.in
CUSTOMER_EMAILS_ENABLED=false
```

Keep `MAIL_USERNAME` and `MAIL_PASSWORD` private and out of Git. An explicit test sends sample data only, creates no order, and works with automation disabled:

```powershell
.\.venv\Scripts\python.exe -m flask --app wsgi:app send-email-test --to YOUR_CONTROLLED_INBOX --kind welcome
.\.venv\Scripts\python.exe -m flask --app wsgi:app send-email-test --to YOUR_CONTROLLED_INBOX --kind order_received
```

After testing delivery and order-email replies, set `CUSTOMER_EMAILS_ENABLED=true` and restart the application. From the project directory run `python -m flask --app wsgi:app send-customer-emails`. During deployment, apply migrations before restarting the updated app. Schedule this command once per minute with the same production environment; prefer a systemd timer/service under the app user on EC2 so overlapping executions are avoided. Existing `send-order-alerts` handles owner alerts separately.

The worker processes up to 50 due emails by default, uses row locking and event uniqueness, backs off failed attempts, and stops automatically after five attempts. Repeated successful processing does not intentionally resend a submitted email. Inactive accounts and unsent notifications for cancelled orders are skipped. A crash after SMTP accepts a message but before the database commit can still cause a duplicate; SMTP acceptance is not proof of inbox delivery. Failed sends do not roll back a saved order or signup. Inspect queue status/attempts privately; never publish recipients or credentials in diagnostic output. Once credentials/configuration are fixed, an operator can reset an exhausted failed record's attempts/due time for an intentional retry.

Local integration is implemented; live SMTP delivery, scheduling and AWS deployment must still be verified. Earlier template-only notes above describe the previous stage.

### Email logo and dark theme

Customer HTML emails use a black background, white text and the supplied AURK logo in `app/static/images/brand/email-logo.png`. Only transparent margins were removed from the original; visible artwork was preserved. The SMTP transport attaches this PNG with Content-ID `aurk-logo` and the templates reference `cid:aurk-logo`. Local preview generation copies the logo alongside the HTML and substitutes a relative URL, so previews can be opened without a server. Regenerate previews after changing source templates. Plain-text emails retain their text-only fallback.

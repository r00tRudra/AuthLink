# AuthLink

AuthLink is a FastAPI-based URL shortener with email/password authentication.
Users can register, log in, create short links, list their own links, delete
their links, and redirect short codes back to the original destination.

## What it does

- Registers users with a unique email address.
- Authenticates users with JWT access tokens.
- Creates short URLs that map a generated 7-character code to a destination.
- Lists the URLs owned by the authenticated user.
- Deletes owned URLs.
- Redirects anyone who visits a short code to the original URL.
- Tracks click counts for each short link.

## Tech Stack

- FastAPI
- SQLAlchemy 2.x with async sessions
- Alembic for database migrations
- PostgreSQL in normal use, SQLite is used by the test suite
- JWT authentication with python-jose
- Password hashing with passlib and bcrypt

## Project Structure

- [app/main.py](app/main.py) creates the FastAPI app and registers routers.
- [app/auth](app/auth) contains authentication routes and service logic.
- [app/urls](app/urls) contains URL creation, listing, deletion, and redirect logic.
- [app/models.py](app/models.py) defines the `User` and `URL` database models.
- [app/schemas.py](app/schemas.py) defines request and response schemas.
- [alembic/](alembic) stores migrations and Alembic configuration.
- [tests/test_api.py](tests/test_api.py) covers the main end-to-end API flow.

## Requirements

- Python 3.11 or newer is recommended.
- A PostgreSQL database for local development.
- A `.env` file with the required environment variables.

Note: this stack expects `bcrypt<5` together with `passlib==1.7.4`.

## Environment Variables

Create a `.env` file in the project root with values like these:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/authlink
SECRET_KEY=change-me-to-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
BASE_URL=http://localhost:8000
```

- `DATABASE_URL` is required and must point to the database used by SQLAlchemy.
- `SECRET_KEY` is required and is used to sign JWT access tokens.
- `ALGORITHM` defaults to `HS256`.
- `ACCESS_TOKEN_EXPIRE_MINUTES` defaults to `30`.
- `BASE_URL` defaults to `http://localhost:8000`.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the initial migration:

```bash
alembic upgrade head
```

Start the API server:

```bash
uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000`.

## API Overview

### Authentication

- `POST /auth/register` creates a new user.
- `POST /auth/login` returns a bearer token.

Register example:

```bash
curl -X POST http://localhost:8000/auth/register \
	-H "Content-Type: application/json" \
	-d '{"email":"user@example.com","password":"StrongPass123!"}'
```

Login example:

```bash
curl -X POST http://localhost:8000/auth/login \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-d "username=user@example.com&password=StrongPass123!"
```

### URLs

- `POST /urls` creates a short URL for the authenticated user.
- `GET /urls/me` lists the authenticated user's URLs.
- `DELETE /urls/{url_id}` deletes one of the authenticated user's URLs.
- `GET /{short_code}` redirects to the original URL.

Create a short URL:

```bash
curl -X POST http://localhost:8000/urls \
	-H "Authorization: Bearer <access_token>" \
	-H "Content-Type: application/json" \
	-d '{"original_url":"https://example.com/articles/123"}'
```

List your URLs:

```bash
curl http://localhost:8000/urls/me \
	-H "Authorization: Bearer <access_token>"
```

Delete a URL:

```bash
curl -X DELETE http://localhost:8000/urls/<url_id> \
	-H "Authorization: Bearer <access_token>"
```

## Behavior Notes

- Short codes are generated with 7 alphanumeric characters.
- The service retries code generation if a collision occurs.
- Redirects use HTTP 307 Temporary Redirect.
- Click counts are incremented every time a short link is visited.
- Only the owner of a URL can delete it.

## Testing

Run the test suite with:

```bash
pytest -q
```

The included integration test uses SQLite and exercises registration, login,
short-link creation, listing, redirecting, click tracking, and deletion.
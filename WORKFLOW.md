# AuthLink Workflow

This document explains how requests move through the main files and functions in
AuthLink.

## High-Level Flow

1. `app/main.py` creates the FastAPI app.
2. `app/main.py` registers the auth router, URL router, and redirect router.
3. Each route depends on `app/database.py` for an async SQLAlchemy session.
4. Protected routes use `app/auth/dependencies.py` to resolve the current user
   from the JWT bearer token.
5. Route handlers call the service layer in `app/auth/service.py` and
   `app/urls/service.py`.
6. The service layer reads and writes `app/models.py` records through SQLAlchemy.
7. Request and response shapes come from `app/schemas.py`.

## Flow Diagram

```mermaid
flowchart TD
    Client[Client / Browser / API consumer] --> Main[app/main.py\nFastAPI app + router registration]

    Main --> AuthRouter[app/auth/router.py\n/auth/register\n/auth/login]
    Main --> UrlRouter[app/urls/router.py\n/urls/*]
    Main --> RedirectRouter[app/urls/router.py\n/{short_code}]

    AuthRouter --> AuthSchemas[app/schemas.py\nUserCreate, UserRead, TokenResponse]
    UrlRouter --> UrlSchemas[app/schemas.py\nURLCreate, URLRead]
    RedirectRouter --> UrlSchemas

    AuthRouter --> DbSession[app/database.py\nget_db()]
    UrlRouter --> DbSession
    RedirectRouter --> DbSession

    AuthRouter --> AuthService[app/auth/service.py\nregister_user()\nlogin_user()]
    UrlRouter --> AuthDeps[app/auth/dependencies.py\nget_current_user()]
    UrlRouter --> UrlService[app/urls/service.py\ncreate_short_url()\nlist_user_urls()\ndelete_url()]
    RedirectRouter --> UrlService[app/urls/service.py\nredirect_url()]

    AuthDeps --> AuthService
    AuthDeps --> ModelsUser[app/models.py\nUser]

    AuthService --> ModelsUser
    UrlService --> ModelsUser
    UrlService --> ModelsURL[app/models.py\nURL]

    AuthService --> JWT[JWT access token]
    AuthDeps --> JWT
    UrlService --> Redirect[HTTP 307 redirect]

    ModelsUser --> Database[(Database)]
    ModelsURL --> Database

    Database --> Tests[tests/test_api.py\nend-to-end API flow]

    classDef file fill:#f7f7f7,stroke:#777,stroke-width:1px,color:#111;
    classDef data fill:#eef7ff,stroke:#4a79a8,stroke-width:1px,color:#111;
    class Client,Main,AuthRouter,UrlRouter,RedirectRouter,AuthSchemas,UrlSchemas,DbSession,AuthService,UrlService,AuthDeps,ModelsUser,ModelsURL,JWT,Redirect,Tests file;
    class Database data;
```

## Auth Workflow

### Register

- `app/auth/router.py::register()` receives `UserCreate`.
- It calls `app/auth/service.py::register_user()`.
- `register_user()` checks for an existing user, hashes the password, and saves
  a new `User` row.
- The route returns `UserRead`.

### Login

- `app/auth/router.py::login()` receives form data through
  `OAuth2PasswordRequestForm`.
- It calls `app/auth/service.py::login_user()`.
- `login_user()` verifies the password, creates a JWT with the user id in the
  `sub` claim, and returns the token string.
- The route wraps the token in `TokenResponse`.

### Protected Requests

- `app/auth/dependencies.py::get_current_user()` reads the bearer token.
- It decodes the JWT and loads the `User` from the database.
- If token validation fails, the request gets a 401 response.

## URL Workflow

### Create a Short URL

- `app/urls/router.py::create_url()` receives `URLCreate`.
- It depends on `get_current_user()` so only authenticated users can create
  links.
- It calls `app/urls/service.py::create_short_url()`.
- `create_short_url()` generates a 7-character code, stores a `URL` row, and
  retries on collisions.

### List Owned URLs

- `app/urls/router.py::get_my_urls()` depends on `get_current_user()`.
- It calls `app/urls/service.py::list_user_urls()`.
- The service returns the authenticated user's URLs ordered by newest first.

### Delete a URL

- `app/urls/router.py::remove_url()` depends on `get_current_user()`.
- It calls `app/urls/service.py::delete_url()`.
- The service verifies ownership before deleting the row.

### Redirect a Short Code

- `app/urls/router.py::redirect_to_original_url()` handles `/{short_code}`.
- It calls `app/urls/service.py::redirect_url()`.
- The service looks up the `URL`, increments `click_count`, and returns the
  original destination.
- The route sends a `307 Temporary Redirect` response.

## Data Model Role

- `app/models.py::User` stores the account identity and hashed password.
- `app/models.py::URL` stores the short code, original URL, click count, and
  owner relationship.
- `app/schemas.py` defines the API payloads that wrap those models at the edge
  of the application.

## Testing Path

The integration test in `tests/test_api.py` follows the same workflow end to
end:

1. Register a user.
2. Log in and capture the access token.
3. Create a short URL.
4. List the user's URLs.
5. Visit the short code and verify the redirect plus click count.
6. Delete the URL and confirm the short code no longer resolves.

This test is the best reference for understanding how the modules interact in
practice.
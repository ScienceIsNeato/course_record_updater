# Email delivery stack

This page describes how LoopCloser sends transactional mail across different environments and what happens when the primary provider fails.

## Environment -> provider mapping

| Environment        | `ENV` value                      | Provider used                            | Purpose                                                                         |
| ------------------ | -------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------- |
| Production         | `production`                     | **Brevo** (`EMAIL_PROVIDER=brevo`)       | Real recipients, Brevo delivers to actual inboxes and tracks deliverability.    |
| Dev (deployed)     | `development`                    | **Brevo** (via secret `brevo-api-key`)   | Real email delivery on dev.loopcloser.io for testing invitation/reminder flows. |
| Local development  | `development`                    | **Brevo** (from `.envrc`)                | Local testing with real email delivery using personal Brevo key.                |
| Staging            | `staging`                        | **Brevo** (via secret `brevo-api-key`)   | Real email delivery for staging validation.                                     |
| Testing / E2E / CI | `test`, `e2e`, or `TESTING=true` | **Ethereal** (`EMAIL_PROVIDER=ethereal`) | Fake SMTP for automated tests - no real emails sent.                            |

Brevo and Ethereal share the same `EmailService` API surface, so the rest of the application doesn't care which provider is in use.

## Runtime fallback behavior

- When the Brevo provider returns `False` (e.g., HTTP 401/429 due to unauthorized IP or rate limit), the service logs the failure and, when the app is not in `production`, automatically retries by creating an Ethereal provider instance.
- The invitation APIs still report a delivery failure (`INVITATION_CREATED_EMAIL_FAILED_MSG`) so operators are aware the real email never went out, even though a duplicate copy landed in Ethereal for debugging.
- This fallback prevents local development and staging from crashing during Brevo outages while still highlighting the need to resolve the production delivery issue.

## How to switch providers manually

1. Create a `.env` override with `EMAIL_PROVIDER=ethereal` and the Ethereal credentials (`ETHEREAL_USER`, `ETHEREAL_PASS`, etc.) when you want to run locally without Brevo.
2. Use `EMAIL_PROVIDER=brevo` plus valid `BREVO_API_KEY` to send real emails.
3. Tests already set `TESTING=true`, so they automatically pick Ethereal via the factory logic—no additional configuration is required.

## Key layers

1. `EmailService` (`src/services/email_service.py`): central API for sending verification, reset, and invitation emails. It enforces protected-domain checks, picks the provider via `create_email_provider`, and handles fallback logging.
2. Provider factory (`src/email_providers/factory.py`): chooses Brevo or Ethereal based on `EMAIL_PROVIDER`, `ENV`, and `TESTING` flags. All configuration is pulled from environment variables.
3. Provider implementations (`src/email_providers/brevo_provider.py` and `src/email_providers/ethereal_provider.py`): handle the actual HTTP/SMTP calls.

Because the factory abstracts the provider selection, adding a third provider (e.g., SendGrid) only requires a new adapter and a small change in the factory; the rest of the stack remains untouched.

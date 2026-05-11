# Subscription Management Design

## Goal

Add monthly subscription management for image generation. Administrators define plans, users default to a Free plan, paid ZPAY orders activate subscriptions, and image generation is blocked with a plan prompt when the user's daily or monthly image quota is insufficient.

## Product Rules

- Plans are monthly subscriptions.
- Each plan has two image quotas:
  - `dailyImageLimit`
  - `monthlyImageLimit`
- Image usage is charged by generated image count. If the user requests 4 images, the system consumes 4 quota units.
- Users default to the Free plan.
- The Free plan is stored in the database so admins can edit its limits.
- The backend keeps a minimal fallback Free plan if the database plan is missing or disabled.
- If either daily or monthly remaining quota is lower than the requested image count, the backend rejects generation with a structured subscription-limit response.
- The frontend shows a plan subscription prompt when it receives that limit response.

## Data Model

### `subscription_plans`

Stores administrator-managed plans.

- `id`
- `code`
- `name`
- `description`
- `price_cents`
- `daily_image_limit`
- `monthly_image_limit`
- `is_active`
- `is_default`
- `sort_order`
- `created_at`
- `updated_at`

Rules:

- `code` is unique.
- Exactly one default plan should be active in normal operation.
- The seed/default Free plan uses `code = "free"`, `price_cents = 0`.

### `user_subscriptions`

Stores a user's current subscription period.

- `id`
- `user_id`
- `plan_id`
- `status`
- `starts_at`
- `ends_at`
- `created_at`
- `updated_at`

Rules:

- Active subscription means `status = "active"` and current time is inside `[starts_at, ends_at)`.
- If no active row exists, the service returns the active default Free plan without requiring a row.
- Paid subscriptions created from ZPAY last one calendar month from activation.

### `image_usage_events`

Stores successful image quota consumption.

- `id`
- `user_id`
- `subscription_id`
- `plan_id`
- `image_count`
- `source`
- `created_at`

Rules:

- Write usage only after image generation succeeds.
- Aggregate usage by user and date/month in the user's subscription period.
- For now, use UTC day/month boundaries to match backend timestamps.

### `payment_orders`

Extend existing ZPAY payment orders:

- `plan_id`
- `order_kind`

Rules:

- Subscription orders use `order_kind = "subscription"`.
- On successful ZPAY notify, the payment service marks the order paid and activates the selected plan.

## Backend Flow

### Read plans

- `GET /api/subscription/plans`
  - Authenticated users can list active plans for purchase prompts.
- `GET /api/admin/subscription/plans`
  - Admins can list all plans.

### Manage plans

- `POST /api/admin/subscription/plans`
- `PATCH /api/admin/subscription/plans/{plan_id}`

Admin validation:

- Name required.
- Price cannot be negative.
- Daily and monthly limits must be positive integers.
- Daily limit cannot exceed monthly limit.
- Free/default plan can be edited but should not be accidentally removed in the first implementation.

### Create subscription payment

- `POST /api/payments/zpay/subscription-orders`
  - Body: `{ "planId": "..." , "payType": "alipay" }`
  - Backend loads the plan and uses its price/name to create the ZPAY order.
  - Free plans do not require payment; selecting Free switches the user to Free directly.

### Payment notify

- Existing `GET|POST /api/payments/zpay/notify` verifies the callback.
- When a paid order has `order_kind = "subscription"` and `plan_id`, the backend activates that user's subscription.
- Activation deactivates prior active paid rows by ending them at the activation time, then inserts a new active row.

### Image quota enforcement

In `POST /api/images/generate`:

1. Validate image request and compute requested image count.
2. Load the user's current entitlement.
3. If daily or monthly quota is insufficient, return `402` with:
   - `errorCode = "SUBSCRIPTION_LIMIT_REACHED"`
   - current plan
   - usage summary
   - active purchasable plans
4. If quota is sufficient, generate images.
5. After successful generation, record an `image_usage_events` row with the actual generated image count.

## Frontend Flow

### Admin plan management

Add an admin page under `/admin/subscriptions`.

Controls:

- Plan list.
- Create/edit plan form.
- Active toggle.
- Default plan marker.
- Daily/monthly image limit fields.
- Price field.

### User billing page

Change `/billing` to load active plans from the backend instead of hardcoded plans.

Selecting a paid plan:

- Calls `POST /api/payments/zpay/subscription-orders`.
- Redirects to the returned ZPAY payment URL.

Selecting Free:

- Calls the same endpoint.
- Backend returns an activated Free subscription or current Free entitlement without a payment URL.

### Quota prompt

When image generation receives `SUBSCRIPTION_LIMIT_REACHED`, the product workbench shows a modal with:

- Current plan name.
- Today's remaining images.
- This month's remaining images.
- Active paid plan options.
- Button to go to `/billing`.

## Testing Strategy

Backend:

- Model and migration shape tests.
- Plan repository/service tests.
- Entitlement and usage aggregation tests.
- Payment order activation tests.
- Image generation quota success and failure route tests.

Frontend:

- Source tests for admin subscription page and API helper.
- Source tests that `/billing` loads plans from API.
- Source tests that product workbench handles `SUBSCRIPTION_LIMIT_REACHED`.

Verification:

- `backend/.venv/Scripts/python -m pytest backend/tests -q`
- `npm test`
- `npm run lint`
- `npm run build`


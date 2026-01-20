# Demo Android App Specification

## Purpose
This document specifies the minimal demo Android app needed for TestRun AI demonstrations.
The app should have predictable UI elements with stable IDs for DroidRun automation.

## App Details
- **Package Name**: `com.testrunai.demoapp`
- **App Name**: Demo Shop
- **Target SDK**: Android 13 (API 33)
- **Min SDK**: Android 10 (API 29)

---

## Screens

### Screen 1: Login
Simple login screen with email/password fields.

| Element | Type | Resource ID | Content Description |
|---------|------|-------------|---------------------|
| Logo | ImageView | `@+id/logo` | "Demo Shop Logo" |
| Email Field | EditText | `@+id/email_field` | "Email address" |
| Password Field | EditText | `@+id/password_field` | "Password" |
| Login Button | Button | `@+id/login_button` | "Login" |
| Sign Up Link | TextView | `@+id/signup_link` | "Sign up" |

**Layout**: Centered vertically, 16dp padding

---

### Screen 2: Home
Dashboard after login with navigation options.

| Element | Type | Resource ID | Content Description |
|---------|------|-------------|---------------------|
| Welcome Text | TextView | `@+id/welcome_text` | "Welcome, User!" |
| Products Button | Button | `@+id/products_button` | "Browse Products" |
| Cart Button | Button | `@+id/cart_button` | "View Cart" |
| Profile Button | Button | `@+id/profile_button` | "My Profile" |
| Logout Button | Button | `@+id/logout_button` | "Logout" |

**Layout**: Vertical stack with 12dp spacing

---

### Screen 3: Products
List of dummy products.

| Element | Type | Resource ID | Content Description |
|---------|------|-------------|---------------------|
| Title | TextView | `@+id/products_title` | "Products" |
| Product 1 | CardView | `@+id/product_1` | "Widget A - $19.99" |
| Product 2 | CardView | `@+id/product_2` | "Widget B - $29.99" |
| Product 3 | CardView | `@+id/product_3` | "Widget C - $39.99" |
| Back Button | ImageButton | `@+id/back_button` | "Go back" |

**Product Card Elements** (inside each CardView):
- `product_image` - Product image
- `product_name` - Product name text
- `product_price` - Price text
- `add_to_cart_button` - "Add to Cart" button

---

## Test Flows

### Flow 1: Login Flow (Basic)
1. Launch app → Login screen appears
2. Tap `email_field`
3. Input "test@example.com"
4. Tap `password_field`
5. Input "password123"
6. Tap `login_button`
7. Verify Home screen appears (check for `welcome_text`)

**Expected**: ~5 actions, ~6 screenshots

### Flow 2: Browse Products (Extended)
1. Complete login flow
2. Tap `products_button`
3. Verify Products screen appears
4. Tap `product_1` card
5. Tap `add_to_cart_button`
6. Verify cart updated

**Expected**: ~8 actions, ~9 screenshots

---

## DroidRun Element Selectors

For reliable automation, prefer these selectors in order:

1. **resource-id** (most reliable)
   ```python
   await tools.tap_by_index(0)  # After get_state()
   ```

2. **content-desc** (for accessibility)
   ```python
   # Elements with content descriptions
   ```

3. **text match** (fallback)
   ```python
   # Match by visible text
   ```

---

## Build Instructions

### Option A: Use existing sample app
Download any simple shopping/login demo app from GitHub.

### Option B: Create minimal app
Use Android Studio to create:
1. New Project → Empty Activity
2. Add 3 activities (Login, Home, Products)
3. Use provided resource IDs
4. No backend needed - use hardcoded responses

### Option C: Use DroidRun's demo app
Check if DroidRun provides a demo app for testing.

---

## Notes
- All buttons should be `clickable="true"`
- All text fields should be `focusable="true"`  
- Use consistent 16dp padding throughout
- Keep animations minimal for test reliability
- Add 500ms delay after navigation for UI to settle

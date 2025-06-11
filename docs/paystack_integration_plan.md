# Paystack Integration Plan

**Goal:** Allow users to subscribe to a plan using Paystack via the link `https://paystack.shop/pay/u5fps8yjkf`, ensuring their subscription status is correctly updated in your application.

**Key Information Used:**

*   Paystack Public Key: `pk_test_d838926de168eb785971f8c46408f8e2ad42918e`
*   Paystack Secret Key: `sk_test_4fb976a4f8413ce76b5bc233740cb9954ace7afd`
*   Paystack Payment Page URL: `https://paystack.shop/pay/u5fps8yjkf`
*   Confirmation: We can append `?reference=<our_unique_id>` to the Payment Page URL, and Paystack includes this `reference` in webhook notifications.
*   Billing Cycle for this plan: `monthly`

**The Plan:**

## Backend Integration (Completed)

1.  **Configuration Update:**
    *   Verify that `Config.PAYSTACK_SECRET_KEY` and `Config.PAYSTACK_API_BASE` in `xavier_back/config.py` (or your environment variables) are correctly set up with the provided secret key.
    *   Ensure `Config.PAYSTACK_PUBLIC_KEY` is available if your frontend needs it (though for this redirect flow, it's mainly backend).

2.  **`PaymentHistory` Model Updates (see `xavier_back_modular_backup/models/payment_history.py`):**
    *   Added `reference` (the unique ID we generate).
    *   Added `payment_gateway_transaction_id` (for Paystack's own transaction ID).
    *   Updated `status` enum to accommodate values like `'pending_paystack_page_payment'`, `'completed'`, `'failed'`.
    *   Updated `payment_method` to include `'paystack_page'`.

3.  **New Backend Endpoints Added:**
    *   **A. Endpoint to Initiate Paystack Payment & Get URL:**
        *   **File:** `xavier_back_modular_backup/routes/subscription.py`
        *   **Path:** `/api/subscription/paystack/initiate_payment_page`
        *   **Method:** `POST`
        *   **Request:** `{ "plan_identifier": "xavier_premium_paystack_page" }`
        *   **Logic:**
            1.  Authenticate the user.
            2.  Map `plan_identifier` to internal `INTERNAL_PLAN_ID_FOR_PAYSTACK_PAGE` (needs configuration).
            3.  Generate a unique `reference` (e.g., `pskpage_USERID_PLANID_UUIDHEX`).
            4.  Construct the Paystack URL: `https://paystack.shop/pay/u5fps8yjkf?reference=<generated_reference>`.
            5.  Return: `{ "paystack_url": "<constructed_url>", "reference": "<generated_reference>" }`.
    *   **B. Webhook Handler Endpoint:**
        *   **File:** `xavier_back_modular_backup/routes/subscription.py`
        *   **Path:** `/api/subscription/paystack_payment_page_webhook` (ensure this is configured in your Paystack dashboard).
        *   **Method:** `POST`
        *   **Logic:**
            1.  Verify Paystack webhook signature.
            2.  Process `charge.success` event.
            3.  Extract `user_id` and `plan_id` from the custom `reference` in the webhook payload.
            4.  Call `SubscriptionService.create_subscription(user_id, plan_id, 'monthly')`.
            5.  Create/Update `PaymentHistory` record with status `'completed'`, Paystack transaction ID, and payment method `'paystack_page'`.
            6.  Respond `200 OK` to Paystack.

4.  **Backend Workflow Diagram:**

    ```mermaid
    sequenceDiagram
        actor User
        participant Frontend
        participant YourBackendAPI as API
        participant PaystackPlatform as Paystack
        participant YourDatabase as DB

        User->>Frontend: Selects plan, clicks "Pay with Paystack"
        Frontend->>API: POST /api/subscription/paystack/initiate_payment_page (plan_identifier)
        API-->>Frontend: { paystack_url: "https://paystack.shop/pay/u5fps8yjkf?reference=unique_ref", reference: "unique_ref" }
        Frontend->>User: Redirect to paystack_url

        User->>Paystack: Completes payment on Paystack Page
        Paystack-->>API: POST /api/subscription/paystack_payment_page_webhook (Event: charge.success, Data: { reference: unique_ref, ... })

        API->>Paystack: Verify Webhook Signature
        alt Signature Valid
            API->>DB: Parse user_id, plan_id from unique_ref
            API->>DB: Call SubscriptionService.create_subscription(user_id, plan_id, 'monthly')
            API->>DB: Create/Update PaymentHistory (status: 'completed', paystack_tx_id, method: 'paystack_page', reference: unique_ref)
        else Problem with Payment Record or Signature
            API->>Log: Log error
        end
        API-->>Paystack: HTTP 200 OK (to acknowledge webhook)
    ```

## Frontend Integration Plan

**Goal:** Add Paystack as a payment option in the `front/xavier_front/src/app/subscription/subscription.component.html` page.

1.  **HTML Changes (`front/xavier_front/src/app/subscription/subscription.component.html`):**
    *   Locate the `div` with class `space-y-3` (around line 165) within the "Checkout Section".
    *   Add a new button for "Pay with Paystack" within this `div`, styled consistently with existing payment buttons (PayPal, Lemon Squeezy).
    *   The button should call a new method `initiatePaystackPaymentPage()` in the component's TypeScript file.
    *   Use a generic payment icon for the button. Example structure:
        ```html
        <!-- Paystack Button -->
        <button
          (click)="initiatePaystackPaymentPage()"
          class="w-full border border-gray-300 bg-white hover:bg-gray-50 p-3 rounded-md flex items-center justify-center"
          [disabled]="!email || !termsAccepted || isProcessingPayment">
          <!-- Generic Payment Icon (e.g., a simple card or wallet icon) -->
          <svg class="h-5 w-5 mr-2 text-gray-700" viewBox="0 0 20 20" fill="currentColor">
            <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" />
            <path fill-rule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zm-7 4a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
          </svg>
          <span class="text-sm font-medium">Pay with Paystack</span>
        </button>
        ```

2.  **TypeScript Changes (`front/xavier_front/src/app/subscription/subscription.component.ts`):**
    *   Define a new public method: `initiatePaystackPaymentPage(): void`.
    *   Inside this method:
        *   Set component property `this.isProcessingPayment = true;`
        *   Set `this.errorMessage = null;` and `this.successMessage = null;`
        *   Call the backend API: `this.subscriptionService.initiatePaystackPaymentPageRedirect(this.selectedPlan.id, EXPECTED_PLAN_IDENTIFIER_FOR_PAYSTACK_PAGE)` (Note: `EXPECTED_PLAN_IDENTIFIER_FOR_PAYSTACK_PAGE` should match the one defined in the backend, e.g., `"xavier_premium_paystack_page"`). The `plan.id` might not be directly needed if the backend relies solely on the `plan_identifier`. The backend endpoint expects `plan_identifier`.
            *   The actual call might look like: `this.subscriptionService.initiatePaystackPaymentPageRedirect({ plan_identifier: "xavier_premium_paystack_page" })`
        *   Subscribe to the observable returned by the service call.
        *   **On success (response from backend):**
            *   Extract `paystack_url` from the response.
            *   Redirect the user: `window.location.href = response.paystack_url;`
        *   **On error:**
            *   Set `this.isProcessingPayment = false;`
            *   Set `this.errorMessage` to an appropriate message (e.g., `error.error.error || 'Failed to initiate Paystack payment. Please try again.'`).
            *   Log the error.
    *   **Subscription Service (`subscription.service.ts` or equivalent):**
        *   Add a new method, e.g., `initiatePaystackPaymentPageRedirect(payload: { plan_identifier: string }): Observable<any>`.
        *   This method should make an HTTP `POST` request to `/api/subscription/paystack/initiate_payment_page` with the provided payload.

3.  **Styling (Optional - `front/xavier_front/src/app/subscription/subscription.component.css`):**
    *   Ensure the new Paystack button's styling is consistent with other payment buttons if default Tailwind classes are not sufficient.

4.  **Frontend Workflow Diagram:**

    ```mermaid
    sequenceDiagram
        actor User
        participant FrontendUI as SubscriptionPageHTML
        participant FrontendLogic as SubscriptionComponentTS
        participant SubscriptionServiceTS
        participant BackendAPI as API

        User->>FrontendUI: Selects plan (if needed)
        User->>FrontendUI: Enters email, accepts terms
        User->>FrontendUI: Clicks "Pay with Paystack" button
        FrontendUI->>FrontendLogic: initiatePaystackPaymentPage()
        FrontendLogic->>FrontendLogic: Set isProcessingPayment = true
        FrontendLogic->>SubscriptionServiceTS: initiatePaystackPaymentPageRedirect({plan_identifier: "xavier_premium_paystack_page"})
        SubscriptionServiceTS->>BackendAPI: POST /api/subscription/paystack/initiate_payment_page
        alt Backend Success
            BackendAPI-->>SubscriptionServiceTS: { paystack_url: "...", reference: "..." }
            SubscriptionServiceTS-->>FrontendLogic: Observable emits success response
            FrontendLogic->>User: window.location.href = response.paystack_url
        else Backend Error
            BackendAPI-->>SubscriptionServiceTS: { error: "..." }
            SubscriptionServiceTS-->>FrontendLogic: Observable emits error
            FrontendLogic->>FrontendLogic: Set isProcessingPayment = false
            FrontendLogic->>FrontendUI: Display error message
        end
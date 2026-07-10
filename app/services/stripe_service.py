import stripe
from app.config import settings

# Initialize Stripe API key
if settings.stripe_api_key:
    stripe.api_key = settings.stripe_api_key

class StripeService:
    @staticmethod
    def create_checkout_session(email: str, trial_days: int = 14) -> str:
        """
        Creates a Stripe Checkout Session for a new user subscribing to the plan.
        Returns the session URL.
        """
        if not settings.stripe_price_id:
            raise ValueError("STRIPE_PRICE_ID is not configured in settings")

        subscription_data = {}
        # Apply trial days if configured
        trial_period = trial_days if trial_days is not None else settings.stripe_trial_period_days
        if trial_period > 0:
            subscription_data["trial_period_days"] = trial_period

        # Add email metadata to identify the pending user upon webhook success
        metadata = {"email": email}

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=email,
            line_items=[
                {
                    "price": settings.stripe_price_id,
                    "quantity": 1,
                }
            ],
            subscription_data=subscription_data,
            success_url=settings.stripe_success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.stripe_cancel_url,
            metadata=metadata,
        )
        return session.url

    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str) -> dict:
        """
        Verifies the webhook signature and returns the parsed event.
        """
        if not settings.stripe_webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET is not configured in settings")
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        return event

    @staticmethod
    def get_card_details(subscription_id: str, customer_id: str) -> dict:
        """
        Retrieves default card details for a subscription or customer.
        Returns a dict with brand, last4, exp_month, exp_year or empty dict.
        """
        try:
            pm_id = None
            if subscription_id:
                sub = stripe.Subscription.retrieve(subscription_id)
                pm_id = sub.get("default_payment_method")
            
            if not pm_id and customer_id:
                customer = stripe.Customer.retrieve(customer_id)
                pm_id = customer.get("invoice_settings", {}).get("default_payment_method")
                
            if pm_id:
                pm = stripe.PaymentMethod.retrieve(pm_id)
                if pm and pm.get("type") == "card":
                    card = pm.get("card", {})
                    return {
                        "brand": card.get("brand"),
                        "last4": card.get("last4"),
                        "exp_month": card.get("exp_month"),
                        "exp_year": card.get("exp_year")
                    }
        except Exception as e:
            print(f"Error fetching card details from Stripe: {e}")
        return {}

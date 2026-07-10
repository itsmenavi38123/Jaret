import stripe
from app.config import settings

# Initialize Stripe API key
if settings.stripe_api_key:
    stripe.api_key = settings.stripe_api_key

class StripeService:
    @staticmethod
    def create_checkout_session(email: str, success_url: str = None, cancel_url: str = None, trial_days: int = 14) -> str:
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

        redirect_success = success_url or settings.stripe_success_url
        redirect_cancel = cancel_url or settings.stripe_cancel_url

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
            success_url=redirect_success,
            cancel_url=redirect_cancel,
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
                pm_id = getattr(sub, "default_payment_method", None)
            
            if not pm_id and customer_id:
                customer = stripe.Customer.retrieve(customer_id)
                invoice_settings = getattr(customer, "invoice_settings", None)
                pm_id = getattr(invoice_settings, "default_payment_method", None) if invoice_settings else None
                
            if pm_id:
                pm = stripe.PaymentMethod.retrieve(pm_id)
                pm_type = getattr(pm, "type", None)
                if pm_type == "card":
                    card = getattr(pm, "card", None)
                    if card:
                        return {
                            "brand": getattr(card, "brand", None),
                            "last4": getattr(card, "last4", None),
                            "exp_month": getattr(card, "exp_month", None),
                            "exp_year": getattr(card, "exp_year", None)
                        }
        except Exception as e:
            print(f"Error fetching card details from Stripe: {e}")
        return {}

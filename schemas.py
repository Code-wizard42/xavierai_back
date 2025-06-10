"""
Schemas Module

This module contains marshmallow schemas for serializing and deserializing models.
"""
from marshmallow import Schema, fields, validate, ValidationError, post_load
from models import User, Chatbot, NotificationPreference, Plan, Subscription, PaymentHistory

class UserSchema(Schema):
    """Schema for User model"""
    id = fields.Integer(dump_only=True)
    username = fields.String(required=True, validate=validate.Length(min=3, max=128))
    email = fields.Email(allow_none=True)
    firebase_uid = fields.String(allow_none=True)
    profile_picture = fields.String(allow_none=True)
    auth_provider = fields.String(allow_none=True)

    # Don't include password_hash in serialization
    password_hash = fields.String(load_only=True, allow_none=True)

    class Meta:
        ordered = True

class ChatbotSchema(Schema):
    """Schema for Chatbot model"""
    id = fields.String(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=80))
    user_id = fields.Integer(required=True)
    data = fields.Dict(allow_none=True)

    class Meta:
        ordered = True

class NotificationPreferenceSchema(Schema):
    """Schema for NotificationPreference model"""
    id = fields.Integer(dump_only=True)
    user_id = fields.Integer(required=True)
    preferences = fields.Dict(required=True)
    notification_email = fields.Email(allow_none=True)
    email_frequency = fields.String(validate=validate.OneOf(['immediate', 'hourly', 'daily', 'weekly']))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    class Meta:
        ordered = True

class PlanSchema(Schema):
    """Schema for Plan model"""
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=50))
    description = fields.String(allow_none=True)
    price = fields.Float(required=True)
    annual_price = fields.Float(allow_none=True)
    features = fields.List(fields.String(), required=True)
    max_chatbots = fields.Integer(required=True)
    is_active = fields.Boolean()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    class Meta:
        ordered = True

class SubscriptionSchema(Schema):
    """Schema for Subscription model"""
    id = fields.Integer(dump_only=True)
    plan_id = fields.Integer(required=True)
    status = fields.String(validate=validate.OneOf(['active', 'canceled', 'past_due', 'trialing', 'unpaid']))
    start_date = fields.DateTime(required=True)
    end_date = fields.DateTime(allow_none=True)
    trial_end = fields.DateTime(allow_none=True)
    billing_cycle = fields.String(validate=validate.OneOf(['monthly', 'annual']))
    # Payment method type (stripe, paypal, etc.)
    payment_method = fields.String(allow_none=True)
    # Stripe specific fields
    stripe_customer_id = fields.String(allow_none=True)
    stripe_subscription_id = fields.String(allow_none=True)
    payment_method_id = fields.String(allow_none=True)
    # PayPal specific fields
    paypal_subscription_id = fields.String(allow_none=True)
    paypal_order_id = fields.String(allow_none=True)
    # Common fields
    cancel_at_period_end = fields.Boolean()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # Include the plan details in the subscription response
    plan = fields.Nested(PlanSchema, dump_only=True)

    class Meta:
        ordered = True

class PaymentHistorySchema(Schema):
    """Schema for PaymentHistory model"""
    id = fields.Integer(dump_only=True)
    subscription_id = fields.Integer(required=True)
    amount = fields.Float(required=True)
    currency = fields.String(required=True)
    status = fields.String(validate=validate.OneOf(['succeeded', 'failed', 'pending']))
    stripe_payment_intent_id = fields.String(allow_none=True)
    stripe_invoice_id = fields.String(allow_none=True)
    payment_method = fields.String(allow_none=True)
    payment_date = fields.DateTime(required=True)

    class Meta:
        ordered = True

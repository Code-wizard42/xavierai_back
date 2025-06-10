"""
Script to create subscription plans in the database
"""
import os
import sys
from datetime import datetime, timezone

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xavier_back.app import create_app
from xavier_back.extensions import db
from xavier_back.models import Plan

def create_plans():
    """Create subscription plans in the database"""
    app = create_app()
    
    with app.app_context():
        # Check if plans already exist
        existing_plans = Plan.query.all()
        if existing_plans:
            print(f"Found {len(existing_plans)} existing plans:")
            for plan in existing_plans:
                print(f"- {plan.name}: ${plan.price}/month, ${plan.annual_price}/year")
            
            # Ask if we should continue
            response = input("Do you want to create new plans anyway? (y/n): ")
            if response.lower() != 'y':
                print("Exiting without creating new plans.")
                return
        
        # Create the plans
        plans = [
            {
                'name': 'Basic',
                'description': 'Perfect for small businesses just getting started',
                'price': 5.0,
                'annual_price': 60.0,
                'features': [
                    'Up to 3 chatbots',
                    'Unlimited conversations',
                    'Lead generation',
                    'Basic analytics'
                ],
                'max_chatbots': 3
            },
            {
                'name': 'Premium',
                'description': 'Ideal for growing businesses with multiple needs',
                'price': 15.0,
                'annual_price': 144.0,
                'features': [
                    'Up to 10 chatbots',
                    'Unlimited conversations',
                    'Advanced lead generation',
                    'Advanced analytics',
                    'Priority support'
                ],
                'max_chatbots': 10
            },
            {
                'name': 'Enterprise',
                'description': 'For large organizations with custom requirements',
                'price': 50.0,
                'annual_price': 480.0,
                'features': [
                    'Unlimited chatbots',
                    'Unlimited conversations',
                    'Custom integrations',
                    'Advanced analytics & reporting',
                    'Dedicated account manager'
                ],
                'max_chatbots': 999999  # Effectively unlimited
            }
        ]
        
        # Add the plans to the database
        for plan_data in plans:
            plan = Plan(
                name=plan_data['name'],
                description=plan_data['description'],
                price=plan_data['price'],
                annual_price=plan_data['annual_price'],
                features=plan_data['features'],
                max_chatbots=plan_data['max_chatbots'],
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(plan)
        
        # Commit the changes
        db.session.commit()
        
        print("Plans created successfully!")
        
        # Print the plans
        plans = Plan.query.all()
        print(f"Found {len(plans)} plans:")
        for plan in plans:
            print(f"- {plan.name}: ${plan.price}/month, ${plan.annual_price}/year")

if __name__ == '__main__':
    create_plans()

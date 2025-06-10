"""
Admin Routes for Database Management
"""

from flask import Blueprint, request, jsonify
from extensions import db
from models.plan import Plan

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/update-plan-limit', methods=['POST'])
def update_plan_limit():
    """Update conversation limit for a specific plan"""
    try:
        data = request.get_json()
        plan_name = data.get('plan_name', 'Premium')
        new_limit = data.get('limit', 1000)
        
        # Update the plan
        plan = Plan.query.filter_by(name=plan_name).first()
        if not plan:
            return jsonify({"error": f"Plan '{plan_name}' not found"}), 404
        
        old_limit = plan.max_conversations_per_month
        plan.max_conversations_per_month = new_limit
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Updated {plan_name} plan from {old_limit} to {new_limit} conversations/month",
            "plan_name": plan_name,
            "old_limit": old_limit,
            "new_limit": new_limit
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/admin/plans', methods=['GET'])
def get_plans():
    """Get all plans and their limits"""
    try:
        plans = Plan.query.all()
        plan_data = []
        for plan in plans:
            plan_data.append({
                "id": plan.id,
                "name": plan.name,
                "max_conversations_per_month": plan.max_conversations_per_month,
                "price": plan.price
            })
        
        return jsonify({
            "success": True,
            "plans": plan_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500 
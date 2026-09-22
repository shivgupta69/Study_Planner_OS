from flask import Blueprint, render_template, request, session

from backend.app.services.analytics_service import get_daily_analytics
from backend.app.utils.helpers import handle_route_errors, login_required


analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics")
@handle_route_errors
@login_required
def analytics_view():
    days = request.args.get("days", default=7, type=int)
    # Cap days to prevent DoS via large analytics queries
    days = max(1, min(days or 7, 90))
    analytics_data = get_daily_analytics(session["user_id"], days=days)


    return render_template(
        "analytics.html",
        analytics_data=analytics_data,
        selected_days=max(7, min(days or 7, 30)),
    )

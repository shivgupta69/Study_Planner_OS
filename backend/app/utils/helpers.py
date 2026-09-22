"""Helper utilities for Flask routes."""

from functools import wraps
import html
import logging
import traceback

from flask import current_app, flash, redirect, session, request, jsonify

# Initialize logger
logger = logging.getLogger(__name__)


def sanitize_input(text, max_length: int = 255) -> str:
    """
    Clean user input by escaping HTML characters and enforcing a maximum length.

    Accepts any value (str, int, float, None) and coerces it to a string first,
    so JSON payloads with numeric values (e.g. duration: 2) cannot crash routes.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return ""
    # Trim whitespace and truncate to max_length
    clean_text = text.strip()[:max_length]
    # Escape HTML characters (e.g., < becomes &lt;)
    return html.escape(clean_text)


def login_required(view_func):
    """
    Decorator to protect routes that require authentication.

    Clears session and redirects to login if user_id is invalid.

    Args:
        view_func: The route function to wrap.

    Returns:
        Wrapped function with authentication check.
    """

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not isinstance(user_id, int) or user_id <= 0:
            session.clear()
            # flash("Please log in to continue.", "error")
            return redirect("/register")
        return view_func(*args, **kwargs)

    return wrapped


def handle_route_errors(view_func):
    """
    Decorator to catch exceptions in Flask routes and return consistent responses.
    - For JSON requests: Returns jsonify({"success": False, "message": ..., "error": ...})
    - For browser requests: Flashes error and redirects to safe page.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except Exception as e:
            # Log the full traceback for developers
            logger.error(f"Exception in route {view_func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())

            # Check if request is JSON or prefers JSON.
            # NOTE: werkzeug's MIMEAccept has no .get(); use [] (quality lookup).
            accepts = request.accept_mimetypes
            is_json_pref = request.is_json or (
                "application/json" in accepts
                and accepts["application/json"] >= accepts["text/html"]
            )

            # Only expose internal error details when the app runs in debug mode.
            # (logging has no PRODUCTION level; use the app's debug flag instead.)
            debug_mode = bool(current_app.debug) if current_app else False

            if is_json_pref:
                return jsonify({
                    "success": False,
                    "message": str(e) if debug_mode else "An internal server error occurred.",
                    "error": e.__class__.__name__
                }), 500

            # Standard browser request
            flash(
                f"An unexpected error occurred: {str(e)}" if debug_mode
                else "An unexpected error occurred. Please try again.",
                "error",
            )
            # Redirect to a safe page. Never redirect back to the same path,
            # otherwise a broken page would cause an infinite redirect loop.
            safe_target = "/login" if request.path in ("/", "/login") else "/"
            return redirect(safe_target)

    return wrapped

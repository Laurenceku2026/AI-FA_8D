"""Enterprise branding helpers for TechLife child apps."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional
from urllib.parse import quote

import jwt
import requests
import streamlit as st


def qp_first(query_params: Any, key: str) -> str:
    val = query_params.get(key)
    if isinstance(val, list):
        return val[0] if val else ""
    return val or ""


def ensure_enterprise_session_defaults() -> None:
    defaults = {
        "organization_id": None,
        "organization_name": "",
        "organization_logo_url": "",
        "_enterprise_branding_loaded": False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def apply_portal_token(
    query_params: Any,
    *,
    set_app_language: Optional[Callable[[str], None]] = None,
) -> None:
    token = qp_first(query_params, "token")
    secret = st.secrets.get("JWT_SECRET_KEY")
    if not token or not secret:
        return
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return

    if payload.get("sub"):
        st.session_state.user_id = payload["sub"]
    if payload.get("email"):
        st.session_state.user_email = payload["email"]
        if "@" in payload["email"]:
            st.session_state.username = payload["email"].split("@")[0]
    if payload.get("organization_id"):
        st.session_state.organization_id = payload["organization_id"]
        st.session_state._enterprise_branding_loaded = False
    if payload.get("organization_name"):
        st.session_state.organization_name = payload["organization_name"]
    if payload.get("org_role"):
        st.session_state.org_role = payload["org_role"]
    if payload.get("trials_left") is not None and "trials_left" not in st.session_state:
        try:
            st.session_state.trials_left = int(payload["trials_left"])
        except (TypeError, ValueError):
            pass
    if set_app_language and "lang" not in st.session_state and payload.get("lang") in ("zh", "en"):
        set_app_language(payload["lang"])


def is_enterprise_user() -> bool:
    return bool(st.session_state.get("organization_id"))


def load_enterprise_branding(supabase_url: str, headers: Dict[str, str]) -> None:
    if not is_enterprise_user() or st.session_state.get("_enterprise_branding_loaded"):
        return

    org_id = st.session_state.get("organization_id")
    logo_url = ""
    try:
        query = f"id=eq.{quote(str(org_id), safe='')}&select=name,logo_url"
        response = requests.get(
            f"{supabase_url}/rest/v1/organizations?{query}",
            headers=headers,
            timeout=12,
        )
        if response.status_code == 200 and response.json():
            row = response.json()[0]
            name = (row.get("name") or "").strip()
            if name:
                st.session_state.organization_name = name
            logo_url = (row.get("logo_url") or "").strip()
    except Exception:
        logo_url = ""

    st.session_state.organization_logo_url = logo_url
    st.session_state._enterprise_branding_loaded = True


def enterprise_display_name() -> str:
    return (st.session_state.get("organization_name") or "").strip()


def enterprise_logo_url() -> str:
    return (st.session_state.get("organization_logo_url") or "").strip()


def render_enterprise_sidebar_brand() -> None:
    if not is_enterprise_user():
        return
    org_name = enterprise_display_name()
    logo_url = enterprise_logo_url()
    if logo_url:
        col_logo, col_name = st.columns([1, 4])
        with col_logo:
            st.image(logo_url, width=40)
        with col_name:
            if org_name:
                st.markdown(f"### {org_name}")
    elif org_name:
        st.markdown(f"### {org_name}")


def render_enterprise_main_brand() -> None:
    if not is_enterprise_user():
        return
    org_name = enterprise_display_name()
    logo_url = enterprise_logo_url()
    if not org_name and not logo_url:
        return
    if logo_url:
        col_logo, col_name = st.columns([1, 10])
        with col_logo:
            st.image(logo_url, width=52)
        with col_name:
            if org_name:
                st.markdown(f"## {org_name}")
    elif org_name:
        st.markdown(f"## {org_name}")

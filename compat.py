# compat.py
# Newer Streamlit replaced use_container_width=True with width="stretch" and will drop the old
# argument. The code base still uses the old one, so translate it here on versions that need it.
# On older Streamlit this does nothing.
import functools
import inspect
import streamlit as st


def _version():
    try: return tuple(int(p) for p in st.__version__.split(".")[:2])
    except Exception: return (0, 0)


def _wrap(name):
    fn = getattr(st, name, None)
    if fn is None or getattr(fn, "_ps_compat", False): return

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if "use_container_width" in kwargs:
            if kwargs.pop("use_container_width") and "width" not in kwargs:
                kwargs["width"] = "stretch"
        return fn(*args, **kwargs)

    wrapper._ps_compat = True
    setattr(st, name, wrapper)


def _wrap_image_for_old_streamlit():
    """Streamlit before ~1.40 has no use_container_width on st.image; its equivalent is use_column_width."""
    fn = getattr(st, "image", None)
    if fn is None or getattr(fn, "_ps_compat", False): return
    try:
        if "use_container_width" in inspect.signature(fn).parameters: return
    except (TypeError, ValueError):
        return

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if "use_container_width" in kwargs:
            if kwargs.pop("use_container_width"): kwargs.setdefault("use_column_width", "always")
        return fn(*args, **kwargs)

    wrapper._ps_compat = True
    st.image = wrapper


if _version() >= (1, 50):
    for _name in ("button", "download_button", "form_submit_button", "popover", "image", "link_button"):
        _wrap(_name)
else:
    _wrap_image_for_old_streamlit()

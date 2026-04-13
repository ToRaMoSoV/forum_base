import bleach

ALLOWED_TAGS = [
    "b","i","u","strong","em",
    "p","br","span","div",
    "img"
]

ALLOWED_ATTRS = {
    "*": ["class","style"],
    "img": ["src","alt","width","height"]
}

def sanitize_html(html):
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True
    ) 
    
import re

ALLOWED_CSS = {
    "color",
    "background-color",
    "font-size",
    "font-weight",
    "text-align",
    "margin",
    "padding"
}

def sanitize_css(css):

    safe=[]

    for line in css.split(";"):

        if ":" not in line:
            continue

        prop,val=line.split(":",1)

        prop=prop.strip().lower()

        if prop not in ALLOWED_CSS:
            continue

        if "javascript:" in val:
            continue

        safe.append(f"{prop}:{val}")

    return ";".join(safe)

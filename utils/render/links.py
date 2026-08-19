import html as html_module
import re
from urllib.parse import urlparse


def _url_is_safe(url: str) -> bool:
    scheme = urlparse(url).scheme.lower()
    return scheme in ("", "http", "https")


_TRAILING_PUNCTUATION = ".,;:!?"


def _strip_trailing_punctuation(url: str) -> tuple[str, str]:
    stripped = url.rstrip(_TRAILING_PUNCTUATION)
    return stripped, url[len(stripped):]


def convert_links_to_html(text: str) -> str:
    result = []
    last_end = 0
    link_pattern = re.compile(r'\[([^\]]+)\]\(((?:[^()]|\([^()]*\))*)\)|(https?://[^\s<>“”"]+)')
    for m in link_pattern.finditer(text):
        result.append(html_module.escape(text[last_end:m.start()]))
        url = m.group(2) or m.group(3)
        label = m.group(1) or url
        trailing = ""
        if m.group(3):
            url, trailing = _strip_trailing_punctuation(url)
            label = url
        if _url_is_safe(url):
            result.append(
                f'<a href="{html_module.escape(url)}">'
                f'{html_module.escape(label)}'
                f'</a>'
            )
        else:
            result.append(html_module.escape(label))
        result.append(trailing)
        last_end = m.end()
    result.append(html_module.escape(text[last_end:]))
    return "".join(result)

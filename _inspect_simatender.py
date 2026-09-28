from pathlib import Path
import os
import re

html = Path(os.environ["TEMP"], "simatender_sample.html").read_text(encoding="utf-8", errors="replace")
out = Path("_inspect_simatender_out.txt")
idx = html.lower().find("<table")
hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
ths = re.findall(r"<th[^>]*>(.*?)</th>", html, flags=re.I | re.S)
chunk = html[idx:idx + 6000] if idx >= 0 else "no table"
out.write_text(
    f"len {len(html)}\nfirst table idx {idx}\n\n{chunk}\n\n---href sample---\n"
    + "\n".join(hrefs[:80])
    + "\n\n---th sample---\n"
    + "\n".join(ths[:30]),
    encoding="utf-8",
)
print("wrote", out)

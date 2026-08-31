from pathlib import Path
path = Path("app.py")
text = path.read_text(encoding="utf-8")
marker = """ocf_growth = yoy(
    ocf,
    previous_ocf,
)
"""
debug = marker + """
st.write("DEBUG — profit_growth:", profit_growth)
st.write("DEBUG — ocf_growth:", ocf_growth)
st.write("DEBUG — ocf:", ocf)
st.write("DEBUG — previous_ocf:", previous_ocf)
"""
if "DEBUG — profit_growth:" in text:
    print("DEBUG ALREADY EXISTS")
    raise SystemExit(0)
if marker not in text:
    print("OCF GROWTH MARKER NOT FOUND")
    raise SystemExit(1)
text = text.replace(marker, debug, 1)
path.write_text(text, encoding="utf-8")
print("Temporary debug lines added.")

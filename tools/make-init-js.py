import sys
import json

with open(sys.argv[1]) as fp:
    css = fp.read()
with open(sys.argv[2]) as fp:
    html = fp.read()
with open(sys.argv[3], "w") as fp:
    fp.write("init(")
    json.dump(css, fp)
    fp.write(",")
    json.dump(html, fp)
    fp.write(");")

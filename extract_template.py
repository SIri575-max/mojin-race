import re

html = open('frontend/index.html', encoding='utf-8').read()
start = html.index('<div id="app">')
# find matching close of #app div
pos = start + len('<div id="app">')
depth = 1
i = pos
while depth > 0:
    open_idx = html.find('<div', i)
    close_idx = html.find('</div>', i)
    if open_idx != -1 and open_idx < close_idx:
        depth += 1
        i = open_idx + 5
    else:
        depth -= 1
        i = close_idx + 6
template = html[start:i]
open('template.txt', 'w', encoding='utf-8').write(template)
print('template extracted, chars =', len(template))

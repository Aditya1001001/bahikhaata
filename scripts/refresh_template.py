"""Re-make templates/review.html from your own live review page source after you change its design.
usage: refresh_template.py PATH_TO_YOUR_review.html
Swaps your flatmate's name for generic text so the template carries no names. Check the printed leftovers before sharing."""
import re, sys, os
src = open(sys.argv[1]).read(); name = re.search(r'let flatmate="([^"]+)"', src).group(1)
up = name.upper()
pairs = [(f'>{name} owes you<', '>Saathi ke naam baaki<'), (f'{name} logged something', '<span class="fm">Saathi</span> logged something'),
         (f'let flatmate="{name}";', 'let flatmate="saathi";'), (f'/^{up}=/i.test(split)', '/^[A-Za-z]+=/.test(split)'),
         (f'{up}=2996', 'THEM=2996'), (f'{name.lower()}Owes', 'theyOwe'), (f'a.{name.lower()}_owes', 'a.they_owe'),
         (f'x.{name.lower()}', 'x.them'), (f't.{name.lower()}', 't.them'),
         ('flatmate=summary.flatmate||flatmate;', 'flatmate=summary.flatmate||flatmate; document.querySelectorAll(".fm").forEach(e=>e.textContent=flatmate);')]
for a, b in pairs: src = src.replace(a, b)
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates', 'review.html')
open(out, 'w').write(src)
left = [m.start() for m in re.finditer(name, src, re.I)]
print('wrote', out, '| leftover mentions of the name:', len(left))

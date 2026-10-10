from pypdf import PdfReader
import re

path = r'c:\Users\betto\Documents\repos\daggerheart-gui\quickstart_adventure.pdf'
reader = PdfReader(path)
text = '\n'.join(page.extract_text() or '' for page in reader.pages)
patterns = ['Marlowe Fairwind', 'Barnacle', 'Garrick Reed', 'Khari Nix', 'Varian Soto']
for pattern in patterns:
    idx = text.upper().find(pattern.upper())
    if idx < 0:
        print('PATTERN NOT FOUND', pattern)
        continue
    start = max(0, idx - 1200)
    end = min(len(text), idx + 4000)
    snippet = text[start:end]
    print('\n' + '='*80)
    print(pattern)
    print(snippet)
    print('\n' + '='*80)

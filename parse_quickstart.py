from pypdf import PdfReader
import re

path = r'c:\Users\betto\Documents\repos\daggerheart-gui\quickstart_adventure.pdf'
reader = PdfReader(path)
text = '\n'.join(page.extract_text() or '' for page in reader.pages)
for name in ['Marlowe', 'Barnacle', 'Garrick', 'Khari', 'Luvia', 'Aster', 'Nix', 'Fairwind', 'Reed']:
    m = re.search(name, text, re.I)
    print('NAME', name, 'found', bool(m), 'pos', (m.start() if m else None))

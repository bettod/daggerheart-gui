from pypdf import PdfReader

path = r'c:\Users\betto\Documents\repos\daggerheart-gui\quickstart_adventure.pdf'
reader = PdfReader(path)
text = '\n'.join(page.extract_text() or '' for page in reader.pages)
needle = 'CHOOSING CHARACTERS'
idx = text.upper().find(needle.upper())
print('idx', idx)
print(text[idx:idx+6000])

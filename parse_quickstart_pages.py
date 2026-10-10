import fitz

path = r'c:\Users\betto\Documents\repos\daggerheart-gui\quickstart_adventure.pdf'
doc = fitz.open(path)
out = open(r'c:\Users\betto\Documents\repos\daggerheart-gui\quickstart_pages.txt', 'w', encoding='utf-8')
print('pages', len(doc), file=out)
for i in range(len(doc)):
    page = doc[i]
    text = page.get_text('text')
    out.write(f'\n===== PAGE {i+1} =====\n')
    out.write(text[:8000])
    out.write(f'\n===== END PAGE {i+1} =====\n')
out.close()
print('saved quickstart_pages.txt')

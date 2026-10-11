import re
from pathlib import Path

import fitz

pdf_path = Path(r'c:\Users\betto\Documents\repos\daggerheart-gui\Daggerheart_Core_Book_-_Full_Art_Cards_-_9-09-25.pdf')
abilities_dir = Path(r'c:\Users\betto\Documents\repos\daggerheart-srd\abilities')
out_dir = Path(r'c:\Users\betto\Documents\repos\daggerheart-gui\data\ability_cards')
out_dir.mkdir(parents=True, exist_ok=True)


def normalize_name(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (value or '').strip().lower()).strip('-')


def search_card_rect(page: fitz.Page, title: str):
    variants = [title, title.replace('–', '-'), title.replace('&', 'and')]
    seen = set()
    for variant in variants:
        key = variant.lower()
        if key in seen:
            continue
        seen.add(key)
        rects = page.search_for(variant)
        if rects:
            rect = rects[0]
            return fitz.Rect(
                max(0, rect.x0 - 18),
                max(0, rect.y0 - 24),
                min(page.rect.width, rect.x1 + 24),
                min(page.rect.height, rect.y1 + 150),
            )
    return None


ability_names = [path.stem for path in sorted(abilities_dir.glob('*.md'))]

doc = fitz.open(str(pdf_path))
count = 0
for ability_name in ability_names:
    normalized = normalize_name(ability_name)
    target = out_dir / f'{normalized}.png'
    if target.exists():
        continue

    found = None
    for page_no in range(368, min(len(doc), 420) + 1):
        page = doc[page_no - 1]
        rect = search_card_rect(page, ability_name)
        if rect is not None:
            found = (page, rect)
            break
        # broaden search to common formatting variants where the PDF title is slightly different
        for variant in [ability_name.replace('-', ' '), ability_name.replace(' ', ' ')]:
            rect = search_card_rect(page, variant)
            if rect is not None:
                found = (page, rect)
                break
        if found:
            break

    if found is None:
        print(f'SKIP {ability_name}: not found in PDF')
        continue

    page, rect = found
    pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=rect)
    pix.save(str(target))
    print(f'{ability_name} -> {target.name}')
    count += 1

print(f'Generated {count} cropped ability cards.')

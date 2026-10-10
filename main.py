import re
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QTextDocument, QDesktopServices
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from daggerheart_api import build_catalog


class RuleSection:
    def __init__(self, title: str, html: str, text: str, anchor: str, level: int = 1):
        self.title = title
        self.html = html
        self.text = text
        self.anchor = anchor
        self.level = level


class DaggerheartViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Daggerheart SRD Viewer")
        self.resize(1100, 700)

        self.sections = []
        self.current_query = ""

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search the rules...")
        self.search_input.textChanged.connect(self.on_search_changed)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_search)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setEnabled(False)

        self.home_button = QPushButton("Home")
        self.home_button.clicked.connect(self.go_home)

        self.theme_button = QPushButton("Switch to Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)

        self.status_label = QLabel("Loading Daggerheart rules...")
        self.status_label.setWordWrap(True)

        self.section_list = QTreeWidget()
        self.section_list.setHeaderHidden(True)
        self.section_list.setUniformRowHeights(True)
        self.section_list.setExpandsOnDoubleClick(False)
        self.section_list.currentItemChanged.connect(self.on_section_changed)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.anchorClicked.connect(self.on_anchor_clicked)
        self.update_browser_link_style()

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.search_input)
        controls_layout.addWidget(self.clear_button)
        controls_layout.addWidget(self.back_button)
        controls_layout.addWidget(self.home_button)
        controls_layout.addWidget(self.theme_button)

        left_layout = QVBoxLayout()
        left_layout.addLayout(controls_layout)
        left_layout.addWidget(self.status_label)
        left_layout.addWidget(self.section_list)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(self.browser)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([280, 820])

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(splitter)

        self.current_file_path = None
        self.history = []
        self.dark_mode = True
        self.apply_theme()

        self.load_rules()

    def load_rules(self):
        try:
            catalog = build_catalog()
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "File Not Found",
                "Could not find the Daggerheart SRD markdown repository.\nPlease place daggerheart-srd adjacent to this project or set DAGGERHEART_SRD_PATH.",
            )
            self.status_label.setText("Daggerheart SRD not found.")
            return

        self.catalog = catalog
        self.section_list.clear()

        for category_name in sorted(catalog["categories"].keys()):
            category = catalog["categories"][category_name]
            category_item = QTreeWidgetItem([f"{category['label']} ({category['count']})"])
            category_item.setExpanded(False)
            category_item.setData(0, Qt.UserRole, {"type": "category", "name": category_name, "data": category})

            for entry in category["entries"]:
                entry_name = entry.get("name") or entry.get("slug") or "Unnamed"
                entry_item = QTreeWidgetItem([entry_name])
                entry_item.setData(0, Qt.UserRole, {"type": "entry", "category": category_name, "entry": entry})

                markdown = entry.get("markdown") or ""
                sub_sections = self.parse_markdown_sections(markdown)
                if len(sub_sections) > 1:
                    for section in sub_sections:
                        section_item = QTreeWidgetItem([section.title])
                        section_item.setData(0, Qt.UserRole, {"type": "section", "section": section})
                        entry_item.addChild(section_item)
                else:
                    summary_item = QTreeWidgetItem(["Summary"])
                    summary_item.setData(0, Qt.UserRole, {"type": "summary", "category": category_name, "entry": entry})
                    entry_item.addChild(summary_item)

                category_item.addChild(entry_item)

            self.section_list.addTopLevelItem(category_item)

        self.status_label.setText(f"Loaded {catalog['total_documents']} Daggerheart documents across {len(catalog['categories'])} categories.")
        for idx in range(self.section_list.topLevelItemCount()):
            self.section_list.topLevelItem(idx).setExpanded(False)

        if self.section_list.topLevelItemCount() > 0:
            first_category = self.section_list.topLevelItem(0)
            first_category.setExpanded(False)
            self.section_list.setCurrentItem(first_category)

    def render_entry_html(self, category_name: str, entry: dict):
        summary = entry.get("summary") or "No summary available."
        markdown = entry.get("markdown")

        if category_name == "characters" and "class_name" in entry:
            lines = [
                f"<h1>{entry['name']}</h1>",
                f"<p><strong>Class:</strong> {entry['class_name']} ({entry['subclass']})</p>",
                f"<p><strong>Heritage:</strong> {entry['heritage']}</p>",
                f"<p><strong>Pronouns:</strong> {entry['pronouns']}</p>",
                f"<p><strong>Story:</strong> {entry.get('story', '')}</p>",
                f"<p><strong>Experiences:</strong> {', '.join(entry.get('experiences', []))}</p>",
                f"<p><strong>Question:</strong> {entry.get('question', '')}</p>",
            ]
            if entry.get("settings"):
                settings = entry["settings"]
                armor = settings.get("armor", {})
                weapon = settings.get("weapon", {})
                lines.extend([
                    f"<p><strong>Armor:</strong> {armor.get('name', 'Unknown')} (Score {armor.get('base_score', '')})</p>",
                    f"<p><strong>Weapon:</strong> {weapon.get('name', 'Unknown')} ({weapon.get('damage', '')})</p>",
                    f"<p><strong>Hope:</strong> {settings.get('hope', '')} &nbsp; <strong>Evasion:</strong> {settings.get('evasion', '')}</p>",
                    f"<p><strong>Hit Points:</strong> {settings.get('hit_points', '')} &nbsp; <strong>Stress:</strong> {settings.get('stress', '')}</p>",
                ])
            return "\n".join(lines)

        if markdown:
            section_html = self.convert_markdown_to_html(markdown.splitlines())
            # Split a long markdown document into readable subsection blocks for the same entry.
            if "<h1" in section_html or "<h2" in section_html:
                return section_html
            return f"<h1>{entry['name']}</h1><p>{summary}</p>"

        return f"<h1>{entry['name']}</h1><p>{summary}</p>"

    def parse_markdown_sections(self, markdown_text: str):
        lines = markdown_text.splitlines()
        sections = []
        current_lines = []
        current_title = "Overview"
        current_anchor = "overview"
        current_level = 1

        def push_section():
            nonlocal current_lines, current_title, current_anchor, current_level
            if not current_lines:
                return
            html = self.convert_markdown_to_html(current_lines)
            plain_text = self.strip_html(html)
            sections.append(RuleSection(current_title, html, plain_text, current_anchor, current_level))
            current_lines = []

        for line in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
            if heading_match:
                push_section()
                hashes, title = heading_match.groups()
                current_level = len(hashes)
                current_title = title.strip()
                current_anchor = re.sub(r"[^a-zA-Z0-9_-]", "-", current_title.lower()).strip("-")
                current_lines.append(line)
            else:
                current_lines.append(line)

        push_section()
        return sections

    def convert_markdown_to_html(self, lines):
        html_parts = []
        in_list = False
        for raw_line in lines:
            line = raw_line.rstrip()
            if not line:
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
            if heading_match:
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                level = len(heading_match.group(1))
                title = self.render_inline(heading_match.group(2).strip())
                anchor = re.sub(r"[^a-zA-Z0-9_-]", "-", heading_match.group(2).lower()).strip("-")
                html_parts.append(f"<h{level} id=\"{anchor}\">{title}</h{level}>")
                continue

            list_match = re.match(r"^[-*+]\s+(.*)", line)
            if list_match:
                if not in_list:
                    html_parts.append("<ul>")
                    in_list = True
                html_parts.append(f"<li>{self.render_inline(list_match.group(1).strip())}</li>")
                continue

            html_parts.append(f"<p>{self.render_inline(line)}</p>")

        if in_list:
            html_parts.append("</ul>")

        return "\n".join(html_parts)

    def render_inline(self, text: str):
        text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__(.*?)__", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
        text = re.sub(r"_(.*?)_", r"<em>\1</em>", text)
        text = re.sub(r"`([^`]*)`", r"<code>\1</code>", text)

        def replace_link(match):
            label = match.group(1)
            target = match.group(2)
            if not target or target.startswith("mailto:"):
                return label

            href = self.build_link_href(target)
            if href.startswith("file:") or target.endswith(".md") or ".md#" in target:
                if self.current_file_path is None:
                    return label
                resolved = self.resolve_link_path(target)
                if not resolved.exists():
                    return label
                return f"<a href='{href}' style='color: #7fa8ff; text-decoration: underline;'>{label}</a>"

            if href.startswith("http://") or href.startswith("https://"):
                return f"<a href='{href}'>{label}</a>"

            return label

        text = re.sub(r"\[(.*?)\]\((.*?)\)", replace_link, text)
        return text

    def strip_html(self, html: str):
        text = re.sub(r"<[^>]+>", "", html)
        return text

    def populate_section_list(self, sections):
        self.section_list.clear()
        stack = []
        for section in sections:
            item = QTreeWidgetItem([section.title])
            item.setData(0, Qt.UserRole, section)
            item.setHidden(False)
            while stack and section.level <= stack[-1][0]:
                stack.pop()
            if stack:
                stack[-1][1].addChild(item)
            else:
                self.section_list.addTopLevelItem(item)
                item.setExpanded(True)
            stack.append((section.level, item))

    def find_first_visible_item(self):
        def recurse(item):
            if not item.isHidden():
                return item
            for idx in range(item.childCount()):
                found = recurse(item.child(idx))
                if found is not None:
                    return found
            return None

        for i in range(self.section_list.topLevelItemCount()):
            item = self.section_list.topLevelItem(i)
            found = recurse(item)
            if found is not None:
                return found
        return None

    def find_item_by_anchor(self, anchor: str):
        def recurse(item):
            section = item.data(0, Qt.UserRole)
            if section and section.anchor == anchor:
                return item
            for idx in range(item.childCount()):
                found = recurse(item.child(idx))
                if found is not None:
                    return found
            return None

        for i in range(self.section_list.topLevelItemCount()):
            item = self.section_list.topLevelItem(i)
            found = recurse(item)
            if found is not None:
                return found
        return None

    def on_section_changed(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        if current is None:
            return

        payload = current.data(0, Qt.UserRole)
        if not payload:
            return

        if payload.get("type") == "entry":
            entry = payload["entry"]
            html = self.render_entry_html(payload["category"], entry)
            self.browser.setHtml(html)
            self.current_query = self.search_input.text().strip()
            if self.current_query:
                self.highlight_matches_from_doc(self.current_query)
            return

        if payload.get("type") == "summary":
            entry = payload["entry"]
            self.browser.setHtml(f"<h1>{entry.get('name', 'Summary')}</h1><p>{entry.get('summary', 'No summary available.')}</p>")
            return

        if payload.get("type") == "category":
            self.browser.setHtml(f"<h1>{payload['data']['label']}</h1><p>{payload['data']['count']} entries</p>")
            return

        if payload.get("type") == "section":
            section = payload["section"]
            self.browser.setHtml(section.html)
            self.highlight_matches(section)
            return

        section = payload
        if hasattr(section, "html"):
            self.browser.setHtml(section.html)
            self.highlight_matches(section)

    def highlight_matches_from_doc(self, query: str):
        if not query:
            self.browser.setExtraSelections([])
            return

        extra_selections = []
        cursor = self.browser.textCursor()
        cursor.movePosition(QTextCursor.Start)
        while True:
            cursor = self.browser.document().find(query, cursor)
            if cursor.isNull():
                break
            selection = QTextBrowser.ExtraSelection()
            selection.cursor = cursor
            selection.format = QTextCharFormat()
            selection.format.setBackground(QColor("#fff59d"))
            extra_selections.append(selection)

        self.browser.setExtraSelections(extra_selections)

    def on_search_changed(self, query: str):
        self.current_query = query.strip()

        if not self.section_list.topLevelItemCount():
            return

        if self.current_query:
            query_lower = self.current_query.lower()
            match_count = 0

            def item_matches(item):
                payload = item.data(0, Qt.UserRole) or {}
                if payload.get("type") == "section":
                    section = payload.get("section")
                    if section:
                        text = f"{section.title} {section.text}"
                        return query_lower in text.lower()
                if payload.get("type") in {"entry", "summary"}:
                    entry = payload.get("entry") or {}
                    text = f"{entry.get('name', '')} {entry.get('summary', '')} {entry.get('slug', '')}"
                    return query_lower in text.lower()
                if payload.get("type") == "category":
                    data = payload.get("data") or {}
                    return query_lower in str(data.get("label", "")).lower()
                return False

            for idx in range(self.section_list.topLevelItemCount()):
                category_item = self.section_list.topLevelItem(idx)
                category_visible = False
                for child_idx in range(category_item.childCount()):
                    entry_item = category_item.child(child_idx)
                    entry_visible = False
                    for grandchild_idx in range(entry_item.childCount()):
                        section_item = entry_item.child(grandchild_idx)
                        matches = item_matches(section_item)
                        section_item.setHidden(not matches)
                        if matches:
                            entry_visible = True
                            match_count += 1
                    if entry_item.childCount() == 0:
                        entry_visible = item_matches(entry_item)
                    entry_item.setHidden(not entry_visible)
                    if entry_visible:
                        category_visible = True
                        entry_item.setExpanded(True)
                category_item.setHidden(not category_visible)

            self.status_label.setText(f"{match_count} matching section(s) found.")
            first_visible = self.find_first_visible_item()
            if first_visible is not None:
                self.section_list.setCurrentItem(first_visible)
            else:
                self.browser.clear()
        else:
            for idx in range(self.section_list.topLevelItemCount()):
                top = self.section_list.topLevelItem(idx)
                top.setHidden(False)
                for child_idx in range(top.childCount()):
                    child = top.child(child_idx)
                    child.setHidden(False)
                    child.setExpanded(False)
            self.status_label.setText("Showing all categories and entries.")
            if self.section_list.topLevelItemCount() > 0:
                first = self.section_list.topLevelItem(0).child(0) if self.section_list.topLevelItem(0).childCount() > 0 else self.section_list.topLevelItem(0)
                self.section_list.setCurrentItem(first)
            else:
                self.browser.clear()

    def clear_search(self):
        self.search_input.clear()

    def toggle_theme(self):
        self.dark_mode = not getattr(self, "dark_mode", False)
        self.apply_theme()

    def apply_theme(self):
        if getattr(self, "dark_mode", False):
            self.theme_button.setText("Switch to Light Mode")
            self.setStyleSheet(
                "QWidget { background-color: #2b2b2b; color: #f0f0f0; }"
                "QLineEdit, QTextBrowser, QTreeWidget { background-color: #313131; color: #f0f0f0; }"
                "QTextBrowser { color: #f0f0f0; }"
                "QTextBrowser a:link, QTextBrowser a:visited { color: #7fa8ff; }"
                "QTextBrowser a:hover { color: #9cc2ff; }"
                "QPushButton { background-color: #3c3f41; color: #f0f0f0; border: 1px solid #5a5a5a; }"
                "QPushButton:hover { background-color: #4a4d4f; }"
                "QLabel { color: #f0f0f0; }"
                "QTreeWidget::item:selected { background-color: #5a7fbf; color: #ffffff; }"
            )
            self.update_browser_link_style("dark")
        else:
            self.theme_button.setText("Switch to Dark Mode")
            self.setStyleSheet(
                "QWidget { background-color: #f2f2f2; color: #202020; }"
                "QLineEdit, QTextBrowser, QTreeWidget { background-color: #ffffff; color: #202020; }"
                "QTextBrowser { color: #202020; }"
                "QTextBrowser a:link, QTextBrowser a:visited { color: #4a79b8; }"
                "QTextBrowser a:hover { color: #6c92cf; }"
                "QPushButton { background-color: #e0e0e0; color: #202020; border: 1px solid #b0b0b0; }"
                "QPushButton:hover { background-color: #d0d0d0; }"
                "QLabel { color: #202020; }"
            )
            self.update_browser_link_style("light")

    def update_browser_link_style(self, theme: str = "dark"):
        if theme == "dark":
            link_color = "#7fa8ff"
            hover_color = "#9cc2ff"
        else:
            link_color = "#4a79b8"
            hover_color = "#6c92cf"
        self.browser.document().setDefaultStyleSheet(
            f"a {{ color: {link_color}; text-decoration: none; }}"
            f"a:hover {{ color: {hover_color}; text-decoration: underline; }}"
        )

    def on_anchor_clicked(self, url: QUrl):
        if url.isLocalFile():
            file_path = Path(url.toLocalFile())
            if file_path.exists():
                anchor = url.fragment()
                self.load_markdown_file(file_path, anchor)
            return

        target = url.toString()
        if target.startswith("#"):
            anchor = target[1:]
            item = self.find_item_by_anchor(anchor)
            if item is not None:
                self.section_list.setCurrentItem(item)
            return

        if url.scheme() in ("http", "https"):
            QDesktopServices.openUrl(url)
            return

        if target.endswith(".md") or ".md#" in target:
            file_path = self.resolve_link_path(target)
            if file_path.exists():
                anchor = None
                if "#" in target:
                    file_path, anchor = target.split("#", 1)
                    file_path = self.resolve_link_path(file_path)
                if file_path.exists():
                    self.load_markdown_file(file_path, anchor)
            return

        return

    def build_link_href(self, target: str) -> str:
        if target.startswith("#"):
            return target
        if target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:"):
            return target

        raw_target, _, fragment = target.partition("#")
        target_path = Path(raw_target)
        if not target_path.is_absolute() and self.current_file_path is not None:
            target_path = (self.current_file_path.parent / target_path).resolve()

        if target_path.suffix.lower() == ".md" and target_path.exists():
            url = QUrl.fromLocalFile(str(target_path))
            if fragment:
                url.setFragment(fragment)
            return url.toString()

        return target

    def resolve_link_path(self, target: str) -> Path:
        raw_target, _, _ = target.partition("#")
        target_path = Path(raw_target)
        if not target_path.is_absolute() and self.current_file_path is not None:
            target_path = (self.current_file_path.parent / target_path).resolve()
        return target_path

    def load_markdown_file(self, file_path: Path, anchor: str = None, record_history: bool = True):
        file_path = file_path.resolve()
        if record_history and self.current_file_path is not None:
            current_anchor = None
            current_item = self.section_list.currentItem()
            if current_item is not None:
                current_section = current_item.data(0, Qt.UserRole)
                if current_section is not None:
                    current_anchor = current_section.anchor
            self.history.append((self.current_file_path, current_anchor))
            self.back_button.setEnabled(True)

        self.current_file_path = file_path
        text = self.current_file_path.read_text(encoding="utf-8")
        self.sections = self.parse_markdown_sections(text)
        if not self.sections:
            self.status_label.setText(f"No sections were found in {self.current_file_path.name}.")
            self.browser.clear()
            return

        self.populate_section_list(self.sections)
        self.status_label.setText(f"Loaded {self.current_file_path.name}. Use search to filter sections.")
        first_item = self.find_first_visible_item()
        if first_item is not None:
            self.section_list.setCurrentItem(first_item)
        if anchor:
            item = self.find_item_by_anchor(anchor)
            if item is not None:
                self.section_list.setCurrentItem(item)

    def go_home(self):
        if self.current_file_path is None:
            return
        home_path = Path(__file__).resolve().parent.parent / "daggerheart-srd" / "README.md"
        if home_path.exists():
            self.load_markdown_file(home_path)

    def go_back(self):
        if not self.history:
            return
        file_path, anchor = self.history.pop()
        self.back_button.setEnabled(bool(self.history))
        self.load_markdown_file(file_path, anchor, record_history=False)

    def highlight_matches(self, section: RuleSection):
        if not self.current_query:
            self.browser.setExtraSelections([])
            return

        extra_selections = []
        cursor = self.browser.textCursor()
        cursor.movePosition(QTextCursor.Start)

        options = QTextDocument.FindFlags()
        while True:
            cursor = self.browser.document().find(self.current_query, cursor, options)
            if cursor.isNull():
                break
            selection = QTextBrowser.ExtraSelection()
            selection.cursor = cursor
            selection.format = QTextCharFormat()
            selection.format.setBackground(QColor("#fff59d"))
            extra_selections.append(selection)

        self.browser.setExtraSelections(extra_selections)


def main():
    app = QApplication(sys.argv)
    viewer = DaggerheartViewer()
    viewer.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

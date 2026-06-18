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
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class RuleSection:
    def __init__(self, title: str, html: str, text: str, anchor: str):
        self.title = title
        self.html = html
        self.text = text
        self.anchor = anchor


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

        self.home_button = QPushButton("Home")
        self.home_button.clicked.connect(self.go_home)

        self.theme_button = QPushButton("Switch to Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)

        self.status_label = QLabel("Loading Daggerheart rules...")
        self.status_label.setWordWrap(True)

        self.section_list = QListWidget()
        self.section_list.currentItemChanged.connect(self.on_section_changed)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.anchorClicked.connect(self.on_anchor_clicked)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.search_input)
        controls_layout.addWidget(self.clear_button)
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
        splitter.setStretchFactor(1, 2)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(splitter)

        self.current_file_path = None
        self.dark_mode = True
        self.apply_theme()

        self.load_rules()

    def load_rules(self):
        readme_path = Path(__file__).resolve().parent.parent / "daggerheart-srd" / "README.md"
        if not readme_path.exists():
            QMessageBox.critical(
                self,
                "File Not Found",
                f"Could not find README at {readme_path}.\nPlease place the daggerheart-srd repository adjacent to this project.",
            )
            self.status_label.setText("README.md not found.")
            return

        self.load_markdown_file(readme_path)

    def parse_markdown_sections(self, markdown_text: str):
        lines = markdown_text.splitlines()
        sections = []
        current_lines = []
        current_title = "Introduction"
        current_anchor = "intro"

        def push_section():
            nonlocal current_lines, current_title, current_anchor
            if not current_lines:
                return
            html = self.convert_markdown_to_html(current_lines)
            plain_text = self.strip_html(html)
            sections.append(RuleSection(current_title, html, plain_text, current_anchor))
            current_lines = []

        for line in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
            if heading_match:
                push_section()
                hashes, title = heading_match.groups()
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
            href = self.build_link_href(target)
            return f"<a href='{href}'>{label}</a>"

        text = re.sub(r"\[(.*?)\]\((.*?)\)", replace_link, text)
        return text

    def strip_html(self, html: str):
        text = re.sub(r"<[^>]+>", "", html)
        return text

    def populate_section_list(self, sections):
        self.section_list.clear()
        for section in sections:
            item = QListWidgetItem(section.title)
            item.setData(Qt.UserRole, section)
            self.section_list.addItem(item)

    def on_section_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current is None:
            return
        section = current.data(Qt.UserRole)
        if not section:
            return
        self.browser.setHtml(section.html)
        self.highlight_matches(section)

    def on_search_changed(self, query: str):
        self.current_query = query.strip()
        if not self.sections:
            return
        filtered = []
        if self.current_query:
            query_lower = self.current_query.lower()
            for section in self.sections:
                if query_lower in section.text.lower() or query_lower in section.title.lower():
                    filtered.append(section)
            self.status_label.setText(f"{len(filtered)} matching section(s) found.")
        else:
            filtered = self.sections
            self.status_label.setText("Showing all sections.")

        self.populate_section_list(filtered)
        if filtered:
            self.section_list.setCurrentRow(0)
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
                "QLineEdit, QTextBrowser, QListWidget { background-color: #313131; color: #f0f0f0; }"
                "QPushButton { background-color: #3c3f41; color: #f0f0f0; border: 1px solid #5a5a5a; }"
                "QPushButton:hover { background-color: #4a4d4f; }"
                "QLabel { color: #f0f0f0; }"
                "QListWidget::item:selected { background-color: #5a7fbf; color: #ffffff; }"
            )
        else:
            self.theme_button.setText("Switch to Dark Mode")
            self.setStyleSheet(
                "QWidget { background-color: #f2f2f2; color: #202020; }"
                "QLineEdit, QTextBrowser, QListWidget { background-color: #ffffff; color: #202020; }"
                "QPushButton { background-color: #e0e0e0; color: #202020; border: 1px solid #b0b0b0; }"
                "QPushButton:hover { background-color: #d0d0d0; }"
                "QLabel { color: #202020; }"
            )

    def on_anchor_clicked(self, url: QUrl):
        if url.isLocalFile():
            file_path = Path(url.toLocalFile())
            anchor = url.fragment()
            if file_path.exists():
                self.load_markdown_file(file_path, anchor)
            return

        target = url.toString()
        if target.startswith("#"):
            anchor = target[1:]
            for row in range(self.section_list.count()):
                item = self.section_list.item(row)
                section = item.data(Qt.UserRole)
                if section and section.anchor == anchor:
                    self.section_list.setCurrentRow(row)
                    break
            return

        if url.scheme() in ("http", "https"):
            QDesktopServices.openUrl(url)
            return

        if url.isLocalFile() or target.startswith("file:"):
            file_path = Path(url.toLocalFile())
            anchor = url.fragment()
            if file_path.exists():
                self.load_markdown_file(file_path, anchor)
            return

        if target.endswith(".md") or ".md#" in target:
            file_path = self.resolve_link_path(target)
            anchor = None
            if "#" in target:
                file_path, anchor = target.split("#", 1)
                file_path = self.resolve_link_path(file_path)
            if file_path and file_path.exists():
                self.load_markdown_file(file_path, anchor)
            return

        QDesktopServices.openUrl(url)

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

    def load_markdown_file(self, file_path: Path, anchor: str = None):
        self.current_file_path = file_path.resolve()
        text = self.current_file_path.read_text(encoding="utf-8")
        self.sections = self.parse_markdown_sections(text)
        if not self.sections:
            self.status_label.setText(f"No sections were found in {self.current_file_path.name}.")
            self.browser.clear()
            return

        self.populate_section_list(self.sections)
        self.status_label.setText(f"Loaded {self.current_file_path.name}. Use search to filter sections.")
        self.section_list.setCurrentRow(0)
        if anchor:
            for row in range(self.section_list.count()):
                item = self.section_list.item(row)
                section = item.data(Qt.UserRole)
                if section and section.anchor == anchor:
                    self.section_list.setCurrentRow(row)
                    break

    def go_home(self):
        if self.current_file_path is None:
            return
        home_path = Path(__file__).resolve().parent.parent / "daggerheart-srd" / "README.md"
        if home_path.exists():
            self.load_markdown_file(home_path)

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

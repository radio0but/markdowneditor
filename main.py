import sys
from markdown import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from PySide6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QTextBrowser, QVBoxLayout,
                               QWidget, QPushButton, QHBoxLayout, QToolBar,  QMenuBar, QMenu,QFileDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QSyntaxHighlighter, QTextCharFormat, QColor
import re
import json
import os


GITHUB_CSS = """
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
        font-size: 14px;
        line-height: 1.5;
        word-wrap: break-word;
        color: black;
    }
    
    pre {
        padding: 16px;
        overflow: auto;
        font-size: 85%;
        line-height: 1.45;
        background-color: #48453D;
        color: white;
        border-radius: 6px;
    }
    
    code {
        padding: 0.2em 0.4em;
        margin: 0;
        font-size: 85%;
        background-color: #48453D;
        color: white;
        border-radius: 6px;
    }
    
    pre > code {
        padding: 0;
        margin: 0;
        font-size: 100%;
        word-break: normal;
        background-color: transparent;
        border: 0;
    }
    
    .highlight {
        margin-bottom: 16px;
    }
/* Styles for dark theme */
.dark-theme body {
    background-color: black;
    color: white;
}
.dark-theme code, .dark-theme pre {
    background-color: #2e2e2e;  /* You can choose any dark color */
    color: #c5c8c6;  /* You can choose any light color */
}

/* Styles for light theme */
.light-theme body {
    background-color: white;
    color: black;
}
.light-theme code, .light-theme pre {
    background-color: #f5f5f5;  /* You can choose any light color */
    color: #333333;  /* You can choose any dark color */
}

"""
class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super(MarkdownHighlighter, self).__init__(parent)
        self.init_rules()

    def init_rules(self):
        # Initialize the highlighting rules

        # Headers
        headers_format = QTextCharFormat()
        headers_format.setFontWeight(80)
        headers_format.setForeground(QColor("orange"))
        self.h1_rule = (r'^# .+', headers_format)
        self.h2_rule = (r'^## .+', headers_format)
        self.h3_rule = (r'^### .+', headers_format)
        self.h4_rule = (r'^#### .+', headers_format)
        self.rules = [self.h1_rule, self.h2_rule, self.h3_rule, self.h4_rule]

        # Bold & Italic
        bold_format = QTextCharFormat()
        bold_format.setFontWeight(75)
        self.bold_rule = (r'\*\*.*\*\*', bold_format)

        italic_format = QTextCharFormat()
        italic_format.setFontItalic(True)
        self.italic_rule = (r'\*.*\*', italic_format)
        
        self.rules.extend([self.bold_rule, self.italic_rule])

        # Code
        code_format = QTextCharFormat()
        code_format.setForeground(QColor("green"))
        self.inline_code_rule = (r'`.*`', code_format)
        self.code_block_rule = (r'```.*```', code_format)
        self.rules.extend([self.inline_code_rule, self.code_block_rule])

        # Links & Images
        link_format = QTextCharFormat()
        link_format.setForeground(QColor("blue"))
        self.link_rule = (r'\[.*\]\(.*\)', link_format)
        self.image_rule = (r'!\[.*\]\(.*\)', link_format)
        self.rules.extend([self.link_rule, self.image_rule])

    def highlightBlock(self, text):
        for pattern, format in self.rules:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end - start, format)
class MarkdownEditor(QMainWindow):
    def __init__(self):
        super().__init__()

        self.github_toolbar = None
        self.non_github_toolbar = None
        self.syncing_editor_to_preview = False
        self.syncing_preview_to_editor = False
        self.recent_files_path = os.path.join(os.path.expanduser("~"), ".markdown_editor_recent_files.json")
        self.recent_files = self.load_recent_files()
        
        self.init_ui()
        self.update_recent_files_menu()
    def init_ui(self):
        self.setWindowTitle('Markdown Editor')
        # Initialize the editor here
        self.editor = QTextEdit()
        self.highlighter = MarkdownHighlighter(self.editor.document())
        self.editor.textChanged.connect(self.update_preview)



        # Menu to toggle toolbars
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)  # Try using a native menu bar
        


        # Markdown editor
        
       

        # HTML preview
        self.preview = QTextBrowser()

        # Layout
        layout = QHBoxLayout()
        layout.addWidget(self.editor)
        layout.addWidget(self.preview)
        self.preview.setStyleSheet(GITHUB_CSS.replace('.dark-theme', '.light-theme'))
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Toolbars
        self.create_github_toolbar()
        self.create_non_github_toolbar()

        # Sync scrolling
        self.editor.verticalScrollBar().valueChanged.connect(self.sync_preview_scroll)
        self.preview.verticalScrollBar().valueChanged.connect(self.sync_editor_scroll)
        self.create_menus()

        self.show()
    def add_to_recent_files(self, file_path):
        """Add a file path to the recent files list and save it."""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:10]  # Keep only the last 10 opened files
        self.save_recent_files()

    def save_recent_files(self):
        """Save recent files to a JSON file."""
        with open(self.recent_files_path, 'w') as file:
            json.dump(self.recent_files, file)

    def load_recent_files(self):
        """Load recent files from a JSON file."""
        try:
            if os.path.exists(self.recent_files_path):
                with open(self.recent_files_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
        except Exception as e:
            print(f"Error loading recent files: {e}")
        return []


    def update_recent_files_menu(self):
        """Update the recent files in the File menu."""
        if hasattr(self, "recent_files_menu"):
            self.file_menu.removeAction(self.recent_files_menu.menuAction())

        self.recent_files_menu = QMenu("Recent Files", self)
        for file_path in self.recent_files:
            action = QAction(file_path, self)
            action.triggered.connect(lambda p=file_path: self.open_specific_file(p))
            self.recent_files_menu.addAction(action)
        
        self.file_menu.addMenu(self.recent_files_menu)

    def open_specific_file(self, file_path):
        """Open a specific file given its path."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.editor.setText(file.read())
            self.current_file_path = file_path
            self.add_to_recent_files(file_path)
            self.update_recent_files_menu()
        except Exception as e:
            print(f"Error opening file: {e}")
    def update_preview(self):
        markdown_text = self.editor.toPlainText()
        html = markdown(markdown_text, extensions=[CodeHiliteExtension(linenums=False)])
        self.preview.document().setDefaultStyleSheet(GITHUB_CSS)
        base_url = self.current_file_path if hasattr(self, 'current_file_path') else "."
        self.preview.setSearchPaths([base_url])
        self.preview.setHtml(html)


    def wrap_text(self, prefix, suffix):
        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText()
        cursor.insertText(f'{prefix}{selected_text}{suffix}')

    def create_github_toolbar(self):
        self.github_toolbar = QToolBar("GitHub Toolbar")
        self.addToolBar(self.github_toolbar)

        actions = [
            ("Bold", '**', '**'),
            ("Italic", '_', '_'),
            ("H1", '# ', ''),
            ("H2", '## ', ''),
            ("H3", '### ', ''),
            ("Image", '![Alt text](URL)', ''),
            ("Link", '[Link text](URL)', ''),
            ("Code Block", '```', '```')
        ]
        for name, prefix, suffix in actions:
            action = QAction(name, self)
            action.triggered.connect(lambda p=prefix, s=suffix: self.wrap_text(p, s))
            self.github_toolbar.addAction(action)

    def create_non_github_toolbar(self):
        self.non_github_toolbar = QToolBar("Non-GitHub Toolbar")
        self.addToolBar(Qt.BottomToolBarArea, self.non_github_toolbar)

        actions = [
            ("Underline", '<u>', '</u>'),
            ("Align Left", '<div style="text-align:left;">', '</div>'),
            ("Align Center", '<div style="text-align:center;">', '</div>'),
            ("Align Right", '<div style="text-align:right;">', '</div>')
        ]
        for name, prefix, suffix in actions:
            action = QAction(name, self)
            action.triggered.connect(lambda p=prefix, s=suffix: self.wrap_text(p, s))
            self.non_github_toolbar.addAction(action)

    def toggle_toolbar_visibility(self, toolbar):
        def toggler():
            toolbar.setVisible(not toolbar.isVisible())
        return toggler
    def sync_preview_scroll(self, value):
        if self.syncing_preview_to_editor:
            return
        
        self.syncing_editor_to_preview = True

        # Calculate the percentage of how far we've scrolled in the editor
        editor_scroll_percentage = value / (self.editor.verticalScrollBar().maximum() - self.editor.verticalScrollBar().minimum())

        # Calculate the corresponding value for the preview's scroll bar
        new_preview_value = editor_scroll_percentage * (self.preview.verticalScrollBar().maximum() - self.preview.verticalScrollBar().minimum())
        self.preview.verticalScrollBar().setValue(new_preview_value)

        self.syncing_editor_to_preview = False

    def sync_editor_scroll(self, value):
        if self.syncing_editor_to_preview:
            return
        
        self.syncing_preview_to_editor = True

        # Calculate the percentage of how far we've scrolled in the preview
        preview_scroll_percentage = value / (self.preview.verticalScrollBar().maximum() - self.preview.verticalScrollBar().minimum())

        # Calculate the corresponding value for the editor's scroll bar
        new_editor_value = preview_scroll_percentage * (self.editor.verticalScrollBar().maximum() - self.editor.verticalScrollBar().minimum())
        self.editor.verticalScrollBar().setValue(new_editor_value)

        self.syncing_preview_to_editor = False

    def create_menus(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = QMenu("File", self)
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        self.file_menu = file_menu
        menu_bar.addMenu(file_menu)

        # Edit Menu
        edit_menu = QMenu("Edit", self)

        actions = [
            ("Copy", self.editor.copy),
            ("Cut", self.editor.cut),
            ("Paste", self.editor.paste),
            ("Select All", self.editor.selectAll),
            # Implement search and replace functionality as needed
        ]
        for name, func in actions:
            action = QAction(name, self)
            action.triggered.connect(func)
            edit_menu.addAction(action)

        menu_bar.addMenu(edit_menu)

        # View Menu
        view_menu = QMenu("View", self)
        toggle_github_toolbar = QAction("Toggle GitHub Toolbar", self)
        toggle_github_toolbar.triggered.connect(self.toggle_toolbar_visibility(self.github_toolbar))
        view_menu.addAction(toggle_github_toolbar)

        toggle_non_github_toolbar = QAction("Toggle Non-GitHub Toolbar", self)
        toggle_non_github_toolbar.triggered.connect(self.toggle_toolbar_visibility(self.non_github_toolbar))
        view_menu.addAction(toggle_non_github_toolbar)
        toggle_theme_action = QAction("Toggle Theme", self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_action)
        menu_bar.addMenu(view_menu)

    def new_file(self):
        self.editor.clear()

    def open_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Markdown File", "", "Markdown Files (*.md);;All Files (*)", options=options)
        if file_name:
            self.open_specific_file(file_name)
            self.add_to_recent_files(file_name)
            self.update_recent_files_menu()


    def save_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Markdown File", "", "Markdown Files (*.md);;All Files (*)", options=options)
        if file_name:
            with open(file_name, 'w') as file:
                file.write(self.editor.toPlainText())
            self.current_file_path = file_name
    def toggle_theme(self):
        # Get the current stylesheet of the preview
        current_stylesheet = self.preview.styleSheet()

        if ".dark-theme" in current_stylesheet:
            # If the current theme is dark, switch to light
            self.editor.setStyleSheet("background-color: white; color: black;")
            self.preview.setStyleSheet(GITHUB_CSS.replace('.dark-theme', '.light-theme'))
        else:
            # If the current theme is light or not set, switch to dark
            self.editor.setStyleSheet("background-color: black; color: white;")
            self.preview.setStyleSheet(GITHUB_CSS.replace('.light-theme', '.dark-theme'))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = MarkdownEditor()
    sys.exit(app.exec())

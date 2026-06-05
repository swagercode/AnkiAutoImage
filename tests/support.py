from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "AnkiAutoImage"


class Signal:
	def __init__(self) -> None:
		self.callbacks = []

	def connect(self, fn) -> None:
		self.callbacks.append(fn)

	def emit(self, *args, **kwargs) -> None:
		for fn in self.callbacks:
			fn(*args, **kwargs)


class Widget:
	def __init__(self, *args, **kwargs) -> None:
		self.visible = True
		self.tooltip = ""
		self.minimum_width = None
		self.minimum_height = None

	def setVisible(self, visible: bool) -> None:
		self.visible = visible

	def setToolTip(self, text: str) -> None:
		self.tooltip = text

	def setMinimumWidth(self, value: int) -> None:
		self.minimum_width = value

	def setMinimumHeight(self, value: int) -> None:
		self.minimum_height = value


class QDialog(Widget):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.title = ""
		self.accepted = False
		self.rejected = False

	def setWindowTitle(self, title: str) -> None:
		self.title = title

	def exec(self):
		return 0

	def accept(self) -> None:
		self.accepted = True

	def reject(self) -> None:
		self.rejected = True


class Layout:
	def __init__(self, *args, **kwargs) -> None:
		self.children = []
		if args and isinstance(args[0], Widget):
			args[0].layout = self

	def addWidget(self, widget) -> None:
		self.children.append(widget)

	def addLayout(self, layout) -> None:
		self.children.append(layout)

	def setContentsMargins(self, *args) -> None:
		self.margins = args


class QVBoxLayout(Layout):
	pass


class QHBoxLayout(Layout):
	pass


class QFormLayout(Layout):
	class FieldGrowthPolicy:
		AllNonFixedFieldsGrow = 1

	def setFieldGrowthPolicy(self, policy) -> None:
		self.policy = policy

	def addRow(self, label, widget) -> None:
		self.children.append((label, widget))


class QScrollArea(Widget):
	def setWidgetResizable(self, value: bool) -> None:
		self.resizable = value

	def setWidget(self, widget) -> None:
		self._widget = widget

	def widget(self):
		return getattr(self, "_widget", None)


class QTabWidget(Widget):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.tabs = []

	def addTab(self, widget, title: str) -> None:
		self.tabs.append((widget, title))


class QLabel(Widget):
	def __init__(self, text: str = "", *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.text = text

	def setText(self, text: str) -> None:
		self.text = text


class QLineEdit(Widget):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self._text = ""
		self.placeholder = ""

	def setText(self, text: str) -> None:
		self._text = text

	def text(self) -> str:
		return self._text

	def setPlaceholderText(self, text: str) -> None:
		self.placeholder = text


class QCheckBox(Widget):
	def __init__(self, text: str = "", *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.text = text
		self._checked = False

	def setChecked(self, value: bool) -> None:
		self._checked = bool(value)

	def isChecked(self) -> bool:
		return self._checked


class QSpinBox(Widget):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self._value = 0
		self.range = (0, 99)
		self.special_text = ""

	def setRange(self, low: int, high: int) -> None:
		self.range = (low, high)

	def setSpecialValueText(self, text: str) -> None:
		self.special_text = text

	def setValue(self, value: int) -> None:
		self._value = int(value)

	def value(self) -> int:
		return self._value


class QComboBox(Widget):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.items = []
		self.data = []
		self.index = -1
		self.editable = False
		self.edit_text = ""
		self.currentTextChanged = Signal()

	def addItem(self, text: str, data=None) -> None:
		self.items.append(text)
		self.data.append(data)
		if self.index < 0:
			self.index = 0

	def addItems(self, items) -> None:
		for item in items:
			self.addItem(item, item)

	def clear(self) -> None:
		self.items.clear()
		self.data.clear()
		self.index = -1
		self.edit_text = ""

	def count(self) -> int:
		return len(self.items)

	def itemData(self, index: int):
		return self.data[index]

	def itemText(self, index: int) -> str:
		return self.items[index]

	def setCurrentIndex(self, index: int) -> None:
		self.index = index

	def currentIndex(self) -> int:
		return self.index

	def currentData(self):
		if 0 <= self.index < len(self.data):
			return self.data[self.index]
		return None

	def currentText(self) -> str:
		if self.editable and self.edit_text:
			return self.edit_text
		if 0 <= self.index < len(self.items):
			return self.items[self.index]
		return ""

	def setCurrentText(self, text: str) -> None:
		if text in self.items:
			self.index = self.items.index(text)
		elif self.editable:
			self.edit_text = text

	def setEditable(self, value: bool) -> None:
		self.editable = bool(value)

	def isEditable(self) -> bool:
		return self.editable

	def setEditText(self, text: str) -> None:
		self.edit_text = text

	def blockSignals(self, value: bool) -> None:
		self.blocked = value


class QPushButton(Widget):
	def __init__(self, text: str = "", *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.text = text
		self.clicked = Signal()


class QDialogButtonBox(Widget):
	class StandardButton:
		Save = 1
		Cancel = 2
		RestoreDefaults = 4

	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.accepted = Signal()
		self.rejected = Signal()
		self._buttons = {
			self.StandardButton.Save: QPushButton("Save"),
			self.StandardButton.Cancel: QPushButton("Cancel"),
			self.StandardButton.RestoreDefaults: QPushButton("RestoreDefaults"),
		}

	def button(self, which):
		return self._buttons.get(which)


class QAction(Widget):
	def __init__(self, text: str = "", *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.text = text
		self.triggered = Signal()


class QShortcut(Widget):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.sequence = args[0] if args else None
		self.parent = args[1] if len(args) > 1 else None
		self.activated = Signal()

	def setContext(self, context) -> None:
		self.context = context


class QKeySequence:
	def __init__(self, text: str) -> None:
		self.text = text

	def toString(self) -> str:
		return self.text


class QKeySequenceEdit(Widget):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self._sequence = QKeySequence("")
		self.clear_button_enabled = False
		self.maximum_sequence_length = None

	def setKeySequence(self, sequence) -> None:
		if isinstance(sequence, QKeySequence):
			self._sequence = sequence
		else:
			self._sequence = QKeySequence(str(sequence or ""))

	def keySequence(self) -> QKeySequence:
		return self._sequence

	def setClearButtonEnabled(self, value: bool) -> None:
		self.clear_button_enabled = bool(value)

	def setMaximumSequenceLength(self, value: int) -> None:
		self.maximum_sequence_length = int(value)


class Qt:
	class ShortcutContext:
		ApplicationShortcut = 1


class AddonManager:
	def __init__(self) -> None:
		self.config = {}
		self.written = None

	def getConfig(self, package: str):
		return dict(self.config)

	def writeConfig(self, package: str, conf: dict) -> None:
		self.written = dict(conf)

	def setConfigAction(self, *args, **kwargs) -> None:
		pass


class MainWindow:
	def __init__(self) -> None:
		self.addonManager = AddonManager()
		self.form = types.SimpleNamespace(menuTools=types.SimpleNamespace(addMenu=lambda name: types.SimpleNamespace(addAction=lambda action: None)))


def install_anki_stubs() -> MainWindow:
	mw = MainWindow()
	qt = types.ModuleType("aqt.qt")
	for name, value in {
		"QAction": QAction,
		"QCheckBox": QCheckBox,
		"QComboBox": QComboBox,
		"QDialog": QDialog,
		"QDialogButtonBox": QDialogButtonBox,
		"QFormLayout": QFormLayout,
		"QHBoxLayout": QHBoxLayout,
		"QKeySequence": QKeySequence,
		"QKeySequenceEdit": QKeySequenceEdit,
		"QLabel": QLabel,
		"QLineEdit": QLineEdit,
		"QPushButton": QPushButton,
		"QScrollArea": QScrollArea,
		"QShortcut": QShortcut,
		"QSpinBox": QSpinBox,
		"QTabWidget": QTabWidget,
		"QVBoxLayout": QVBoxLayout,
		"QWidget": Widget,
		"Qt": Qt,
	}.items():
		setattr(qt, name, value)
	qt.qconnect = lambda signal, fn: signal.connect(fn) if hasattr(signal, "connect") else None

	aqt = types.ModuleType("aqt")
	aqt.mw = mw
	aqt.qt = qt
	utils = types.ModuleType("aqt.utils")
	utils.opened_links = []
	utils.openLink = lambda link: utils.opened_links.append(str(link))
	utils.showInfo = lambda *args, **kwargs: None
	utils.showWarning = lambda *args, **kwargs: None

	anki = types.ModuleType("anki")
	notes = types.ModuleType("anki.notes")
	collection = types.ModuleType("anki.collection")
	notes.Note = dict
	collection.Collection = object
	anki.notes = notes
	anki.collection = collection

	sys.modules["aqt"] = aqt
	sys.modules["aqt.qt"] = qt
	sys.modules["aqt.utils"] = utils
	sys.modules["anki"] = anki
	sys.modules["anki.notes"] = notes
	sys.modules["anki.collection"] = collection
	return mw


def load_addon_module(module_name: str):
	if str(ROOT) not in sys.path:
		sys.path.insert(0, str(ROOT))
	install_anki_stubs()
	if PACKAGE not in sys.modules:
		pkg = types.ModuleType(PACKAGE)
		pkg.__path__ = [str(ROOT)]
		sys.modules[PACKAGE] = pkg
	full_name = f"{PACKAGE}.{module_name}"
	if full_name in sys.modules:
		return importlib.reload(sys.modules[full_name])
	return importlib.import_module(full_name)

from PySide2.QtWidgets import QHBoxLayout, QVBoxLayout, QSlider, QWidget, QLabel, QComboBox, QSpinBox, QLineEdit
from PySide2.QtCore import Slot, Signal, Qt, QTimer, QRect
from PySide2.QtGui import QMouseEvent, QColor, QPainter
import math


class LabeledComboBox(QWidget):
    currentTextChanged = Signal(str)
    def __init__(self, label_string, items=[]):
        super(LabeledComboBox, self).__init__()
        self.label = QLabel(label_string)
        self.combo_box = QComboBox(self)
        self.items = items
        for item in self.items:
            self.combo_box.addItem(item)
        self.previous_item = [None, None]
        self.combo_box.currentTextChanged.connect(self._currentTextChanged)

        ComboBoxLayout = QVBoxLayout(self)
        ComboBoxLayout.addWidget(self.label)
        ComboBoxLayout.addWidget(self.combo_box)

    def currentText(self):
        return self.combo_box.currentText()

    def _currentTextChanged(self, text):
        self.previous_item = [self.previous_item[1], self.combo_box.currentText()]
        self.currentTextChanged.emit(text)

    def revert(self):
        self.setCurrentText(self.previous_item[0], quiet=True)
        self.previous_item = [None, self.previous_item[0]]

    def setCurrentText(self, value, quiet=False):
        if quiet:
            self.combo_box.blockSignals(True)
            self.combo_box.setCurrentText(value)
            self.combo_box.blockSignals(False)
        else:
            self.combo_box.setCurrentText(value)

class LabeledSlider(QWidget):
    valueChanged = Signal(int)
    def __init__(self, label_string, orientation=Qt.Horizontal, single_step=1, page_step=10, minimum=0, maximum=100, starting_value=0):
        super(LabeledSlider, self).__init__()
        self.slider = QSlider(orientation=orientation)
        self.slider.setSingleStep(single_step)
        self.slider.setPageStep(page_step)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(starting_value)
        self.label = QLabel()
        self.label_string = label_string
        self.label.setText(self.label_string.format(starting_value))
        self.slider.valueChanged.connect(self._valueChanged)

        SliderLayout = QVBoxLayout(self)
        SliderLayout.addWidget(self.label)
        SliderLayout.addWidget(self.slider)

    def _valueChanged(self, value):
        self.label.setText(self.label_string.format(value))
        self.valueChanged.emit(value)

    def set_label_alignment(self, alignment):
        self.label.setAlignment(alignment)

    def value(self):
        return self.slider.value()

    def setValue(self, value):
        self.slider.setValue(value)
        self.label.setText(self.label_string.format(value))

    def setMinimum(self, value):
        self.slider.setMinimum(value)

    def setMaximum(self, value):
        self.slider.setMaximum(value)


class LabeledSpinBox(QWidget):
    valueChanged = Signal(int)
    def __init__(self, label_string, minimum=1, maximum=100, starting_value=0):
        super(LabeledSpinBox, self).__init__()
        self.spinbox = QSpinBox()
        self.spinbox.setRange(minimum, maximum)
        self.spinbox.setSuffix('/{}'.format(maximum))
        self.spinbox.setValue(starting_value)
        self.spinbox.valueChanged.connect(self._valueChanged)
        self.label = QLabel()
        self.label.setText(label_string)

        SpinBoxLayout = QHBoxLayout(self)
        SpinBoxLayout.addWidget(self.label)
        SpinBoxLayout.addWidget(self.spinbox)

    def setValue(self, value, quiet=False):
        if quiet:
            self.spinbox.blockSignals(True)
            self.spinbox.setValue(value)
            self.spinbox.blockSignals(False)
        else:
            self.spinbox.setValue(value)

    def value(self):
        return self.spinbox.value()

    def setRange(self, minimum, maximum):
        self.spinbox.setRange(minimum, maximum)
        self.spinbox.setSuffix("/{}".format(maximum))

    def _valueChanged(self, value):
        self.valueChanged.emit(value)


class ClickableLineEdit(QLineEdit):
    clicked = Signal(QMouseEvent)
    def __init__(self, *args, text=None, readOnly=False, **kwargs):
        super(ClickableLineEdit, self).__init__(*args, **kwargs)
        self.setText(text)
        self.setReadOnly(readOnly)

    def mousePressEvent(self, e):
        self.clicked.emit(e)

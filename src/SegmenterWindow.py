import cv2
import glob
import imghdr
import os
import tempfile
from pathlib import Path
import numpy as np

from PySide2.QtWidgets import QVBoxLayout, QHBoxLayout, QToolButton, QSpinBox, QLineEdit, QGraphicsView, QSlider, QWidget, QApplication, QFileDialog, QMainWindow, QAction, QMessageBox, QPushButton, QLabel, QGroupBox, QComboBox
from PySide2.QtGui import QPixmap, QImage
from PySide2.QtCore import Slot, Qt
from .SegmenterView import ImageSegmenterView
from .CustomClasses import LabeledComboBox, LabeledSlider, LabeledSpinBox, ClickableLineEdit
from .spinner import WaitingSpinner


def ensure_dir(*paths):
    full_path = ''
    for path in paths:
        full_path = os.path.join(full_path, path)
        if os.path.exists(full_path) and os.path.isdir(full_path):
            continue
        elif os.path.exists(full_path):
            raise ValueError("A file without an extension is blocking directory creation at {}".format(full_path))
        else:
            os.mkdir(full_path)
    return full_path


def QImage_to_CVMat(image):
    image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    width = image.width()
    height = image.height()

    ptr = image.constBits()
    arr = np.array(ptr).reshape(height, width, 4)
    return arr


class SegmenterWidget(QWidget):
    def __init__(self):
        super(SegmenterWidget, self).__init__()
        self.active_image_dir = None
        self.active_label_dir = None
        self.src_paths = []
        self.current_idx = None
        self.prev_idx = 0
        label_types = [
            'Foot',
            'Inner Wound',
            'Outer Wound'
        ]

        # Load last used image directory
        self.meta_file = os.path.join(os.path.dirname(__file__), 'meta.txt')
        if os.path.exists(self.meta_file):
            with open(self.meta_file, 'r') as f:
                last_active_image_dir = f.readline().strip()
                # print(last_active_image_dir)
                if os.path.exists(last_active_image_dir):
                    self.active_image_dir = last_active_image_dir

        # Set up Segmenter Widget
        self.image_title = QLineEdit(self)
        self.image_title.setText('--None--')
        self.image_title.setReadOnly(True)
        self.viewer = ImageSegmenterView(self)

        # Bottom Toolbar Widgets

        ## 'Set Image Folder' button
        self.select_dir_btn = QToolButton(self)
        self.select_dir_btn.setText('Set Image Folder')
        self.select_dir_btn.clicked.connect(self.set_image_dir)
        self.current_dir = ClickableLineEdit(self, text='--None--', readOnly=True)
        self.current_dir.clicked.connect(self.set_image_dir)

        self.select_label_dir_btn = QToolButton(self)
        self.select_label_dir_btn.setText('Set Label Folder')
        self.select_label_dir_btn.clicked.connect(self.set_label_dir)
        self.current_label_dir = ClickableLineEdit(self, text='--None--', readOnly=True)
        self.current_label_dir.clicked.connect(self.set_label_dir)

        self.prev_btn = QToolButton(self)
        self.prev_btn.setText('Previous Image')
        self.prev_btn.clicked.connect(self.goto_previous)
        self.image_idx = LabeledSpinBox('Current Image:',
        minimum=0,
        maximum=0,
        starting_value=0)
        self.image_idx.valueChanged.connect(self.goto_image)
        self.next_btn = QToolButton(self)
        self.next_btn.setText('Next Image')
        self.next_btn.clicked.connect(self.goto_next)
        self.skip_btn = QToolButton(self)
        self.skip_btn.setText('Next Unlabeled Image')
        self.skip_btn.clicked.connect(self.skipto_next)
        self.skip_label_btn = QToolButton(self)
        self.skip_label_btn.setText('Next Labeled Image  ')
        self.skip_label_btn.clicked.connect(self.skipto_next_label)

        ## Sliders
        self.opacity_slider = LabeledSlider('Mask Opacity: {}%',
                                            single_step=5,
                                            page_step=20,
                                            minimum=0,
                                            maximum=100,
                                            starting_value=50)
        self.opacity_slider.valueChanged.connect(self.viewer.set_opacity)
        self.pen_size_slider = LabeledSlider('Pen Size: {}px',
                                             single_step=1,
                                             page_step=5,
                                             minimum=1,
                                             maximum=100,
                                             starting_value=8)
        self.pen_size_slider.valueChanged.connect(self.viewer.set_pen_size)

        # Right Toolbar
        self.label_options = LabeledComboBox("Current Segmentation Mask", items=label_types)
        self.label_options.currentTextChanged.connect(self.label_changed)

        ## Paint Buttons
        self.brush_box = QGroupBox("Brush Options")
        self.foreground_btn = QPushButton('Foreground')
        self.foreground_btn.setCheckable(True)
        self.foreground_btn.setChecked(True)
        self.foreground_btn.setAutoExclusive(True)
        self.foreground_btn.clicked.connect(self.viewer.set_foreground)
        self.poss_foreground_btn = QPushButton("Possible Foreground")
        self.poss_foreground_btn.setCheckable(True)
        self.poss_foreground_btn.setChecked(False)
        self.poss_foreground_btn.setAutoExclusive(True)
        self.poss_foreground_btn.clicked.connect(self.viewer.set_possible_foreground)
        self.background_btn = QPushButton('Background')
        self.background_btn.setCheckable(True)
        self.background_btn.setChecked(False)
        self.background_btn.setAutoExclusive(True)
        self.background_btn.clicked.connect(self.viewer.set_background)
        self.eraser_button = QPushButton('Erase')
        self.eraser_button.setCheckable(True)
        self.eraser_button.setChecked(False)
        self.eraser_button.setAutoExclusive(True)
        self.eraser_button.clicked.connect(self.viewer.set_possible_background)
        brush_layout = QVBoxLayout()
        brush_layout.addWidget(self.foreground_btn)
        brush_layout.addWidget(self.poss_foreground_btn)
        brush_layout.addWidget(self.background_btn)
        brush_layout.addWidget(self.eraser_button)
        self.brush_box.setLayout(brush_layout)

        ## Image Action Buttons
        self.undo_btn = QToolButton(self)
        self.undo_btn.setText('Undo')
        self.undo_btn.clicked.connect(self.viewer.undo)
        self.redo_btn = QToolButton(self)
        self.redo_btn.setText('Redo')
        self.redo_btn.clicked.connect(self.viewer.redo)

        self.save_button = QToolButton(self)
        self.save_button.setText('&Save Mask')
        self.save_button.clicked.connect(self.saveSegmentation)
        self.clear_button = QToolButton(self)
        self.clear_button.setText('Clear Mask')
        self.clear_button.clicked.connect(self.viewer.resetSegLayer)

        self.gc_spinner = WaitingSpinner(self, opacity=1, radius=20, line_width=3, line_length=10)
        self.grabcut_button = QToolButton(self)
        self.grabcut_button.setText('Run &GrabCut Segmenter')
        self.grabcut_button.clicked.connect(self.run_grabcut)

        # Arrange layout
        MainLayout = QVBoxLayout(self)

        BottomStack = QVBoxLayout()

        BottomToolbar = QHBoxLayout()
        BottomToolbar.setAlignment(Qt.AlignLeft)
        Selectors = QVBoxLayout()
        ImageDirSelector = QHBoxLayout()
        ImageDirSelector.addWidget(self.select_dir_btn)
        ImageDirSelector.addWidget(self.current_dir)
        Selectors.addLayout(ImageDirSelector)
        LabelDirSelector = QHBoxLayout()
        LabelDirSelector.addWidget(self.select_label_dir_btn)
        LabelDirSelector.addWidget(self.current_label_dir)
        Selectors.addLayout(LabelDirSelector)

        BottomToolbar.addLayout(Selectors)
        BottomToolbar.addWidget(self.image_idx)
        BottomToolbar.addWidget(self.prev_btn)
        BottomToolbar.addWidget(self.next_btn)
        Skippers = QVBoxLayout()
        Skippers.addWidget(self.skip_btn)
        Skippers.addWidget(self.skip_label_btn)

        # BottomToolbar.addWidget(self.skip_btn)
        BottomToolbar.addLayout(Skippers)
        BottomStack.addLayout(BottomToolbar)

        RightToolbar = QVBoxLayout()
        RightToolbar.setAlignment(Qt.AlignCenter)
        RightToolbar.addWidget(self.label_options)
        RightToolbar.addStretch()
        RightToolbar.addWidget(self.brush_box)
        RightToolbar.addWidget(self.undo_btn)
        RightToolbar.addWidget(self.redo_btn)
        RightToolbar.addStretch()
        # self.gc_spinner.setFixedHeight(0)
        # RightToolbar.addWidget(self.gc_spinner)
        RightToolbar.addWidget(self.grabcut_button)
        RightToolbar.addWidget(self.save_button)
        RightToolbar.addWidget(self.clear_button)

        TopLayout = QHBoxLayout()
        ImageLayout = QVBoxLayout()
        ImageLayout.addWidget(self.image_title)
        ImageLayout.addWidget(self.viewer)
        TopLayout.addLayout(ImageLayout)
        TopLayout.addLayout(RightToolbar)

        MainLayout.addLayout(TopLayout)
        FlatSliders = QHBoxLayout()
        FlatSliders.addWidget(self.pen_size_slider)
        FlatSliders.addWidget(self.opacity_slider)
        MainLayout.addLayout(FlatSliders)
        MainLayout.addLayout(BottomStack)

    @Slot()
    def exit_app(self, checked):
        QApplication.quit()

    def set_image_dir(self):
        dialog = QFileDialog(self, 'Select Image Directory')
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setNameFilters(["Any Files (*)"])
        dialog.setViewMode(QFileDialog.List)
        if dialog.exec():
            selected_dir = dialog.selectedFiles()[0]
            if not os.path.isdir(selected_dir):
                selected_dir = os.path.dirname(selected_dir)
            self.active_image_dir = selected_dir
            with open(self.meta_file, 'a+') as f:
                f.write('Set Image Dir: ' + self.active_image_dir + '\n')
            if self.active_label_dir is None:
                self.active_label_dir = self.active_image_dir
                self.current_label_dir.setText(self.active_label_dir)
                with open(self.meta_file, 'a+') as f:
                    f.write('Set Label Dir: ' + self.active_label_dir + '\n')
            self.label_dir = ensure_dir(os.path.join(self.active_label_dir, self.label_options.currentText().replace(' ', '_')))
            # image_paths = glob.glob(os.path.join(self.active_image_dir, '*.png')) + glob.glob(os.path.join(self.active_image_dir, '*.jpg'))
            paths = glob.glob(os.path.join(self.active_image_dir, '*'))
            image_paths = []
            for path in paths:
                if os.path.isdir(path):
                    continue
                if imghdr.what(path) in ['jpeg', 'png', 'jpg']:
                    image_paths.append(path)
            self.src_paths = sorted(image_paths)
            self.current_dir.setText(self.active_image_dir)
            self.image_idx.setRange(1, len(self.src_paths))
            self.goto_image(1)

    def set_label_dir(self):
        dialog = QFileDialog(self, 'Select Label Directory')
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setNameFilters(["Any Files (*)"])
        dialog.setViewMode(QFileDialog.List)
        if dialog.exec():
            selected_dir = dialog.selectedFiles()[0]
            if not os.path.isdir(selected_dir):
                selected_dir = os.path.dirname(selected_dir)
            self.active_label_dir = selected_dir
            self.current_label_dir.setText(self.active_label_dir)
            with open(self.meta_file, 'a+') as f:
                f.write('Set Label Dir: ' + self.active_label_dir + '\n')
            self.label_dir = ensure_dir(os.path.join(self.active_label_dir, self.label_options.currentText().replace(' ', '_')))
            if self.active_image_dir is not None:
                image_name = os.path.basename(self.src_paths[self.current_idx])
                image_name, suff = os.path.splitext(image_name)
                self.current_label_path = os.path.join(self.label_dir, image_name + '_label.png')
                if os.path.exists(self.current_label_path):
                    self.viewer.setSegLayer(QPixmap(self.current_label_path))
                else:
                    self.viewer.resetSegLayer()
                self.viewer.changed = False

    def label_changed(self, value):
        if len(self.src_paths) > 0:
            if self.viewer.changed:
                result = self.show_save_warning()
                if result == QMessageBox.Save:
                    self.saveSegmentation()
                elif result == QMessageBox.Cancel:
                    self.label_options.revert()
                    return
                elif result == QMessageBox.Discard:
                    pass
            self.label_dir = ensure_dir(os.path.join(self.active_label_dir, value.replace(' ', '_')))
            image_name = os.path.basename(self.src_paths[self.current_idx])
            image_name, suff = os.path.splitext(image_name)
            self.current_label_path = os.path.join(self.label_dir, image_name + '_label.png')
            if os.path.exists(self.current_label_path):
                self.viewer.setSegLayer(QPixmap(self.current_label_path))
            else:
                self.viewer.resetSegLayer()
            self.viewer.changed = False

    def goto_image(self, idx):
        if len(self.src_paths) > 0:
            if self.viewer.changed:
                result = self.show_save_warning()
                if result == QMessageBox.Save:
                    self.saveSegmentation()
                elif result == QMessageBox.Cancel:
                    self.image_idx.setValue(self.prev_idx, quiet=True)
                    return
                elif result == QMessageBox.Discard:
                    pass
            self.viewer.clear_history()
            self.current_idx = idx - 1
            self.viewer.setPhoto(QPixmap(self.src_paths[self.current_idx]))
            image_name = os.path.basename(self.src_paths[self.current_idx])
            image_name, suff = os.path.splitext(image_name)
            self.image_title.setText(image_name)
            self.current_label_path = os.path.join(self.label_dir, image_name + '_label.png')
            if os.path.exists(self.current_label_path):
                self.viewer.setSegLayer(QPixmap(self.current_label_path))
            self.prev_idx = idx

    def skipto_next(self):
        # print(self.current_idx)
        if self.current_idx < len(self.src_paths):
            check_idx = self.current_idx
            # print(check_idx)
            found = False
            while check_idx < len(self.src_paths):
                # print(check_idx, len(self.src_paths))
                image_name = os.path.basename(self.src_paths[current_idx])
                image_name, suff = os.path.splitext(image_name)
                label_path = os.path.join(self.label_dir, image_name + '_label.png')
                if os.path.exists(label_path):
                    check_idx += 1
                    continue
                else:
                    found = True
                    break
            if found:
                self.image_idx.setValue(check_idx + 1)
            else:
                return QMessageBox.warning(self, "Segmenter Tool", "No unlabeled images found for label type '{}'".format(self.label_options.currentText()),
                                   QMessageBox.Ok, QMessageBox.Ok)

    def skipto_next_label(self):
        if self.current_idx < len(self.src_paths):
            check_idx = self.current_idx + 1
            found = False
            while check_idx < len(self.src_paths):
                image_name = os.path.basename(self.src_paths[check_idx])
                print(image_name)
                image_name, suff = os.path.splitext(image_name)
                label_path = os.path.join(self.label_dir, image_name + '_label.png')
                print(label_path, os.path.exists(label_path))
                if os.path.exists(label_path):
                    found = True
                    break
                else:
                    check_idx += 1
                    continue
            if found:
                self.image_idx.setValue(check_idx + 1)
            else:
                return QMessageBox.warning(self, "Segmenter Tool", "No labeled images found for label type '{}'".format(self.label_options.currentText()),
                                   QMessageBox.Ok, QMessageBox.Ok)

    def goto_next(self):
        if self.prev_idx < len(self.src_paths):
            self.image_idx.setValue(self.prev_idx + 1)

    def goto_previous(self):
        if self.prev_idx > 1:
            self.image_idx.setValue(self.prev_idx - 1)

    def saveSegmentation(self):
        if self.viewer.hasPhoto():
            segmentation = QImage_to_CVMat(self.viewer.seg_image)
            cv2.imwrite(self.current_label_path, segmentation)
            self.viewer.changed = False

    def run_grabcut(self):
        if self.viewer.hasPhoto():
            # self.gc_spinner.start()
            image = QImage_to_CVMat(QPixmap(self.src_paths[self.current_idx]).toImage())[:, :, :3]
            segmentation = QImage_to_CVMat(self.viewer.seg_image)
            pfg, fg, bg, pbg = np.split(segmentation / 255, segmentation.shape[-1], axis=-1)
            pbg = 1 - pbg
            has_bg = (pbg.sum() + bg.sum()) > 0
            has_fg = (pfg.sum() + fg.sum()) > 0
            if not (has_bg and has_fg):
                if not has_bg:
                    message = 'You must select some background or empty area.'
                elif not has_fg:
                    message = 'You must select some foreground or possible foreground.'
                x = QMessageBox.critical(self, "Segmenter Tool", message, QMessageBox.Ok)
                # self.gc_spinner.stop()
                return

            mask = (cv2.GC_FGD * fg + cv2.GC_BGD * bg + cv2.GC_PR_FGD * pfg + cv2.GC_PR_BGD * pbg).astype(np.uint8)

            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)
            mask, _, _ = cv2.grabCut(image, mask, None, bgd_model, fgd_model, 2, cv2.GC_INIT_WITH_MASK)
            pfg = np.where(mask==cv2.GC_PR_FGD, 255, 0)
            fg = np.where(mask==cv2.GC_FGD, 255, 0)
            bg = np.where(mask==cv2.GC_BGD, 255, 0)
            pbg = np.where(mask==cv2.GC_PR_BGD, 0, 255)
            new_segmentation = np.concatenate([pfg, fg, bg, pbg], axis=2).astype(np.uint8)
            tempdir = tempfile.mkdtemp()
            temp_png = os.path.join(tempdir, 'grabcut.png')
            cv2.imwrite(temp_png, new_segmentation)
            self.viewer.setSegLayer(QPixmap(temp_png))
            self.viewer.changed = True
            os.remove(temp_png)
            os.removedirs(tempdir)
            # self.gc_spinner.stop()

    def show_save_warning(self):
        return QMessageBox.warning(self, "Segmenter Tool", 'This segmentation has been modified.\nDo you want to save your changes?',
                                   QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)


class SegmenterWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("Segmenter Tool")
        self.widget = SegmenterWidget()
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")
        self.edit_menu = self.menu.addMenu("Edit")

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.widget.saveSegmentation)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.exit_app)

        undo_action = QAction("Undo", self)
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.widget.viewer.undo)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut('Shift+Ctrl+Z')
        redo_action.triggered.connect(self.widget.viewer.redo)

        grabcut_action = QAction("Run GrabCut", self)
        grabcut_action.setShortcut("Ctrl+G")
        grabcut_action.triggered.connect(self.widget.run_grabcut)

        self.file_menu.addAction(save_action)
        self.file_menu.addAction(exit_action)
        self.edit_menu.addAction(undo_action)
        self.edit_menu.addAction(redo_action)
        self.edit_menu.addAction(grabcut_action)

        self.setCentralWidget(self.widget)

    @Slot()
    def exit_app(self, checked):
        if self.widget.viewer.changed:
            result = self.widget.show_save_warning()
            if result == QMessageBox.Save:
                self.widget.saveSegmentation()
            elif result == QMessageBox.Cancel:
                return
            elif result == QMessageBox.Discard:
                pass
        QApplication.quit()

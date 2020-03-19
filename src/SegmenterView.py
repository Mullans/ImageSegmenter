from PySide2 import QtCore
from PySide2.QtCore import Signal, QPoint, Slot
from PySide2.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QFrame
from PySide2.QtGui import QColor, QBrush, QPixmap, QPainter, QImage, QPen
import collections


class ImageSegmenterView(QGraphicsView):
    photoClicked = Signal(QPoint)
    def __init__(self, parent):
        super(ImageSegmenterView, self).__init__(parent)
        self._zoom = 0
        self.empty = True
        self._scene = QGraphicsScene(self)
        self._photo = QGraphicsPixmapItem()
        self._seglayer = QGraphicsPixmapItem()
        self._seglayer.setOpacity(0.5)
        self._scene.addItem(self._photo)
        self._scene.addItem(self._seglayer)
        self.setScene(self._scene)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        # self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QtCore.Qt.darkGray))
        self.setFrameShape(QFrame.NoFrame)

        self.seg_image = None
        self.start = False
        self.prev_point = None
        self.painter = None
        self.segmenter_pen = QPen(QtCore.Qt.green, 8, QtCore.Qt.SolidLine)
        self.segmenter_pen.setCapStyle(QtCore.Qt.RoundCap)
        self.segmenter_pen.setJoinStyle(QtCore.Qt.RoundJoin)
        self.erase = False
        self.changed = False

        self.history = collections.deque(maxlen=10)
        self.future = collections.deque(maxlen=10)

    def hasPhoto(self):
        return not self.empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0

    def setPhoto(self, pixmap=None):
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self.empty = False
            self.changed = False
            self._photo.setPixmap(pixmap)
            self.seg_image = QImage(pixmap.width(), pixmap.height(), QImage.Format_ARGB32_Premultiplied)
            self.seg_image.fill(QtCore.Qt.transparent)
            self._seglayer.setPixmap(QPixmap.fromImage(self.seg_image))
        else:
            self._empty = True
            self._photo.setPixmap(QPixmap())
        self.fitInView()

    def save_state(self):
        if self.future is not None:
            while len(self.future) > 0:
                present = self.future.pop()
                del present
        if self.seg_image is not None:
            self.history.append(self.seg_image.copy())

    def clear_history(self):
        while len(self.history) > 0:
            present = self.history.pop()
            del present

    def undo(self):
        if len(self.history) > 0:
            self.future.append(self.seg_image)
            present = self.history.pop()
            self.seg_image = present
            self._seglayer.setPixmap(QPixmap.fromImage(self.seg_image))

    def redo(self):
        if len(self.future) > 0:
            self.history.append(self.seg_image)
            present = self.future.pop()
            self.seg_image = present
            self._seglayer.setPixmap(QPixmap.fromImage(self.seg_image))

    def setSegLayer(self, pixmap=None):
        if not self._photo.pixmap().isNull():
            self.save_state()
            self.seg_image = QImage(pixmap.toImage())
            self._seglayer.setPixmap(QPixmap.fromImage(self.seg_image))

    def resetSegLayer(self):
        if not self._photo.pixmap().isNull():
            self.changed = True
            self.save_state()
            del self.seg_image
            self.seg_image = QImage(self._photo.pixmap().width(), self._photo.pixmap().height(), QImage.Format_ARGB32_Premultiplied)
            self.seg_image.fill(QtCore.Qt.transparent)
            self._seglayer.setPixmap(QPixmap.fromImage(self.seg_image))

    def wheelEvent(self, event):
        if self.hasPhoto() and not self.start:
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            elif self._zoom == 0:
                self.fitInView()
            else:
                self._zoom = 0

    def mousePressEvent(self, event):
        if not self._photo.pixmap().isNull():
            if event.button() == QtCore.Qt.LeftButton:
                self.save_state()
                self.start = True
                self.painter = QPainter(self.seg_image)
                if self.erase:
                    self.painter.setCompositionMode(QPainter.CompositionMode_Clear)
                self.painter.setPen(self.segmenter_pen)
                self.paint_point(event.pos())
            elif event.button() == QtCore.Qt.RightButton:
                if not self._photo.pixmap().isNull():
                    self.setDragMode(QGraphicsView.ScrollHandDrag)
                    self.scroll_origin = self.mapToScene(event.pos())
                # if self._photo.isUnderMouse():
                #     self.photoClicked.emit(self.mapToScene(event.pos()).toPoint())
        super(ImageSegmenterView, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._photo.pixmap().isNull():
            if self.start:
                self.paint_point(event.pos())
            if event.buttons() & QtCore.Qt.RightButton:
                newpoint = self.mapToScene(event.pos())
                translation = newpoint - self.scroll_origin
                self.translate(translation.x(), translation.y())
                self.scroll_origin = self.mapToScene(event.pos())
        super(ImageSegmenterView, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self._photo.pixmap().isNull():
            if self.start:
                self.start = False
                self.prev_point = None
                self.painter.end()
            if self.dragMode() == QGraphicsView.ScrollHandDrag:
                self.setDragMode(QGraphicsView.NoDrag)

    def paint_point(self, pos):
        self.changed = True
        pos = self.mapToScene(pos).toPoint()
        if self.prev_point is not None:
            self.painter.drawLine(self.prev_point, pos)
        else:
            self.painter.drawPoint(pos)
        self.prev_point = pos
        self._seglayer.setPixmap(QPixmap.fromImage(self.seg_image))

    def set_foreground(self):
        self.erase = False
        self.segmenter_pen.setColor(QtCore.Qt.green)

    def set_possible_foreground(self):
        self.erase = False
        self.segmenter_pen.setColor(QtCore.Qt.blue)

    def set_possible_background(self):
        self.erase = True
        self.segmenter_pen.setColor(QtCore.Qt.transparent)

    def set_background(self):
        self.erase = False
        self.segmenter_pen.setColor(QtCore.Qt.red)

    def set_pen_size(self, size):
        self.segmenter_pen.setWidth(size)

    def set_opacity(self, value):
        self._seglayer.setOpacity(value / 100)

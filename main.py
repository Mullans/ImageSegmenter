from src.SegmenterWindow import SegmenterWindow
from PySide2.QtWidgets import QApplication


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = SegmenterWindow()
    window.setGeometry(100, 50, 1000, 1000)
    window.show()
    sys.exit(app.exec_())

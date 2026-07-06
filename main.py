import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import ImageConverter

def main():
    app = QApplication(sys.argv)
    window = ImageConverter()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

"""应用入口"""
import sys

from src.osm_tool.app import OSMToolApp


def main():
    """启动应用"""
    app = OSMToolApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

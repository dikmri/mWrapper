from PySide6.QtGui import QImage

from mwrapper.constants import APP_ICON_PATH


def test_app_icon_asset_exists_and_has_transparent_corner() -> None:
    assert APP_ICON_PATH.exists()

    image = QImage(str(APP_ICON_PATH))

    assert not image.isNull()
    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0

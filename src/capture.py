from pathlib import Path
from datetime import datetime

import mss


class ScreenCapture:

    def capture(self):

        folder = Path("../captures")
        folder.mkdir(exist_ok=True)

        filename = datetime.now().strftime("%Y%m%d_%H%M%S.png")

        path = folder / filename

        with mss.mss() as sct:
            sct.shot(output=str(path))

        return path
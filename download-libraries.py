from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile
destination = Path("/opt/libraries")
destination.mkdir(parents=True, exist_ok=True)
with urlopen("https://apps.mzstatic.com/content/android-apple-music-apk/applemusic.apk", timeout=180) as response:
    data = response.read()
with ZipFile(BytesIO(data)) as apk:
    for name in ("libCoreADI.so", "libstoreservicescore.so"):
        (destination / name).write_bytes(apk.read("lib/x86_64/" + name))

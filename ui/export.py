"""
export.py - put a finished file where the user can find it.

On Android 10+ the PDF is added to the public Downloads folder (Downloads/VedicAstrology/)
through MediaStore, which needs no storage permission, and can be opened straight in the phone's
PDF viewer. On older Android it goes to the app's own external folder; on desktop (tests) into
<data folder>/reports/. Fully offline; nothing is uploaded anywhere.
"""
import os


class Saved:
    def __init__(self, where, open_fn=None):
        self.where = where          # human-readable location
        self.open_fn = open_fn      # callable() -> None, or None when the file cannot be opened from here


def _android():
    try:
        from jnius import autoclass
        return autoclass
    except Exception:  # noqa: BLE001 - not on Android
        return None


def save_pdf(data, filename, fallback_dir):
    autoclass = _android()
    if autoclass is None:
        folder = os.path.join(fallback_dir, "reports")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)
        with open(path, "wb") as fh:
            fh.write(data)
        return Saved(path)

    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    sdk = autoclass("android.os.Build$VERSION").SDK_INT
    if sdk < 29:
        folder = activity.getExternalFilesDir(None).getAbsolutePath()
        path = os.path.join(folder, filename)
        with open(path, "wb") as fh:
            fh.write(data)
        return Saved(path)

    ContentValues = autoclass("android.content.ContentValues")
    Downloads = autoclass("android.provider.MediaStore$Downloads")
    values = ContentValues()
    values.put("_display_name", filename)
    values.put("mime_type", "application/pdf")
    values.put("relative_path", "Download/VedicAstrology")
    resolver = activity.getContentResolver()
    uri = resolver.insert(Downloads.EXTERNAL_CONTENT_URI, values)
    if uri is None:
        raise OSError("Android would not create the file in Downloads")
    stream = resolver.openOutputStream(uri)
    try:
        try:
            stream.write(data)
        except Exception:  # noqa: BLE001 - some pyjnius versions want an explicit bytearray
            stream.write(bytearray(data))
    finally:
        stream.close()

    def open_it():
        Intent = autoclass("android.content.Intent")
        intent = Intent(Intent.ACTION_VIEW)
        intent.setDataAndType(uri, "application/pdf")
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK)
        activity.startActivity(intent)

    return Saved("Downloads/VedicAstrology/" + filename, open_it)

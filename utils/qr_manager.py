import qrcode
import cv2
import numpy as np
from PIL import Image
import io


def generate_qr_image(data_string):
    """
    Tworzy obraz QR i zwraca go jako bufor bajtów (PNG),
    który jest zrozumiały dla st.image().
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data_string)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    buffer.seek(0)

    return buffer


def decode_qr_image(uploaded_image):
    """
    Odczytuje ciąg znaków z obrazu (UploadedFile lub BytesIO).
    Używa OpenCV.
    """
    try:
        file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)

        if data:
            return data
        return None
    except Exception as e:
        print(f"Błąd dekodowania QR: {e}")
        return None
package com.niknolig.app

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.qrcode.QRCodeWriter
import com.google.zxing.qrcode.decoder.ErrorCorrectionLevel

internal object PairingQrSupport {
    /** Black on white with a quiet zone; scanners need the contrast regardless of the dark app theme. */
    fun render(text: String, sizePx: Int): Bitmap {
        val matrix = QRCodeWriter().encode(
            text, BarcodeFormat.QR_CODE, sizePx, sizePx,
            mapOf(EncodeHintType.ERROR_CORRECTION to ErrorCorrectionLevel.M, EncodeHintType.MARGIN to 2),
        )
        val pixels = IntArray(sizePx * sizePx) { if (matrix[it % sizePx, it / sizePx]) Color.BLACK else Color.WHITE }
        return Bitmap.createBitmap(pixels, sizePx, sizePx, Bitmap.Config.ARGB_8888)
    }

    /**
     * Scans one QR code with the Google Play services code scanner (no camera permission, no image leaves the
     * scanner UI). [onResult] receives the raw text, or null when the user cancelled; [onUnavailable] is called
     * when the scanner cannot run (e.g. no Play services), in which case manual code entry remains available.
     */
    fun scan(context: Context, onResult: (String?) -> Unit, onUnavailable: () -> Unit) {
        val options = GmsBarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_QR_CODE).build()
        GmsBarcodeScanning.getClient(context, options).startScan()
            .addOnSuccessListener { onResult(it.rawValue) }
            .addOnCanceledListener { onResult(null) }
            .addOnFailureListener { onUnavailable() }
    }
}

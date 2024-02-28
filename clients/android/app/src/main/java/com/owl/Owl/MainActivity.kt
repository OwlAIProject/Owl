package com.owl.Owl

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.util.UUID

class MainActivity : AppCompatActivity() {

    private lateinit var cameraHandler: CameraHandler
    private lateinit var audioStreamer: AudioStreamer
    private val TAG = "CaptureActivity"
    private val REQUEST_PERMISSIONS = 101
    private val captureUUID: String = UUID.randomUUID().toString().replace("-", "")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        cameraHandler = CameraHandler(this, captureUUID)
        requestPermissions()
    }

    private fun requestPermissions() {
        val requiredPermissions = arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.CAMERA)
        val permissionsToRequest = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }.toTypedArray()

        if (permissionsToRequest.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, permissionsToRequest, REQUEST_PERMISSIONS)
        } else {
            permissionsGranted()
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_PERMISSIONS && grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
            permissionsGranted()
        } else {
            Log.e(TAG, "Permissions not granted by the user.")
        }
    }

    private fun permissionsGranted() {
        cameraHandler.startBackgroundThread()
        cameraHandler.openCamera()
        audioStreamer = AudioStreamer(this, captureUUID)
        audioStreamer.startStreaming()
    }

    override fun onResume() {
        super.onResume()
        cameraHandler.startBackgroundThread()
    }

    override fun onPause() {
        cameraHandler.stopBackgroundThread()
        super.onPause()
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraHandler.closeCamera()
        cameraHandler.stopBackgroundThread()
    }
}

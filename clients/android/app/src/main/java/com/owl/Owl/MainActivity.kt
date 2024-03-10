package com.owl.Owl

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.util.UUID

class MainActivity : ComponentActivity() {

    private lateinit var cameraHandler: CameraHandler
    private lateinit var audioStreamer: AudioStreamer
    private val TAG = "CaptureActivity"
    private val REQUEST_PERMISSIONS = 101
    private val captureUUID: String = UUID.randomUUID().toString().replace("-", "")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface {
                    var isCaptureStarted by remember { mutableStateOf(false) }
                    Column {
                        Button(onClick = {
                            if (isCaptureStarted) {
                                stopCapture()
                                isCaptureStarted = false
                            } else {
                                if (checkAndRequestPermissions()) {
                                    startCapture()
                                    isCaptureStarted = true
                                }
                            }
                        }) {
                            Text(if (isCaptureStarted) "Stop Local Capture" else "Start Local Capture")
                        }
                        ConversationsScreen()
                    }
                }
            }
        }
        cameraHandler = CameraHandler(this, captureUUID)
        audioStreamer = AudioStreamer(this, captureUUID)
    }

    private fun checkAndRequestPermissions(): Boolean {
        val requiredPermissions = arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.CAMERA)
        val permissionsToRequest = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }.toTypedArray()

        if (permissionsToRequest.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, permissionsToRequest, REQUEST_PERMISSIONS)
            return false
        } else {
            return true
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_PERMISSIONS && grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
            startCapture()
        } else {
            Log.e(TAG, "Permissions not granted by the user.")
        }
    }

    private fun startCapture() {
        cameraHandler.startBackgroundThread()
        cameraHandler.openCamera()
        audioStreamer.startStreaming()
    }

    private fun stopCapture() {
        cameraHandler.closeCamera()
        cameraHandler.stopBackgroundThread()
        audioStreamer.stopStreaming()
    }

    override fun onResume() {
        super.onResume()
        if (::cameraHandler.isInitialized && ::audioStreamer.isInitialized) {
            cameraHandler.startBackgroundThread()
        }
    }

    override fun onPause() {
        if (::cameraHandler.isInitialized && ::audioStreamer.isInitialized) {
            cameraHandler.stopBackgroundThread()
        }
        super.onPause()
    }

    override fun onDestroy() {
        if (::cameraHandler.isInitialized && ::audioStreamer.isInitialized) {
            cameraHandler.closeCamera()
            cameraHandler.stopBackgroundThread()
            audioStreamer.stopStreaming()
        }
        super.onDestroy()
    }
}

# Always-on Perceptive AI

[<< Home](../README.md)

## XIAO ESP32S3 Sense Board Setup and User Guide

Seeed Studio's [XIAO ESP32S3 Sense board](https://www.seeedstudio.com/XIAO-ESP32S3-Sense-p-5639.html) is an extremely compact and reasonably power-efficient development board that features BLE and WiFi connectivity, a microphone, a camera, and dual Xtensa LX7 (RISC-V-based) cores running at 240 MHz. It can be powered via its USB-C port or by soldering on a battery and placed in a small case.

This board is simple to get up and running without any modifications but for a truly wearable solution, some additional work is required. This guide will cover procurement, basic set up, and instructions for building a very crude prototype wearable.

### Table of Contents

TODO: write me

### Procurement

The XIAO ESP32S3 Sense board can be obtained from numerous vendors including Seeed Studio:

- [Seeed Studio](https://www.seeedstudio.com/XIAO-ESP32S3-Sense-p-5639.html)
- [DigiKey](https://www.digikey.com/en/products/detail/seeed-technology-co.,-ltd/113991115/18724504)
- [Mouser](https://www.mouser.com/ProductDetail/Seeed-Studio/113991115?qs=3Rah4i%252BhyCEkFZeikDKazg%3D%3D)

To build a wearable version, purchase a 3.7V lithium polymer battery. Some suggested products are listed below:

- [EEMB 1200 mAh battery](https://www.amazon.com/EEMB-Battery-1200mah-Rechargeable-Connector/dp/B09G2S88Q3) - for 8 or more hours of continuous operation.
- [EEMB 540 mAh battery](https://www.amazon.com/EEMB-Battery-Rechargeable-Lithium-Connector/dp/B09WR78RY3) - for 4 hours of continuous operation. Recommended for its compact size.

<p align="center">
<img alt="1200 mAh lithium polymer battery" src="images/xiao_esp32s3_sense/battery_eemb_1200mah.jpg"><br>
<i>A 1200 mAh 3.7V lithium polymer battery.</i>
</p>

The batteries listed above use male JST-PH 2.0 connectors. It is *highly* recommended that additional connector cables be purchased to solder onto the XIAO board rather than attempting to solder the battery directly. This allows the battery to be easily detached and swapped.

- [JPT-PH 2.0 male and female connector cables](https://www.amazon.com/Upgraded-Connector-Battery-Inductrix-Eachine/dp/B07NWD5NTN)

## Board Setup

Follow Seeed Studio's [guide for setting up the board](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/). Ensure that:

- The antenna is attached. Refer to Seeed Studio's instructions, included below. It is normal for this process to induce high blood pressure, feelings of depression and hopelessness, and violent mood swings. Just keep at it patiently.

<p align="center">
<img alt="Antenna installation" src="images/xiao_esp32s3_sense/antenna_installation.gif"><br>
<i>They make antenna installation look so easy!</i>
</p>

```
On the bottom left of the front of XIAO ESP32S3, there is a separate "WiFi/BT Antenna
Connector". In order to get better WiFi/Bluetooth signal, you need to take out the antenna
inside the package and install it on the connector.

There is a little trick to the installation of the antenna, if you press down hard on it
directly, you will find it very difficult to press and your fingers will hurt! The correct way
to install the antenna is to put one side of the antenna connector into the connector block
first, then press down a little on the other side, and the antenna will be installed.

Remove the antenna is also the case, do not use brute force to pull the antenna directly, one
side of the force to lift, the antenna is easy to take off.
```

- The Sense daughterboard, which contains the camera and microphone, is mounted onto the main board. Align the connectors and press gently and evenly until they snap into place.

<p align="center">
<img alt="Daughterboard installation" src="images/xiao_esp32s3_sense/daughterboard_installation.gif"><br>
<i>Mount the Sense daughterboard onto the main board.</i>
</p>

## Software Installation

The board firmware at `clients/xiao-esp32s3-sense` uses the Arduino SDK but with the [PlatformIO](https://platformio.org/) Visual Studio Code extension rather than the Arduino IDE. To build and flash the firmware for the first time, follow these instructions:

- [Install Visual Studio Code](https://code.visualstudio.com/download) if not already available.

- Install the PlatformIO extension. The extensions marketplace can be accessed by clicking the button in the left vertical tool bar that consists of a series of squares. Search `platformio` and install the extension.

<p align="center">
<img alt="Extensions icon" src="images/xiao_esp32s3_sense/vscode_extensions.png"><br>
<i>Location of the extensions button in Visual Studio Code.</i>
</p>

<p align="center">
<img alt="PlatformIO extension installation" src="images/xiao_esp32s3_sense/vscode_platformio.png"><br>
<i>Search for and install PlatformIO.</i>
</p>

- Open the project. From Visual Studio Code, select *File* and *Open Folder...*. Choose `clients/xiao-esp32s3-sense/firmware`, where `platformio.ini` is. It may take a moment for PlatformIO to initialize the project.

- Build the firmware by clicking the build button, located in the bottom toolbar.

<p align="center">
<img alt="Build button" src="images/xiao_esp32s3_sense/vscode_platformio_build_button.png"><br>
<i>Location of the PlatformIO build button.</i>
</p>

- A terminal window will appear showing the build progress. Ensure that `firmware.elf` is produced successfully.

<p align="center">
<img alt="Successful build output" src="images/xiao_esp32s3_sense/vscode_platformio_build_success.png"><br>
<i>Output of a successful build.</i>
</p>

- Connect the board to your PC using a USB-C cable. Upload the firmware image by clicking the upload button.

<p align="center">
<img alt="Upload button" src="images/xiao_esp32s3_sense/vscode_platformio_upload_button.png"><br>
<i>Location of the PlatformIO upload button.</i>
</p>

- Ensure that the upload was successful. If the board could not be found, try clicking on the serial port selection button to confirm that there is a usable COM port.

<p align="center">
<img alt="Successful upload output" src="images/xiao_esp32s3_sense/vscode_platformio_upload_success.png"><br>
<i>Output of a successful upload.</i>
</p>

<p align="center">
<img alt="Serial port selection button" src="images/xiao_esp32s3_sense/vscode_platformio_serial_port_button.png"><br>
<i>Location of the PlatformIO serial port button. Use this to check whether the board is connected to the computer and manually select the appropriate port if necessary.</i>
</p>

- Now the board will always run the loaded firmware until it is reprogrammed.

### Connecting to the iOS App

The firmware makes the board act as a Bluetooth peripheral that constantly broadcasts audio packets using a specific Bluetooth service ID. It must connect to an Internet-connected device in order to forward audio packets to the server. The iOS app will automatically do this.

To test with iOS:

- [Build and deploy the iOS app](ios_instructions.md).
- Ensure the server is running and that the iOS app is able to reach it.
- Power on the XIAO ESP32S3 Sense board (e.g., connect it to your PC or outlet via USB-C).
- Open the iOS app. It should indicate that the board is connected. Begin speaking and an in-progress conversation will appear.

<p align="center">
<img alt="Conversation in progress" src="images/xiao_esp32s3_sense/ios_conversation_in_progress.png"><br>
<i>iOS app indicating the XIAO ESP32S3 Sense board is connected and that a conversation is being captured.</i>
</p>

- Remove power from the board or simply stop speaking for several minutes (e.g., 5 minutes, depending on the server's conversation detection parameters). A completed conversation will appear.


<p align="center">
<img alt="Completed conversation in list" src="images/xiao_esp32s3_sense/ios_conversation_completed.png"> <img alt="Conversation details" src="images/xiao_esp32s3_sense/ios_conversation_details.png"><br>
<i>The completed test conversation.</i>
</p>

### Resources

- [Getting Started with Seeed Studio XIAO ESP32S3 (Sense)](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/)

[<< Home](../README.md)

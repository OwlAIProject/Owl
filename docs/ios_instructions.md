# Owl - Always-on Wearable AI

[<< Home](../README.md)

## iOS and watchOS Application Build Instructions

Step-by-step instructions are provided here for building and installing the iOS and watchOS apps. If you are not planning to deploy the Apple Watch app, steps involving the watchOS target can be ignored.

### 1. Install Xcode

- [Download and install Xcode](https://developer.apple.com/xcode/).
- Create the required Apple Developer Program account. This is free.

### 2. Enable Developer Mode on iPhone and Watch

- [Enable developer mode on your devices](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device). This is required in order to deploy builds from Xcode.

- On iPhone, open *Settings* and then *Privacy & Security*. Scroll to the bottom to find the *Developer Mode* option.

<p align="center">
<img alt="Signing & Capabilities" src="../docs/images/xcode/developer_mode_iphone.png"><br>
<i>Location of the Developer Mode setting under Privacy & Security on iPhone.</i>
</p>

- On Watch, developer mode can only be enabled on the device itself, not through the iPhone companion app. Open *Settings* and then *Privacy & Security*. The *Developer Mode* option is found at the bottom.

<p align="center">
<img alt="Signing & Capabilities" src="../docs/images/xcode/developer_mode_watch.png"><br>
<i>Location of the Developer Mode setting under Privacy & Security on Apple Watch.</i>
</p>

### 3. Open Xcode Project and Configure Development Team

Upon first cloning the repository, the development team values in the Xcode project will be invalid and must be manually set.

- Open the Xcode project, located at `clients/ios/Owl.xcodeproj`.

- To find the targets, select the project in the left-most file browser pane, then click on each target in the target list. The *Team* field is under *Signing & Capabilities*.

<p align="center">
<img alt="Signing & Capabilities" src="../docs/images/xcode/xcode_signing_and_capabilities.png"><br>
<i>Location of the Team field in Xcode.</i>
</p>

- Change the development team to your personal team. Do this for each target. **Tip:** You can attempt to build the project immediately and then use the issue navigator to locate all the places that *Team* must be changed.

<p align="center">
<img alt="Team selection" src="../docs/images/xcode/xcode_team_selection.png"><br>
<i>Choose a valid development team, such as your personal team.</i>
</p>

### 4. Configure Exception Domains

We **strongly** recommend running the server over HTTPS in order to ensure that conversation transcripts and audio cannot be intercepted. Remember that this affects not only you but other parties captured in your conversations. If running a server at home not associated with an HTTPS-enabled domain, use a reverse proxy like [ngrok](https://ngrok.com). If this is simply not an option or for conducting quick testing, and being mindful of the security risks involved, you must configure the iOS project to allow HTTP access to your server. By default, iOS prohibits unencrypted HTTP traffic.

- Enter the host IP address of your server in the *App Transport Security Exception* section of *Signing & Capabilities* for the main iOS and watchOS targets. This setting is found in the same dialog as the developer team setting. Add a new exception domain to the list or change the sample IP address (31.41.59.265, a placeholder).

<p align="center">
<img alt="Signing & Capabilities" src="../docs/images/xcode/xcode_signing_and_capabilities.png"><br>
<i>Exception domains are specified in the same place as development team.</i>
</p>

- **Note:** Don't forget to do this for the *Owl Watch App* target, too. The process must be performed for both the *Owl* **and** *Owl Watch App* targets!

### 5. Configure App Constants

The server address and client token (created during [server configuration](server_configuration.md)) must be entered into their respective fields in the `AppConstants` structure, found in `Shared/AppConstants.swift`.

<p align="center">
<img alt="Signing & Capabilities" src="../docs/images/xcode/xcode_app_constants.png"><br>
<i>Server address and client token must be set in `AppConstants.swift`.</i>
</p>

### 6. Build and Deploy

#### iPhone App

- Select *Owl* as the current scheme. The scheme is found near the top-center of the Xcode window, as shown below.

<p align="center">
<img alt="Scheme selection" src="../docs/images/xcode/xcode_scheme.png"><br>
<i>Location of the scheme selection drop-down on the Xcode window.</i>
</p>

- Connect your iPhone to your Mac using the appropriate cable. After enabling developer mode, your iPhone should appear in the list of supported run destinations. On the initial connection, there may be a lengthy symbol download process. Run destinations are found next to the scheme.

<p align="center">
<img alt="Run destination selection" src="../docs/images/xcode/xcode_device.png"><br>
<i>Location of the run destination selection drop-down on the Xcode window. Strictly Confidential is the physical device that will be used.</i>
</p>

- If your device does not appear, open *Devices and Simulators*, which can be found in the *Window* menu on the Xcode menu bar, and make sure it appears there and is enabled as a run destination.

- Click the play button to build and deploy to your phone. To build without deploying, select *Build* from the *Product* menu or use the Command-B keyboard shortcut.

- If any errors occur during the build or deployment process, they will be viewable in the issue navigator in the left pane.

<p align="center">
<img alt="Issue navigator showing build errors" src="../docs/images/xcode/xcode_issue_navigator.png"><br>
<i>Issue navigator showing build errors that must be addressed. In this case, the development team must be changed.</i>
</p>

#### Watch App

- Select *Owl Watch App* as the scheme. The rest of the procedure is identical to building and deploying the iPhone app. Note that deployment to Watch is often buggy and slow (this is not unique to Owl).

#### How to Fix Corrupted Projects After Git Checkout

Sometimes the Xcode project settings, particularly the schemes, become corrupted when checking out a new version of the repository. This usually manifests itself with missing schemes (e.g., *Owl* or *Owl Watch App* may be missing entirely). To fix this problem, close Xcode and issue the following command on the terminal, then open the project again.

```
rm -rf ~/Library/Developer/Xcode/DerivedData
```

### 7. Reverse Proxy for HTTPS Support

Using a reverse proxy to securely access the server is simple. Any reverse proxy can be used but instructions for [ngrok](https://ngrok.com) will be shown here.

- Install and configure ngrok by [following this guide](https://ngrok.com/docs/getting-started/). Ensure it is accessible from your path.

- Assuming the server is running on its default port of 8000, start the reverse proxy by running: `ngrok http http://localhost:8000`

- Note the public address and enter it into `AppConstants.swift`. Do not specify port 8000 (the proxy URL will automatically redirect to it). Because this is an HTTPS-capable connection, there is no need to modify the exception domains list.

- Build and deploy the iOS and watchOS apps.

[<< Home](../README.md)

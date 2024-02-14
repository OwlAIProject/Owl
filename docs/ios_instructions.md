# Always-on Perceptive AI

[<< Home](../README.md)

## iOS and watchOS Application Build Instructions

Step-by-step instructions are provided here for building and installing the iOS and watchOS apps.

### 1. Install Xcode

- [Download and install Xcode](https://developer.apple.com/xcode/).
- Create the required Apple Developer Program account. This is free.

### 2. Enable Developer Mode on iPhone and Watch

- [Enable developer mode on your devices](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device). This is required in order to deploy builds from Xcode.

### 3. Open Xcode Project and Configure Development Team

Upon first cloning the repository, the development team values in the Xcode project will be invalid and must be manually set.

- Open the Xcode project, located at `clients/ios/UntitledAI.xcodeproj`.

- To find the targets, select the project in the left-most file browser pane, then click on each target in the target list. The *Team* field is under *Signing & Capabilities*.

<p align="center">
<img alt="Signing & Capabilities" src="../docs/images/xcode/xcode_signing_and_capabilities.png"><br>
<i>Location of the Team and Exception Domains fields in Xcode.</i>
</p>

- Change the development team to your personal team. Do this for each target. **Tip:** You can attempt to build the project immediately and then use the error message pane to locate all the places that *Team* must be changed.

<p align="center">
<img alt="Team selection" src="../docs/images/xcode/xcode_team_selection.png"><br>
<i>Choose a valid development team, such as your personal team.</i>
</p>

### 4. Configure Exception Domains



### 5. Configure App Constants

### 6. Reverse Proxy for SSL Support

[<< Home](../README.md)

# AxionAOSP builds for Xiaomi Pad 6
<h2>Installation Guide</h2>
<div>
<h4>NOTE: HyperOS 2 Globa Firmware is already included in ROM</h4>

<h3>Installing Axion for the first time</h3>
<details>
  <ol>
    <li>Download the rom package along with boot,dtbo and vendor_boot(links mentioned in post)</li>
    <li>Put downloaded files in a folder(your platform tools folder preferred)</li>
    <li>reboot to bootloader(hold power + volume down button)</li>
    <li>In your pc,open terminal where you copied the above files and run the following commands:</li>
<br>
    
    fastboot flash boot boot.img
<br>

    fastboot flash dtbo dtbo.img
<br>
    
    fastboot flash vendor_boot vendor_boot.img
 <br>
 
    fastboot reboot recovery
<br>
    <li>Format data via recovery(optional if flashing on the same rom)</li>
    <li>select reboot to recovery(advanced -> reboot to recovery)</li>
    <li>select apply update in recovery</li>
    <li>In your pc terminal, run adb sideload rom.zip(replace rom.zip with the downloaded rom package name.zip)</li>
    <li>if you are flashing a vanilla build and want to flash gapps, select reboot to recovery(installation ends at 47% displayed on your pc terminal) and then sideload gapps by selecting apply update. Skip this step if you are already flashing a gapps build</li>
    <li>Reboot to system</li>
  </ol>
</details>


<h3>Updating from an existing Axion build</h3>
<details>
    <li>select reboot to recovery(advanced -> reboot to recovery)</li>
    <li>select apply update in recovery</li>
    <li>In your pc terminal, run adb sideload rom.zip(replace rom.zip with the downloaded rom package name.zip)</li>
    <li>if you are flashing a vanilla build and want to flash gapps, select reboot to recovery(installation ends at 47% displayed on your pc terminal) and then sideload gapps by selecting apply update. Skip this step if you are already flashing a gapps build</li>

</div>
</details>
<h1>Changelog</h1>

<details>
  <summary>April 11, 2025</summary>

- Rebased sm8250-common tree
- Added ZRAM, and remove SWAP
- Added a lot of powerhint changes
- Added a lot of boost changes
- Removed a lot of unneeded services
- change full changes for common <a href="https://github.com/ai94iq/android_device_xiaomi_sm8250-common/commits/axv-qpr2/">here</a></li>
</details>

<details>
  <summary>April 04, 2025</summary>
  
  - Added back Dolby Audio
  - Added back Dolby Vision
  - Added back Webcam over USB
  - Added Per app Refresh Rate under display settings
  - Added Refresh Rate QS Tile
  - Adjusted VOIP Mic configs
  - Adjusted Dolby configs for BT
  - Removed Viper4FX
</details>

<details>
  <summary>April 03, 2025</summary>

  - Removed Dolby
  - Added Viper4FX
  - Keyboard will be disabled when screen is turned off, only wake to lockscreen then stops
  - Updated Kernel
  - Updated Common Tree
  - Added Firmware to ROM ZIP
</details>

<h4>ROM is already rooted with KernelSU-Next, Install apk only to use it</h4>

<h2>Useful Links</h1>
<li>Google Apps for A15:<a href="https://github.com/MindTheGapps/15.0.0-arm64/releases">Here</a></li>
<li>KerenelSU-Next:<a href="https://github.com/KernelSU-Next/KernelSU-Next/releases">Here</a></li>

<div>
</div>
<br>

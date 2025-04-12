# axion-pipa-releases
 AxionAOSP builds for Xiaomi Pad 6
<h2>Installation Guide</h2>
<div>
<h3>NOTE: HyperOS 2 Globa Firmware is already included in ROM</h3>
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
<h3>For updating from existing Axion build</h3>
    <li>select reboot to recovery(advanced -> reboot to recovery)</li>
    <li>select apply update in recovery</li>
    <li>In your pc terminal, run adb sideload rom.zip(replace rom.zip with the downloaded rom package name.zip)</li>
    <li>if you are flashing a vanilla build and want to flash gapps, select reboot to recovery(installation ends at 47% displayed on your pc terminal) and then sideload gapps by selecting apply update. Skip this step if you are already flashing a gapps build</li>

</div>

<h4>ROM is already rooted with KernelSU-Next, Install apk only to use it</h4>

<h2>Useful Links</h1>
<li>Google Apps for A15:  <a href="https://github.com/MindTheGapps/15.0.0-arm64/releases">Here</a></li>
<li>KerenelSU-Next:  <a href="https://github.com/KernelSU-Next/KernelSU-Next/releases">Here</a></li>

<div>
</div>
<br>

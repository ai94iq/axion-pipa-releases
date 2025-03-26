#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
import time

def run_command(cmd, check=True):
    """Run a command and return its output."""
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.returncode

def check_github_auth():
    """Check if GitHub CLI is authenticated properly with correct permissions."""
    print("Checking GitHub CLI authentication...", end="", flush=True)
    result, exit_code = run_command(["gh", "auth", "status"], check=False)
    
    if exit_code != 0:
        print("\nError: GitHub CLI is not authenticated properly.")
        print(result)
        print("\nPlease run 'gh auth login' to authenticate before using this script.")
        print("You must use HTTPS with a token that has 'repo' scope for repository write access.")
        return False
    
    # Check if token has repo scope
    if "Token scopes" in result:
        scopes = result.split("Token scopes:")[1].split("\n")[0].strip()
        if "repo" not in scopes.lower():
            print("\nWarning: Your GitHub token may not have required 'repo' scope.")
            print("Current scopes:", scopes)
            print("To re-authenticate with correct scopes, run 'gh auth login'")
            print("When prompted, choose 'Generate a token' option with 'repo' scope")
            proceed = input("Do you want to proceed anyway? (y/N): ").lower()
            if proceed != 'y':
                return False
    
    print(" OK!")
    return True

def check_repository_access():
    """Check if we have proper access to the repository."""
    print("Checking repository access...", end="", flush=True)
    
    # First, try to get the current repository
    repo_cmd = ["gh", "repo", "view"]
    result, exit_code = run_command(repo_cmd, check=False)
    
    if exit_code != 0:
        print("\nError: Cannot access repository.")
        print(result)
        print("\nMake sure you're in a valid GitHub repository directory.")
        print("Or run 'gh repo set-default' to specify your repository.")
        return False
    
    # Check if we have write access
    print(f" OK! Using repository: {result.splitlines()[0]}")
    return True

def check_tag_exists(tag):
    """Check if a GitHub tag already exists and return True if it does."""
    _, exit_code = run_command(["gh", "release", "view", tag], check=False)
    return exit_code == 0

def get_unique_tag(tag):
    """Generate a unique tag if the original already exists."""
    if not check_tag_exists(tag):
        return tag
    
    print(f"Warning: A release with tag \"{tag}\" already exists.")
    
    # Try incrementing versions
    version = 2
    while check_tag_exists(f"{tag}-v{version}"):
        version += 1
    
    new_tag = f"{tag}-v{version}"
    print(f"Using new tag: {new_tag}")
    return new_tag

def get_user_notes(interactive):
    """Get release notes from user input."""
    if not interactive:
        return "- Auto-generated release"
    
    print("\nEnter up to 5 release notes (press Enter after each, type 'done' when finished):")
    print("Do not start with '-', bullets will be added automatically")
    
    notes = []
    for i in range(5):
        note = input(f"Note {i}: ")
        if not note or note.lower() == "done":
            break
        notes.append(f"- {note}")
    
    if not notes:
        return "- Auto-generated release"
    return "\n".join(notes)

def get_confirmation(auto_confirm):
    """Get user confirmation unless auto_confirm is True."""
    if auto_confirm:
        return True
    
    while True:
        response = input("Execute this command? (Y/N): ").lower()
        if response == "y":
            return True
        elif response == "n":
            return False
        else:
            print("Please enter Y or N")

def extract_tag_from_zip(zip_file):
    """Extract tag from ZIP filename."""
    match = re.search(r"(.*?-.*?-\d+).*", os.path.basename(zip_file))
    if match:
        return match.group(1)
    return None

def find_files_by_extension(extensions):
    """Find files by extension(s)."""
    files = []
    for ext in extensions:
        files.extend(list(Path(".").glob(f"*.{ext}")))
    return files

def get_matching_sha(zip_file, sha_files):
    """Get matching SHA256 file for a ZIP file if it exists."""
    sha_path = Path(f"{zip_file}.sha256sum")
    return sha_path if sha_path in sha_files else None

def add_sha_files(files_to_release, zip_files, sha_files):
    """Add matching SHA files for ZIPs to the release list."""
    result = files_to_release.copy()
    for zip_file in zip_files:
        if zip_file in files_to_release:  # Only if ZIP is selected
            sha_file = get_matching_sha(zip_file, sha_files)
            if sha_file:
                result.append(sha_file)
    return result

def fetch_recent_releases(limit=3):
    """Fetch the most recent GitHub releases."""
    print(f"Fetching {limit} most recent releases...", end="", flush=True)
    cmd = ["gh", "release", "list", "--limit", str(limit)]
    result, exit_code = run_command(cmd, check=False)
    
    if exit_code != 0:
        print("\nError: Failed to fetch recent releases.")
        print(result)
        return []
    
    print(" OK!")
    releases = []
    
    # Debug output to see actual format
    print("\nDEBUG: GitHub CLI release list format:")
    print("----------------------------------------")
    print(result[:500] if len(result) > 500 else result)
    print("----------------------------------------")
    
    for line in result.strip().split("\n"):
        if line.strip():
            parts = line.split("\t")
            if len(parts) >= 3:  # We expect at least 3 columns
                # FIXED: The correct column order from GitHub CLI is:
                # FILE, TITLE, TAG, DATE
                file_name = parts[0].strip()
                title = parts[1].strip() 
                tag = parts[2].strip().split()[0]  # The tag might have date info after it
                date = parts[3].strip() if len(parts) > 3 else "Unknown"
                
                releases.append({
                    "file": file_name,
                    "tag": tag,
                    "title": title,
                    "date": date
                })
    
    return releases

def upload_to_existing_release(tag, files_to_release):
    """Upload files to an existing release."""
    # Critical safety check
    if tag.endswith(".zip") or tag.endswith(".img") or tag.endswith(".sha256sum"):
        print(f"\nERROR: '{tag}' appears to be a filename, not a release tag!")
        print("Release tags should be short identifiers like 'axion-1.2-BETA-20250326'")
        correct_tag = input("Please enter the correct release tag: ")
        if not correct_tag:
            print("Operation cancelled - no tag provided.")
            return False
        tag = correct_tag
    
    print(f"\nUploading files to release with tag '{tag}'...")
    
    # First verify that the release exists
    print(f"Verifying release '{tag}' exists...", end="", flush=True)
    result, exit_code = run_command(["gh", "release", "view", tag], check=False)
    if exit_code != 0:
        print(f"\nError: Release with tag '{tag}' does not exist.")
        print(result)
        return False
    print(" OK!")
    
    # Build the upload command
    cmd = ["gh", "release", "upload", tag]
    for file in files_to_release:
        cmd.append(str(file))
    
    # Show final command
    print("\nFinal command to be executed:")
    print("================================")
    print(" ".join(cmd))
    print("================================")
    print()
    
    # Get confirmation and execute
    if get_confirmation(False):
        print("Executing command...")
        # For uploads, we don't need to create a release first
        # We'll just upload files directly with progress tracking
        
        file_paths = [str(file) for file in files_to_release]
        
        # Get file sizes and total size
        file_sizes = {file: os.path.getsize(file) for file in file_paths}
        total_size = sum(file_sizes.values())
        
        print(f"Total upload size: {format_size(total_size)} across {len(file_paths)} files")
        
        # Process each file individually for better tracking
        overall_start_time = time.time()
        total_uploaded = 0
        success = True
        
        for file_index, file in enumerate(file_paths):
            file_size = file_sizes[file]
            file_name = os.path.basename(file)
            
            print(f"\nUploading file {file_index + 1}/{len(file_paths)}: {file_name}")
            print(f"File size: {format_size(file_size)}")
            
            # Upload this specific file
            upload_cmd = ["gh", "release", "upload", tag, file]
            
            # Try with retries
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                if attempt > 1:
                    print(f"\nRetrying upload ({attempt}/{max_retries})...")
                
                upload_result, upload_code = run_command(upload_cmd, check=False)
                
                if upload_code == 0:
                    # Success!
                    total_uploaded += file_size
                    elapsed_time = time.time() - overall_start_time
                    overall_percentage = (total_uploaded / total_size) * 100
                    
                    print(f"✓ File {file_index+1}/{len(file_paths)} uploaded: {file_name}")
                    print(f"  Overall: {overall_percentage:5.1f}% complete • {format_size(total_uploaded)}/{format_size(total_size)} • Elapsed: {format_time(elapsed_time)}")
                    break
                    
                if attempt == max_retries:
                    print(f"\nError uploading file {file_name}:")
                    print(upload_result)
                    print(f"Failed after {max_retries} attempts.")
                    success = False
                    break
            
            if not success:
                break
        
        # Show final results
        if success:
            total_elapsed = time.time() - overall_start_time
            print(f"\nAll {len(file_paths)} files uploaded successfully!")
            print(f"Total size: {format_size(total_size)} • Completed in {format_time(total_elapsed)}")
            return True
        else:
            print("\nUpload process failed.")
            return False
    else:
        print("Operation cancelled by user.")
        return False

def interactive_mode():
    """Run the script in fully interactive mode with a menu interface."""
    print("=======================================================")
    print("             GitHub ROM Release Creator                ")
    print("=======================================================")
    
    # Check for files to release
    zip_files = find_files_by_extension(["zip"])
    img_files = find_files_by_extension(["img"])
    sha_files = find_files_by_extension(["sha256sum"])
    
    if not (zip_files or img_files):
        print("Error: No .img or .zip files found for release")
        input("Press Enter to continue...")
        return 1
    
    # Display available files
    print("\nAvailable files:")
    if zip_files:
        print("\nZIP files:")
        for i, file in enumerate(zip_files):
            print(f"  {i+1}. {file.name}")
    
    if img_files:
        print("\nIMG files:")
        for i, file in enumerate(img_files):
            print(f"  {i+1}. {file.name}")
    
    # Ask what the user wants to do
    print("\nWhat would you like to do?")
    print("1. Create a new release")
    print("2. Upload to an existing release")
    
    action_choice = ""
    while action_choice not in ["1", "2"]:
        action_choice = input("Choose an option (1-2): ")
    
    # If user chose to upload to existing release
    if action_choice == "2":
        # Fetch recent releases
        releases = fetch_recent_releases(5)  # Get more releases to show
        if not releases:
            print("No recent releases found. Creating a new release instead.")
            action_choice = "1"
        else:
            print("\nRecent releases:")
            print("  #  FILE                                  TAG                      TITLE")
            print("  -------------------------------------------------------------------------")
            for i, release in enumerate(releases):
                print(f"  {i+1}. {release['file']:<35} {release['tag']:<20} {release['title']}")
            print(f"  {len(releases)+1}. Enter a tag manually")
            
            release_choice = ""
            valid_choices = [str(i) for i in range(1, len(releases) + 2)]
            while release_choice not in valid_choices:
                release_choice = input(f"Choose a release (1-{len(releases)+1}): ")
            
            # If user chose to enter a tag manually
            if release_choice == str(len(releases) + 1):
                # Clear explanation of what a tag is
                print("\nEnter the tag name of the existing release (NOT the full filename).")
                print("Example: If your ROM is 'axion-1.2-BETA-20250326-OFFICIAL-GMS-pipa.zip',")
                print("the tag might be 'axion-1.2-BETA-20250326'")
                
                tag = input("Enter release tag: ")
                while not tag:
                    tag = input("Tag cannot be empty. Enter release tag: ")
            else:
                # Use the selected release tag from recent releases
                tag = releases[int(release_choice) - 1]["tag"]
            
            # Very important: Verify the tag exists before proceeding
            print(f"Verifying release '{tag}' exists...", end="", flush=True)
            if not check_tag_exists(tag):
                print(f"\nError: Release with tag '{tag}' does not exist.")
                print("Please check the available tags at: https://github.com/ai94iq/axion-pipa-releases/tags")
                print("You may need to create a new release instead.")
                input("Press Enter to continue...")
                return 1
            print(" OK!")
            
            # Choose which files to include
            files_to_release = select_files_for_release(zip_files, img_files, sha_files)
            
            if not files_to_release:
                print("Error: No files selected for release")
                input("Press Enter to continue...")
                return 1
            
            # Show selected files
            print("\nSelected files for release:")
            for file in files_to_release:
                print(f"  - {file.name}")
            
            # Upload files to the existing release - PASS THE CORRECT TAG
            if upload_to_existing_release(tag, files_to_release):
                input("Files uploaded successfully. Press Enter to continue...")
                return 0
            else:
                input("Failed to upload files. Press Enter to continue...")
                return 1

    # If user chose to create a new release or fallback from no releases found
    if action_choice == "1":
        # Extract tag and title from zip filename or ask user
        tag = ""
        title = ""
        
        if zip_files:
            zipname = str(zip_files[0])
            title = zipname
            tag = extract_tag_from_zip(zipname)
            
            if tag:
                print(f"\nExtracted tag: {tag}")
                change_tag = input("Do you want to use a different tag? (Y/N): ").lower()
                if change_tag == "y":
                    tag = input("Enter release tag: ")
            else:
                print("Could not extract tag from ZIP filename.")
                tag = input("Enter release tag: ")
        else:
            print("No ZIP files found. Please enter release information manually:")
            tag = input("Enter release tag: ")
            title = input("Enter release title: ")
        
        # Check if title needs to be changed
        change_title = input(f"Current title: {title}\nDo you want to change it? (Y/N): ").lower()
        if change_title == "y":
            title = input("Enter release title: ")
        
        # Check if tag already exists on GitHub and get a unique tag
        print(f"\nChecking if tag \"{tag}\" already exists...")
        tag = get_unique_tag(tag)
        
        # Get release notes
        notes = get_user_notes(True)
        
        # Choose which files to include
        files_to_release = select_files_for_release(zip_files, img_files, sha_files)
        
        if not files_to_release:
            print("Error: No files selected for release")
            input("Press Enter to continue...")
            return 1
        
        # Show selected files
        print("\nSelected files for release:")
        for file in files_to_release:
            print(f"  - {file.name}")
        
        # Build command for creating the release
        cmd = ["gh", "release", "create", tag]
        for file in files_to_release:
            cmd.append(str(file))
        # Change the order of title and notes in the command
        cmd.extend(["--notes", notes, "--title", title])
        
        # Show final command
        print("\nFinal command to be executed:")
        print("================================")
        print(" ".join(cmd))
        print("================================")
        print()
        
        # Get confirmation and execute
        if get_confirmation(False):
            print("Executing command...")
            result, exit_code = create_release_with_progress(cmd, [str(file) for file in files_to_release])
            
            # If the first method fails, try the alternative direct method
            if exit_code != 0:
                print("\nFirst method failed. Trying alternative approach...")
                result, exit_code = create_release_with_direct_command(cmd, [str(file) for file in files_to_release])
            
            if exit_code == 0:
                print("Release created successfully.")
            else:
                print(f"Error: Failed to create release\n{result}")
                print("\nPlease check your GitHub token permissions:")
                print("1. Run 'gh auth login' to re-authenticate")
                print("2. Choose GitHub.com -> HTTPS -> Generate a token (with 'repo' scope)")
                print("3. Follow the instructions to complete authentication")
                input("Press Enter to continue...")
                return 1
        
        input("Press Enter to continue...")
        return 0

def select_files_for_release(zip_files, img_files, sha_files):
    """Helper function to select which files to include in a release."""
    print("\nRelease options:")
    print("1. Release all files")
    print("2. Release only .img files")
    print("3. Release only .zip files")
    print("4. Select files individually")
    
    choice = ""
    while choice not in ["1", "2", "3", "4"]:
        choice = input("Choose release option (1-4): ")
    
    files_to_release = []
    
    if choice == "1":
        files_to_release = zip_files + img_files
    elif choice == "2":
        files_to_release = img_files
    elif choice == "3":
        files_to_release = zip_files
    elif choice == "4":
        # Individual file selection (show only ZIP and IMG files)
        print("\nSelect files to include:")
        all_files = []
        
        # Display available files with numbers
        if zip_files:
            print("\nZIP files:")
            for i, file in enumerate(zip_files):
                print(f"  {i+1}. {file.name}")
                all_files.append(file)
        
        if img_files:
            offset = len(zip_files)
            print("\nIMG files:")
            for i, file in enumerate(img_files):
                print(f"  {i+offset+1}. {file.name}")
                all_files.append(file)
        
        # Improved file selection UI with clearer instructions
        print("\nEnter file numbers separated by spaces (e.g. 1 3 5)")
        print("To select all files, just press Enter")
        print("To select a range, use 'start-end' notation (e.g. 1-3 for files 1,2,3)")
        
        selected = input("Select files: ")
        
        # If empty, select all files
        if not selected.strip():
            print("No selection made - using all files.")
            files_to_release = zip_files + img_files
        else:
            try:
                # Process the selection input
                selected_indices = []
                
                # Split by spaces first
                parts = selected.split()
                
                for part in parts:
                    # Check if it's a range (contains '-')
                    if '-' in part:
                        try:
                            start, end = map(int, part.split('-'))
                            # Convert to 0-based indices
                            start_idx = start - 1
                            end_idx = end - 1
                            
                            # Validate range
                            if 0 <= start_idx <= end_idx < len(all_files):
                                selected_indices.extend(range(start_idx, end_idx + 1))
                            else:
                                print(f"Warning: Invalid range {part}, skipping.")
                        except ValueError:
                            print(f"Warning: Invalid range format '{part}', skipping.")
                    else:
                        # It's a single number
                        try:
                            idx = int(part) - 1  # Convert to 0-based index
                            if 0 <= idx < len(all_files):
                                selected_indices.append(idx)
                            else:
                                print(f"Warning: File number {part} out of range, skipping.")
                        except ValueError:
                            print(f"Warning: Invalid number '{part}', skipping.")
                
                # Remove duplicates and sort
                selected_indices = sorted(set(selected_indices))
                
                # Add the selected files
                for idx in selected_indices:
                    files_to_release.append(all_files[idx])
                
                # If no valid selections were made, use all files
                if not files_to_release:
                    print("No valid selections - using all files.")
                    files_to_release = zip_files + img_files
                else:
                    print(f"\nSelected {len(files_to_release)} file(s):")
                    for file in files_to_release:
                        print(f"  - {file.name}")
                    
            except Exception as e:
                print(f"Error processing selection: {str(e)}")
                print("Using all files.")
                files_to_release = zip_files + img_files
    
    # Add matching SHA files for selected ZIPs
    files_to_release = add_sha_files(files_to_release, zip_files, sha_files)
    
    return files_to_release

def create_release_with_progress(cmd, files_to_release):
    """Create a release with per-file progress estimation."""
    # Get file sizes and total size
    file_sizes = {file: os.path.getsize(file) for file in files_to_release}
    total_size = sum(file_sizes.values())
    
    print(f"Total upload size: {format_size(total_size)} across {len(files_to_release)} files")
    
    # Show limitation message to manage user expectations
    print("\nNote: Progress is estimated and may not reflect actual upload status.")
    print("GitHub CLI doesn't provide real-time upload progress information.")
    
    # Process each file individually
    current_file_index = 0
    total_uploaded = 0
    
    # Start timing for overall progress
    overall_start_time = time.time()
    
    # Create the release without files first
    # Fix: Make sure we're using the title and notes correctly
    title_index = cmd.index("--title") + 1 if "--title" in cmd else -1
    notes_index = cmd.index("--notes") + 1 if "--notes" in cmd else -1
    
    create_cmd = ["gh", "release", "create", cmd[3]]
    if notes_index > 0:
        create_cmd.extend(["--notes", cmd[notes_index]])
    if title_index > 0:
        create_cmd.extend(["--title", cmd[title_index]])
    
    print("\nCreating empty release...")
    print(f"Command: {' '.join(create_cmd)}")
    
    # Run command with full output
    try:
        process = subprocess.Popen(
            create_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy()
        )
        stdout, stderr = process.communicate()
        exit_code = process.returncode
        
        if exit_code != 0:
            print(f"\nError creating release (exit code {exit_code})")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            
            # Try to get more info about the GitHub account
            print("\nAttempting to get additional GitHub account info...")
            gh_info, _ = run_command(["gh", "auth", "status"], check=False)
            print(f"GitHub auth status: {gh_info}")
            
            # Check for specific common errors
            if "Unauthorized" in stderr or "authentication" in stderr.lower():
                print("\nAuthentication error: Your GitHub token might be expired or invalid.")
                print("Try running 'gh auth login' to re-authenticate.")
            elif "already exists" in stderr.lower():
                print("\nA release with this tag already exists. Choose a different tag name.")
            elif "permission" in stderr.lower():
                print("\nPermission error: You might not have write access to this repository.")
            
            return f"Creation failed: {stderr}", exit_code
        
        print(" Done! Release created successfully.")
        
    except Exception as e:
        print(f"\nException during release creation: {str(e)}")
        return f"Exception: {str(e)}", 1

    # Continue with file uploads...
    # Rest of the function remains the same

    # Upload each file separately
    for current_file_index, file in enumerate(files_to_release):
        file_size = file_sizes[file]
        file_name = os.path.basename(file)
        
        print(f"\nUploading file {current_file_index + 1}/{len(files_to_release)}: {file_name}")
        print(f"File size: {format_size(file_size)}")
        
        # Use a conservative speed estimate
        base_speed = 2 * 1024 * 1024  # 2 MB/s for uploads
        if file_size > 1024 * 1024 * 1024:  # > 1GB
            base_speed = 1.5 * 1024 * 1024  # 1.5 MB/s for large files
        
        # Start the upload command for this file
        upload_cmd = ["gh", "release", "upload", cmd[3], file]

        # Add retry mechanism for potential auth issues
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            process = subprocess.Popen(
                upload_cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=os.environ.copy()  # Ensure we inherit the environment variables including GitHub tokens
            )
            
            # Set up progress tracking for this file
            start_time = time.time()
            last_update = start_time
            last_estimate = 0
            adaptive_speed = base_speed
            last_progress_length = 0
            
            try:
                # Track progress while process is running
                while process.poll() is None:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    # Only update every second to avoid too many updates
                    if current_time - last_update >= 1:
                        if elapsed > 0:
                            # Calculate all progress metrics
                            time_factor = min(1.0, elapsed / 60)
                            adaptive_speed = base_speed * (1.0 - (time_factor * 0.5))
                            current_estimate = min(file_size, adaptive_speed * elapsed)
                            estimated_uploaded = max(last_estimate, current_estimate)
                            last_estimate = estimated_uploaded
                            percentage = min(99.9, (estimated_uploaded / file_size) * 100)
                            avg_speed = estimated_uploaded / elapsed if elapsed > 0 else 0
                            speed_str = f"{format_size(avg_speed)}/s"
                            
                            # Calculate ETA
                            if avg_speed > 0:
                                file_eta = (file_size - estimated_uploaded) / avg_speed
                                file_eta_str = format_time(file_eta)
                            else:
                                file_eta_str = "Calculating..."
                            
                            # Determine file state
                            if percentage < 1:
                                state = "Starting"
                            elif percentage < 80:
                                state = "Uploading"
                            else:
                                state = "Finalizing"
                            
                            # Create progress bar
                            bar_length = 20
                            filled_length = int(bar_length * percentage / 100)
                            file_bar = '█' * filled_length + '▒' * (bar_length - filled_length)
                            
                            # Build progress string
                            file_progress = f"\rFile {current_file_index+1}/{len(files_to_release)}: [{file_bar}] {percentage:5.1f}% • {format_size(estimated_uploaded)}/{format_size(file_size)} • {speed_str} • ETA: {file_eta_str} • {state}"
                            
                            # Ensure the line is completely clear before printing new progress
                            if last_progress_length > 0:
                                print('\r' + ' ' * last_progress_length, end='')
                            
                            print(file_progress, end='', flush=True)
                            last_progress_length = len(file_progress)
                        
                        last_update = current_time
                    
                    # Sleep briefly to avoid high CPU usage
                    time.sleep(0.1)
                
                # Process completed for this file
                stdout, stderr = process.communicate()
                exit_code = process.returncode
                
                if exit_code == 0:
                    break  # Success, exit retry loop
                elif "authentication" in stderr.lower() or "permission" in stderr.lower():
                    retry_count += 1
                    print(f"\nAuthentication issue. Retrying ({retry_count}/{max_retries})...")
                    time.sleep(2)  # Brief pause before retry
                else:
                    # Not an authentication issue, don't retry
                    print("\n\nError uploading file {}: {}".format(file_name, stderr))
                    return stderr, exit_code
            
                # Update total uploaded size
                total_uploaded += file_size
                
                # Print newline to ensure next output starts on a clean line
                print()
                
                # Show completion message for this file
                elapsed_time = time.time() - start_time
                print(f"✓ File {current_file_index+1}/{len(files_to_release)} completed: {file_name}")
                print(f"  Size: {format_size(file_size)} • Time: {format_time(elapsed_time)} • Speed: {format_size(file_size/elapsed_time)}/s")
                
                # Add simple overall progress update after each file
                overall_elapsed = time.time() - overall_start_time
                overall_percentage = (total_uploaded / total_size) * 100
                print(f"  Overall: {overall_percentage:5.1f}% complete • {format_size(total_uploaded)}/{format_size(total_size)} • Elapsed: {format_time(overall_elapsed)}")
                
            except KeyboardInterrupt:
                print("\n\nProcess interrupted by user. Attempting to clean up...")
                process.kill()
                return "Interrupted by user", 1

        if retry_count == max_retries:
            print(f"\n\nFailed to upload {file_name} after {max_retries} attempts.")
            return "Authentication failure", 1
    
    # All files uploaded successfully
    total_elapsed = time.time() - overall_start_time
    print(f"\nAll {len(files_to_release)} files uploaded successfully!")
    print(f"Total size: {format_size(total_size)} • Completed in {format_time(total_elapsed)}")
    return "Success", 0

def create_release_with_direct_command(cmd, files_to_release):
    """Try creating a release with direct GitHub CLI command."""
    print("\nTrying alternative release creation method...")
    
    # Extract tag name (it's at position 3 in the cmd list)
    tag = cmd[3]
    
    # Find title and notes indices
    title_index = cmd.index("--title") + 1 if "--title" in cmd else -1
    notes_index = cmd.index("--notes") + 1 if "--notes" in cmd else -1
    
    # Build the direct command
    direct_cmd = ["gh", "release", "create", tag]
    
    # Add files directly to the initial command
    for file in files_to_release:
        direct_cmd.append(file)
    
    # Add title and notes
    if title_index > 0:
        direct_cmd.extend(["--title", cmd[title_index]])
    if notes_index > 0:
        direct_cmd.extend(["--notes", cmd[notes_index]])
    
    print(f"Command: {' '.join(direct_cmd)}")
    
    # Execute the command directly
    try:
        result, exit_code = run_command(direct_cmd, check=False)
        
        if exit_code != 0:
            print(f"\nError creating release (exit code {exit_code})")
            print(f"Output: {result}")
            
            # Check for specific permission errors
            if "HTTP 403" in result:
                print("\nPermission error: Your GitHub token doesn't have sufficient permissions.")
                print("Make sure your token has the 'repo' scope to create releases.")
                print("Run 'gh auth login' and follow the steps to get a token with correct permissions.")
                print("For more details, visit: https://cli.github.com/manual/gh_auth_login")
            
            return result, exit_code
        
        print("Release created successfully!")
        return "Success", 0
    
    except Exception as e:
        print(f"\nException during release creation: {str(e)}")
        return f"Exception: {str(e)}", 1

def format_size(size_bytes):
    """Format bytes into a human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"

def format_time(seconds):
    """Format seconds into a human-readable time."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def estimate_upload_speed():
    """Estimate upload speed using a simple HTTP upload test."""
    print("Estimating upload speed...", end="", flush=True)
    
    # Skip real upload test and use conservative estimate
    # This is simpler and doesn't require GitHub API interactions
    default_speed = 1.5 * 1024 * 1024  # 1.5 MB/s as a conservative estimate
    
    print(f" Using default estimate ({format_size(default_speed)}/s)")
    return default_speed

def main():
    # First check GitHub CLI authentication
    if not check_github_auth():
        return 1
        
    # Then check repository access
    if not check_repository_access():
        return 1
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Create GitHub releases for ROM files")
    parser.add_argument("-a", "--all", action="store_true", help="Release all files without prompting")
    parser.add_argument("-i", "--img", action="store_true", help="Release only .img files")
    parser.add_argument("-z", "--zip", action="store_true", help="Release only .zip files")
    parser.add_argument("-n", "--notes", action="append", help="Set release notes (use multiple times for multiple lines)")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm release creation")
    parser.add_argument("-u", "--upload", help="Upload to existing release tag instead of creating a new one")
    args = parser.parse_args()
    
    # If no args specified, go to interactive mode
    if not any(vars(args).values()):
        return interactive_mode()
    
    # Non-interactive mode
    auto_confirm = args.yes
    
    # Check for files to release
    zip_files = find_files_by_extension(["zip"])
    img_files = find_files_by_extension(["img"])
    sha_files = find_files_by_extension(["sha256sum"])
    
    if not (zip_files or img_files):
        print("Error: No .img or .zip files found for release")
        return 1
    
    # Determine which files to release
    if args.img:
        files_to_release = img_files
    elif args.zip:
        files_to_release = zip_files
    else:  # --all or default
        files_to_release = zip_files + img_files
    
    # Add matching SHA files for ZIPs
    files_to_release = add_sha_files(files_to_release, zip_files, sha_files)
    
    if not files_to_release:
        print("Error: No matching files found for selected option")
        return 1
    
    # If upload to existing release
    if args.upload:
        tag = args.upload
        print(f"Uploading to existing release with tag: {tag}")
        
        # Verify that the release exists
        print(f"Verifying release '{tag}' exists...", end="", flush=True)
        result, exit_code = run_command(["gh", "release", "view", tag], check=False)
        if exit_code != 0:
            print(f"\nError: Release with tag '{tag}' does not exist.")
            print(result)
            return 1
        print(" OK!")
        
        # Upload files to the existing release using our upload function
        if upload_to_existing_release(tag, files_to_release):
            print("Files uploaded successfully.")
            return 0
        else:
            print("Failed to upload files.")
            return 1
    
    # Otherwise create a new release
    # Extract tag and title from zip filename
    tag = ""
    title = ""
    
    if zip_files:
        zipname = str(zip_files[0])
        title = zipname
        tag = extract_tag_from_zip(zipname)
    
    # If no tag was extracted, exit with error
    if not tag:
        print("Error: Could not extract tag from ZIP filename")
        return 1
    
    # Show extracted information
    print(f"Tag: {tag}")
    print(f"Title: {title}")
    
    # Check if tag already exists on GitHub and get a unique tag
    tag = get_unique_tag(tag)
    
    # Get release notes
    notes = ""
    if args.notes:
        notes = "\n".join([f"- {note}" for note in args.notes])
    else:
        notes = "- Auto-generated release"
    
    # Build command for creating the release
    cmd = ["gh", "release", "create", tag]
    for file in files_to_release:
        cmd.append(str(file))
    cmd.extend(["--notes", notes, "--title", title])
    
    # Show final command
    print("\nFinal command to be executed:")
    print("================================")
    print(" ".join(cmd))
    print("================================")
    print()
    
    # Get confirmation and execute
    if get_confirmation(auto_confirm):
        print("Executing command...")
        result, exit_code = create_release_with_progress(cmd, [str(file) for file in files_to_release])
        
        # If the first method fails, try the alternative direct method
        if exit_code != 0:
            print("\nFirst method failed. Trying alternative approach...")
            result, exit_code = create_release_with_direct_command(cmd, [str(file) for file in files_to_release])
        
        if exit_code == 0:
            print("Release created successfully.")
        else:
            print(f"Error: Failed to create release\n{result}")
            print("\nPlease check your GitHub token permissions:")
            print("1. Run 'gh auth login' to re-authenticate")
            print("2. Choose GitHub.com -> HTTPS -> Generate a token (with 'repo' scope)")
            print("3. Follow the instructions to complete authentication")
            return 1
    else:
        print("Operation cancelled by user.")
        return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
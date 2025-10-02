# Bookshop Management System

A Flask-based bookshop management system that helps you manage inventory, sales, and categories of books.

## Prerequisites

Before you begin, ensure you have the following installed on your computer:
- [Python 3.12](https://www.python.org/downloads/) or later
- [Git](https://git-scm.com/downloads) (optional, for cloning the repository)

## Setup Instructions

### 1. Get the Project Files

Either:
- Clone the repository using Git:
  ```bash
  git clone [your-repository-url]
  ```
- Or download and extract the project ZIP file

### 2. Create and Set Up Python Virtual Environment

1. Open Command Prompt (cmd) and navigate to the project directory:
   ```cmd
   cd path\to\bookshop
   ```

2. Create a new virtual environment:
   ```cmd
   python -m venv .venv
   ```

3. Activate the virtual environment:
   ```cmd
   .venv\Scripts\activate
   ```

### 3. Install Required Packages

With the virtual environment activated, install the required packages:
```cmd
pip install -r requirements.txt
```

This will install:
- Flask
- Flask-SQLAlchemy
- pandas
- openpyxl

## How to run this 
run this command on terminal 

python app.py


### 4. Create Desktop Shortcut

You have two options to create a desktop shortcut:

#### Method 1: Using PowerShell Script (Recommended)

1. Create a file named `run_bookshop.bat` with the following content:
   ```batch
   @echo off
   cd /d "%~dp0"
   call .venv\Scripts\activate.bat
   start http://127.0.0.1:5000
   python app.py
   ```

2. Create a file named `create_shortcut.ps1` with the following content:
   ```powershell
   $WshShell = New-Object -comObject WScript.Shell
   $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Bookshop.lnk")
   $Shortcut.TargetPath = "$PSScriptRoot\run_bookshop.bat"
   $Shortcut.WorkingDirectory = "$PSScriptRoot"
   $Shortcut.IconLocation = "$PSScriptRoot\bookshop.ico"
   $Shortcut.Save()
   ```

3. Run the PowerShell script:
   ```cmd
   powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
   ```

#### Method 2: Using PyInstaller (Alternative)

1. Install PyInstaller:
   ```cmd
   pip install pyinstaller
   ```

2. Make sure bookshop.ico is in the main directory

3. create file

launcher.py file
   ```
   import os
   os.system('start http://127.0.0.1:5000')
   os.system('cmd /c ".venv\\Scripts\\activate && python app.py"')
   ```

3. Create the executable: run this in terminal
   ```cmd
   pyinstaller --onefile --icon=bookshop.ico launcher.py
   ```

4. Find the executable in the `dist` folder and create a shortcut on your desktop

## Running the Application

### Using the Desktop Shortcut
Simply double-click the "Bookshop" shortcut on your desktop. This will:
1. Start the Flask server
2. Open your default web browser to the application
3. You can access the application at http://127.0.0.1:5000

### Manual Start
1. Open Command Prompt
2. Navigate to the project directory
3. Activate the virtual environment:
   ```cmd
   .venv\Scripts\activate
   ```
4. Run the application:
   ```cmd
   python app.py
   ```

## File Structure
```
bookshop/
├── .venv/                  # Virtual environment (created during setup)
├── models/                 # Database models
├── routes/                # Route handlers
├── static/                # Static files (CSS, images)
├── templates/             # HTML templates
├── utils/                 # Utility functions
├── app.py                 # Main application file
├── config.py             # Configuration settings
├── requirements.txt      # Package dependencies
├── bookshop.ico         # Application icon
├── launcher.py          # PyInstaller launcher script
└── run_bookshop.bat     # Batch file to run the application
```

## Troubleshooting

1. If you see "Import could not be resolved" errors:
   - Make sure you've activated the virtual environment
   - Verify that all packages are installed using `pip list`

2. If the application won't start:
   - Check that you're in the correct directory
   - Ensure the virtual environment is activated
   - Verify that all required packages are installed

3. If the shortcut doesn't work:
   - Verify the paths in the shortcut properties
   - Make sure the working directory is set to the project folder
   - Check that the required files exist

## Notes

- The application runs on http://127.0.0.1:5000 by default
- To stop the application, close the command prompt window
- The database file (`bookshop.db`) will be created automatically on first run
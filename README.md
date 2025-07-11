# Laptop Flask Labeler System

A Flask-based web application for labeling images with keep/delete decisions and managing face recognition interactively while working offline. This system works with a local cache of images and OCR data, synchronizing with a NAS periodically.

## Features

- **Local Caching**: Uses a local cache for images, OCR, and face data
- **Face Recognition**: Identifies faces in images and allows name assignment
- **Offline Labeling**: Works offline using cached data
- **NAS Synchronization**: Automatically syncs with NAS when connected to the correct WiFi
- **OCR Display**: Shows OCR text from pre-processed files (no local OCR processing)
- **Keyboard Shortcuts**: Quick labeling with customizable key bindings

## System Architecture

### Directory Structure

- `cache/images/` — Local copy of images to label
- `cache/ocr/` — Local copy of OCR text files from NAS
- `cache/labels.csv` — Image file names with keep/delete decision
- `cache/faces.pkl` — Known face encodings and names
- `labeled/` — Symbolic links to labeled images, organized by category

### Components

1. **Flask Server (`app.py`)**: Main web interface for labeling and face recognition
2. **Sync Worker (`worker.py`)**: Runs as a scheduled task to sync with NAS
3. **Web Templates**: HTML interfaces for the labeling process

## Setup

### Prerequisites

- Python 3.7+
- Windows computer
- NAS drive mapped to Z:
- Rsync for Windows (cwRsync or similar)

### Installation

1. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Set up NAS mapping:**
   - Map your NAS share to drive `Z:`
   - Ensure the following paths exist on the NAS:
     - `Z:/photos_preprocessed/` - Source images
     - `Z:/ocr_data/` - OCR text files
     - `Z:/labels/` - For syncing labels.csv
     - `Z:/known_faces/` - For syncing faces.pkl

3. **Configure Windows Scheduled Task:**
   - Open Task Scheduler
   - Create a new task with these settings:
     - Name: "Image Labeler Sync"
     - Trigger: Every 10 minutes
     - Action: Start Program
     - Program/script: `python`
     - Add arguments: `worker.py`
     - Start in: `C:\Users\dell\source\AI Classifier` (adjust to your path)
   
   Optional: Add a condition to only run when connected to "Abayasekera" WiFi
   (The worker script already checks for this, but you can add it as a task condition too)

4. **Run the Flask application:**
   ```powershell
   python app.py
   ```

5. **Open your browser:**
   Navigate to `http://localhost:5000`

## Usage

### Labeling Images

1. Open the web interface at http://localhost:5000
2. For each image:
   - Review any OCR text displayed
   - Check detected faces and assign/confirm names
   - Click a category button or use keyboard shortcuts to label the image

### Face Recognition

- Faces are automatically detected in images
- If a face matches someone in the database, their name will appear
- Enter or update names in the text box for each face
- Names are saved to the database for future recognition

### Keyboard Shortcuts

- Use keyboard keys corresponding to categories (shown in parentheses)
- Press `u` to undo the last labeling action

### Synchronization

- The sync worker runs every 10 minutes when connected to "Abayasekera" WiFi
- It pulls new images and OCR text from the NAS
- It pushes updated labels and face data to the NAS
- No manual sync is needed
- Delete (Key: 2, Emoji: ❌)
- Favorite (Key: 3, Emoji: ⭐)
- Archive (Key: 4, Emoji: 📦)

### Supported Image Formats
- JPG/JPEG
- PNG
- WebP
- BMP
- GIF

## API Endpoints

### Image Labeling
- `GET /` - Main labeling interface
- `POST /label` - Submit image label
- `GET /undo` - Undo last action
- `GET /image/<filename>` - Serve images from NAS

### Category Management
- `GET /categories` - Category management interface
- `POST /categories/add` - Add new category
- `POST /categories/update` - Update existing category
- `POST /categories/delete` - Delete category

## Data Storage

### Labels CSV Format
```csv
filename.jpg,category_id
another_image.png,favorite
...
```

### Categories JSON Format
```json
{
  "category_id": {
    "name": "Display Name",
    "key": "1",
    "emoji": "✅"
  }
}
```

## Tips for Efficient Labeling

1. **Use keyboard shortcuts** - Much faster than clicking
2. **Set up logical categories** - Think about your organization needs
3. **Use memorable shortcuts** - 1-9 keys work best
4. **Batch similar images** - Sort your source folder first if possible
5. **Regular backups** - Back up your `labels.csv` and `categories.json` periodically

## Troubleshooting

### "No images found" Error
- Check that your NAS drive is properly mounted
- Verify the path in `UNLABELLED_FOLDER` is correct
- Ensure the images directory contains supported image formats

### Images Not Loading
- Check network connectivity to your NAS
- Verify file permissions on the image directory
- Try accessing the image path directly in Windows Explorer

### Categories Not Saving
- Check write permissions in the application directory
- Ensure `categories.json` is not read-only

## Future Enhancements

- Batch operations
- Export to different formats
- Image preview caching
- Multi-user support
- Integration with cloud storage
- Machine learning suggestions

## License

This project is open source and available under the MIT License.

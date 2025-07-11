# Enhanced Image Classifier

A Flask-based web application for classifying images with dynamic categories and keyboard shortcuts. Perfect for organizing large photo collections from your NAS drive.

## Features

### 🆕 New Features
- **Dynamic Categories**: Add, edit, and delete categories on the fly
- **Keyboard Shortcuts**: Quick labeling with customizable key bindings
- **NAS Integration**: Direct access to images from network drives (Z://GooglePhotos/images)
- **Modern UI**: Beautiful, responsive interface with visual feedback
- **Category Management**: Full CRUD operations for categories via web interface

### 📋 Core Features
- Label images into custom categories
- Undo functionality
- Progress tracking
- Automatic image organization into labeled folders
- CSV export of all labels

## Setup

### Prerequisites
- Python 3.7+
- Access to your NAS drive mapped to Z: (or modify the path in app.py)
- Flask

### Installation

1. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Configure image source:**
   - Make sure your NAS is mapped to `Z:/GooglePhotos/images`
   - Or modify the `UNLABELLED_FOLDER` path in `app.py` to point to your image directory

3. **Run the application:**
   ```powershell
   python app.py
   ```

4. **Open your browser:**
   Navigate to `http://localhost:5000`

## Usage

### Labeling Images
1. Open the web interface
2. Use mouse clicks or keyboard shortcuts to classify images
3. Default shortcuts:
   - `1` - ✅ Keep
   - `2` - ❌ Delete  
   - `3` - ⭐ Favorite
   - `4` - 📦 Archive
   - `u` - Undo last action

### Managing Categories
1. Click "⚙️ Manage Categories" from the main interface
2. **Add Categories**: Enter name, keyboard shortcut, and emoji
3. **Edit Categories**: Modify existing category properties
4. **Delete Categories**: Remove unwanted categories (must keep at least one)

### Keyboard Shortcuts
- **Number keys (1-9)**: Quick labeling based on your category setup
- **U key**: Undo the last labeling action
- **Focus**: No need to click - shortcuts work immediately when page loads

## File Structure

```
AI Classifier/
├── app.py                 # Main Flask application
├── categories.json        # Dynamic category configuration
├── labels.csv            # Label history and results
├── requirements.txt      # Python dependencies
├── labeled/              # Organized labeled images
│   ├── keep/
│   ├── delete/
│   ├── favorite/
│   └── archive/
├── templates/
│   ├── index.html        # Main labeling interface
│   ├── categories.html   # Category management
│   └── completed.html    # Completion page
└── static/              # Static assets (if any)
```

## Configuration

### Changing Image Source
Edit the `UNLABELLED_FOLDER` variable in `app.py`:
```python
UNLABELLED_FOLDER = 'Z:/GooglePhotos/images'  # Your image directory
```

### Default Categories
The app starts with these categories, but you can modify them via the web interface:
- Keep (Key: 1, Emoji: ✅)
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

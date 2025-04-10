
@bp.route('/url-to-base64', methods=['POST'])
def url_to_base64():
    """
    Convert an image URL to a base64-encoded data URL.
    Expects JSON payload with:
      { "url": "https://example.com/image.jpg" }
    """
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "URL is required"}), 400
            
        image_url = data['url']
        response = requests.get(image_url)
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch image from URL"}), 400
            
        content_type = response.headers.get('content-type', 'application/octet-stream')
        base64_data = base64.b64encode(response.content).decode('utf-8')
        data_url = f"data:{content_type};base64,{base64_data}"
        return jsonify({"base64": data_url}), 200
    except Exception as e:
        logger.error(f"Error converting URL to base64: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/ocr', methods=['POST'])
def perform_ocr():
    """
    Extract text from an image using Tesseract OCR.
    Accepts:
      - Multipart form data with an image file,
      - JSON with base64 encoded image,
      - JSON with image URL.
    Returns JSON with extracted text and average confidence.
    """
    try:
        from PIL import Image
        import io
        import pytesseract

        image = None
        if request.files and 'image' in request.files:
            file = request.files['image']
            image = Image.open(file.stream)
        elif request.is_json:
            data = request.json
            if 'base64' in data:
                base64_data = data['base64']
                if 'base64,' in base64_data:
                    base64_data = base64_data.split('base64,')[1]
                image_data = base64.b64decode(base64_data)
                image = Image.open(io.BytesIO(image_data))
            elif 'url' in data:
                response = requests.get(data['url'])
                if response.status_code != 200:
                    return jsonify({"error": "Failed to fetch image from URL"}), 400
                image = Image.open(io.BytesIO(response.content))
        
        if not image:
            return jsonify({"error": "No image provided"}), 400

        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        text = " ".join(ocr_data['text'])
        confidences = [conf for conf, txt in zip(ocr_data['conf'], ocr_data['text']) 
                       if txt.strip() and conf != -1]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return jsonify({
            "text": text,
            "confidence": round(avg_confidence, 2)
        }), 200

    except Exception as e:
        logger.error(f"Error performing OCR: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

def safe_rename(src: str, dst: str, backup: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Safely rename a file with optional backup creation.
    
    Args:
        src: Source file path
        dst: Destination file path
        backup: Whether to create a backup before renaming
        
    Returns:
        Tuple of (success: bool, backup_path: Optional[str])
        
    Raises:
        OSError: If the rename operation fails and cannot be recovered
    """
    src_path = Path(src)
    dst_path = Path(dst)
    
    if not src_path.exists():
        logger.error(f"Source file does not exist: {src}")
        return False, None
        
    if src_path == dst_path:
        logger.info(f"Source and destination are the same: {src}")
        return True, None
    
    backup_path = None
    
    try:
        # Create destination directory if it doesn't exist
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if requested
        if backup and dst_path.exists():
            backup_path = str(dst_path) + ".bak"
            shutil.copy2(str(dst_path), backup_path)
            logger.info(f"Created backup at: {backup_path}")
        
        # Use atomic rename when possible (same filesystem)
        try:
            os.replace(str(src_path), str(dst_path))
            logger.info(f"Renamed {src} to {dst}")
            return True, backup_path
            
        # Fall back to copy + delete if atomic rename fails
        except OSError:
            logger.warning(f"Atomic rename failed, falling back to copy + delete for {src}")
            # Use temporary file for atomic copy
            temp_dir = dst_path.parent
            with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False) as tmp:
                shutil.copy2(str(src_path), tmp.name)
                os.replace(tmp.name, str(dst_path))
            os.unlink(str(src_path))
            logger.info(f"Completed copy + delete rename from {src} to {dst}")
            return True, backup_path
            
    except OSError as e:
        logger.error(f"Failed to rename {src} to {dst}: {str(e)}")
        # Try to restore backup if it exists
        if backup_path and os.path.exists(backup_path):
            try:
                os.replace(backup_path, str(dst_path))
                logger.info(f"Restored backup from {backup_path}")
            except OSError as restore_error:
                logger.error(f"Failed to restore backup: {str(restore_error)}")
        raise
        
def bulk_rename(file_pairs: list[Tuple[str, str]], backup: bool = True) -> list[Tuple[str, str, bool]]:
    
    async def fetch_citation(self, doi: str) -> Dict:

        try:
            response = await requests.get(f"https://api.crossref.org/works/{doi}")
            return response.json()["message"]
        except Exception as e:
            print(f"Citation fetch failed: {e}")
            return None

def process_file_embed(self, file: Dict, file_url: str) -> str:
        """
        Generate appropriate embed HTML based on file type.
        Referenced from from_utils.js lines 1388-1415
        """
        file_ext = file["name"].split(".")[-1].lower()
        
        # Code files
        code_extensions = {
            'js', 'jsx', 'ts', 'tsx', 'py', 'java', 'cpp', 'c', 'cs', 
            'php', 'rb', 'go', 'rs', 'swift', 'kt', 'dart', 'sql',
            'html', 'css', 'scss', 'less', 'json', 'xml', 'yaml', 'yml', 'toml'
        }
        
        if file_ext in code_extensions:
            return f"```{file_ext}\n{file['name']}\n```"
            
        # Markdown files
        if file_ext in ['md', 'markdown']:
            return f"[View Markdown: {file['name']}]({file_url})"
            
        # Text files
        if file["type"] == "text/plain" or file_ext in ['txt', 'log', 'csv', 'tsv']:
            return f'<div class="text-embed-container" data-file-url="{file_url}">\n' \
                   f'    <pre class="text-content">Loading text content...</pre>\n' \
                   f'</div>'
                   
        # Default fallback
        return f'<div class="file-embed-container">\n' \
               f'    <a href="{file_url}" target="_blank" rel="noopener noreferrer">\n' \
               f'        <i class="fas fa-file"></i> {file["name"]}\n' \
               f'    </a>\n' \
               f'</div>'

def get_supported_mime_types(self) -> List[str]:
        """
        Get list of supported MIME types for file processing.
        Referenced from from_simple_alt_text.js lines 140-185
        """
        return [
            # Image Formats
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
            'image/webp', 'image/heic', 'image/heif', 'image/avif',
            'image/tiff', 'image/bmp', 'image/x-icon',
            'image/vnd.microsoft.icon', 'image/svg+xml',
            'image/vnd.adobe.photoshop', 'image/x-adobe-dng',
            'image/x-canon-cr2', 'image/x-nikon-nef',
            'image/x-sony-arw', 'image/x-fuji-raf',
            'image/x-olympus-orf', 'image/x-panasonic-rw2',
            'image/x-rgb', 'image/x-portable-pixmap',
            'image/x-portable-graymap', 'image/x-portable-bitmap',
            # Video Formats
            'video/mp4', 'video/quicktime', 'video/webm',
            'video/x-msvideo', 'video/x-flv', 'video/x-ms-wmv',
            'video/x-matroska', 'video/3gpp', 'video/x-m4v',
            'video/x-ms-asf', 'video/x-mpegURL', 'video/x-ms-vob',
            'video/x-ms-tmp', 'video/x-mpeg', 'video/mp2t',
            'application/octet-stream'
        ]

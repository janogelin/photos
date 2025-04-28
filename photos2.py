import os
import sys
import shutil
import logging
from typing import List, Dict, Set
from pathlib import Path
from datetime import datetime
from PIL import Image, UnidentifiedImageError
import imagehash

def setup_logging(output_dir: str) -> None:
    """Set up logging to both file and console."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    log_file = os.path.join(output_dir, f'photo_dedup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # Configure logging to write to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info(f"Logging to: {log_file}")

class Photo:
    """A class to handle photo deduplication based on perceptual image hashing."""
    
    # Supported image formats
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    
    def scan_directory(self, directory: str) -> List[str]:
        """
        Scan a directory recursively for supported image files.
        
        Args:
            directory (str): Path to the directory to scan
            
        Returns:
            List[str]: List of paths to image files
            
        Raises:
            SystemExit: If the directory doesn't exist
        """
        if not os.path.exists(directory):
            logging.error(f"Error: Input directory '{directory}' does not exist")
            sys.exit(1)
            
        image_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_ext = os.path.splitext(file.lower())[1]
                if file_ext in self.SUPPORTED_FORMATS:
                    image_files.append(os.path.join(root, file))
        
        if not image_files:
            logging.warning(f"No supported image files found in {directory}")
            
        return image_files
    
    def find_unique_images(self, files: List[str], hash_size: int = 8, threshold: int = 0) -> Dict[str, str]:
        """
        Find unique images using perceptual hashing.
        
        Args:
            files (List[str]): List of image file paths
            hash_size (int): Size of the hash to generate (default: 8)
            threshold (int): Similarity threshold (0-100, default: 0)
            
        Returns:
            Dict[str, str]: Dictionary mapping hash values to file paths
        """
        unique_images = {}
        total_files = len(files)
        
        for i, filepath in enumerate(files, 1):
            try:
                with Image.open(filepath) as img:
                    hash_value = str(imagehash.average_hash(img, hash_size))
                    
                    # Check for similar images if threshold > 0
                    if threshold > 0:
                        is_similar = False
                        for existing_hash in unique_images:
                            if self._calculate_similarity(hash_value, existing_hash) >= threshold:
                                is_similar = True
                                break
                        if not is_similar:
                            unique_images[hash_value] = filepath
                    else:
                        unique_images[hash_value] = filepath
                    
                    # Log progress every 10%
                    if i % max(1, total_files // 10) == 0:
                        logging.info(f"Processed {i}/{total_files} images ({i/total_files*100:.1f}%)")
                        
            except UnidentifiedImageError:
                logging.warning(f"Skipping corrupted or unsupported image: {filepath}")
            except Exception as e:
                logging.error(f"Error processing {filepath}: {e}")
                
        return unique_images
    
    def _calculate_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity percentage between two image hashes."""
        if len(hash1) != len(hash2):
            return 0.0
        diff_bits = sum(bit1 != bit2 for bit1, bit2 in zip(hash1, hash2))
        return 100 - (diff_bits * 100 / len(hash1))
    
    def process_unique_files(self, filetable: Dict[str, str], output_directory: str, copy: bool = False) -> None:
        """
        Process unique files by either moving or copying them to the output directory.
        
        Args:
            filetable (Dict[str, str]): Dictionary mapping hash values to file paths
            output_directory (str): Path to the output directory
            copy (bool): If True, copy files instead of moving them
        """
        if not os.path.exists(output_directory):
            try:
                os.makedirs(output_directory)
                logging.info(f"Created output directory: {output_directory}")
            except Exception as e:
                logging.error(f"Error creating output directory: {e}")
                sys.exit(1)

        operation = shutil.copy2 if copy else shutil.move
        operation_name = "Copying" if copy else "Moving"
        
        total_files = len(filetable)
        for i, (hash_value, filepath) in enumerate(filetable.items(), 1):
            try:
                filename = os.path.basename(filepath)
                dest_path = os.path.join(output_directory, filename)
                
                # Handle filename conflicts
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(dest_path):
                        new_filename = f"{base}_{counter}{ext}"
                        dest_path = os.path.join(output_directory, new_filename)
                        counter += 1
                
                operation(filepath, dest_path)
                logging.info(f"{operation_name} ({i}/{total_files}): {filepath}")
                logging.debug(f"Hash: {hash_value}")
                
            except Exception as e:
                logging.error(f"Error {operation_name.lower()} file {filepath}: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Find and process duplicate images based on perceptual hashing")
    parser.add_argument("input_dir", help="Input directory containing images")
    parser.add_argument("output_dir", help="Output directory for unique images")
    parser.add_argument("--copy", action="store_true", help="Copy files instead of moving them")
    parser.add_argument("--hash-size", type=int, default=8, help="Hash size for image comparison (default: 8)")
    parser.add_argument("--threshold", type=int, default=0, 
                      help="Similarity threshold percentage (0-100, default: 0)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set up logging first
    setup_logging(args.output_dir)
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.threshold < 0 or args.threshold > 100:
        logging.error("Threshold must be between 0 and 100")
        sys.exit(1)
    
    logging.info(f"Starting photo deduplication")
    logging.info(f"Input directory: {args.input_dir}")
    logging.info(f"Output directory: {args.output_dir}")
    logging.info(f"Options: copy={args.copy}, hash_size={args.hash_size}, threshold={args.threshold}, debug={args.debug}")
    
    photo = Photo()
    files = photo.scan_directory(args.input_dir)
    unique_files = photo.find_unique_images(files, args.hash_size, args.threshold)
    photo.process_unique_files(unique_files, args.output_dir, args.copy)
    
    logging.info(f"Found {len(unique_files)} unique images out of {len(files)} total images")

if __name__ == "__main__":
    main()
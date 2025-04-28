import os
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime

class PhotoDedupTester:
    def __init__(self):
        self.test_dir = Path("test_data")
        self.logs_dir = Path("logs")
        self.example_dir = Path("example")
        self.setup_directories()
        
    def setup_directories(self):
        """Create necessary directories for testing."""
        self.logs_dir.mkdir(exist_ok=True)
        self.test_dir.mkdir(exist_ok=True)
        
    def cleanup(self):
        """Clean up test directories while preserving logs."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        
    def run_test(self, test_name: str, args: list):
        """Run a test case and save its output."""
        print(f"\nRunning test: {test_name}")
        print("=" * 50)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"{test_name}_{timestamp}.log"
        
        # Run the command and capture output
        cmd = ["python3", "photos2.py"] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Save output to log file
        with open(log_file, "w") as f:
            f.write(f"Test: {test_name}\n")
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write("\nOutput:\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\nErrors:\n")
                f.write(result.stderr)
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
            
        return result.returncode == 0
        
    def prepare_test_files(self):
        """Copy example files to test directory."""
        self.cleanup()
        for file in self.example_dir.glob("*.JPG"):
            shutil.copy(file, self.test_dir)
            
    def test_basic_functionality(self):
        """Test basic move functionality."""
        self.prepare_test_files()
        return self.run_test(
            "basic_move",
            [str(self.test_dir), "out_basic"]
        )
        
    def test_copy_functionality(self):
        """Test copy functionality."""
        self.prepare_test_files()
        return self.run_test(
            "copy_mode",
            [str(self.test_dir), "out_copy", "--copy"]
        )
        
    def test_similarity_threshold(self):
        """Test similarity threshold functionality."""
        self.prepare_test_files()
        # Create a slightly modified copy of the image
        for file in self.test_dir.glob("*.JPG"):
            shutil.copy(file, self.test_dir / "modified_copy.JPG")
        return self.run_test(
            "similarity_threshold",
            [str(self.test_dir), "out_threshold", "--threshold", "90"]
        )
        
    def test_hash_size(self):
        """Test different hash sizes."""
        self.prepare_test_files()
        return self.run_test(
            "hash_size",
            [str(self.test_dir), "out_hash", "--hash-size", "16"]
        )
        
    def test_debug_mode(self):
        """Test debug mode output."""
        self.prepare_test_files()
        return self.run_test(
            "debug_mode",
            [str(self.test_dir), "out_debug", "--debug"]
        )
        
    def test_empty_directory(self):
        """Test behavior with empty directory."""
        self.cleanup()
        return self.run_test(
            "empty_directory",
            [str(self.test_dir), "out_empty"]
        )
        
    def test_invalid_directory(self):
        """Test behavior with invalid directory."""
        return self.run_test(
            "invalid_directory",
            ["nonexistent_dir", "out_invalid"]
        )
        
    def test_filename_conflicts(self):
        """Test handling of filename conflicts."""
        self.prepare_test_files()
        # Create multiple copies of the same file
        for i in range(3):
            for file in self.test_dir.glob("*.JPG"):
                shutil.copy(file, self.test_dir / f"copy_{i}.JPG")
        return self.run_test(
            "filename_conflicts",
            [str(self.test_dir), "out_conflicts"]
        )
        
    def run_all_tests(self):
        """Run all test cases."""
        tests = [
            ("Basic Functionality", self.test_basic_functionality),
            ("Copy Functionality", self.test_copy_functionality),
            ("Similarity Threshold", self.test_similarity_threshold),
            ("Hash Size", self.test_hash_size),
            ("Debug Mode", self.test_debug_mode),
            ("Empty Directory", self.test_empty_directory),
            ("Invalid Directory", self.test_invalid_directory),
            ("Filename Conflicts", self.test_filename_conflicts),
        ]
        
        results = []
        for name, test_func in tests:
            try:
                success = test_func()
                results.append((name, success))
            except Exception as e:
                print(f"Error in test {name}: {e}")
                results.append((name, False))
            finally:
                # Clean up output directories
                for dir in Path(".").glob("out_*"):
                    if dir.is_dir():
                        shutil.rmtree(dir)
        
        # Print summary
        print("\nTest Summary:")
        print("=" * 50)
        for name, success in results:
            status = "PASSED" if success else "FAILED"
            print(f"{name:30} {status}")
            
        # Clean up test directory
        self.cleanup()

if __name__ == "__main__":
    tester = PhotoDedupTester()
    tester.run_all_tests() 
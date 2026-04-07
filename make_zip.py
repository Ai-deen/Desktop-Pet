import os
import zipfile

def should_exclude(path):
    exclude_patterns = [
        '__pycache__',
        '.pyc',
        '.pyo',
        '.pyd',
        'node_modules',
        'venv',
        'env',
        '.git',
        '.vscode',
        '.idea',
        '.egg-info',
        'dist',
        'build',
    ]
    return any(pattern in path for pattern in exclude_patterns)

def create_zip(source_dir, output_filename):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Remove excluded directories from dirs list
            dirs[:] = [d for d in dirs if not should_exclude(d)]
            
            for file in files:
                file_path = os.path.join(root, file)
                if not should_exclude(file_path):
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    print(f"Added: {arcname}")

if __name__ == "__main__":
    create_zip('.', 'desktop_pet_project.zip')
    print("Zip created successfully!")
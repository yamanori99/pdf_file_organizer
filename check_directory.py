from pathlib import Path

def print_directory_structure(startpath: str, exclude_dirs: set = None):
    """
    ディレクトリ構造を表示する
    
    Args:
        startpath (str): 表示を開始するディレクトリパス
        exclude_dirs (set): 除外するディレクトリ名のセット
    """
    if exclude_dirs is None:
        exclude_dirs = {'.git', '__pycache__', 'venv', '.idea'}
    
    startpath = Path(startpath)
    
    def _print_tree(path: Path, prefix: str = ''):
        entries = sorted([x for x in path.iterdir() if x.name not in exclude_dirs])
        
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = '└── ' if is_last else '├── '
            
            print(f"{prefix}{connector}{entry.name}")
            
            if entry.is_dir():
                extension = '    ' if is_last else '│   '
                _print_tree(entry, prefix + extension)
    
    print(f"\n📁 プロジェクトディレクトリ構造: {startpath.absolute()}")
    print(".")
    _print_tree(startpath)

def get_file_info(path: str):
    """
    ディレクトリ内のファイル情報を表示する
    
    Args:
        path (str): 確認するディレクトリパス
    """
    path = Path(path)
    
    print(f"\n📊 ファイル統計:")
    
    # ファイル拡張子ごとの統計
    extension_count = {}
    total_size = 0
    
    for file_path in path.rglob('*'):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            extension_count[ext] = extension_count.get(ext, 0) + 1
            total_size += file_path.stat().st_size
    
    # 拡張子ごとの統計を表示
    print("\n拡張子ごとのファイル数:")
    for ext, count in sorted(extension_count.items()):
        if ext:
            print(f"{ext:8} : {count:3} ファイル")
    
    # 総サイズを適切な単位で表示
    units = ['B', 'KB', 'MB', 'GB']
    size = total_size
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    print(f"\n総ファイルサイズ: {size:.2f} {units[unit_index]}")

def main():
    current_dir = "."  # カレントディレクトリ
    print_directory_structure(current_dir)
    get_file_info(current_dir)

if __name__ == "__main__":
    main() 
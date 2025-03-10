import shutil
from pathlib import Path
import re
from typing import Dict, Any
from collections import defaultdict
import logging
from datetime import datetime
import pdfplumber  # 追加

class PDFOrganizer:
    def __init__(self, source_dir: str, destination_dir: str):
        """
        PDFファイルを整理するクラスの初期化
        
        Args:
            source_dir (str): PDFファイルが存在するソースディレクトリ
            destination_dir (str): 分類後のファイルを保存するディレクトリ
        """
        self.source_dir = Path(source_dir)
        self.destination_dir = Path(destination_dir)
        self.projects = {
            'basic': '意思決定に関する心理学実験 (実験参加)',
            'additional': '意思決定に関する心理学実験 (実験参加) 追加支払い'
        }
        
        # ログの設定
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"pdf_organizer_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8')
            ]
        )
        
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        PDFファイルからテキストを抽出する
        
        Args:
            pdf_path (Path): PDFファイルのパス
            
        Returns:
            str: 抽出されたテキスト
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ''
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        text += page_text
                        
                        if not page_text.strip():
                            logging.warning(f"  ページ {page_num}: テキストが抽出できませんでした")
                        else:
                            logging.debug(f"  ページ {page_num}: {len(page_text)} 文字抽出")
                            # デバッグ用に抽出テキストの詳細を記録
                            lines = page_text.split('\n')
                            for i, line in enumerate(lines[:5]):  # 最初の5行をサンプルとして表示
                                logging.debug(f"    行 {i + 1}: {line}")
                            
                    except Exception as e:
                        logging.error(f"  ページ {page_num} の処理中にエラー: {str(e)}")
                
                return text
            
        except Exception as e:
            logging.error(f"PDFファイル処理エラー: {pdf_path} - {str(e)}")
            return ''

    def categorize_pdf(self, text: str) -> str:
        """
        テキスト内容に基づいてカテゴリを判定する
        
        Args:
            text (str): PDFから抽出したテキスト
            
        Returns:
            str: 判定されたカテゴリ
        """
        # テキストの前処理
        text = text.lower()  # 小文字化

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        アナライザーと同じ方法でテキストを分析する
        """
        analysis = {
            'total_length': len(text),
            'line_count': text.count('\n') + 1,
            'patterns_found': {}
        }

        # アナライザーと同じパターン定義
        patterns = {
            '領収書番号': r'領収書番号[：:]\s*([0-9]+)',
            '発行日': r'発[行⾏]日[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)',
            '宛名': r'([一-龥々ぁ-んァ-ヶ\s]{1,20})[様殿]',
            '領収者': r'領収者[：\s]*([一-龥々ぁ-んァ-ヶ]{1,20})',
            '金額': r'[￥¥]\s*([0-9,]+)',
            '案件名': r'案件名[：:]\s*(.+)'
        }

        for key, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            analysis['patterns_found'][key] = [
                {
                    'matched_text': m.group(0),
                    'captured_group': m.group(1),
                    'position': m.span()
                } for m in matches
            ]

        return analysis

    def extract_username(self, text: str) -> str:
        """
        テキストから相手先（ユーザー名）を抽出する
        """
        # テキストを行に分割
        lines = text.split('\n')
        
        # 案件名の行を探し、その次の行を確認
        for i, line in enumerate(lines[:-1]):  # 最後の行を除いて処理
            if line.startswith('案件名：'):
                next_line = lines[i + 1].strip()
                logging.debug(f"案件名の次の行からユーザー名を検出: {next_line}")
                return next_line

        # バックアップとして他のパターンも確認
        analysis = self.analyze_text(text)
        patterns_found = analysis['patterns_found']
        
        # 表形式からの抽出
        table_match = re.search(r'品名\s+相⼿先\s+数量.*?\n.*?\s+([a-zA-Z0-9._\-]+)\s+\d+\s+個', text, re.DOTALL)
        if table_match:
            username = table_match.group(1).strip()
            logging.debug(f"表形式からユーザー名を検出: {username}")
            return username

        # 領収者パターン
        if patterns_found.get('領収者'):
            username = patterns_found['領収者'][0]['captured_group']
            logging.debug(f"領収者パターンからユーザー名を検出: {username}")
            return username

        logging.warning(f"ユーザー名を検出できませんでした。テキストサンプル: {text[:200]}")
        return 'unknown_user'

    def extract_project_type(self, text: str) -> str:
        """
        テキストからプロジェクトの種類を判定する
        """
        analysis = self.analyze_text(text)
        patterns_found = analysis['patterns_found']
        
        # 案件名から判定
        if '案件名' in patterns_found and patterns_found['案件名']:
            project_name = patterns_found['案件名'][0]['captured_group']
            if '追加支払い' in project_name:
                logging.debug(f"追加支払い案件を検出: {project_name}")
                return 'additional'
            logging.debug(f"基本案件を検出: {project_name}")
            return 'basic'
        
        # 表形式からも判定
        if '追加支払い' in text:
            logging.debug("表形式から追加支払い案件を検出")
            return 'additional'
        
        logging.debug("基本案件として判定")
        return 'basic'

    def extract_project_and_username(self, text: str) -> tuple[str, str]:
        """
        テキストから案件名（プロジェクト名）と相手先（ユーザー名）を抽出する
        
        Args:
            text (str): PDFから抽出したテキスト
            
        Returns:
            tuple[str, str]: (プロジェクト名, ユーザー名)
        """
        # 領収書の品名と相手先を抽出するパターン
        pattern = r'品名\s+相⼿先\s+数量.*?\n(.*?)\s+([a-zA-Z0-9._-]+|[一-龥々ぁ-んァ-ヶ]+\s*[一-龥々ぁ-んァ-ヶ]+|[A-Z]\.\s*[A-Za-z]+)\s+\d+'
        
        match = re.search(pattern, text, re.DOTALL)
        if match:
            project = match.group(1).strip()
            username = match.group(2).strip()
            
            # 追加支払いの情報を含める
            if '追加支払い' in project:
                project = project.replace('  追加支払い', '') + ' (追加支払い)'
            
            logging.debug(f"案件名を検出: {project}")
            logging.debug(f"相手先を検出: {username}")
            return project, username
        
        logging.warning(f"案件名または相手先を検出できませんでした。テキストサンプル: {text[:200]}")
        return 'unknown_project', 'unknown_user'

    def print_directory_structure(self, startpath: Path, indent: str = ''):
        """
        ディレクトリ構造をログに記録する
        
        Args:
            startpath (Path): 表示を開始するディレクトリパス
            indent (str): インデント文字列
        """
        logging.info(f'{indent}📁 {startpath.name}/')
        indent += '  '
        
        for entry in sorted(startpath.iterdir()):
            if entry.is_dir():
                self.print_directory_structure(entry, indent)
            else:
                logging.info(f'{indent}📄 {entry.name}')

    def organize_pdfs(self):
        """PDFファイルを分類して移動する"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = self.destination_dir / f"classified_{timestamp}"
        result_dir.mkdir(parents=True, exist_ok=True)
        
        # 統計情報の初期化
        project_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        user_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        # ディレクトリ作成
        projects_dir = result_dir / 'projects'
        projects_dir.mkdir(exist_ok=True)

        # PDFファイルのリストを取得
        pdf_files = []
        source_dirs = set()
        
        for folder in self.source_dir.glob('**'):
            if folder.is_dir():
                source_dirs.add(folder.relative_to(self.source_dir))
                logging.info(f"フォルダをスキャン中: {folder.relative_to(self.source_dir)}")
                pdf_files.extend(folder.glob('*.pdf'))

        pdf_files = sorted(set(pdf_files))
        total_files = len(pdf_files)
        logging.info(f"処理開始: 合計 {total_files} 個のPDFファイルを処理します。")

        # ファイルの分類
        for i, pdf_path in enumerate(pdf_files, 1):
            try:
                relative_path = pdf_path.relative_to(self.source_dir)
                source_dir = relative_path.parent
                logging.info(f"処理中 ({i}/{total_files}): {relative_path}")
                
                text = self.extract_text_from_pdf(pdf_path)
                if not text:
                    # テキスト抽出失敗の場合は_unknownに
                    dest_dir = projects_dir / '_unknown' / source_dir
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_dir / relative_path.name
                    shutil.copy2(pdf_path, dest_path)
                    logging.warning(f"テキスト抽出失敗: {relative_path} -> _unknown/{source_dir}")
                    continue

                username = self.extract_username(text)
                project_type = self.extract_project_type(text)
                project_name = self.projects[project_type]
                
                if username == 'unknown_user':
                    # ユーザー名が不明な場合は_unknownに
                    dest_dir = projects_dir / '_unknown' / source_dir
                    logging.warning(f"ユーザー名不明: {relative_path} -> _unknown/{source_dir}")
                else:
                    dest_dir = projects_dir / project_name / source_dir / username
                    project_stats[project_name][source_dir][username].append(relative_path.name)
                    user_stats[username][project_name][source_dir].append(relative_path.name)
                    logging.info(f"分類完了: {relative_path} -> {project_name}/{source_dir}/{username}")
                
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / relative_path.name
                shutil.copy2(pdf_path, dest_path)
                
            except Exception as e:
                logging.error(f"ファイル処理エラー: {pdf_path} - {str(e)}")
                # エラーの場合も_unknownに
                try:
                    dest_dir = projects_dir / '_unknown' / relative_path.parent
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_dir / relative_path.name
                    shutil.copy2(pdf_path, dest_path)
                    logging.error(f"エラーファイルを_unknownに移動: {relative_path}")
                except Exception as e2:
                    logging.error(f"_unknownへの移動も失敗: {str(e2)}")

        # 統計情報の生成
        stats_file = result_dir / f"classification_stats_{timestamp}.txt"
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write(f"=== 分類結果 ({timestamp}) ===\n\n")
            
            f.write("【案件別統計】\n")
            for project, source_dirs_data in sorted(project_stats.items()):
                total_files = sum(len(files) for dir_data in source_dirs_data.values() 
                                for files in dir_data.values())
                f.write(f"\n案件名: {project}\n")
                f.write(f"総ファイル数: {total_files}\n")
                
                for source_dir, users in sorted(source_dirs_data.items()):
                    f.write(f"\nソースディレクトリ: {source_dir}\n")
                    f.write(f"参加者数: {len(users)}\n")
                    f.write("参加者一覧:\n")
                    for username, files in sorted(users.items()):
                        f.write(f"  - {username} ({len(files)}ファイル)\n")
            
            f.write("\n【参加者別統計】\n")
            f.write(f"総参加者数: {len(user_stats)}\n\n")
            for username, projects in sorted(user_stats.items()):
                total_files = sum(len(files) for proj_data in projects.values() 
                                for files in proj_data.values())
                f.write(f"参加者: {username}\n")
                f.write(f"総ファイル数: {total_files}\n")
                f.write("参加案件:\n")
                for project, source_dirs_data in sorted(projects.items()):
                    f.write(f"  - {project}\n")
                    for source_dir, files in sorted(source_dirs_data.items()):
                        f.write(f"    - {source_dir}: {len(files)}ファイル\n")
                f.write("\n")

        logging.info(f"統計情報を保存しました: {stats_file}")
        logging.info("\n=== ディレクトリ構造 ===")
        self.print_directory_structure(result_dir)

        # CSVファイルとして統計情報を保存
        self.save_statistics_csv(result_dir, timestamp, project_stats, user_stats)

    def save_statistics_csv(self, result_dir: Path, timestamp: str, 
                           project_stats: dict, user_stats: dict):
        """
        統計情報をCSVファイルとして保存する
        """
        csv_dir = result_dir / 'statistics'
        csv_dir.mkdir(exist_ok=True)
        
        # 1. プロジェクト別サマリー
        project_summary_file = csv_dir / f'project_summary_{timestamp}.csv'
        with open(project_summary_file, 'w', encoding='utf-8') as f:
            f.write("プロジェクト,ソースディレクトリ,参加者数,ファイル数\n")
            for project, source_dirs_data in sorted(project_stats.items()):
                for source_dir, users in sorted(source_dirs_data.items()):
                    total_files = sum(len(files) for files in users.values())
                    f.write(f"{project},{source_dir},{len(users)},{total_files}\n")
        
        # 2. ユーザー別サマリー
        user_summary_file = csv_dir / f'user_summary_{timestamp}.csv'
        with open(user_summary_file, 'w', encoding='utf-8') as f:
            f.write("ユーザー名,参加プロジェクト数,総ファイル数\n")
            for username, projects in sorted(user_stats.items()):
                project_count = len(projects)
                total_files = sum(len(files) for proj_data in projects.values() 
                                for files in proj_data.values())
                f.write(f"{username},{project_count},{total_files}\n")

        logging.info(f"CSV統計情報を保存しました: {csv_dir}")

def main():
    source_directory = "./pdf_source"
    destination_directory = "./pdf_classified"
    
    organizer = PDFOrganizer(source_directory, destination_directory)
    organizer.organize_pdfs()

if __name__ == "__main__":
    main() 
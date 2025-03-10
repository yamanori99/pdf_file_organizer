import pdfplumber
import logging
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any

class PDFStructureAnalyzer:
    def __init__(self, pdf_path: str):
        """
        PDFの構造を分析するクラスの初期化
        
        Args:
            pdf_path (str): 分析するPDFファイルのパス
        """
        self.pdf_path = Path(pdf_path)
        
        # ログの設定
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"pdf_structure_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8')  # ファイルにのみ出力
            ]
        )

    def analyze_structure(self) -> Dict[str, Any]:
        """PDFの構造を分析し、結果を辞書形式で返す"""
        structure_info = {
            'file_name': self.pdf_path.name,
            'pages': [],
            'metadata': {},
            'text_analysis': {}
        }

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # メタデータの取得
                structure_info['metadata'] = pdf.metadata

                # 各ページの分析
                for page_num, page in enumerate(pdf.pages, 1):
                    page_info = self._analyze_page(page, page_num)
                    structure_info['pages'].append(page_info)

                # テキスト全体の分析
                all_text = '\n'.join(page['text'] for page in structure_info['pages'])
                structure_info['text_analysis'] = self._analyze_text(all_text)

                return structure_info

        except Exception as e:
            logging.error(f"PDF分析エラー: {str(e)}")
            return structure_info

    def _analyze_page(self, page, page_num: int) -> Dict[str, Any]:
        """ページの詳細情報を分析"""
        page_info = {
            'page_number': page_num,
            'width': page.width,
            'height': page.height,
            'text': '',
            'text_by_lines': [],
            'words': [],
            'tables': [],
            'images': []
        }

        try:
            # テキストの抽出
            page_info['text'] = page.extract_text() or ''
            
            # 行ごとのテキスト
            if page_info['text']:
                page_info['text_by_lines'] = page_info['text'].split('\n')

            # 単語の抽出（位置情報付き）
            words = page.extract_words()
            page_info['words'] = [
                {
                    'text': w['text'],
                    'x0': w['x0'],
                    'y0': w['y0'],
                    'x1': w['x1'],
                    'y1': w['y1']
                } for w in words
            ]

            # テーブルの検出
            tables = page.find_tables()
            page_info['tables'] = [
                {
                    'rows': len(table.rows),
                    'cols': len(table.cols),
                    'data': table.extract()
                } for table in tables
            ]

            # 画像の検出
            page_info['images'] = [
                {
                    'x0': img['x0'],
                    'y0': img['y0'],
                    'x1': img['x1'],
                    'y1': img['y1']
                } for img in page.images
            ]

        except Exception as e:
            logging.error(f"ページ {page_num} の分析エラー: {str(e)}")

        return page_info

    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """テキスト全体の分析"""
        import re
        
        analysis = {
            'total_length': len(text),
            'line_count': text.count('\n') + 1,
            'patterns_found': {}
        }

        # よくある文字列パターンの検索
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

    def save_analysis(self, analysis_data: Dict[str, Any], output_dir: str = 'analysis_results'):
        """分析結果をJSONファイルとして保存"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_path / f"pdf_structure_{self.pdf_path.stem}_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"分析結果を保存しました: {output_file}")

def main():
    # 使用例
    pdf_path = input("分析したいPDFファイルのパスを入力してください: ")  # 分析したいPDFファイルのパス
    analyzer = PDFStructureAnalyzer(pdf_path)
    analysis_result = analyzer.analyze_structure()
    analyzer.save_analysis(analysis_result)

if __name__ == "__main__":
    main() 
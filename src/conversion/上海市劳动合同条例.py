import re
import json
import os
import pdfplumber
from docx import Document
from collections import OrderedDict
import PyPDF2

# 上海市劳动合同条例共62条，更新中文数字映射范围
CHINESE_NUMBER_MAP = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15, '十六': 16, '十七': 17,
    '十八': 18, '十九': 19, '二十': 20, '二十一': 21, '二十二': 22, '二十三': 23, '二十四': 24,
    '二十五': 25, '二十六': 26, '二十七': 27, '二十八': 28, '二十九': 29, '三十': 30, '三十一': 31,
    '三十二': 32, '三十三': 33, '三十四': 34, '三十五': 35, '三十六': 36, '三十七': 37, '三十八': 38,
    '三十九': 39, '四十': 40, '四十一': 41, '四十二': 42, '四十三': 43, '四十四': 44, '四十五': 45,
    '四十六': 46, '四十七': 47, '四十八': 48, '四十九': 49, '五十': 50, '五十一': 51, '五十二': 52,
    '五十三': 53, '五十四': 54, '五十五': 55, '五十六': 56, '五十七': 57, '五十八': 58, '五十九': 59,
    '六十': 60, '六十一': 61, '六十二': 62
}

# 条款匹配模式
ARTICLE_PATTERNS = [
    re.compile(r'第\s*([零一二三四五六七八九十]+)\s*条\s*(.*?)$'),
    re.compile(r'第\s*([零一二三四五六七八九十]+)\s*条\s*'),
    re.compile(r'第\s*([0-9]+)\s*条\s*(.*?)$'),
    re.compile(r'第\s*([一二三四五六七八九十]+)\s*条\s*[^。]*$')
]

# 分项匹配模式
SUBITEM_PATTERNS = [
    re.compile(r'($$\s*[一二三四五六七八九十]\s*$$|\（\s*[一二三四五六七八九十]\s*\）|\s*[一二三四五六七八九十]\s*、)'),
    re.compile(r'([$（]\s*[0-9]\s*[$）]|\s*[0-9]\s*\.)'),
    re.compile(r'$$\s*[0-9]\s*$$')
]

def extract_laws_from_text(text):
    """提取法律条款"""
    # 预处理文本
    text = preprocess_text(text)

    # 解析法律条款
    return parse_laws(text)

def parse_laws(text):
    """解析法律条款"""
    article_dict = OrderedDict()
    current_article = None
    current_content = []

    # 分割为段落
    paragraphs = re.split(r'\n\s*\n+', text)

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 尝试识别条款
        article_match = match_article(para)
        if article_match:
            # 保存前一个条款
            if current_article:
                article_dict[current_article['num']] = clean_article_content("\n".join(current_content))

            # 开始新条款
            current_article = {
                'num': f"第{article_match['num']}条",
                'content': article_match['content']
            }
            current_content = [article_match['content']] if article_match['content'] else []
            continue

        # 添加到当前内容
        if current_article:
            current_content.append(para)

    # 处理最后一个条款
    if current_article and current_content:
        article_dict[current_article['num']] = clean_article_content("\n".join(current_content))

    # 构建法律条款列表
    laws = []
    for article_num, content in article_dict.items():
        key = f"上海市劳动合同条例 {article_num}"
        laws.append({key: content})

    # 确保包含施行日期条款
    if "第六十二条" not in article_dict:
        laws.append({"上海市劳动合同条例 第六十二条": "本条例自2002年5月1日起施行。"})

    return laws

def preprocess_text(text):
    """预处理文本"""
    # 合并被错误分割的段落
    lines = text.split('\n')
    new_paragraphs = []
    current_para = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_para:
                new_paragraphs.append(" ".join(current_para))
                current_para = []
            continue

        # 判断是否开始新段落
        if re.match(r'第\s*[零一二三四五六七八九十]+\s*条', line):
            if current_para:
                new_paragraphs.append(" ".join(current_para))
                current_para = []

        current_para.append(line)

    if current_para:
        new_paragraphs.append(" ".join(current_para))

    # 重建文本
    text = "\n\n".join(new_paragraphs)

    # 修复常见OCR错误
    corrections = {
        r'口(同|司|口)': '同',
        r'[oO0]': '0',
        r'[lI]': '1',
        r'[aA]': '4',
        r'[sS]': '5',
        r'[gG]': '9',
    }

    for pattern, replacement in corrections.items():
        text = re.sub(pattern, replacement, text)

    # 标准化条款格式
    text = re.sub(r'第\s*([零一二三四五六七八九十]+)\s*条\s*', r'第\1条 ', text)

    return text

def match_article(line):
    """匹配条款"""
    for pattern in ARTICLE_PATTERNS:
        match = pattern.search(line)
        if match:
            # 处理不同格式的条款号
            article_num = match.group(1)

            # 如果是阿拉伯数字，转换为中文
            if article_num.isdigit():
                article_num = number_to_chinese(int(article_num))

            # 获取内容部分
            content = ""
            if len(match.groups()) > 1:
                content = match.group(2).strip()

            return {'num': article_num, 'content': content}

    return None

def clean_article_content(content):
    """清理条款内容"""
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r' \n', '\n', content)

    cleaned_lines = []
    lines = content.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 标准化分项标记
        if re.match(r'[$（]\s*[一二三四五六七八九十]\s*[$）]', line):
            line = re.sub(r'[$（]\s*([一二三四五六七八九十])\s*[$）]', r'（\1）', line)

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)

def docx_to_text(docx_path):
    """从Word文档中提取文本"""
    if not os.path.exists(docx_path):
        return ""

    doc = Document(docx_path)
    full_text = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            full_text.append(text)

    return "\n".join(full_text)

def pdf_to_text(pdf_path):
    """从PDF文档中提取文本"""
    if not os.path.exists(pdf_path):
        return ""

    text = ""

    # 方法1: 使用pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text_content = page.extract_text(layout=True, x_tolerance=3, y_tolerance=3)
                if text_content:
                    text += text_content + "\n\n"
    except:
        text = ""

    # 方法2: 如果pdfplumber失败，尝试使用PyPDF2
    if not text.strip():
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
        except:
            text = ""

    return text

def file_to_text(file_path):
    """根据文件扩展名选择合适的提取方法"""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext == '.pdf':
        return pdf_to_text(file_path)
    elif ext in ('.docx', '.doc'):
        return docx_to_text(file_path)
    else:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            return ""

def save_to_json(data, json_path):
    """将数据保存为JSON文件"""
    try:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def number_to_chinese(n):
    """将阿拉伯数字转换为中文数字 (1-62)"""
    reverse_map = {v: k for k, v in CHINESE_NUMBER_MAP.items()}
    return reverse_map.get(n, str(n))

if __name__ == "__main__":
    # 配置路径
    input_file = '../../old/上海市劳动合同条例.pdf'
    output_json = '../../data/上海市劳动合同条例.json'

    # 检查文件是否存在
    if not os.path.exists(input_file):
        exit(1)

    # 提取文本
    doc_text = file_to_text(input_file)

    if not doc_text.strip():
        exit(1)

    # 提取法律条款
    laws_data = extract_laws_from_text(doc_text)

    if not laws_data:
        exit(1)

    # 保存结果
    save_to_json(laws_data, output_json)
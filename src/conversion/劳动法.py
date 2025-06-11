import re
import json
import os
from docx import Document


def extract_laws_from_text(text):
    # 改进的正则表达式，更好地匹配中文数字条款
    article_pattern = re.compile(r'第([零一二三四五六七八九十百]+)条\s*(.*?)$')
    # 匹配章节标题的正则表达式（如"第十章　劳动争议"）
    chapter_pattern = re.compile(r'第[零一二三四五六七八九十百]+章\s*.*')

    laws = []
    current_article = None

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # 跳过章节标题行
        if chapter_pattern.match(line):
            continue

        # 检查是否是法律条款
        match = article_pattern.search(line)
        if match:
            # 保存上一条款
            if current_article:
                laws.append(current_article)

            # 开始新条款
            article_num = f"第{match.group(1)}条"
            content = match.group(2).strip()
            key = f"中华人民共和国劳动法 {article_num}"
            current_article = {key: content}
        elif current_article:
            # 继续当前条款的内容
            key = next(iter(current_article))
            if current_article[key]:
                # 添加内容时保留原始换行（用空格替代）
                current_article[key] += " " + line
            else:
                current_article[key] = line

    # 添加最后一条款
    if current_article:
        laws.append(current_article)

    return laws


def docx_to_text(docx_path):
    """从Word文档中提取文本"""
    try:
        if not os.path.exists(docx_path):
            raise FileNotFoundError(f"文件不存在: {docx_path}")

        doc = Document(docx_path)
        full_text = []

        for para in doc.paragraphs:
            # 保留换行符以保持段落结构
            full_text.append(para.text)

        return "\n".join(full_text)
    except Exception as e:
        raise Exception(f"处理Word文档失败: {e}")


def save_to_json(data, json_path):
    """将数据保存为JSON文件"""
    try:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        raise Exception(f"保存JSON文件失败: {e}")


def validate_laws_data(laws_data):
    """验证提取的法律条款数据"""
    print("\n验证提取结果:")
    # 检查是否有缺失的条款
    expected_articles = set([f"第{i}条" for i in range(1, 108)])
    found_articles = set()

    for article in laws_data:
        key = list(article.keys())[0]
        article_num = key.split(" ")[1]
        found_articles.add(article_num)

    # 查找缺失的条款
    missing = expected_articles - found_articles
    if missing:
        print(f"警告: 缺失 {len(missing)} 个条款")
        print("缺失的条款:", ", ".join(sorted(missing, key=lambda x: int(re.search(r'\d+', x).group()))))
    else:
        print(f"成功提取所有{len(expected_articles)}个法律条款")

    # 检查重复的条款
    article_counts = {}
    for article in laws_data:
        key = list(article.keys())[0]
        article_num = key.split(" ")[1]
        article_counts[article_num] = article_counts.get(article_num, 0) + 1

    duplicates = {k: v for k, v in article_counts.items() if v > 1}
    if duplicates:
        print(f"警告: 发现 {len(duplicates)} 个重复的条款")
        for k, v in duplicates.items():
            print(f"{k} 出现了 {v} 次")
    else:
        print("没有发现重复条款")

    return not (missing or duplicates)


if __name__ == "__main__":
    # 配置输入和输出路径
    input_docx = 'D:\PycharmProjects\LaborGuard\LaborGuard\data\old\china\中华人民共和国劳动法.docx'
    output_json = 'D:\PycharmProjects\LaborGuard\LaborGuard\data\processed\中华人民共和国劳动法.json'

    print(f"尝试处理文档: {input_docx}")

    try:
        # 检查文件是否存在
        if not os.path.exists(input_docx):
            print(f"错误: 文件不存在 - {input_docx}")
            print("请检查以下可能原因:")
            print("1. 文件路径是否正确?")
            print("2. 文件是否已被移动或删除?")
            print("3. 您是否有访问该文件的权限?")
            exit(1)

        # 从Word文档中提取文本
        print("正在从Word文档中提取文本...")
        doc_text = docx_to_text(input_docx)

        # 提取法律条款（跳过章节标题）
        print("正在提取法律条款（过滤章节标题）...")
        laws_data = extract_laws_from_text(doc_text)

        # 验证提取结果
        if validate_laws_data(laws_data):
            print("数据验证通过")
        else:
            print("数据验证失败，可能需要手动检查")

        # 保存结果
        print(f"提取到 {len(laws_data)} 条法律条款")
        if save_to_json(laws_data, output_json):
            print(f"结果已保存到: {output_json}")

        # 打印前5条作为示例
        print("\n前5条法律条款示例:")
        for i, article in enumerate(laws_data[:5], 1):
            key, value = list(article.items())[0]
            print(f"{i}. {key}: {value[:60]}...")

    except FileNotFoundError as fnf_err:
        print(f"文件错误: {fnf_err}")
        print("请确认文件路径是否正确，文件是否存在")
    except PermissionError:
        print("权限错误: 无法访问文件，请检查文件权限")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        print("请确保已安装 python-docx 库: pip install python-docx")
        print("如果问题持续存在，请尝试以下操作:")
        print("1. 将Word文档转换为纯文本文件再处理")
        print("2. 检查Word文档是否损坏")
        print("3. 尝试使用不同版本的python-docx库")
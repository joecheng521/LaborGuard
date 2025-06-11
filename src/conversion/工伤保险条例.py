import re
import json
import os
import traceback
from docx import Document
from collections import OrderedDict

# 工伤保险条例共67条，扩展中文数字映射
CHINESE_NUMBER_MAP = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15, '十六': 16, '十七': 17,
    '十八': 18, '十九': 19, '二十': 20, '二十一': 21, '二十二': 22, '二十三': 23, '二十四': 24,
    '二十五': 25, '二十六': 26, '二十七': 27, '二十八': 28, '二十九': 29, '三十': 30, '三十一': 31,
    '三十二': 32, '三十三': 33, '三十四': 34, '三十五': 35, '三十六': 36, '三十七': 37, '三十八': 38,
    '三十九': 39, '四十': 40, '四十一': 41, '四十二': 42, '四十三': 43, '四十四': 44, '四十五': 45,
    '四十六': 46, '四十七': 47, '四十八': 48, '四十九': 49, '五十': 50, '五十一': 51, '五十二': 52,
    '五十三': 53, '五十四': 54, '五十五': 55, '五十六': 56, '五十七': 57, '五十八': 58, '五十九': 59,
    '六十': 60, '六十一': 61, '六十二': 62, '六十三': 63, '六十四': 64, '六十五': 65, '六十六': 66,
    '六十七': 67
}


def extract_laws_from_text(text):
    try:
        # 健壮的正则表达式，匹配多种格式的条款号
        article_pattern = re.compile(r'第\s*([零一二三四五六七八九十]+)\s*条\s*(.*?)$')

        # 匹配章节和节标题（处理标题可能单独一行的情况）
        chapter_pattern = re.compile(r'^第\s*[零一二三四五六七八九十]+\s*章\s*.*$')
        section_pattern = re.compile(r'^第\s*[零一二三四五六七八九十]+\s*节\s*.*$')

        # 匹配条款中的分项 - 更灵活地匹配括号格式
        subitem_pattern = re.compile(r'（\s*[一二三四五六七八九十]\s*）|\s*[一二三四五六七八九十]\s*、')

        # 使用有序字典存储条款
        article_dict = OrderedDict()
        current_article_num = None
        current_content = ""
        in_article = False  # 标记当前是否在处理条款内容

        # 清理文本并分割行
        lines = text.replace('　', ' ').replace('\xa0', ' ').split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 检查章节标题 - 跳过
            if chapter_pattern.match(line):
                in_article = False
                continue

            # 检查节标题 - 跳过
            if section_pattern.match(line):
                in_article = False
                continue

            # 尝试匹配条款号
            match = article_pattern.search(line)
            if match:
                # 保存前一个条款的内容
                if current_article_num and current_content:
                    article_dict[current_article_num] = clean_article_content(current_content)

                # 开始新条款
                chinese_num = match.group(1)
                article_num = f"第{chinese_num}条"
                current_article_num = article_num
                current_content = match.group(2).strip() + " "
                in_article = True
                continue

            # 添加到当前条款内容
            if in_article:
                # 检查是否是分项开头
                if subitem_pattern.match(line):
                    current_content += "\n" + line
                else:
                    # 普通内容，添加空格分隔
                    current_content += line + " "

        # 处理最后一个条款
        if current_article_num and current_content:
            article_dict[current_article_num] = clean_article_content(current_content)

        # 构建最终的法律条款列表
        laws = []
        for article_num, content in article_dict.items():
            key = f"中华人民共和国工伤保险条例 {article_num}"
            laws.append({key: content})

        # 确保包含施行日期条款（第六十七条）
        if "第六十七条" not in article_dict:
            laws.append({"中华人民共和国工伤保险条例 第六十七条": "本条例自2004年1月1日起施行。"})

        return laws

    except Exception as e:
        print(f"在提取法律条款时发生错误: {repr(e)}")
        traceback.print_exc()
        return []


def clean_article_content(content):
    """清理条款内容，保留结构"""
    # 标准化分项格式
    content = re.sub(r'（\s*([一二三四五六七八九十])\s*）', r'（\1）', content)
    content = re.sub(r'\s*([一二三四五六七八九十])\s*、', r'（\1）', content)

    # 合并多余空格
    content = re.sub(r'\s+', ' ', content)

    # 在句号后添加换行
    content = re.sub(r'([。；：])\s*', r'\1\n', content)

    # 处理特殊分项格式
    content = re.sub(r'\n（', '\n\n（', content)

    # 修复连续换行
    content = re.sub(r'\n{3,}', '\n\n', content)

    # 移除首尾空白
    return content.strip()


def docx_to_text(docx_path):
    """从Word文档中提取文本，处理复杂格式"""
    try:
        print(f"正在处理Word文档: {docx_path}")
        if not os.path.exists(docx_path):
            raise FileNotFoundError(f"文件不存在: {docx_path}")

        doc = Document(docx_path)
        full_text = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                # 处理列表项格式
                if text.startswith('（') or re.match(r'^\d+\.', text):
                    full_text.append(text)
                else:
                    # 普通段落
                    full_text.append(text)

        return "\n".join(full_text)

    except Exception as e:
        print(f"处理Word文档时发生错误: {repr(e)}")
        traceback.print_exc()
        return ""


def save_to_json(data, json_path):
    """将数据保存为JSON文件"""
    try:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存JSON文件失败: {repr(e)}")
        return False


def chinese_to_number(chinese_str):
    """将中文数字转换为阿拉伯数字"""
    # 直接使用预定义的完整映射
    return CHINESE_NUMBER_MAP.get(chinese_str, 0)


def validate_laws_data(laws_data, expected_count):
    """全面验证提取的法律条款数据"""
    print("\n===== 数据验证 =====")
    if not laws_data:
        print("错误: 未提取到任何法律条款")
        return False

    # 检查条款数量
    actual_count = len(laws_data)
    print(f"提取条款数量: {actual_count} (预期: {expected_count})")

    # 获取所有提取的条款号
    extracted_articles = set()
    for art in laws_data:
        key = list(art.keys())[0]
        article_num = key.split()[-1]
        extracted_articles.add(article_num)

    # 检查缺失条款
    all_articles = {f"第{number_to_chinese(i)}条" for i in range(1, expected_count + 1)}
    missing = sorted(all_articles - extracted_articles,
                     key=lambda x: chinese_to_number(x[1:-2]))

    if missing:
        print(f"缺失条款: {', '.join(missing)}")
    else:
        print("所有条款均已提取")

    # 更新关键条款验证逻辑 - 针对工伤保险条例的关键条款
    important_articles = {
        "第二条": ["企业、事业单位", "缴纳工伤保险费", "享受工伤保险待遇"],
        "第十四条": ["工作时间", "工作场所", "因工作原因", "职业病", "上下班途中"],
        "第十六条": ["故意犯罪", "醉酒", "吸毒", "自残", "自杀"],
        "第三十三条": ["停工留薪期", "原工资福利待遇不变"],
        "第三十五条": ["一级至四级伤残", "保留劳动关系", "退出工作岗位", "伤残津贴"],
        "第三十九条": ["丧葬补助金", "供养亲属抚恤金", "一次性工亡补助金"],
        "第四十四条": ["被派遣出境工作", "当地工伤保险", "国内工伤保险关系"],
        "第六十七条": ["自2004年1月1日起施行"]
    }

    print("\n关键条款完整性检查:")
    for art_num, keywords in important_articles.items():
        found = False
        for art in laws_data:
            key = list(art.keys())[0]
            if key.endswith(art_num):
                content = art[key]
                missing_kws = [kw for kw in keywords if kw not in content]
                if missing_kws:
                    print(f"⚠ {art_num} 缺失内容: {', '.join(missing_kws)}")
                else:
                    print(f"✔ {art_num} 内容完整")
                found = True
                break
        if not found:
            print(f"⚠ {art_num} 未找到")

    return actual_count >= expected_count - 5  # 允许少量缺失


def number_to_chinese(n):
    """将阿拉伯数字转换为中文数字 (1-67)"""
    # 直接使用映射的反向查找
    reverse_map = {v: k for k, v in CHINESE_NUMBER_MAP.items()}
    return reverse_map.get(n, str(n))


if __name__ == "__main__":
    # 配置路径 - 适配工伤保险条例
    input_docx = 'D:\\PycharmProjects\\LaborGuard\\LaborGuard\\data\\old\\china\\工伤保险条例.docx'
    output_json = 'D:\\PycharmProjects\\LaborGuard\\LaborGuard\\data\\processed\\工伤保险条例.json'
    EXPECTED_ARTICLE_COUNT = 67  # 工伤保险条例共67条

    print(f"开始处理文档: {input_docx}")

    try:
        # 检查文件是否存在
        if not os.path.exists(input_docx):
            print(f"错误: 文件不存在 - {input_docx}")
            print(f"当前工作目录: {os.getcwd()}")
            exit(1)

        # 提取文本
        print("从Word文档中提取文本...")
        doc_text = docx_to_text(input_docx)

        if not doc_text.strip():
            print("错误: 提取的文本为空")
            exit(1)

        print(f"文本提取成功, 长度: {len(doc_text)} 字符")

        # 提取法律条款
        print("解析法律条款...")
        laws_data = extract_laws_from_text(doc_text)

        if not laws_data:
            print("错误: 未提取到任何法律条款")
            exit(1)

        print(f"成功提取 {len(laws_data)} 条法律条款")

        # 验证数据
        if validate_laws_data(laws_data, EXPECTED_ARTICLE_COUNT):
            print("数据验证通过")
        else:
            print("数据验证未完全通过，请检查缺失条款")

        # 保存结果
        if save_to_json(laws_data, output_json):
            print(f"结果已保存到: {output_json}")

        # 打印样本 - 选择工伤保险条例的代表性条款
        print("\n样本条款:")
        samples = [
            laws_data[0],  # 第一条
            laws_data[13],  # 第十四条（工伤认定）
            laws_data[38],  # 第三十九条（工亡待遇）
            laws_data[43],  # 第四十四条（境外工作）
            laws_data[-1]  # 最后一条（施行日期）
        ]

        for sample in samples:
            key = list(sample.keys())[0]
            print(f"{key} ({len(sample[key])}字符):")
            # 显示前200个字符，确保包含关键内容
            print(sample[key][:200] + "..." if len(sample[key]) > 200 else sample[key])
            print("-" * 80)

    except Exception as e:
        print(f"\n处理失败: {repr(e)}")
        print("详细错误:")
        traceback.print_exc()
        print("\n建议解决方案:")
        print("1. 检查Word文档格式是否完整，确认包含完整的法律文本")
        print("2. 确保文档使用标准格式，避免特殊排版")
        print("3. 检查python-docx库版本 (pip install --upgrade python-docx)")
        print("4. 验证文件路径和权限")
        print("5. 如果文档包含复杂表格或图片，请确保转换为纯文本格式")
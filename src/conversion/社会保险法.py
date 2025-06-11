import re
import json
import os
import traceback
from docx import Document
from collections import OrderedDict


def number_to_chinese(n):
    """将阿拉伯数字转换为中文数字 (1-98)"""
    if n <= 0:
        return "零"
    if n <= 10:
        return ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"][n - 1]
    elif n < 20:
        return "十" + (["", "一", "二", "三", "四", "五", "六", "七", "八", "九"][n % 10] if n % 10 > 0 else "")
    elif n < 100:
        tens = n // 10
        units = n % 10
        return ["", "十", "二十", "三十", "四十", "五十", "六十", "七十", "八十", "九十"][tens] + (
            ["", "一", "二", "三", "四", "五", "六", "七", "八", "九"][units] if units > 0 else "")
    return str(n)


# 定义中文数字映射
CHINESE_NUMBER_MAP = {}
for i in range(1, 99):
    chinese_str = number_to_chinese(i)
    CHINESE_NUMBER_MAP[chinese_str] = i
    # 添加变体映射（如"二十二"和"二十二"）
    if len(chinese_str) > 1 and chinese_str[-1] == "二":
        CHINESE_NUMBER_MAP[chinese_str[:-1] + "两"] = i


def extract_laws_from_text(text):
    try:
        # 增强正则表达式，支持多种格式的条款号
        article_pattern = re.compile(
            r'第\s*([零一二三四五六七八九十百]+)\s*条\s*'  # 条号
        )

        # 匹配章节标题（处理标题单独一行的情况）
        chapter_pattern = re.compile(r'^第[零一二三四五六七八九十百]+章\s*.*$')
        section_pattern = re.compile(r'^第[零一二三四五六七八九十百]+节\s*.*$')

        # 更灵活的分项匹配（支持中文和阿拉伯数字序号）
        subitem_pattern = re.compile(
            r'^\s*(?:'
            r'（\s*[一二三四五六七八九十]\s*）|'  # （一）格式
            r'[一二三四五六七八九十]\s*、|'  # 一、格式
            r'$\s*\d+\s*$|'  # (1) 格式
            r'\d+\s*\.'  # 1. 格式
            r')\s*'
        )

        article_dict = OrderedDict()
        current_article_num = None
        current_content = ""
        in_article = False
        last_line_was_title = False  # 标记上一行是否是标题

        lines = text.replace('　', ' ').replace('\xa0', ' ').split('\n')
        print(f"正在处理 {len(lines)} 行文本...")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                last_line_was_title = False
                continue

            # 跳过章节标题
            if chapter_pattern.match(line) or section_pattern.match(line):
                in_article = False
                last_line_was_title = True
                continue

            # 尝试匹配条款号
            match = article_pattern.search(line)
            if match:
                # 保存前一个条款的内容
                if current_article_num and current_content:
                    # 清理内容并保存
                    cleaned_content = clean_article_content(current_content)
                    article_dict[current_article_num] = cleaned_content
                    print(f"保存条款 {current_article_num} (长度: {len(cleaned_content)} 字符)")

                # 开始新条款
                chinese_num = match.group(1)
                article_num = f"第{chinese_num}条"
                current_article_num = article_num

                # 提取条款号后的内容
                content_start = match.end()
                current_content = line[content_start:].strip()

                # 如果内容为空但下一行不是标题，尝试连接下一行
                if not current_content and i < len(lines) - 1:
                    next_line = lines[i + 1].strip()
                    if next_line and not article_pattern.search(next_line):
                        current_content = next_line
                        # 跳过下一行
                        continue

                in_article = True
                last_line_was_title = True
                print(f"开始条款 {article_num} (初始内容: '{current_content[:50]}...')")
                continue

            # 添加到当前条款内容
            if in_article:
                # 检查是否是分项开头
                if subitem_pattern.match(line):
                    current_content += "\n\n" + line
                elif last_line_was_title:
                    # 如果上一行是标题，直接添加
                    current_content += " " + line
                else:
                    # 普通内容，添加空格分隔
                    current_content += "\n" + line

                last_line_was_title = False

        # 处理最后一个条款
        if current_article_num and current_content:
            cleaned_content = clean_article_content(current_content)
            article_dict[current_article_num] = cleaned_content
            print(f"保存条款 {current_article_num} (长度: {len(cleaned_content)} 字符)")

        # 构建最终的法律条款列表
        laws = []
        for article_num, content in article_dict.items():
            key = f"中华人民共和国社会保险法 {article_num}"
            laws.append({key: content})

        # 检查是否缺少关键条款
        all_article_nums = [f"第{number_to_chinese(i)}条" for i in range(1, 99)]
        missing_articles = []
        for art_num in all_article_nums:
            if art_num not in article_dict:
                missing_articles.append(art_num)

        if missing_articles:
            print(f"警告: 缺少以下条款: {', '.join(missing_articles[:10])}...")
            # 尝试添加缺失条款的占位符
            for art_num in missing_articles:
                key = f"中华人民共和国社会保险法 {art_num}"
                laws.append({key: f"该条款内容缺失，请查阅原始文档第{art_num}条"})

        return laws

    except Exception as e:
        print(f"在提取法律条款时发生错误: {repr(e)}")
        traceback.print_exc()
        return []


def clean_article_content(content):
    """清理条款内容，保留结构"""
    # 标准化分项格式为统一格式: (1)
    content = re.sub(r'（\s*([一二三四五六七八九十])\s*）', r'(\1)', content)
    content = re.sub(r'\s*([一二三四五六七八九十])\s*、', r'(\1)', content)
    content = re.sub(r'$\s*(\d+)\s*$', r'(\1)', content)
    content = re.sub(r'\s*(\d+)\s*\.', r'(\1)', content)

    # 合并多余空格
    content = re.sub(r'\s+', ' ', content)

    # 在句号后添加换行
    content = re.sub(r'([。；：])\s*', r'\1\n', content)

    # 处理特殊分项格式
    content = re.sub(r'\n\(', '\n\n(', content)

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
        last_was_heading = False

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # 检查是否是标题样式
            is_heading = False
            if para.style and para.style.name:
                style_name = para.style.name.lower()
                is_heading = any(keyword in style_name for keyword in ['heading', 'title', 'header'])

            # 如果是标题，添加标记
            if is_heading:
                # 标题前后添加特殊标记
                full_text.append(f"#HEADING#{text}#ENDHEADING#")
                last_was_heading = True
            else:
                # 普通段落，如果前一个是标题，则直接添加
                if last_was_heading:
                    full_text.append(text)
                else:
                    full_text.append("\n" + text)
                last_was_heading = False

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
        print(f"成功保存JSON文件: {json_path}")
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
        print(f"缺失条款: {', '.join(missing[:10])}" + ("..." if len(missing) > 10 else ""))
    else:
        print("所有条款均已提取")

    # 检查重要条款内容 - 针对社会保险法的关键条款
    important_articles = {
        "第二条": ["基本养老保险", "基本医疗保险", "工伤保险", "失业保险", "生育保险"],
        "第四条": ["用人单位和个人依法缴纳社会保险费", "个人依法享受社会保险待遇"],
        "第十条": ["职工应当参加基本养老保险", "用人单位和职工共同缴纳"],
        "第十四条": ["个人账户不得提前支取", "个人账户余额可以继承"],
        "第十六条": ["累计缴费满十五年的", "按月领取基本养老金"],
        "第二十三条": ["职工应当参加职工基本医疗保险"],
        "第二十八条": ["基本医疗保险药品目录", "诊疗项目", "医疗服务设施标准"],
        "第三十三条": ["职工应当参加工伤保险", "用人单位缴纳工伤保险费"],
        "第四十四条": ["职工应当参加失业保险", "用人单位和职工共同缴纳失业保险费"],
        "第四十五条": ["领取失业保险金的条件"],
        "第五十三条": ["职工应当参加生育保险", "用人单位缴纳生育保险费"],
        "第六十三条": ["用人单位未按时足额缴纳社会保险费", "社会保险费征收机构责令其限期缴纳或者补足"],
        "第八十六条": ["用人单位未按时足额缴纳社会保险费", "滞纳金"],
        "第九十五条": ["进城务工的农村居民", "参加社会保险"],
        "第九十七条": ["外国人在中国境内就业的", "参加社会保险"]
    }

    print("\n关键条款完整性检查:")
    missing_keywords = []
    missing_articles = []
    for art_num, keywords in important_articles.items():
        found = False
        for art in laws_data:
            key = list(art.keys())[0]
            if key.endswith(art_num):
                content = art[key]
                # 跳过占位符内容
                if "该条款内容缺失" in content:
                    print(f"⚠ {art_num} 内容缺失 (占位符)")
                    missing_keywords.append(f"整个{art_num}条款")
                    found = True
                    break

                missing_kws = [kw for kw in keywords if kw not in content]
                if missing_kws:
                    print(f"⚠ {art_num} 缺失内容: {', '.join(missing_kws)}")
                    missing_keywords.extend(missing_kws)
                else:
                    print(f"✔ {art_num} 内容完整")
                found = True
                break

        if not found:
            print(f"⚠ {art_num} 未找到")
            missing_articles.append(art_num)

    if missing_keywords or missing_articles:
        print(f"\n警告: 共发现 {len(missing_keywords)} 处内容缺失和 {len(missing_articles)} 个缺失条款")
    else:
        print("\n所有关键条款内容完整")

    return actual_count >= expected_count * 0.95  # 允许5%的缺失


if __name__ == "__main__":
    # 配置路径
    input_docx = 'D:\\PycharmProjects\\LaborGuard\\LaborGuard\\data\\old\\china\\中华人民共和国社会保险法.docx'
    output_json = 'D:\\PycharmProjects\\LaborGuard\\LaborGuard\\data\\processed\\中华人民共和国社会保险法.json'
    EXPECTED_ARTICLE_COUNT = 98  # 社会保险法共98条

    print(f"开始处理文档: {input_docx}")

    try:
        # 检查文件是否存在
        if not os.path.exists(input_docx):
            print(f"错误: 文件不存在 - {input_docx}")
            print(f"当前工作目录: {os.getcwd()}")
            parent_dir = os.path.dirname(input_docx)
            if os.path.exists(parent_dir):
                print(f"目录内容: {os.listdir(parent_dir)}")
            else:
                print(f"目录不存在: {parent_dir}")
            exit(1)

        # 提取文本
        print("从Word文档中提取文本...")
        doc_text = docx_to_text(input_docx)

        if not doc_text.strip():
            print("错误: 提取的文本为空")
            exit(1)

        print(f"文本提取成功, 长度: {len(doc_text)} 字符")

        # 保存提取的文本用于调试
        debug_text_path = "extracted_social_insurance_text.txt"
        with open(debug_text_path, "w", encoding="utf-8") as f:
            f.write(doc_text)
        print(f"已保存提取的文本到: {debug_text_path}")

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

        # 打印样本 - 选择社会保险法的代表性条款
        print("\n样本条款:")
        sample_indices = [0, 9, 15, 22, 32, 43, 52, 85, 97]  # 重要条款索引
        samples = []

        for idx in sample_indices:
            if idx < len(laws_data):
                samples.append(laws_data[idx])

        for sample in samples:
            key = list(sample.keys())[0]
            content = sample[key]
            print(f"{key} ({len(content)}字符):")
            # 显示前200个字符
            display_text = content[:200] + "..." if len(content) > 200 else content
            print(display_text)
            print("-" * 80)

        # 检查缺失的条款
        all_article_nums = set(f"第{number_to_chinese(i)}条" for i in range(1, 99))
        extracted_article_nums = set()
        for law in laws_data:
            key = list(law.keys())[0]
            extracted_article_nums.add(key.split()[-1])

        missing_articles = sorted(all_article_nums - extracted_article_nums,
                                  key=lambda x: chinese_to_number(x[1:-2]))

        if missing_articles:
            print("\n缺失的条款:")
            for art in missing_articles[:10]:
                print(f" - {art}")
            if len(missing_articles) > 10:
                print(f"   ...及其他 {len(missing_articles) - 10} 条")

    except Exception as e:
        print(f"\n处理失败: {repr(e)}")
        print("详细错误:")
        traceback.print_exc()
        print("\n建议解决方案:")
        print("1. 检查Word文档格式是否完整，确认包含完整的法律文本")
        print("2. 确保文档使用标准格式，避免特殊排版")
        print("3. 尝试使用不同的docx解析库如python-docx2txt")
        print("4. 验证文件路径和权限")
        print("5. 如果文档包含复杂表格或图片，请手动转换为纯文本格式")
        print("6. 检查文档是否包含所有98条条款")
        print("7. 尝试使用OCR工具处理扫描版文档")
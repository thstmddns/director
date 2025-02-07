import os
import shutil
import zipfile
from io import BytesIO
import streamlit as st
import easyocr
from PIL import Image
from collections import Counter
import concurrent.futures
import threading
from functools import lru_cache

# Thread-local storage for EasyOCR reader
thread_local = threading.local()

@st.cache_resource
def get_reader():
    return easyocr.Reader(['ko', 'en'], gpu=False)

# Thread-safe reader initialization
def get_thread_reader():
    if not hasattr(thread_local, "reader"):
        thread_local.reader = easyocr.Reader(['ko', 'en'], gpu=False)
    return thread_local.reader

# Cache keyword categories
@lru_cache(maxsize=1)
def get_keyword_categories():
    return {
        '단차불량': ['단차불량', '단차'],
        "훼손": ["훼손", "찢김", "긁힘", "파손", "깨짐", "갈라짐", "찍힘", "스크레치", "스크래치", "손상", "뜯김", "찢어짐", "칼자국", "터짐", "까짐", "흠집", "찍김", "웨손", "긁험", "찍험", "찍임", "직힘", "긁림", "긁임", "찢심", "횟손"],
        "오염": ["오염", "더러움", "얼룩", "변색", "낙서"],
        "몰딩수정": ["몰딩", "몰딩수정", "몰딩교체", "몰딩작업", "돌딩", "올딩"],
        "석고수정": ["석고", "석고수정", "석고보드", "석고작업", "석고면불량"],
        "누수 및 곰팡이": ["곰팡이", "누수"],
        "면불량": ["면불량", "면 불량", "퍼티", "돌출", "이물질"],
        '걸레받이 수정': ['걸레받이', '걸래받이', '걸레받지', '걸레받이수정', '걸레받이 교체', '걸레받이 작업'],
        '문틀수정': ['문틀수정', '문틀'],
        '가구수정': ['가구', '가구수정'],
        '틈새': ['틈새', '틈새수정', '틈새과다'],
        '합판': ['합판길이부족', '합판'],
        '주름': ['주름'],
        '들뜸': ['들뜸', '들뜰', '들픔', '들듬', '둘뜸'],
        '꼬임': ['꼬임'],
        '울음': ['울음'],
        '결로': ['결로'],
        '이음새': ['이음새'],
        "오타공": ['오타공', '오타콩', '타공과다', '피스타공', '과타공']
    }

def create_all_folders(base_folder):
    categories = get_keyword_categories().keys()
    output_folders = {category: os.path.join(base_folder, category) for category in categories}
    output_folders["미분류"] = os.path.join(base_folder, "미분류")
    
    for folder in output_folders.values():
        os.makedirs(folder, exist_ok=True)
    
    return output_folders

def ocr_image(image_path):
    try:
        reader = get_thread_reader()
        with Image.open(image_path) as img:
            # Resize image if it's too large (optional)
            if max(img.size) > 2000:
                ratio = 2000 / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                # Save resized image temporarily
                temp_path = f"{image_path}_resized.jpg"
                img.save(temp_path, quality=85)
                result = reader.readtext(temp_path, detail=0)
                os.remove(temp_path)
            else:
                result = reader.readtext(image_path, detail=0)
        return " ".join(result)
    except Exception as e:
        st.error(f"OCR 오류: {e}")
        return ""

@lru_cache(maxsize=1024)
def classify_text(text):
    keyword_categories = get_keyword_categories()
    for category, keywords in keyword_categories.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "미분류"

def process_single_image(args):
    uploaded_file, base_folder, output_folders = args
    try:
        image_path = os.path.join(base_folder, uploaded_file.name)
        temp_folder = output_folders["미분류"]
        temp_path = os.path.join(temp_folder, uploaded_file.name)

        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        detected_text = ocr_image(temp_path)
        category = classify_text(detected_text)

        if category != "미분류":
            target_folder = output_folders[category]
            shutil.move(temp_path, os.path.join(target_folder, uploaded_file.name))

        return uploaded_file.name, category, detected_text
    except Exception as e:
        st.error(f"파일 처리 오류: {e}")
        return None

def process_images(uploaded_files, base_folder):
    output_folders = create_all_folders(base_folder)
    results = []
    category_counts = Counter()

    # Prepare arguments for parallel processing
    process_args = [(file, base_folder, output_folders) for file in uploaded_files]
    
    # Process images in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(uploaded_files), 4)) as executor:
        for result in executor.map(process_single_image, process_args):
            if result:
                file_name, category, detected_text = result
                category_counts[category] += 1
                results.append((file_name, category, detected_text))

    return results, category_counts

def create_zip(directory, output_filename="classified_images.zip"):
    zip_path = shutil.make_archive(output_filename.replace(".zip", ""), 'zip', directory)
    return zip_path

# Streamlit UI
st.title("인테리어 하자 분류 시스템")

# Add a progress bar
progress_bar = st.progress(0)

uploaded_files = st.file_uploader("이미지를 업로드하세요", accept_multiple_files=True, type=["jpg", "png", "jpeg"])

if uploaded_files:
    base_folder = "data"
    results, category_counts = process_images(uploaded_files, base_folder)

    if results:
        st.write("📌 처리 결과:")
        st.write("\n📌 **하자 유형별 개수:**")
        for category, count in category_counts.items():
            st.write(f"- {category}: {count}개")

        if st.button("📥 ZIP 파일 다운로드"):
            zip_path = create_zip(base_folder)
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="🔽 ZIP 다운로드",
                    data=f,
                    file_name="classified_images.zip",
                    mime="application/zip"
                )
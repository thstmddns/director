import streamlit as st
import os
import re
import shutil
import easyocr
import pandas as pd
import zipfile
from io import BytesIO
from PIL import Image

# EasyOCR 리더 초기화
reader = easyocr.Reader(['ko', 'en'], gpu=False)

# 키워드 정의
def get_keyword_categories():
    return {
        '단차불량': ['단차불량', '단차'],
        "훼손": ["훼손", "찢김", "긁힘", "파손", "깨짐", "갈라짐", "찍힘", "스크레치", "손상", "뜯김"],
        "오염": ["오염", "더러움", "얼룩", "변색", "낙서"],
        "몰딩수정": ["몰딩", "몰딩수정", "몰딩교체", "몰딩작업"],
        "석고수정": ["석고", "석고수정", "석고보드", "석고작업"],
        "누수 및 곰팡이": ["곰팡이", "누수"],
        "면불량": ["면불량", "퍼티", "돌출", "이물질"],
        '걸레받이 수정': ['걸레받이', '걸레받이수정', '걸레받이 교체'],
        '문틀수정': ['문틀수정', '문틀'],
        '가구수정': ['가구', '가구수정'],
        '틈새': ['틈새', '틈새수정', '틈새과다'],
        '합판': ['합판길이부족', '합판'],
        '주름': ['주름'],
        '들뜸': ['들뜸'],
        '꼬임': ['꼬임'],
        '울음': ['울음'],
        '결로': ['결로'],
        '이음새': ['이음새'],
        "오타공": ['오타공', '타공과다', '피스타공']
    }

# 텍스트 정규화
def normalize_text(text):
    return re.sub(r'\s+', '', text)

# 텍스트 분류
def classify_text(text, keyword_categories):
    normalized_text = normalize_text(text)
    for category, keywords in keyword_categories.items():
        for keyword in keywords:
            if normalize_text(keyword) in normalized_text:
                return category
    return "unidentified"

# OCR 수행
def ocr_image(image_path):
    try:
        result = reader.readtext(image_path, detail=0)
        return " ".join(result)
    except Exception as e:
        st.error(f"OCR 오류: {e}")
        return ""

# 모든 폴더 생성
def create_all_folders(base_folder):
    keyword_categories = get_keyword_categories()
    output_folders = {category: os.path.join(base_folder, category) for category in keyword_categories.keys()}
    output_folders["unidentified"] = os.path.join(base_folder, "unidentified")
    for folder in output_folders.values():
        os.makedirs(folder, exist_ok=True)
    return output_folders

# 이미지 처리 및 OCR 실행
def process_images(uploaded_files, base_folder):
    keyword_categories = get_keyword_categories()
    output_folders = create_all_folders(base_folder)
    results = []
    
    for uploaded_file in uploaded_files:
        image_path = os.path.join(base_folder, uploaded_file.name)
        with open(image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        try:
            detected_text = ocr_image(image_path)
            category = classify_text(detected_text, keyword_categories)
            target_folder = output_folders[category]
            shutil.move(image_path, os.path.join(target_folder, uploaded_file.name))
            results.append((uploaded_file.name, category, detected_text))
        except Exception as e:
            st.error(f"파일 처리 오류: {e}")
    return results

# ZIP 파일 생성
def create_zip(directory):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, directory))
    zip_buffer.seek(0)
    return zip_buffer

# Streamlit UI
st.title("🔍 이미지 자동 분류 시스템")
st.write("OCR을 이용하여 이미지 분류 후 다운로드 가능")

uploaded_files = st.file_uploader("이미지 업로드", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
if uploaded_files:
    base_folder = "sorted_images"
    results = process_images(uploaded_files, base_folder)
    
    # 결과 표시
    st.success("✅ 분류 완료!")
    for filename, category, detected_text in results:
        st.write(f"**{filename}** → `{category}`")
        st.text(f"OCR 결과: {detected_text[:100]}...")  # 너무 길면 자름
    
    # CSV 저장
    df = pd.DataFrame(results, columns=["파일명", "분류", "OCR 결과"])
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_buffer.seek(0)
    st.download_button(label="📥 OCR 결과 CSV 다운로드", data=csv_buffer, file_name="ocr_results.csv", mime="text/csv")
    
    # ZIP 파일 생성 및 다운로드
    zip_buffer = create_zip(base_folder)
    st.download_button(label="📥 분류된 이미지 ZIP 다운로드", data=zip_buffer, file_name="classified_images.zip", mime="application/zip")

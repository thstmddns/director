import os
import shutil
import zipfile
from io import BytesIO
import streamlit as st
import easyocr
from PIL import Image

# 🔹 OCR 리더를 캐싱하여 메모리 절약
@st.cache_resource
def get_reader():
    return easyocr.Reader(['ko', 'en'], gpu=False)

reader = get_reader()

# 🔹 분류 기준 정의
def get_keyword_categories():
    return {
        "훼손": ["찢어짐", "파손", "금", "긁힘"],
        "오염": ["얼룩", "변색", "곰팡이"],
        "몰딩수정": ["몰딩", "마감"],
        "석고수정": ["석고", "크랙"]
    }

# 🔹 폴더 생성
def create_all_folders(base_folder):
    categories = get_keyword_categories().keys()
    output_folders = {category: os.path.join(base_folder, category) for category in categories}
    output_folders["미분류"] = os.path.join(base_folder, "미분류")
    
    for folder in output_folders.values():
        os.makedirs(folder, exist_ok=True)
    
    return output_folders

# 🔹 OCR 실행
def ocr_image(image_path):
    try:
        with Image.open(image_path) as img:  # 메모리 자동 해제
            result = reader.readtext(image_path, detail=0)
        return " ".join(result)
    except Exception as e:
        st.error(f"OCR 오류: {e}")
        return ""

# 🔹 텍스트 기반 분류
def classify_text(text, keyword_categories):
    for category, keywords in keyword_categories.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "미분류"

# 🔹 이미지 처리
def process_images(uploaded_files, base_folder):
    keyword_categories = get_keyword_categories()
    output_folders = create_all_folders(base_folder)
    results = []
    
    for uploaded_file in uploaded_files:
        image_path = os.path.join(base_folder, uploaded_file.name)

        # 🔹 파일 저장 (with 문으로 메모리 절약)
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

# 🔹 ZIP 파일 생성 (메모리 누수 방지)
def create_zip(directory):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, directory))
    
    zip_buffer.seek(0)
    return zip_buffer

# 🔹 Streamlit UI
st.title("인테리어 하자 분류 시스템")

uploaded_files = st.file_uploader("이미지를 업로드하세요", accept_multiple_files=True, type=["jpg", "png", "jpeg"])

if uploaded_files:
    base_folder = "data"
    results = process_images(uploaded_files, base_folder)

    # 🔹 결과 표시
    if results:
        st.write("📌 처리 결과:")
        for file_name, category, detected_text in results:
            st.write(f"✅ **{file_name}** → {category} (검출된 텍스트: {detected_text})")

        # 🔹 ZIP 파일 다운로드 제공
        if st.button("📥 ZIP 파일 다운로드"):
            zip_buffer = create_zip(base_folder)
            st.download_button(
                label="🔽 ZIP 다운로드",
                data=zip_buffer,
                file_name="classified_images.zip",
                mime="application/zip"
            )

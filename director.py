import os
import shutil
import zipfile
from io import BytesIO
import streamlit as st
import easyocr
from PIL import Image
from collections import Counter

@st.cache_resource
def get_reader():
    return easyocr.Reader(['ko', 'en'], gpu=False)

reader = get_reader()

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
        with Image.open(image_path) as img:
            result = reader.readtext(image_path, detail=0)
        return " ".join(result)
    except Exception as e:
        st.error(f"OCR 오류: {e}")
        return ""

def classify_text(text, keyword_categories):
    for category, keywords in keyword_categories.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "미분류"

def process_images(uploaded_files, base_folder):
    keyword_categories = get_keyword_categories()
    output_folders = create_all_folders(base_folder)
    results = []
    category_counts = Counter()  # 하자 유형 개수 저장
    
    for uploaded_file in uploaded_files:
        image_path = os.path.join(base_folder, uploaded_file.name)
        
        # 🔹 먼저 "미분류" 폴더에 저장
        temp_folder = output_folders["미분류"]
        temp_path = os.path.join(temp_folder, uploaded_file.name)

        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            detected_text = ocr_image(temp_path)
            category = classify_text(detected_text, keyword_categories)
            category_counts[category] += 1  # 유형별 개수 증가

            # 🔹 올바른 폴더로 이동 (미분류에 남아 있는 걸 방지)
            if category != "미분류":
                target_folder = output_folders[category]
                shutil.move(temp_path, os.path.join(target_folder, uploaded_file.name))

            results.append((uploaded_file.name, category, detected_text))

        except Exception as e:
            st.error(f"파일 처리 오류: {e}")
    
    return results, category_counts


def create_zip(directory, output_filename="classified_images.zip"):
    zip_path = shutil.make_archive(output_filename.replace(".zip", ""), 'zip', directory)
    return zip_path

st.title("인테리어 하자 분류 시스템")

uploaded_files = st.file_uploader("이미지를 업로드하세요", accept_multiple_files=True, type=["jpg", "png", "jpeg"])

if uploaded_files:
    base_folder = "data"
    results, category_counts = process_images(uploaded_files, base_folder)

    if results:
        st.write("📌 처리 결과:")
        # for file_name, category, detected_text in results:
        #     st.write(f"✅ **{file_name}** → {category} (검출된 텍스트: {detected_text})")

        # 🔹 하자 유형별 개수 출력
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

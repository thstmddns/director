import os
import re
import shutil
import easyocr
import streamlit as st
import zipfile
from io import BytesIO

# EasyOCR 리더 초기화 (GPU 비활성화)
reader = easyocr.Reader(['ko', 'en'], gpu=False)  # gpu=False로 설정

# 키워드 정의
def get_keyword_categories():
    return {
        '단차불량' : ['단차불량', '단차'],
        "훼손": ["훼손", "찢김", "긁힘", "파손", "깨짐", "갈라짐", "찍힘", '스크레치', '스크래치', '손상', '뜯김', '찢어짐', '칼자국', '터짐', '까짐', '흠집', '찍김', '웨손', '긁험', '찍험', '찍임', '직힘', '긁림', '긁임', '찢심', '횟손'],
        "오염": ["오염", "더러움", "얼룩", "변색", '낙서'],
        "몰딩수정": ["몰딩", "몰딩수정", "몰딩교체", "몰딩작업", '몰딩', '돌딩', '올딩'],
        "석고수정": ["석고", "석고수정", "석고보드", "석고작업", "석고면불량"],
        "누수 및 곰팡이" : ['곰팡이', '누수'],
        "면불량" : ['면불량', '면 불량', '퍼티', '돌출', '이물질'],
        '걸레받이 수정' : ['걸레받이', '걸래받이', '걸레받지', '걸레받이수정', '걸레받이 교체', '걸레받이 작업'],
        '문틀수정' : ['문틀수정', '문틀'],
        '가구수정' : ['가구', '가구수정'],
        '틈새' : ['틈새', '틈새수정', '틈새과다'],
        '합판' : ['합판길이부족', '합판'],
        '주름' : ['주름'],
        '들뜸' : ['들뜸', '들뜰', '들픔', '들듬', '둘뜸'],
        '꼬임' : ['꼬임'],
        '울음' : ['울음'],
        '결로' : ['결로'],
        '이음새' : ['이음새'],
        "오타공" : ['오타공', '오타콩', '타공과다', '피스타공', '과타공'],
    }

def normalize_text(text):
    """텍스트에서 띄어쓰기를 무시하도록 정규화"""
    return re.sub(r'\\s+', '', text)

def classify_text(text, keyword_categories):
    """텍스트를 키워드에 따라 분류"""
    normalized_text = normalize_text(text)
    for category, keywords in keyword_categories.items():
        for keyword in keywords:
            if normalize_text(keyword) in normalized_text:
                return category
    return "unidentified"

def ocr_image(image):
    """EasyOCR을 사용하여 이미지에서 텍스트 추출"""
    try:
        result = reader.readtext(image, detail=0)  # 텍스트만 반환
        return " ".join(result)  # 인식된 텍스트를 하나의 문자열로 합치기
    except Exception as e:
        print(f"Error during OCR: {e}")
        return ""

def process_uploaded_images(uploaded_files):
    """업로드된 이미지들을 OCR 후 분류하여 각 폴더로 이동"""
    keyword_categories = get_keyword_categories()
    category_count = {category: 0 for category in keyword_categories.keys()}
    category_count["unidentified"] = 0
    
    # 업로드된 이미지 처리
    classified_images = {"unidentified": []}
    
    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        image = uploaded_file.read()
        
        # OCR 수행
        detected_text = ocr_image(image)
        
        # 텍스트 분류
        category = classify_text(detected_text, keyword_categories)
        
        # 카운트 업데이트
        category_count[category] += 1
        
        # 분류된 이미지 리스트에 추가
        if category not in classified_images:
            classified_images[category] = []
        classified_images[category].append((file_name, image))
    
    return category_count, classified_images

def zip_classified_images(classified_images):
    """분류된 이미지를 ZIP 파일로 압축"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for category, images in classified_images.items():
            for file_name, image in images:
                zip_file.writestr(f"{category}/{file_name}", image)
    zip_buffer.seek(0)
    return zip_buffer

# Streamlit UI 설정
st.title("이미지 분류 및 통계 시스템")

# 이미지 업로드
uploaded_files = st.file_uploader("이미지를 업로드하세요", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    # 이미지 처리
    category_count, classified_images = process_uploaded_images(uploaded_files)

    # 통계 출력
    st.subheader("하자 유형별 개수")
    for category, count in category_count.items():
        st.write(f"{category}: {count}개")
    
    # 분류된 이미지 다운로드 링크 제공
    st.subheader("분류된 이미지 다운로드")
    zip_buffer = zip_classified_images(classified_images)
    st.download_button(
        label="분류된 이미지 다운로드",
        data=zip_buffer,
        file_name="classified_images.zip",
        mime="application/zip"
    )

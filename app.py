from flask import Flask, render_template, render_template_string, request, abort
import requests
from bs4 import BeautifulSoup
import time
import subprocess
import urllib.parse
from datetime import datetime
import re

app = Flask(__name__)

# 임시 캐시를 위한 딕셔너리
details_cache_s = {}  # 서울 캐시

@app.route('/')
def main_homepage():
    return render_template('main_homepage.html')

''' 지역 선택 '''
@app.route('/Seoul')
def Seoul():
    return render_template('Seoul.html')

@app.route('/Gyeonggi')
def Gyeonggi():
    return render_template('Gyeonggi.html')

@app.route('/Incheon')
def Incheon():
    return render_template('Incheon.html')

''' 서울 '''
def sanitize_filename_s(filename):
    sanitized_filename = re.sub(r'[^\w\s-]', '', filename).strip().replace(' ', '_')
    return sanitized_filename

def calculate_d_day_s(period):
    try:
        if '~' in period:
            start_date_str, end_date_str = period.split('~')
            end_date_str = end_date_str.strip()
        else:
            end_date_str = period.strip()

        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        today = datetime.today().date()

        delta = (end_date - today).days
        return f"D-{delta}" if delta >= 0 else "마감됨"
    except Exception as e:
        return "기간 형식 오류"

def extract_links_and_content_s(rows, total_pages=3):
    results_s = []
    start = time.time()
    for row in rows:
        columns = row.find_all("td")
        if len(columns) >= 4:
            status = columns[3].text.strip()
            if status == "모집중":
                row_data = {
                    "region": columns[1].text.strip(),
                    "title": columns[2].text.strip(),
                    "status": status,
                    "period": columns[4].text.strip(),
                    "d_day": calculate_d_day_s(columns[4].text.strip()),
                    "views": columns[6].text.strip(),
                    "link": "",
                    "body_content": "",
                    "images": []
                }

                title_box = row.select(".title_box")
                if len(title_box) == 0:
                    continue
                title_link = row.select_one(".title")
                if title_link is None:
                    continue
                href_attr = title_link['href']
                if not(href_attr and "javascript" in href_attr):
                    continue

                link_start = href_attr.find("bsnsView('") + len("bsnsView('")
                link_end = href_attr.find("'", link_start)
                bsns_id = href_attr[link_start:link_end]
                full_link = f"https://1in.seoul.go.kr/front/bsns/bsnsView.do?bsns_id={bsns_id}"
                row_data["link"] = full_link

                response = requests.get(full_link)
                soup = BeautifulSoup(response.content, 'html.parser')

                body_content = soup.select_one("#writeFrm > div > div.board_detail").text.strip()
                row_data["body_content"] = body_content

                images = soup.body.find_all('img')
                if len(images) == 1:
                    continue
                for img in images[1:]:
                    img_url = img.get('src')
                    if img_url:
                        full_img_url = urllib.parse.urljoin("https://1in.seoul.go.kr", img_url)
                        row_data["images"].append(full_img_url)

                results_s.append(row_data)
    end = time.time()
    print(f"{end-start:.2f} seconds")
    return results_s

def create_main_page_s(results_s):
    rows_html = ""
    for result in results_s:
        sanitized_title = sanitize_filename_s(result['title'])
        details_cache_s[sanitized_title] = result  # 캐시에 저장
        rows_html += f"""
        <tr>
            <td>{result['region']}</td>
            <td><a href="{result['link']}" target="_blank">{result['title']}</a></td>
            <td>{result['status']}</td>
            <td>{result['period']} ({result['d_day']})</td>
            <td>{result['views']}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>모집중인 공고 목록</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            header {{
                background: #2c3e50;
                color: #fff;
                padding: 15px 0;
                text-align: center;
                position: relative;
            }}
            table {{
                width: 90%;
                margin: 20px auto;
                border-collapse: collapse;
                background: #fff;
            }}
            th, td {{
                padding: 12px;
                border: 1px solid #ddd;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            tr:hover {{
                background-color: #f1f1f1;
            }}
            .button-container {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                width: 90%;
                margin: 20px auto;
            }}
            .button-container button {{
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
            }}
            .back-button {{
                margin-left: 0;
                margin-right: auto;
            }}
            .refresh-button {{
                margin-right: 0;
                margin-left: auto;
            }}
            @media (max-width: 768px) {{
                table {{
                    width: 100%;
                }}
                th, td {{
                    padding: 8px;
                }}
                header {{
                    padding: 10px 0;
                }}
                h1 {{
                    font-size: 1.5em;
                }}
            }}
        </style>
    </head>
    <body>
    <header>
        <h1>모집중인 공고 목록</h1>
    </header>

    <div class="button-container">
        <button class="back-button" onclick="window.history.back()">Back</button>
        <form method="POST" action="/Seoul/SPH" style="margin: 0;">
            <button type="submit" class="refresh-button">새로고침</button>
        </form>
    </div>

    <table>
        <thead>
            <tr>
                <th>Region</th>
                <th>Title</th>
                <th>Status</th>
                <th>Period</th>
                <th>Views</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    </body>
    </html>
    """
    return html_content


@app.route('/Seoul/SPH', methods=['GET', 'POST'])
def Seoul_SPH():
    if request.method == 'POST':
        url = "https://1in.seoul.go.kr/front/bsns/bsnsList.do"
        tables = []
        page = 1
        fail_count = 0
        while True:
            html_data = requests.get(url, params={"miv_pageNo": page})
            if html_data.status_code != 200:
                fail_count += 1
                if fail_count > 5:
                    raise TimeoutError(f"통신 오류: {fail_count}회")
                continue
            soup = BeautifulSoup(html_data.text, "html.parser")
            if soup.find("img") is not None:
                break
            print(page)
            elements = soup.select("tr")
            tables.extend(elements)
            page += 1
        
        results_s = extract_links_and_content_s(tables, total_pages=5)
        return render_template_string(create_main_page_s(results_s))
    else:
        return render_template_string(create_main_page_s([]))

@app.route('/Seoul/SPH/<title>')
def Seoul_SPH_detail(title):
    decoded_title = sanitize_filename_s(urllib.parse.unquote(title))
    if decoded_title in details_cache_s:
        data = details_cache_s[decoded_title]
        return render_template('detail_page.html', data=data)  # 템플릿에 데이터 전달
    else:
        return abort(404)

@app.route('/Seoul/Elder')
def Seoul_Elder():
    return render_template('Seoul_Elder.html')


''' 경기 '''
# 기본 설정
base_url = "https://www.gg.go.kr"
api_url = f"{base_url}/1ingg/bbs/ajax/boardList.do"
total_pages = 8

# 경기도 지역 코드와 지역 이름 매핑
region_mapping = {
    "1": "가평군",
    "2": "고양특례시",
    "3": "과천시",
    "4": "광명시",
    "5": "광주시",
    "6": "구리시",
    "7": "군포시",
    "8": "김포시",
    "9": "남양주시",
    "10": "동두천시",
    "11": "부천시",
    "12": "성남시",
    "13": "수원특례시",
    "14": "시흥시",
    "15": "안산시",
    "16": "안성시",
    "17": "안양시",
    "18": "양주시",
    "19": "양평군",
    "20": "여주시",
    "21": "연천군",
    "22": "오산시",
    "23": "용인특례시",
    "24": "의왕시",
    "25": "의정부시",
    "26": "이천시",
    "27": "파주시",
    "28": "평택시",
    "29": "포천시",
    "30": "하남시",
    "31": "화성시"
}

# 날짜 변환 함수 (YYYY-MM-DD 형식을 datetime 객체로 변환)
def convert_to_datetime(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return datetime.min  # 변환할 수 없는 경우 가장 오래된 날짜로 처리

# 파일 이름을 안전하게 만드는 함수
def sanitize_filename(filename):
    # 파일 이름에서 특수 문자를 제거하고, 공백을 밑줄로 대체합니다.
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    filename = filename.replace(" ", "_")
    return filename

# 상세 페이지 추출 함수
def extract_detail_page(detail_url):
    response = requests.get(detail_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    detail_content = {}

    # 이미지 URL 추출
    image_element = soup.find('div', class_='categori_img').find('img')
    image_url = image_element['src'] if image_element else None
    if image_url and image_url.startswith("../"):
        image_url = urllib.parse.urljoin(base_url + "/1ingg/", image_url[3:])
    else:
        image_url = urllib.parse.urljoin(base_url, image_url)
    
    detail_content['이미지 URL'] = image_url

    # 텍스트 정보 추출
    ul_elements = soup.select('div.categori_txt ul li')
    for li in ul_elements:
        strong_text = li.find('strong').text.strip() if li.find('strong') else ''
        p_text = li.find('p').text.replace("\n", "").replace("\t", "").strip() if li.find('p') else ''
        detail_content[strong_text] = p_text

    # 온라인 접수 링크 추출
    online_link_element = soup.find('a', class_='categori_view_home_link_bt')
    online_link = online_link_element['href'] if online_link_element else None
    detail_content['온라인 접수 링크'] = urllib.parse.urljoin(base_url, online_link) if online_link else None

    return detail_content

# 메인 페이지 생성 함수
def create_main_page(results):
    rows_html = ""
    for result in results:
        rows_html += f"""
        <tr>
            <td>{result['상태']}</td>
            <td>{region_mapping.get(result['지역'], result['지역'])}</td>
            <td><a href="/Gyeonggi/SPH/{sanitize_filename(result['제목'])}" target="_blank">{result['제목']}</a></td>
            <td>{result['조회수']}</td>
            <td>{result['날짜']}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>모집중인 공고 목록</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            header {{
                background: #2c3e50;
                color: #fff;
                padding: 15px 0;
                text-align: center;
                position: relative;
            }}
            table {{
                width: 90%;
                margin: 20px auto;
                border-collapse: collapse;
                background: #fff;
            }}
            th, td {{
                padding: 12px;
                border: 1px solid #ddd;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            tr:hover {{
                background-color: #f1f1f1;
            }}
            .button-container {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                width: 90%;
                margin: 20px auto;
            }}
            .button-container button {{
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
            }}
            .back-button {{
                margin-left: 0;
                margin-right: auto;
            }}
            .refresh-button {{
                margin-right: 0;
                margin-left: auto;
            }}
            @media (max-width: 768px) {{
                table {{
                    width: 100%;
                }}
                th, td {{
                    padding: 8px;
                }}
                header {{
                    padding: 10px 0;
                }}
                h1 {{
                    font-size: 1.5em;
                }}
            }}
        </style>

    </head>
    <body>
    <header>
        <h1>모집중인 공고 목록</h1>
    </header>

    <div class="button-container">
        <button class="back-button" onclick="window.history.back()">Back</button>
        <form method="POST" action="/Gyeonggi/SPH" style="margin: 0;">
            <button type="submit" class="refresh-button">새로고침</button>
        </form>
    </div>

    <table>
        <thead>
            <tr>
                <th>상태</th>
                <th>지역</th>
                <th>제목</th>
                <th>조회수</th>
                <th>날짜</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    </body>
    </html>
    """
    return html_content

def fetch_data():
    results = []
    for page_num in range(1, total_pages + 1):
        params = {
            'menuId': '4112',
            'bsIdx': '873',
            'page': str(page_num)
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": base_url,
            "Referer": f"{base_url}/1ingg/bbs/board.do?bsIdx=873&menuId=4112"
        }

        response = requests.post(api_url, headers=headers, data=params)

        if response.status_code == 200:
            json_data = response.json()
            items = json_data.get('resultList', [])
            for item in items:
                status = item.get('ADD_COLUMN09', '')
                if status == "신청중":
                    region_code = item.get('ADD_COLUMN01', '')
                    region_name = region_mapping.get(region_code, region_code)
                    title = item.get('SUBJECT', '')
                    views = item.get('VIEW_CNT', '')
                    date = item.get('WRITE_DATE2', '')
                    detail_page_link = f"{base_url}/1ingg/bbs/boardView.do?bsIdx={item.get('BS_IDX', '')}&bIdx={item.get('B_IDX', '')}&page=1&menuId=4112&bcIdx=0"

                    result = {
                        "상태": status,
                        "지역": region_name,
                        "제목": title,
                        "조회수": views,
                        "날짜": date,
                        "상세 링크": detail_page_link
                    }

                    results.append(result)
        else:
            print(f"Failed to fetch data for page {page_num}: {response.status_code}")

    return results

@app.route('/Gyeonggi/SPH', methods=['GET', 'POST'])
def Gyeonggi_SPH():
    if request.method == 'POST':
        results = fetch_data()
        return render_template_string(create_main_page(results))
    else:
        results = fetch_data()  # 기존 데이터를 불러오는 대신 실시간 데이터를 사용
        return render_template_string(create_main_page(results))


@app.route('/Gyeonggi/SPH/<title>')
def Gyeonggi_SPH_detail(title):
    sanitized_title = sanitize_filename(title)
    # 상세 페이지의 링크를 찾기 위해 데이터에서 해당 제목을 검색합니다.
    results = fetch_data()
    for result in results:
        if sanitize_filename(result['제목']) == sanitized_title:
            detail_content = extract_detail_page(result['상세 링크'])
            # HTML로 렌더링하여 반환합니다.
            detail_html = f"""
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{result['제목']}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 20px;
                        padding: 0;
                        background-color: #f4f4f4;
                    }}
                    header {{
                        background: #2c3e50;
                        color: #fff;
                        padding: 15px;
                        text-align: center;
                    }}
                    section {{
                        background: #fff;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                    }}
                    a {{
                        color: #4682B4;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
            <header>
                <h1>{result['제목']}</h1>
            </header>
            <section>
                <img src="{detail_content['이미지 URL']}" alt="Image"><br>
            """

            for key, value in detail_content.items():
                if key != '이미지 URL':
                    if key == "온라인 접수 링크" and value:
                        detail_html += f"<p><strong>{key}:</strong> <a href='{value}' target='_blank'>{value}</a></p>"
                    else:
                        detail_html += f"<p><strong>{key}:</strong> {value}</p>"

            detail_html += """
            </section>
            </body>
            </html>
            """
            return render_template_string(detail_html)

    return abort(404)

''' 인천 '''
# 인천 공고 목록 추출 함수
def extract_data_from_page_i(page_url):
    try:
        response = requests.get(page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
        return []

    rows = soup.select("tr")
    base_url = "https://www.incheon.go.kr/fnct/1in/"
    results = []

    for row in rows:
        columns = row.find_all("td")
        if len(columns) > 1:
            number = columns[0].text.strip()
            category = columns[1].text.strip()
            region = columns[2].text.strip()
            date_posted = columns[3].text.strip()
            title_elem = columns[4].find("a")
            title = title_elem.text.strip() if title_elem else columns[4].text.strip()
            period = columns[5].text.strip()

            status_elem = row.find("p", {"class": ["text-blue", "text-green", "text-red"]})
            status_class = status_elem['class'][0] if status_elem else "No status"

            if "text-red" in status_class:
                continue

            status = status_elem.text.strip() if status_elem else "No status"

            if title_elem:
                onclick_text = title_elem['onclick']
                link_start = onclick_text.find("f_searchPopup('") + len("f_searchPopup('")
                link_end = onclick_text.find("'", link_start)
                link = onclick_text[link_start:link_end]
                full_link = f"{base_url}searchListPopup?{link}"
            else:
                full_link = "No link"

            results.append({
                "category": category,
                "region": region,
                "title": title,
                "period": period,
                "status": status,
                "link": full_link
            })
    
    return results

# 상세 페이지 내용 추출 함수
def extract_content_from_body_i(detail_url):
    response = requests.get(detail_url)
    soup = BeautifulSoup(response.content, "html.parser")
    
    body = soup.find("tbody")
    content = {}
    if body:
        text_items = body.find_all(['th', 'td', 'pre', 'img'])
        for item in text_items:
            if item.name == 'img':
                img_url = item['src']
                content.setdefault('images', []).append(img_url)
            else:
                previous_sibling = item.find_previous_sibling('th')
                if previous_sibling:
                    key = previous_sibling.text.strip()
                else:
                    key = "Unknown Key"  # 기본 키 설정
                value = item.get_text(strip=True)
                content[key] = value
    else:
        content["Error"] = "No content found in body"
    
    return content

def sanitize_filename(title):
    # 파일명을 안전하게 변환하는 함수
    return urllib.parse.quote(title)

def create_main_page_i(results):
    # 메인 페이지의 HTML을 생성하는 함수
    rows_html = ""
    for result in results:
        rows_html += f"""
        <tr>
            <td>{result['category']}</td>
            <td>{result['region']}</td>
            <td><a href="{result['link']}" target="_blank">{result['title']}</a></td>
            <td>{result['period']}</td>
            <td>{result['status']}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>모집중인 공고 목록</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            header {{
                background: #2c3e50;
                color: #fff;
                padding: 15px 0;
                text-align: center;
                position: relative;
            }}
            table {{
                width: 90%;
                margin: 20px auto;
                border-collapse: collapse;
                background: #fff;
            }}
            th, td {{
                padding: 12px;
                border: 1px solid #ddd;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            tr:hover {{
                background-color: #f1f1f1;
            }}
            .button-container {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                width: 90%;
                margin: 20px auto;
            }}
            .button-container button {{
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
            }}
            .back-button {{
                margin-left: 0;
                margin-right: auto;
            }}
            .refresh-button {{
                margin-right: 0;
                margin-left: auto;
            }}
            @media (max-width: 768px) {{
                table {{
                    width: 100%;
                }}
                th, td {{
                    padding: 8px;
                }}
                header {{
                    padding: 10px 0;
                }}
                h1 {{
                    font-size: 1.5em;
                }}
            }}
        </style>



    </head>
    <body>
    <header>
        <h1>모집중인 공고 목록</h1>
    </header>

    <div class="button-container">
        <button class="back-button" onclick="window.history.back()">Back</button>
        <form method="POST" action="/Incheon/SPH" style="margin: 0;">
            <button type="submit" class="refresh-button">새로고침</button>
        </form>
    </div>

    <table>
        <thead>
            <tr>
                <th>분류</th>
                <th>지역</th>
                <th>제목</th>
                <th>기간</th>
                <th>상태</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    </body>
    </html>
    """
    return html_content


@app.route('/Incheon/SPH', methods=['GET', 'POST'])
def Incheon_SPH():
    results = []
    if request.method == 'POST':
        base_url = "https://www.incheon.go.kr/1in/OHH020107"
        for page_num in range(1, 6):
            page_url = f"{base_url}?curPage={page_num}"
            print(f"Extracting data from page: {page_num}")
            page_results = extract_data_from_page_i(page_url)
            results.extend(page_results)
    return render_template_string(create_main_page_i(results))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
import requests
import json
import re
from bs4 import BeautifulSoup
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
}


def get_price_from_detail_page(url: str) -> tuple[float | None, float | None]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        price_tag = soup.select_one("span.concert_details_pricing_value")
        if not price_tag:
            return None, None

        price_text = price_tag.get_text(strip=True).replace(',', '.')
        prices = re.findall(r'\d+\.\d+', price_text)

        if len(prices) == 2:
            return float(prices[0]), float(prices[1])
        elif len(prices) == 1:
            return float(prices[0]), None
        else:
            return None, None
    except Exception as e:
        print(f"  - Ошибка при парсинге цены для {url}: {e}")
        return None, None


def parse_site(config: dict) -> list[dict]:
    site_name = config['site_name']
    url = config['url']
    all_events_data = []
    page_num = 1

    print(f"Начинаю парсинг: {site_name}")

    # Этап 1: Сбор базовой информации и ссылок со всех страниц
    print("  - Этап 1: Сбор ссылок со страниц списка...")
    while True:
        paginated_url = f"{url}page:{page_num}/"
        print(f"    - Сканирую страницу: {page_num}")

        try:
            response = requests.get(paginated_url, headers=HEADERS, timeout=20)
            if response.status_code != 200: break

            match = re.search(r'window\.concertsListEvents\s*=\s*(\[.*?\]);', response.text)
            if not match: break

            events_on_page = json.loads(match.group(1))
            if not events_on_page: break

            all_events_data.extend(events_on_page)
            page_num += 1
            time.sleep(1)
        except requests.RequestException as e:
            print(f"  - Ошибка при запросе к странице {page_num}: {e}")
            break

    print(f"  - Этап 1 завершен. Собрано {len(all_events_data)} событий для детального анализа.")

    # Этап 2: Заход на каждую страницу для сбора цен
    print("  - Этап 2: Сбор цен с детальных страниц...")
    final_events = []
    for i, event_info in enumerate(all_events_data):
        keys = config['json_keys']
        link = event_info.get(keys['link'])
        if not link: continue

        if not link.startswith('http'):
            link = 'https://www.kvitki.by' + link

        print(f"    - Обработка {i + 1}/{len(all_events_data)}: {event_info.get('title')}")
        price_min, price_max = get_price_from_detail_page(link)

        start_time_data = event_info.get('startTime', {})
        timestamp = start_time_data.get('stamp') if isinstance(start_time_data, dict) else None

        final_events.append({
            'title': event_info.get(keys['title']),
            'place': event_info.get(keys['place']),
            'time': event_info.get(keys['time']),
            'link': link,
            'timestamp': timestamp,
            'price_min': price_min,
            'price_max': price_max
        })
        time.sleep(0.5)

    print(f"Сайт {site_name} спарсен. Найдено событий: {len(final_events)}")
    return final_events
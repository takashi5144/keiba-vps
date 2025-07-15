import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re
from typing import Dict, List, Optional
import logging

class NetKeibaScraper:
    """NetKeibaから競馬データをスクレイピングするクラス"""
    
    def __init__(self):
        self.base_url = "https://db.netkeiba.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_race_list(self, date: str, jyo_cd: str = "") -> List[Dict]:
        """指定日のレース一覧を取得"""
        url = f"{self.base_url}/race/list/{date}/"
        if jyo_cd:
            url += f"?jyo_cd={jyo_cd}"
            
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            races = []
            race_links = soup.find_all('a', href=re.compile(r'/race/\d+'))
            
            for link in race_links:
                race_id = re.search(r'/race/(\d+)', link['href']).group(1)
                race_name = link.text.strip()
                races.append({
                    'race_id': race_id,
                    'race_name': race_name,
                    'url': f"{self.base_url}{link['href']}"
                })
                
            return races
            
        except Exception as e:
            logging.error(f"レース一覧の取得に失敗: {e}")
            return []
    
    def get_race_info(self, race_id: str) -> Dict:
        """レース情報を取得"""
        url = f"{self.base_url}/race/{race_id}/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # レース基本情報
            race_info = {}
            race_info['race_id'] = race_id
            
            # レース名
            race_name_elem = soup.find('h1', class_='RaceName')
            if race_name_elem:
                race_info['race_name'] = race_name_elem.text.strip()
            
            # レース詳細情報
            race_data = soup.find('div', class_='RaceData01')
            if race_data:
                race_info['race_details'] = race_data.text.strip()
                
            # 開催情報
            race_data2 = soup.find('div', class_='RaceData02')
            if race_data2:
                spans = race_data2.find_all('span')
                if len(spans) >= 3:
                    race_info['course'] = spans[0].text.strip()
                    race_info['weather'] = spans[1].text.strip()
                    race_info['track_condition'] = spans[2].text.strip()
            
            return race_info
            
        except Exception as e:
            logging.error(f"レース情報の取得に失敗: {e}")
            return {}
    
    def get_race_result(self, race_id: str) -> List[Dict]:
        """レース結果を取得"""
        url = f"{self.base_url}/race/{race_id}/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            result_table = soup.find('table', class_='RaceTable01')
            
            if not result_table:
                return []
                
            rows = result_table.find_all('tr')[1:]  # ヘッダーを除く
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 10:
                    continue
                    
                result = {
                    'ranking': cols[0].text.strip(),
                    'frame_number': cols[1].text.strip(),
                    'horse_number': cols[2].text.strip(),
                    'horse_name': cols[3].text.strip(),
                    'age_sex': cols[4].text.strip(),
                    'weight': cols[5].text.strip(),
                    'jockey': cols[6].text.strip(),
                    'time': cols[7].text.strip(),
                    'margin': cols[8].text.strip(),
                    'odds': cols[9].text.strip() if len(cols) > 9 else '',
                    'popularity': cols[10].text.strip() if len(cols) > 10 else ''
                }
                
                # 馬IDを取得
                horse_link = cols[3].find('a')
                if horse_link and 'href' in horse_link.attrs:
                    horse_id = re.search(r'/horse/(\d+)', horse_link['href'])
                    if horse_id:
                        result['horse_id'] = horse_id.group(1)
                
                results.append(result)
                
            return results
            
        except Exception as e:
            logging.error(f"レース結果の取得に失敗: {e}")
            return []
    
    def get_horse_info(self, horse_id: str) -> Dict:
        """馬情報を取得"""
        url = f"{self.base_url}/horse/{horse_id}/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            horse_info = {}
            horse_info['horse_id'] = horse_id
            
            # 馬名
            horse_name = soup.find('h1', class_='horse_title')
            if horse_name:
                horse_info['horse_name'] = horse_name.text.strip()
            
            # プロフィール
            profile_table = soup.find('table', class_='db_prof_table')
            if profile_table:
                rows = profile_table.find_all('tr')
                for row in rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        key = th.text.strip()
                        value = td.text.strip()
                        
                        if '生年月日' in key:
                            horse_info['birth_date'] = value
                        elif '調教師' in key:
                            horse_info['trainer'] = value
                        elif '馬主' in key:
                            horse_info['owner'] = value
                        elif '生産者' in key:
                            horse_info['breeder'] = value
                        elif '父' in key:
                            horse_info['father'] = value
                        elif '母' in key:
                            horse_info['mother'] = value
            
            return horse_info
            
        except Exception as e:
            logging.error(f"馬情報の取得に失敗: {e}")
            return {}
    
    def get_odds(self, race_id: str, odds_type: str = '1') -> Dict:
        """オッズ情報を取得
        odds_type: 1=単勝, 2=複勝, 3=馬連, 4=馬単, 5=ワイド, 6=三連複, 7=三連単
        """
        url = f"{self.base_url}/odds/{odds_type}/{race_id}/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            odds_data = {}
            
            if odds_type == '1':  # 単勝
                odds_table = soup.find('table', id='odds_tan_block')
                if odds_table:
                    rows = odds_table.find_all('tr')[1:]  # ヘッダーを除く
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            horse_num = cols[0].text.strip()
                            odds = cols[2].text.strip()
                            odds_data[horse_num] = odds
            
            return odds_data
            
        except Exception as e:
            logging.error(f"オッズ情報の取得に失敗: {e}")
            return {}
    
    def close(self):
        """セッションを閉じる"""
        self.session.close()


if __name__ == "__main__":
    # テスト実行
    scraper = NetKeibaScraper()
    
    # 本日のレース一覧を取得
    today = datetime.now().strftime('%Y%m%d')
    races = scraper.get_race_list(today)
    
    if races:
        print(f"本日のレース数: {len(races)}")
        # 最初のレースの情報を取得
        race = races[0]
        print(f"レース名: {race['race_name']}")
        
        # レース結果を取得
        results = scraper.get_race_result(race['race_id'])
        if results:
            print(f"出走頭数: {len(results)}")
    
    scraper.close()
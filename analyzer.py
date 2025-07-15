import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import DatabaseManager, Race, RaceResult, Horse, Odds
import logging

class KeibaAnalyzer:
    """競馬データ分析クラス"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    def calculate_win_rate(self, horse_id: str, days: int = 365) -> Dict:
        """指定期間の勝率を計算"""
        session = self.db.get_session()
        try:
            # 指定期間のレース結果を取得
            cutoff_date = datetime.now().date() - timedelta(days=days)
            
            results = session.query(RaceResult).join(Race).filter(
                RaceResult.horse_id == horse_id,
                Race.race_date >= cutoff_date
            ).all()
            
            if not results:
                return {
                    'total_races': 0,
                    'wins': 0,
                    'win_rate': 0.0,
                    'top3_rate': 0.0
                }
            
            total_races = len(results)
            wins = sum(1 for r in results if r.ranking == 1)
            top3 = sum(1 for r in results if r.ranking <= 3)
            
            return {
                'total_races': total_races,
                'wins': wins,
                'win_rate': wins / total_races * 100,
                'top3_rate': top3 / total_races * 100
            }
            
        finally:
            session.close()
    
    def analyze_jockey_performance(self, jockey_name: str, days: int = 365) -> Dict:
        """騎手の成績を分析"""
        session = self.db.get_session()
        try:
            cutoff_date = datetime.now().date() - timedelta(days=days)
            
            results = session.query(RaceResult).join(Race).filter(
                RaceResult.jockey == jockey_name,
                Race.race_date >= cutoff_date
            ).all()
            
            if not results:
                return {
                    'total_races': 0,
                    'wins': 0,
                    'win_rate': 0.0,
                    'avg_ranking': None,
                    'avg_odds': None
                }
            
            total_races = len(results)
            wins = sum(1 for r in results if r.ranking == 1)
            rankings = [r.ranking for r in results if r.ranking]
            odds = [r.odds for r in results if r.odds]
            
            return {
                'total_races': total_races,
                'wins': wins,
                'win_rate': wins / total_races * 100,
                'avg_ranking': np.mean(rankings) if rankings else None,
                'avg_odds': np.mean(odds) if odds else None
            }
            
        finally:
            session.close()
    
    def analyze_track_condition(self, horse_id: str) -> Dict:
        """馬場状態別の成績を分析"""
        session = self.db.get_session()
        try:
            results = session.query(RaceResult, Race).join(Race).filter(
                RaceResult.horse_id == horse_id
            ).all()
            
            condition_stats = {}
            
            for result, race in results:
                condition = race.track_condition or '不明'
                
                if condition not in condition_stats:
                    condition_stats[condition] = {
                        'races': 0,
                        'wins': 0,
                        'rankings': []
                    }
                
                condition_stats[condition]['races'] += 1
                if result.ranking == 1:
                    condition_stats[condition]['wins'] += 1
                if result.ranking:
                    condition_stats[condition]['rankings'].append(result.ranking)
            
            # 統計情報を計算
            for condition, stats in condition_stats.items():
                stats['win_rate'] = stats['wins'] / stats['races'] * 100 if stats['races'] > 0 else 0
                stats['avg_ranking'] = np.mean(stats['rankings']) if stats['rankings'] else None
            
            return condition_stats
            
        finally:
            session.close()
    
    def analyze_distance_performance(self, horse_id: str) -> Dict:
        """距離別の成績を分析"""
        session = self.db.get_session()
        try:
            results = session.query(RaceResult, Race).join(Race).filter(
                RaceResult.horse_id == horse_id
            ).all()
            
            distance_categories = {
                'sprint': {'min': 0, 'max': 1400, 'races': 0, 'wins': 0, 'rankings': []},
                'mile': {'min': 1400, 'max': 1800, 'races': 0, 'wins': 0, 'rankings': []},
                'intermediate': {'min': 1800, 'max': 2200, 'races': 0, 'wins': 0, 'rankings': []},
                'long': {'min': 2200, 'max': 9999, 'races': 0, 'wins': 0, 'rankings': []}
            }
            
            for result, race in results:
                if race.distance:
                    for category, data in distance_categories.items():
                        if data['min'] < race.distance <= data['max']:
                            data['races'] += 1
                            if result.ranking == 1:
                                data['wins'] += 1
                            if result.ranking:
                                data['rankings'].append(result.ranking)
                            break
            
            # 統計情報を計算
            for category, data in distance_categories.items():
                if data['races'] > 0:
                    data['win_rate'] = data['wins'] / data['races'] * 100
                    data['avg_ranking'] = np.mean(data['rankings']) if data['rankings'] else None
                else:
                    data['win_rate'] = 0
                    data['avg_ranking'] = None
            
            return distance_categories
            
        finally:
            session.close()
    
    def predict_race_result(self, race_id: str) -> List[Dict]:
        """レース結果を予測"""
        session = self.db.get_session()
        try:
            # 出走馬情報を取得
            entries = session.query(RaceResult, Horse).join(Horse).filter(
                RaceResult.race_id == race_id
            ).all()
            
            predictions = []
            
            for entry, horse in entries:
                # 各馬のスコアを計算
                score = 0
                
                # 過去の成績を取得
                past_results = session.query(RaceResult).filter(
                    RaceResult.horse_id == horse.horse_id,
                    RaceResult.race_id != race_id
                ).order_by(RaceResult.id.desc()).limit(5).all()
                
                if past_results:
                    # 最近の順位の平均
                    recent_rankings = [r.ranking for r in past_results if r.ranking]
                    if recent_rankings:
                        avg_ranking = np.mean(recent_rankings)
                        score += (20 - avg_ranking) * 5  # 順位が良いほど高スコア
                    
                    # 勝率
                    wins = sum(1 for r in past_results if r.ranking == 1)
                    win_rate = wins / len(past_results) * 100
                    score += win_rate * 2
                
                # 人気度を考慮
                if entry.popularity:
                    score += (20 - entry.popularity) * 3
                
                predictions.append({
                    'horse_id': horse.horse_id,
                    'horse_name': horse.horse_name,
                    'horse_number': entry.horse_number,
                    'score': score,
                    'jockey': entry.jockey,
                    'popularity': entry.popularity
                })
            
            # スコアでソート
            predictions.sort(key=lambda x: x['score'], reverse=True)
            
            # 予測順位を追加
            for i, pred in enumerate(predictions):
                pred['predicted_rank'] = i + 1
            
            return predictions
            
        finally:
            session.close()
    
    def analyze_return_rate(self, strategy: str = 'favorite', 
                          days: int = 365) -> Dict:
        """投資戦略の回収率を分析
        strategy: 'favorite'=1番人気, 'longshot'=大穴狙い, 'value'=期待値重視
        """
        session = self.db.get_session()
        try:
            cutoff_date = datetime.now().date() - timedelta(days=days)
            
            races = session.query(Race).filter(
                Race.race_date >= cutoff_date
            ).all()
            
            total_investment = 0
            total_return = 0
            wins = 0
            
            for race in races:
                results = session.query(RaceResult).filter_by(
                    race_id=race.race_id
                ).all()
                
                if not results:
                    continue
                
                # 戦略に基づいて馬を選択
                selected_horse = None
                
                if strategy == 'favorite':
                    # 1番人気を選択
                    favorites = [r for r in results if r.popularity == 1]
                    if favorites:
                        selected_horse = favorites[0]
                
                elif strategy == 'longshot':
                    # 10番人気以下で最もオッズが高い馬を選択
                    longshots = [r for r in results if r.popularity and r.popularity >= 10]
                    if longshots:
                        selected_horse = max(longshots, key=lambda x: x.odds or 0)
                
                elif strategy == 'value':
                    # 期待値が高い馬を選択（3-8番人気）
                    values = [r for r in results if r.popularity and 3 <= r.popularity <= 8]
                    if values:
                        # オッズと人気のバランスを考慮
                        selected_horse = max(values, 
                            key=lambda x: (x.odds or 0) / x.popularity if x.popularity else 0)
                
                if selected_horse:
                    total_investment += 100  # 100円ずつ賭ける
                    
                    if selected_horse.ranking == 1:
                        wins += 1
                        total_return += 100 * (selected_horse.odds or 0)
            
            return {
                'strategy': strategy,
                'total_races': len(races),
                'total_investment': total_investment,
                'total_return': total_return,
                'return_rate': (total_return / total_investment * 100) if total_investment > 0 else 0,
                'win_rate': (wins / len(races) * 100) if races else 0,
                'profit': total_return - total_investment
            }
            
        finally:
            session.close()
    
    def get_hot_horses(self, limit: int = 10) -> List[Dict]:
        """最近好調な馬を取得"""
        session = self.db.get_session()
        try:
            # 過去30日間のレース結果を取得
            cutoff_date = datetime.now().date() - timedelta(days=30)
            
            # 馬ごとの成績を集計
            horse_stats = {}
            
            results = session.query(RaceResult, Horse, Race).join(Horse).join(Race).filter(
                Race.race_date >= cutoff_date
            ).all()
            
            for result, horse, race in results:
                if horse.horse_id not in horse_stats:
                    horse_stats[horse.horse_id] = {
                        'horse_id': horse.horse_id,
                        'horse_name': horse.horse_name,
                        'races': 0,
                        'wins': 0,
                        'top3': 0,
                        'recent_rankings': []
                    }
                
                stats = horse_stats[horse.horse_id]
                stats['races'] += 1
                
                if result.ranking:
                    stats['recent_rankings'].append(result.ranking)
                    if result.ranking == 1:
                        stats['wins'] += 1
                    if result.ranking <= 3:
                        stats['top3'] += 1
            
            # スコアを計算してソート
            hot_horses = []
            
            for horse_id, stats in horse_stats.items():
                if stats['races'] >= 2:  # 最低2レース以上出走
                    # スコア計算（勝率と連対率を考慮）
                    win_rate = stats['wins'] / stats['races'] * 100
                    top3_rate = stats['top3'] / stats['races'] * 100
                    avg_ranking = np.mean(stats['recent_rankings']) if stats['recent_rankings'] else 999
                    
                    score = win_rate * 3 + top3_rate * 2 + (20 - avg_ranking) * 5
                    
                    hot_horses.append({
                        'horse_id': stats['horse_id'],
                        'horse_name': stats['horse_name'],
                        'races': stats['races'],
                        'wins': stats['wins'],
                        'win_rate': win_rate,
                        'top3_rate': top3_rate,
                        'avg_ranking': avg_ranking,
                        'score': score
                    })
            
            # スコア順にソート
            hot_horses.sort(key=lambda x: x['score'], reverse=True)
            
            return hot_horses[:limit]
            
        finally:
            session.close()


if __name__ == "__main__":
    # テスト実行
    from database import DatabaseManager
    
    db = DatabaseManager()
    analyzer = KeibaAnalyzer(db)
    
    # テスト用の馬IDを指定
    test_horse_id = "2020100001"
    
    # 勝率を計算
    win_rate = analyzer.calculate_win_rate(test_horse_id)
    print(f"勝率: {win_rate}")
    
    # 馬場状態別の成績
    track_stats = analyzer.analyze_track_condition(test_horse_id)
    print(f"馬場状態別成績: {track_stats}")
    
    # 距離別の成績
    distance_stats = analyzer.analyze_distance_performance(test_horse_id)
    print(f"距離別成績: {distance_stats}")
    
    # 回収率分析
    return_analysis = analyzer.analyze_return_rate('favorite', days=30)
    print(f"1番人気の回収率: {return_analysis}")
    
    # 好調馬
    hot_horses = analyzer.get_hot_horses(5)
    print(f"最近好調な馬: {hot_horses}")
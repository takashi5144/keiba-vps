from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Date, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime
import os
from typing import List, Dict, Optional

Base = declarative_base()

class Race(Base):
    """レース情報テーブル"""
    __tablename__ = 'races'
    
    race_id = Column(String(20), primary_key=True)
    race_name = Column(String(100))
    race_date = Column(Date)
    race_number = Column(Integer)
    course = Column(String(50))
    distance = Column(Integer)
    track_type = Column(String(10))  # 芝/ダート
    track_condition = Column(String(10))  # 良/稍重/重/不良
    weather = Column(String(10))
    start_time = Column(String(10))
    
    # リレーション
    results = relationship("RaceResult", back_populates="race")
    odds = relationship("Odds", back_populates="race")

class Horse(Base):
    """馬情報テーブル"""
    __tablename__ = 'horses'
    
    horse_id = Column(String(20), primary_key=True)
    horse_name = Column(String(50))
    birth_date = Column(Date)
    sex = Column(String(10))
    father = Column(String(50))
    mother = Column(String(50))
    trainer = Column(String(50))
    owner = Column(String(100))
    breeder = Column(String(100))
    
    # リレーション
    results = relationship("RaceResult", back_populates="horse")

class RaceResult(Base):
    """レース結果テーブル"""
    __tablename__ = 'race_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(String(20), ForeignKey('races.race_id'))
    horse_id = Column(String(20), ForeignKey('horses.horse_id'))
    horse_number = Column(Integer)
    frame_number = Column(Integer)
    ranking = Column(Integer)
    jockey = Column(String(50))
    weight = Column(Float)
    time = Column(String(20))
    margin = Column(String(20))
    odds = Column(Float)
    popularity = Column(Integer)
    horse_weight = Column(Integer)
    horse_weight_change = Column(Integer)
    
    # リレーション
    race = relationship("Race", back_populates="results")
    horse = relationship("Horse", back_populates="results")

class Odds(Base):
    """オッズ情報テーブル"""
    __tablename__ = 'odds'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(String(20), ForeignKey('races.race_id'))
    odds_type = Column(String(20))  # win, place, exacta, etc.
    horse_numbers = Column(String(20))  # 馬番号（複数の場合は-で連結）
    odds_value = Column(Float)
    
    # リレーション
    race = relationship("Race", back_populates="odds")

class ScrapeLog(Base):
    """スクレイピングログテーブル"""
    __tablename__ = 'scrape_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    scrape_date = Column(DateTime, default=datetime.now)
    target_date = Column(Date)
    target_type = Column(String(20))  # race_list, race_info, horse_info
    target_id = Column(String(50))
    status = Column(String(20))  # success, failed
    error_message = Column(Text)


class DatabaseManager:
    """データベース管理クラス"""
    
    def __init__(self, db_url: str = None):
        if db_url is None:
            db_url = os.getenv('DATABASE_URL', 'sqlite:///keiba_data.db')
        
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """データベースセッションを取得"""
        return self.SessionLocal()
    
    def save_race(self, race_data: Dict) -> bool:
        """レース情報を保存"""
        session = self.get_session()
        try:
            race = Race(
                race_id=race_data['race_id'],
                race_name=race_data.get('race_name'),
                race_date=race_data.get('race_date'),
                race_number=race_data.get('race_number'),
                course=race_data.get('course'),
                distance=race_data.get('distance'),
                track_type=race_data.get('track_type'),
                track_condition=race_data.get('track_condition'),
                weather=race_data.get('weather'),
                start_time=race_data.get('start_time')
            )
            
            session.merge(race)
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            print(f"レース情報の保存に失敗: {e}")
            return False
        finally:
            session.close()
    
    def save_horse(self, horse_data: Dict) -> bool:
        """馬情報を保存"""
        session = self.get_session()
        try:
            horse = Horse(
                horse_id=horse_data['horse_id'],
                horse_name=horse_data.get('horse_name'),
                birth_date=horse_data.get('birth_date'),
                sex=horse_data.get('sex'),
                father=horse_data.get('father'),
                mother=horse_data.get('mother'),
                trainer=horse_data.get('trainer'),
                owner=horse_data.get('owner'),
                breeder=horse_data.get('breeder')
            )
            
            session.merge(horse)
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            print(f"馬情報の保存に失敗: {e}")
            return False
        finally:
            session.close()
    
    def save_race_results(self, race_id: str, results: List[Dict]) -> bool:
        """レース結果を保存"""
        session = self.get_session()
        try:
            # 既存の結果を削除
            session.query(RaceResult).filter_by(race_id=race_id).delete()
            
            for result_data in results:
                result = RaceResult(
                    race_id=race_id,
                    horse_id=result_data.get('horse_id'),
                    horse_number=result_data.get('horse_number'),
                    frame_number=result_data.get('frame_number'),
                    ranking=result_data.get('ranking'),
                    jockey=result_data.get('jockey'),
                    weight=result_data.get('weight'),
                    time=result_data.get('time'),
                    margin=result_data.get('margin'),
                    odds=result_data.get('odds'),
                    popularity=result_data.get('popularity'),
                    horse_weight=result_data.get('horse_weight'),
                    horse_weight_change=result_data.get('horse_weight_change')
                )
                session.add(result)
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            print(f"レース結果の保存に失敗: {e}")
            return False
        finally:
            session.close()
    
    def save_odds(self, race_id: str, odds_type: str, odds_data: Dict) -> bool:
        """オッズ情報を保存"""
        session = self.get_session()
        try:
            # 既存のオッズを削除
            session.query(Odds).filter_by(
                race_id=race_id,
                odds_type=odds_type
            ).delete()
            
            for horse_numbers, odds_value in odds_data.items():
                odds = Odds(
                    race_id=race_id,
                    odds_type=odds_type,
                    horse_numbers=horse_numbers,
                    odds_value=float(odds_value) if odds_value else 0.0
                )
                session.add(odds)
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            print(f"オッズ情報の保存に失敗: {e}")
            return False
        finally:
            session.close()
    
    def get_races_by_date(self, date: Date) -> List[Race]:
        """指定日のレース一覧を取得"""
        session = self.get_session()
        try:
            races = session.query(Race).filter_by(race_date=date).all()
            return races
        finally:
            session.close()
    
    def get_race_results(self, race_id: str) -> List[RaceResult]:
        """レース結果を取得"""
        session = self.get_session()
        try:
            results = session.query(RaceResult).filter_by(race_id=race_id).all()
            return results
        finally:
            session.close()
    
    def log_scrape(self, target_date: Date, target_type: str, 
                   target_id: str, status: str, error_message: str = None):
        """スクレイピングログを記録"""
        session = self.get_session()
        try:
            log = ScrapeLog(
                target_date=target_date,
                target_type=target_type,
                target_id=target_id,
                status=status,
                error_message=error_message
            )
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"ログの記録に失敗: {e}")
        finally:
            session.close()


if __name__ == "__main__":
    # テスト実行
    db = DatabaseManager()
    
    # テストデータの保存
    test_race = {
        'race_id': '202405010101',
        'race_name': 'テストレース',
        'race_date': datetime.now().date(),
        'course': '東京',
        'distance': 1600,
        'track_type': '芝',
        'track_condition': '良',
        'weather': '晴'
    }
    
    if db.save_race(test_race):
        print("レース情報を保存しました")
    
    # 保存したレースを取得
    races = db.get_races_by_date(datetime.now().date())
    if races:
        print(f"取得したレース数: {len(races)}")
        print(f"レース名: {races[0].race_name}")
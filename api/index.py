from flask import Flask, jsonify, request
from datetime import datetime
import os
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager, Race, RaceResult, Horse
from scraper import NetKeibaScraper
from analyzer import KeibaAnalyzer

app = Flask(__name__)

# ツールの初期化
db = DatabaseManager()
scraper = NetKeibaScraper()
analyzer = KeibaAnalyzer(db)

@app.route('/api', methods=['GET'])
def home():
    """APIのホームページ"""
    return jsonify({
        'message': '競馬データ分析API',
        'version': '1.0',
        'endpoints': {
            '/api/races': 'レース一覧を取得',
            '/api/race/<race_id>': 'レース詳細情報を取得',
            '/api/horse/<horse_id>': '馬の詳細情報を取得',
            '/api/analysis/predict/<race_id>': 'レース予測結果を取得',
            '/api/analysis/hot-horses': '最近好調な馬を取得',
            '/api/analysis/return-rate': '投資戦略の回収率を取得'
        }
    })

@app.route('/api/races', methods=['GET'])
def get_races():
    """レース一覧を取得"""
    try:
        # クエリパラメータから日付を取得
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'error': 'date parameter is required'}), 400
        
        # 日付をパース
        try:
            race_date = datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYYMMDD'}), 400
        
        # データベースからレースを取得
        session = db.get_session()
        try:
            races = session.query(Race).filter_by(race_date=race_date).all()
            
            result = []
            for race in races:
                result.append({
                    'race_id': race.race_id,
                    'race_name': race.race_name,
                    'race_number': race.race_number,
                    'course': race.course,
                    'distance': race.distance,
                    'track_type': race.track_type,
                    'start_time': race.start_time
                })
            
            return jsonify({
                'date': date_str,
                'count': len(result),
                'races': result
            })
            
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/race/<race_id>', methods=['GET'])
def get_race_detail(race_id):
    """レース詳細情報を取得"""
    try:
        session = db.get_session()
        try:
            # レース情報を取得
            race = session.query(Race).filter_by(race_id=race_id).first()
            if not race:
                return jsonify({'error': 'Race not found'}), 404
            
            # レース結果を取得
            results = session.query(RaceResult, Horse).join(Horse).filter(
                RaceResult.race_id == race_id
            ).order_by(RaceResult.ranking).all()
            
            race_data = {
                'race_id': race.race_id,
                'race_name': race.race_name,
                'race_date': race.race_date.strftime('%Y-%m-%d') if race.race_date else None,
                'course': race.course,
                'distance': race.distance,
                'track_type': race.track_type,
                'track_condition': race.track_condition,
                'weather': race.weather,
                'results': []
            }
            
            for result, horse in results:
                race_data['results'].append({
                    'ranking': result.ranking,
                    'horse_number': result.horse_number,
                    'horse_name': horse.horse_name,
                    'horse_id': horse.horse_id,
                    'jockey': result.jockey,
                    'time': result.time,
                    'odds': result.odds,
                    'popularity': result.popularity
                })
            
            return jsonify(race_data)
            
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/horse/<horse_id>', methods=['GET'])
def get_horse_detail(horse_id):
    """馬の詳細情報を取得"""
    try:
        session = db.get_session()
        try:
            # 馬情報を取得
            horse = session.query(Horse).filter_by(horse_id=horse_id).first()
            if not horse:
                return jsonify({'error': 'Horse not found'}), 404
            
            # 最近のレース結果を取得
            recent_results = session.query(RaceResult, Race).join(Race).filter(
                RaceResult.horse_id == horse_id
            ).order_by(Race.race_date.desc()).limit(10).all()
            
            horse_data = {
                'horse_id': horse.horse_id,
                'horse_name': horse.horse_name,
                'birth_date': horse.birth_date.strftime('%Y-%m-%d') if horse.birth_date else None,
                'sex': horse.sex,
                'father': horse.father,
                'mother': horse.mother,
                'trainer': horse.trainer,
                'owner': horse.owner,
                'recent_results': []
            }
            
            for result, race in recent_results:
                horse_data['recent_results'].append({
                    'race_date': race.race_date.strftime('%Y-%m-%d') if race.race_date else None,
                    'race_name': race.race_name,
                    'ranking': result.ranking,
                    'odds': result.odds,
                    'jockey': result.jockey
                })
            
            # 成績統計を追加
            stats = analyzer.calculate_win_rate(horse_id)
            horse_data['statistics'] = stats
            
            return jsonify(horse_data)
            
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/predict/<race_id>', methods=['GET'])
def predict_race(race_id):
    """レース予測結果を取得"""
    try:
        predictions = analyzer.predict_race_result(race_id)
        
        if not predictions:
            return jsonify({'error': 'No predictions available'}), 404
        
        return jsonify({
            'race_id': race_id,
            'predictions': predictions[:10]  # TOP10のみ返す
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/hot-horses', methods=['GET'])
def get_hot_horses():
    """最近好調な馬を取得"""
    try:
        limit = request.args.get('limit', 10, type=int)
        hot_horses = analyzer.get_hot_horses(limit)
        
        return jsonify({
            'count': len(hot_horses),
            'horses': hot_horses
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/return-rate', methods=['GET'])
def get_return_rate():
    """投資戦略の回収率を取得"""
    try:
        strategy = request.args.get('strategy', 'favorite')
        days = request.args.get('days', 30, type=int)
        
        if strategy not in ['favorite', 'longshot', 'value']:
            return jsonify({'error': 'Invalid strategy. Choose from: favorite, longshot, value'}), 400
        
        result = analyzer.analyze_return_rate(strategy, days)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Vercel用のエントリーポイント
def handler(request):
    """Vercel用のハンドラー関数"""
    with app.test_request_context(
        request.url,
        method=request.method,
        headers=request.headers,
        data=request.get_data()
    ):
        response = app.full_dispatch_request()
        return response

if __name__ == '__main__':
    app.run(debug=True)
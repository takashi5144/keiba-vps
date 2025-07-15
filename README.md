# 競馬データ分析ツール

NetKeibaから競馬データをスクレイピングし、分析・予測を行うWebアプリケーションです。

## 機能

- **データ収集**: NetKeibaからレース情報、馬情報、オッズ情報を自動収集
- **データ分析**: 馬の成績分析、騎手分析、馬場状態別分析など
- **レース予測**: 過去データに基づくレース結果予測
- **投資戦略分析**: 様々な投資戦略の回収率シミュレーション
- **ダッシュボード**: 直感的なUIでデータを可視化

## 技術スタック

- **バックエンド**: Python, Flask
- **フロントエンド**: Streamlit
- **データベース**: SQLAlchemy (SQLite/PostgreSQL対応)
- **スクレイピング**: BeautifulSoup4, Requests
- **データ分析**: Pandas, NumPy
- **可視化**: Plotly

## セットアップ

### 必要条件

- Python 3.8以上
- pip

### インストール

1. リポジトリをクローン
```bash
git clone <repository-url>
cd keiba-analysis-tool
```

2. 仮想環境を作成（推奨）
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 依存関係をインストール
```bash
pip install -r requirements.txt
```

## 使用方法

### ローカルで実行

1. Streamlitアプリを起動
```bash
streamlit run app.py
```

2. ブラウザで `http://localhost:8501` にアクセス

### データ収集

1. サイドバーから「データ収集」を選択
2. 対象日と競馬場を選択
3. 「データ取得開始」をクリック

### 分析機能

- **ダッシュボード**: 全体的な統計情報と最近の傾向を表示
- **馬情報分析**: 個別の馬の詳細な成績分析
- **レース予測**: 機械学習を使用したレース結果予測
- **投資戦略分析**: 様々な投資戦略のバックテスト

## API エンドポイント

Vercelにデプロイした場合、以下のAPIエンドポイントが利用可能：

- `GET /api/races?date=YYYYMMDD` - 指定日のレース一覧
- `GET /api/race/{race_id}` - レース詳細情報
- `GET /api/horse/{horse_id}` - 馬の詳細情報
- `GET /api/analysis/predict/{race_id}` - レース予測結果

## デプロイ

### Vercelへのデプロイ

1. Vercel CLIをインストール
```bash
npm i -g vercel
```

2. プロジェクトをデプロイ
```bash
vercel
```

3. 環境変数を設定（必要に応じて）
```
DATABASE_URL=your_database_url
```

## 注意事項

- スクレイピングは対象サイトの利用規約を守って行ってください
- 過度なアクセスは避け、適切な間隔を空けてアクセスしてください
- 本ツールによる予測は参考情報であり、実際の投資判断は自己責任で行ってください

## ライセンス

MIT License

## 貢献

プルリクエストは歓迎します。大きな変更の場合は、まずissueを作成して変更内容を議論してください。
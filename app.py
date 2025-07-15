import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from database import DatabaseManager, Race, RaceResult, Horse
from scraper import NetKeibaScraper
from analyzer import KeibaAnalyzer
import os

# ページ設定
st.set_page_config(
    page_title="競馬データ分析ダッシュボード",
    page_icon="🏇",
    layout="wide"
)

# データベースとツールの初期化
@st.cache_resource
def init_tools():
    db = DatabaseManager()
    scraper = NetKeibaScraper()
    analyzer = KeibaAnalyzer(db)
    return db, scraper, analyzer

db, scraper, analyzer = init_tools()

# サイドバー
st.sidebar.title("🏇 競馬データ分析")
page = st.sidebar.selectbox(
    "ページ選択",
    ["ダッシュボード", "データ収集", "馬情報分析", "レース予測", "投資戦略分析"]
)

# メインコンテンツ
if page == "ダッシュボード":
    st.title("競馬データ分析ダッシュボード")
    
    # 概要統計
    col1, col2, col3, col4 = st.columns(4)
    
    session = db.get_session()
    try:
        total_races = session.query(Race).count()
        total_horses = session.query(Horse).count()
        total_results = session.query(RaceResult).count()
        recent_date = session.query(Race.race_date).order_by(Race.race_date.desc()).first()
        
        with col1:
            st.metric("総レース数", f"{total_races:,}")
        with col2:
            st.metric("登録馬数", f"{total_horses:,}")
        with col3:
            st.metric("レース結果数", f"{total_results:,}")
        with col4:
            st.metric("最新データ", recent_date[0] if recent_date else "なし")
    finally:
        session.close()
    
    # 最近好調な馬
    st.subheader("🔥 最近好調な馬 TOP10")
    hot_horses = analyzer.get_hot_horses(10)
    
    if hot_horses:
        df_hot = pd.DataFrame(hot_horses)
        
        # グラフ表示
        fig = px.bar(df_hot, x='horse_name', y='score', 
                     hover_data=['win_rate', 'top3_rate', 'races'],
                     title="好調馬スコアランキング")
        st.plotly_chart(fig)
        
        # テーブル表示
        st.dataframe(
            df_hot[['horse_name', 'races', 'wins', 'win_rate', 'top3_rate', 'avg_ranking']],
            use_container_width=True
        )
    else:
        st.info("データがありません")
    
    # 投資戦略パフォーマンス
    st.subheader("💰 投資戦略パフォーマンス（過去30日）")
    
    strategies = ['favorite', 'longshot', 'value']
    strategy_results = []
    
    for strategy in strategies:
        result = analyzer.analyze_return_rate(strategy, days=30)
        strategy_results.append(result)
    
    if strategy_results:
        df_strategy = pd.DataFrame(strategy_results)
        
        # 回収率グラフ
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_strategy['strategy'],
            y=df_strategy['return_rate'],
            text=df_strategy['return_rate'].round(1),
            textposition='auto',
            marker_color=['green' if x > 100 else 'red' for x in df_strategy['return_rate']]
        ))
        fig.update_layout(
            title="戦略別回収率(%)",
            xaxis_title="戦略",
            yaxis_title="回収率(%)",
            showlegend=False
        )
        fig.add_hline(y=100, line_dash="dash", line_color="gray")
        st.plotly_chart(fig)
        
        # 詳細テーブル
        st.dataframe(df_strategy, use_container_width=True)

elif page == "データ収集":
    st.title("データ収集")
    
    st.subheader("レースデータの取得")
    
    # 日付選択
    target_date = st.date_input(
        "対象日",
        value=date.today(),
        max_value=date.today()
    )
    
    # 競馬場選択
    jyo_options = {
        "": "全競馬場",
        "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
        "05": "東京", "06": "中山", "07": "中京", "08": "京都",
        "09": "阪神", "10": "小倉"
    }
    jyo_cd = st.selectbox("競馬場", options=list(jyo_options.keys()), 
                          format_func=lambda x: jyo_options[x])
    
    if st.button("データ取得開始"):
        with st.spinner("データを取得中..."):
            # レース一覧を取得
            date_str = target_date.strftime("%Y%m%d")
            races = scraper.get_race_list(date_str, jyo_cd)
            
            if races:
                st.success(f"{len(races)}件のレースを取得しました")
                
                # プログレスバー
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, race in enumerate(races):
                    status_text.text(f"処理中: {race['race_name']}")
                    
                    # レース情報を取得
                    race_info = scraper.get_race_info(race['race_id'])
                    if race_info:
                        race_info['race_date'] = target_date
                        db.save_race(race_info)
                    
                    # レース結果を取得
                    results = scraper.get_race_result(race['race_id'])
                    if results:
                        db.save_race_results(race['race_id'], results)
                        
                        # 馬情報を取得
                        for result in results:
                            if 'horse_id' in result:
                                horse_info = scraper.get_horse_info(result['horse_id'])
                                if horse_info:
                                    db.save_horse(horse_info)
                    
                    # オッズ情報を取得
                    odds = scraper.get_odds(race['race_id'])
                    if odds:
                        db.save_odds(race['race_id'], '1', odds)
                    
                    progress_bar.progress((i + 1) / len(races))
                
                st.success("データ取得が完了しました！")
            else:
                st.warning("レースが見つかりませんでした")

elif page == "馬情報分析":
    st.title("馬情報分析")
    
    # 馬選択
    session = db.get_session()
    try:
        horses = session.query(Horse).all()
        horse_options = {h.horse_id: f"{h.horse_name} ({h.horse_id})" for h in horses}
    finally:
        session.close()
    
    if horse_options:
        selected_horse_id = st.selectbox(
            "分析対象の馬",
            options=list(horse_options.keys()),
            format_func=lambda x: horse_options[x]
        )
        
        if selected_horse_id:
            # 基本情報
            session = db.get_session()
            try:
                horse = session.query(Horse).filter_by(horse_id=selected_horse_id).first()
                if horse:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("基本情報")
                        st.write(f"**馬名**: {horse.horse_name}")
                        st.write(f"**性別**: {horse.sex}")
                        st.write(f"**生年月日**: {horse.birth_date}")
                        st.write(f"**父**: {horse.father}")
                        st.write(f"**母**: {horse.mother}")
                    
                    with col2:
                        st.subheader("関係者")
                        st.write(f"**調教師**: {horse.trainer}")
                        st.write(f"**馬主**: {horse.owner}")
                        st.write(f"**生産者**: {horse.breeder}")
            finally:
                session.close()
            
            # 成績分析
            st.subheader("成績分析")
            
            # 期間選択
            days = st.slider("分析期間（日）", 30, 365, 180)
            
            # 勝率
            win_stats = analyzer.calculate_win_rate(selected_horse_id, days)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("出走数", win_stats['total_races'])
            with col2:
                st.metric("勝利数", win_stats['wins'])
            with col3:
                st.metric("勝率", f"{win_stats['win_rate']:.1f}%")
            with col4:
                st.metric("連対率", f"{win_stats['top3_rate']:.1f}%")
            
            # 馬場状態別成績
            st.subheader("馬場状態別成績")
            track_stats = analyzer.analyze_track_condition(selected_horse_id)
            
            if track_stats:
                df_track = pd.DataFrame([
                    {
                        '馬場状態': condition,
                        '出走数': stats['races'],
                        '勝利数': stats['wins'],
                        '勝率': stats['win_rate'],
                        '平均着順': stats['avg_ranking']
                    }
                    for condition, stats in track_stats.items()
                ])
                
                # グラフ
                fig = px.bar(df_track, x='馬場状態', y='勝率', 
                            hover_data=['出走数', '勝利数'])
                st.plotly_chart(fig)
                
                # テーブル
                st.dataframe(df_track, use_container_width=True)
            
            # 距離別成績
            st.subheader("距離別成績")
            distance_stats = analyzer.analyze_distance_performance(selected_horse_id)
            
            if distance_stats:
                df_distance = pd.DataFrame([
                    {
                        '距離区分': category,
                        '出走数': stats['races'],
                        '勝利数': stats['wins'],
                        '勝率': stats['win_rate'],
                        '平均着順': stats['avg_ranking']
                    }
                    for category, stats in distance_stats.items()
                ])
                
                # グラフ
                fig = px.bar(df_distance, x='距離区分', y='勝率',
                            hover_data=['出走数', '勝利数'])
                st.plotly_chart(fig)
                
                # テーブル
                st.dataframe(df_distance, use_container_width=True)
    else:
        st.info("馬情報がありません。先にデータを収集してください。")

elif page == "レース予測":
    st.title("レース予測")
    
    # レース選択
    session = db.get_session()
    try:
        # 最近のレースを取得
        recent_races = session.query(Race).order_by(Race.race_date.desc()).limit(50).all()
        race_options = {
            r.race_id: f"{r.race_date} - {r.race_name or r.race_id}"
            for r in recent_races
        }
    finally:
        session.close()
    
    if race_options:
        selected_race_id = st.selectbox(
            "予測対象レース",
            options=list(race_options.keys()),
            format_func=lambda x: race_options[x]
        )
        
        if st.button("予測実行"):
            with st.spinner("予測中..."):
                predictions = analyzer.predict_race_result(selected_race_id)
                
                if predictions:
                    st.success("予測が完了しました")
                    
                    # 予測結果表示
                    df_pred = pd.DataFrame(predictions)
                    
                    # グラフ
                    fig = px.bar(df_pred.head(10), 
                                x='horse_name', y='score',
                                hover_data=['jockey', 'popularity'],
                                title="予測スコア TOP10")
                    st.plotly_chart(fig)
                    
                    # テーブル
                    st.dataframe(
                        df_pred[['predicted_rank', 'horse_number', 'horse_name', 
                               'jockey', 'popularity', 'score']],
                        use_container_width=True
                    )
                    
                    # 実際の結果と比較（結果がある場合）
                    session = db.get_session()
                    try:
                        actual_results = session.query(RaceResult).filter_by(
                            race_id=selected_race_id
                        ).filter(RaceResult.ranking.isnot(None)).all()
                        
                        if actual_results:
                            st.subheader("予測と実際の結果の比較")
                            
                            comparison = []
                            for pred in predictions[:5]:  # TOP5のみ
                                actual = next((r for r in actual_results 
                                             if r.horse_id == pred['horse_id']), None)
                                if actual:
                                    comparison.append({
                                        '馬名': pred['horse_name'],
                                        '予測順位': pred['predicted_rank'],
                                        '実際の順位': actual.ranking,
                                        '差': abs(pred['predicted_rank'] - actual.ranking)
                                    })
                            
                            if comparison:
                                df_comp = pd.DataFrame(comparison)
                                st.dataframe(df_comp, use_container_width=True)
                    finally:
                        session.close()
                else:
                    st.warning("予測できませんでした")
    else:
        st.info("レースデータがありません。先にデータを収集してください。")

elif page == "投資戦略分析":
    st.title("投資戦略分析")
    
    st.subheader("戦略別パフォーマンス分析")
    
    # 期間選択
    days = st.slider("分析期間（日）", 7, 365, 30)
    
    # 各戦略の結果を取得
    strategies = {
        'favorite': '1番人気',
        'longshot': '大穴狙い（10番人気以下）',
        'value': 'バリュー投資（3-8番人気）'
    }
    
    results = []
    for key, name in strategies.items():
        result = analyzer.analyze_return_rate(key, days)
        result['strategy_name'] = name
        results.append(result)
    
    if results:
        df_results = pd.DataFrame(results)
        
        # メトリクス表示
        col1, col2, col3 = st.columns(3)
        
        for i, (col, result) in enumerate(zip([col1, col2, col3], results)):
            with col:
                st.subheader(result['strategy_name'])
                st.metric("回収率", f"{result['return_rate']:.1f}%",
                         delta=f"{result['return_rate'] - 100:.1f}%")
                st.metric("勝率", f"{result['win_rate']:.1f}%")
                st.metric("収支", f"¥{result['profit']:,.0f}")
        
        # 詳細グラフ
        st.subheader("戦略比較")
        
        # 回収率比較
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            x=df_results['strategy_name'],
            y=df_results['return_rate'],
            text=df_results['return_rate'].round(1),
            textposition='auto',
            marker_color=['green' if x > 100 else 'red' for x in df_results['return_rate']]
        ))
        fig1.update_layout(
            title="戦略別回収率",
            yaxis_title="回収率(%)",
            showlegend=False
        )
        fig1.add_hline(y=100, line_dash="dash", line_color="gray")
        st.plotly_chart(fig1)
        
        # 収支比較
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df_results['strategy_name'],
            y=df_results['profit'],
            text=df_results['profit'].round(0),
            textposition='auto',
            marker_color=['green' if x > 0 else 'red' for x in df_results['profit']]
        ))
        fig2.update_layout(
            title="戦略別収支",
            yaxis_title="収支(円)",
            showlegend=False
        )
        fig2.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig2)
        
        # 詳細データ
        st.subheader("詳細データ")
        st.dataframe(
            df_results[['strategy_name', 'total_races', 'total_investment', 
                       'total_return', 'return_rate', 'win_rate', 'profit']],
            use_container_width=True
        )
        
        # アドバイス
        best_strategy = df_results.loc[df_results['return_rate'].idxmax()]
        st.info(f"""
        💡 分析結果：
        - 最も回収率が高い戦略: **{best_strategy['strategy_name']}** 
          (回収率: {best_strategy['return_rate']:.1f}%)
        - 投資総額: ¥{best_strategy['total_investment']:,}
        - 回収総額: ¥{best_strategy['total_return']:,}
        """)

# フッター
st.sidebar.markdown("---")
st.sidebar.markdown("Created with ❤️ using Streamlit")
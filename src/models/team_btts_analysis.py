from decimal import Decimal
from sqlalchemy import Column, Integer, String, BigInteger, Numeric
from src.models.base import Base


class TeamBttsAnalysis(Base):
    __tablename__ = "mart_team_btts_analysis"
    
    team_id = Column(Integer, primary_key=True)
    team_name = Column(String)
    season_id = Column(Integer, primary_key=True)
    season_name = Column(String)
    season_year = Column(String)
    matches_played = Column(BigInteger)
    
    # Overall stats
    overall_win_pct = Column(Numeric)
    overall_avg_goals_per_match = Column(Numeric)
    overall_avg_scored = Column(Numeric)
    overall_avg_conceded = Column(Numeric)
    overall_btts_pct = Column(Numeric)
    overall_clean_sheet_pct = Column(Numeric)
    overall_avg_xg = Column(Numeric)
    overall_avg_xga = Column(Numeric)
    
    # Home stats
    home_matches_played = Column(BigInteger)
    home_win_pct = Column(Numeric)
    home_avg_goals_per_match = Column(Numeric)
    home_avg_scored = Column(Numeric)
    home_avg_conceded = Column(Numeric)
    home_btts_pct = Column(Numeric)
    home_clean_sheet_pct = Column(Numeric)
    home_avg_xg = Column(Numeric)
    home_avg_xga = Column(Numeric)
    
    # Away stats
    away_matches_played = Column(BigInteger)
    away_win_pct = Column(Numeric)
    away_avg_goals_per_match = Column(Numeric)
    away_avg_scored = Column(Numeric)
    away_avg_conceded = Column(Numeric)
    away_btts_pct = Column(Numeric)
    away_clean_sheet_pct = Column(Numeric)
    away_avg_xg = Column(Numeric)
    away_avg_xga = Column(Numeric)

    home_scored_over_05_pct	= Column(Numeric)
    home_scored_over_15_pct	= Column(Numeric)
    home_scored_over_25_pct	= Column(Numeric)
    home_scored_over_35_pct	= Column(Numeric)
    home_failed_to_score_pct = Column(Numeric)
    away_scored_over_05_pct	= Column(Numeric)
    away_scored_over_15_pct = Column(Numeric)
    away_scored_over_25_pct	= Column(Numeric)
    away_scored_over_35_pct	= Column(Numeric)
    away_failed_to_score_pct = Column(Numeric)
    home_conceded_over_05_pct = Column(Numeric)
    home_conceded_over_15_pct = Column(Numeric)
    home_conceded_over_25_pct = Column(Numeric)
    home_conceded_over_35_pct = Column(Numeric)
    away_conceded_over_05_pct = Column(Numeric)
    away_conceded_over_15_pct = Column(Numeric)
    away_conceded_over_25_pct = Column(Numeric)
    away_conceded_over_35_pct = Column(Numeric)
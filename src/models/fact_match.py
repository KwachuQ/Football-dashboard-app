from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Text
from src.models.base import SilverBase


class FactMatch(SilverBase):
    __tablename__ = "fact_match"
    
    match_id = Column(Integer, primary_key=True)
    match_slug = Column(Text)
    match_date = Column(Date)
    start_timestamp = Column(DateTime(timezone=True))
    status_type = Column(Text)
    status_description = Column(Text)
    winner_code = Column(Integer)
    home_score = Column(Integer)
    away_score = Column(Integer)
    home_score_period1 = Column(Integer)
    home_score_period2 = Column(Integer)
    away_score_period1 = Column(Integer)
    away_score_period2 = Column(Integer)
    home_team_id = Column(Integer)
    home_team_name = Column(Text)
    away_team_id = Column(Integer)
    away_team_name = Column(Text)
    tournament_id = Column(Integer)
    tournament_name = Column(Text)
    season_id = Column(Integer)
    season_name = Column(Text)
    season_year = Column(Text)
    country_name = Column(Text)
    has_statistics = Column(Integer)
    loaded_at = Column(DateTime(timezone=True))
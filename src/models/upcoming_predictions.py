from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, Text
from src.models.base import Base


class UpcomingPredictions(Base):
    __tablename__ = "mart_upcoming_predictions"
    
    match_id = Column(Integer, primary_key=True)
    match_date = Column(DateTime(timezone=True))
    season_id = Column(Integer)
    season_name = Column(Text)
    season_year = Column(Text)
    home_team_id = Column(Integer)
    home_team_name = Column(Text)
    away_team_id = Column(Integer)
    away_team_name = Column(Text)
    tournament_name = Column(Text)
    predicted_home_goals = Column(Integer)
    predicted_away_goals = Column(Integer)
    predicted_total_xg = Column(Integer)
    match_outlook = Column(Text)
    home_win_probability = Column(Integer)
    draw_probability = Column(Integer)
    away_win_probability = Column(Integer)
    home_win_fair_odds = Column(Integer)
    draw_fair_odds = Column(Integer)
    away_win_fair_odds = Column(Integer)
    created_at = Column(DateTime(timezone=True))
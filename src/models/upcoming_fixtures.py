from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, Text
from src.models.base import Base


class UpcomingFixtures(Base):
    __tablename__ = "mart_upcoming_fixtures"
    
    match_id = Column(Integer, primary_key=True)
    match_slug = Column(Text)
    custom_id = Column(Text)
    start_timestamp = Column(DateTime(timezone=True))
    status_type = Column(Text)
    home_team_id = Column(Integer)
    home_team_name = Column(Text)
    away_team_id = Column(Integer)
    away_team_name = Column(Text)
    tournament_id = Column(Integer)
    tournament_name = Column(Text)
    season_id = Column(Integer)
    season_name = Column(Text)
    season_year = Column(Text)
    round_number = Column(Integer)
    extraction_date = Column(Date)
    extracted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
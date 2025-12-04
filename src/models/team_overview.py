from decimal import Decimal
from sqlalchemy import Column, Integer, String, BigInteger, Numeric
from src.models.base import Base


class TeamOverview(Base):
    __tablename__ = "mart_team_overview"
    
    season_id = Column(Integer, primary_key=True)
    season_name = Column(String)
    season_year = Column(String)
    team_id = Column(Integer, primary_key=True)
    team_name = Column(String)
    matches_played = Column(BigInteger)
    wins = Column(BigInteger)
    draws = Column(BigInteger)
    losses = Column(BigInteger)
    total_points = Column(BigInteger)
    points_per_game = Column(Numeric)
    goals_for = Column(BigInteger)
    goals_against = Column(BigInteger)
    goal_difference = Column(BigInteger)
    goals_per_game = Column(Numeric)
    goals_conceded_per_game = Column(Numeric)
    clean_sheets = Column(BigInteger)
    clean_sheet_percentage = Column(Numeric)
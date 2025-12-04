from decimal import Decimal
from sqlalchemy import Column, Integer, String, BigInteger, Numeric
from src.models.base import Base


class TeamDefense(Base):
    __tablename__ = "mart_team_defense"
    
    team_id = Column(Integer, primary_key=True)
    team_name = Column(String)
    season_id = Column(Integer, primary_key=True)
    season_name = Column(String)
    season_year = Column(String)
    matches_played = Column(BigInteger)
    total_goals_conceded = Column(BigInteger)
    goals_conceded_per_game = Column(Numeric)
    clean_sheets = Column(BigInteger)
    clean_sheet_pct = Column(Numeric)
    total_saves = Column(Numeric)
    saves_per_game = Column(Numeric)
    total_tackles = Column(Numeric)
    tackles_per_game = Column(Numeric)
    avg_tackles_won_pct = Column(Numeric)
    total_interceptions = Column(Numeric)
    interceptions_per_game = Column(Numeric)
    total_clearances = Column(Numeric)
    clearances_per_game = Column(Numeric)
    total_blocked_shots = Column(Numeric)
    blocked_shots_per_game = Column(Numeric)
    total_ball_recoveries = Column(Numeric)
    ball_recoveries_per_game = Column(Numeric)
    avg_aerial_duels_pct = Column(Numeric)
    avg_ground_duels_pct = Column(Numeric)
    avg_duels_won_pct = Column(Numeric)
    total_errors_lead_to_goal = Column(Numeric)
    total_errors_lead_to_shot = Column(Numeric)
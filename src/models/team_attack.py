from decimal import Decimal
from sqlalchemy import Column, Integer, String, BigInteger, Numeric
from src.models.base import Base


class TeamAttack(Base):
    __tablename__ = "mart_team_attack"
    
    team_id = Column(Integer, primary_key=True)
    team_name = Column(String)
    season_id = Column(Integer, primary_key=True)
    season_name = Column(String)
    season_year = Column(String)
    matches_played = Column(BigInteger)
    total_goals = Column(BigInteger)
    goals_per_game = Column(Numeric)
    total_xg = Column(Numeric)
    xg_per_game = Column(Numeric)
    xg_difference = Column(Numeric)
    xg_diff_per_game = Column(Numeric)
    total_big_chances_created = Column(Numeric)
    big_chances_created_per_game = Column(Numeric)
    total_big_chances_missed = Column(Numeric)
    big_chances_missed_per_game = Column(Numeric)
    total_big_chances_scored = Column(Numeric)
    big_chances_scored_per_game = Column(Numeric)
    total_shots_on_target = Column(Numeric)
    shots_on_target_per_game = Column(Numeric)
    total_shots_off_target = Column(Numeric)
    shots_off_target_per_game = Column(Numeric)
    total_blocked_shots = Column(Numeric)
    blocked_shots_per_game = Column(Numeric)
    total_shots = Column(Numeric)
    shots_per_game = Column(Numeric)
    total_shots_inside_box = Column(Numeric)
    shots_inside_box_per_game = Column(Numeric)
    total_shots_outside_box = Column(Numeric)
    shots_outside_box_per_game = Column(Numeric)
    total_hit_woodwork = Column(Numeric)
    total_corners = Column(Numeric)
    corners_per_game = Column(Numeric)
    avg_dribbles_success_pct = Column(Numeric)
    total_touches_in_box = Column(Numeric)
    touches_in_box_per_game = Column(Numeric)
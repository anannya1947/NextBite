import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.models.user import UserProfile
from app.tools.firestore_tools import save_user_profile
from app.agents.health_analyzer import analyze_health_and_tdee
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def seed_demo_data():
    """Seeds demo user profile and triggers baseline TDEE calculation."""
    demo_user = UserProfile(
        uid="demo-user-001",
        name="Alex Demo",
        email="alex.demo@nextbite.local",
        age=30,
        weight_kg=75.0,
        height_cm=175.0,
        sex="male",
        goal="maintain",
        dietary_restrictions=["None"],
        fitness_user_id="1503960366"
    )
    
    logger.info(f"Seeding user: {demo_user.uid}...")
    save_user_profile(demo_user)
    
    logger.info("Computing baseline health profile & TDEE...")
    health_profile = analyze_health_and_tdee(demo_user)
    logger.info(f"Generated Health Profile: BMR={health_profile.bmr}, TDEE={health_profile.tdee}, Target={health_profile.target_calories} kcal")
    logger.info("Seeding complete!")

if __name__ == "__main__":
    seed_demo_data()

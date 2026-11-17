"""消融实验: w/o Goal (移除目标驱动)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from DSAGM.消融实验._base import main_ablation, dsl_wo_goal


if __name__ == "__main__":
    main_ablation(dsl_wo_goal, "w/o Goal")

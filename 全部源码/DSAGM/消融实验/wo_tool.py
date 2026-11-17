"""消融实验: w/o Tool (移除工具增强)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from DSAGM.消融实验._base import main_ablation, dsl_wo_tool


if __name__ == "__main__":
    main_ablation(dsl_wo_tool, "w/o Tool")

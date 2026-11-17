"""消融实验: Direct-Mapping (无中间层, 缺失 Agent-IR)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from DSAGM.消融实验._base import main_ablation, dsl_direct_mapping


if __name__ == "__main__":
    main_ablation(dsl_direct_mapping, "Direct-Mapping", num_examples=15)

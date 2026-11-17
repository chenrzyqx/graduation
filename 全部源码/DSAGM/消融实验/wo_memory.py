"""消融实验: w/o Memory (移除记忆机制, 不使用 few-shot 示例)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from DSAGM.消融实验._base import main_ablation, build_default_dsl


if __name__ == "__main__":
    # w/o Memory: 使用完整 DSL 但 num_examples=0 (不注入 few-shot 记忆)
    main_ablation(build_default_dsl, "w/o Memory", num_examples=0)

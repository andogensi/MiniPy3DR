"""ゲームのエントリポイント。

実行方法:

    python main.py
"""

import os

# 課題の必須条件: カレントディレクトリをこのファイルの場所に固定する
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from game.core import Game
from game.features import FEATURES
from game.level import MAP


def main() -> None:
    game = Game(
        map_data=MAP,
        features=FEATURES,
        title="ProjExD Group0X - DOOM風FPS",
    )
    game.run()


if __name__ == "__main__":
    main()

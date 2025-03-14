"""
loop:
    guild_id: int
    loop: int

shuffle:
    guild_id: int
    shuffle: int
"""

import os
import sqlite3
from contextlib import closing
from musicbot.config import Development as Config


class Database:
    def __init__(self):
        self.statistics = "statistics"
        self.language = "language"
        self.loop_table = "loop_setting"
        self.shuffle_table = "shuffle"

    def create_table(self) -> None:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)

        # Create the database
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    time TEXT,
                    guild_id TEXT,
                    channel_id TEXT,
                    user_id TEXT,
                    video_id TEXT,
                    title TEXT,
                    artist TEXT,
                    duration INTEGER,
                    success BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                )
                # 인덱스 생성
                cursor.execute(
                    """
                CREATE INDEX IF NOT EXISTS idx_date_guild 
                ON statistics(date, guild_id)
                """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS language (
                        id TEXT,
                        language TEXT
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS loop_setting (
                        guild_id TEXT,
                        loop_set INTEGER
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS shuffle (
                        guild_id TEXT,
                        shuffle INTEGER
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS volume (
                        guild_id TEXT PRIMARY KEY,
                        volume INTEGER
                    )
                    """
                )
                conn.commit()
            print("Database created successfully.")

    def set_statistics(self, date: str, video_id: str, count: int) -> None:
        """통계 저장"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                # add statistics
                cursor.execute(
                    f"INSERT INTO {self.statistics} VALUES(?, ?, ?)",
                    (date, video_id, count),
                )
                conn.commit()

    def get_statistics(self, date: str, video_id: str) -> int | None:
        """통계 가져오기"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    f"SELECT * FROM {self.statistics} WHERE date=? AND video_id=?",
                    (date, video_id),
                )
                count = cursor.fetchone()

                if count is not None:
                    count = count[2]

                return count

    def set_loop(self, guild_id: int, loop: int) -> None:
        """길드 아이디로 루프 저장"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                guild = str(guild_id)

                # read loop
                cursor.execute(
                    f"SELECT * FROM {self.loop_table} WHERE guild_id=?", (guild,)
                )
                db_loop = cursor.fetchone()
                if db_loop is None:
                    # add loop
                    cursor.execute(
                        f"INSERT INTO {self.loop_table} VALUES(?, ?)", (guild, loop)
                    )
                else:
                    # modify loop
                    cursor.execute(
                        f"UPDATE {self.loop_table} SET loop_set=? WHERE guild_id=?",
                        (loop, guild),
                    )

                conn.commit()

    def get_loop(self, guild_id: int) -> int | None:
        """모든 루프설정 가져오기"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                # read loop
                cursor.execute(
                    f"SELECT * FROM {self.loop_table} WHERE guild_id=?",
                    (str(guild_id),),
                )
                loop = cursor.fetchone()

                if loop is not None:
                    loop = loop[1]

                return loop

    def set_shuffle(self, guild_id: int, shuffle: bool) -> None:
        """길드 아이디로 셔플 저장"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                guild = str(guild_id)

                # read shuffle
                cursor.execute(
                    f"SELECT * FROM {self.shuffle_table} WHERE guild_id=?", (guild,)
                )
                db_shuffle = cursor.fetchone()
                if db_shuffle is None:
                    # add shuffle
                    cursor.execute(
                        f"INSERT INTO {self.shuffle_table} VALUES(?, ?)",
                        (guild, shuffle),
                    )
                else:
                    # modify shuffle
                    cursor.execute(
                        f"UPDATE {self.shuffle_table} SET shuffle=? WHERE guild_id=?",
                        (shuffle, guild),
                    )

                conn.commit()

    def get_shuffle(self, guild_id: int) -> bool | None:
        """모든 셔플설정 가져오기"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                # read shuffle
                cursor.execute(
                    f"SELECT * FROM {self.shuffle_table} WHERE guild_id=?",
                    (str(guild_id),),
                )
                shuffle = cursor.fetchone()

                if shuffle is not None:
                    shuffle = shuffle[1]

                return shuffle

    def set_volume(self, guild_id: int, volume: int) -> None:
        """길드별 볼륨 설정 저장"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                # 길드 ID를 문자열로 변환
                guild = str(guild_id)

                # 기존 볼륨 설정 확인
                cursor.execute("SELECT * FROM volume WHERE guild_id=?", (guild,))
                db_volume = cursor.fetchone()

                if db_volume is None:
                    # 새로운 볼륨 설정 추가
                    cursor.execute("INSERT INTO volume VALUES(?, ?)", (guild, volume))
                else:
                    # 기존 볼륨 설정 수정
                    cursor.execute(
                        "UPDATE volume SET volume=? WHERE guild_id=?", (volume, guild)
                    )
                conn.commit()

    def get_volume(self, guild_id: int) -> int:
        """길드별 볼륨 설정 가져오기"""
        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    "SELECT volume FROM volume WHERE guild_id=?", (str(guild_id),)
                )
                result = cursor.fetchone()

                # 결과가 없으면 기본값 100 반환
                return result[0] if result else 20

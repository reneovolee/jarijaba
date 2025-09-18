"""로깅 설정"""

import sys
from loguru import logger
from pathlib import Path

# 로그 디렉토리 생성
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 기본 로거 설정 제거
logger.remove()

# 콘솔 로그 설정
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True
)

# 파일 로그 설정
logger.add(
    log_dir / "app.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="10 MB",
    retention="7 days",
    compression="zip"
)

# 추천 요청 전용 로그 파일
logger.add(
    log_dir / "recommendations.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    rotation="5 MB",
    retention="30 days",
    compression="zip"
)

def get_logger(name: str = None):
    """로거 인스턴스 반환"""
    if name:
        return logger.bind(name=name)
    return logger

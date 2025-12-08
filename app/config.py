import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))


class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev-secret'
    SQLALCHEMY_DATABASE_URI = (
        f"mysql://{os.environ.get('MYSQL_USER','root')}:{os.environ.get('MYSQL_PASSWORD','')}@{os.environ.get('MYSQL_HOST','localhost')}/{os.environ.get('MYSQL_DB','news_ai_system')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

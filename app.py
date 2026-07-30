from dotenv import load_dotenv
from flask import Flask  # import flask framwork

load_dotenv()  # local dev: read DB_* from .env (docker sets them via compose)

from api.routes import api  # import custom api routes
from database.db import close_db, init_db  # import db fn

init_db()  # idempotent: CREATE TABLE IF NOT EXISTS

app = Flask(__name__, static_folder="statics", static_url_path="")
app.register_blueprint(api)  # register api routes
app.teardown_appcontext(close_db)  # cleanup db after request completes


@app.route("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=True)


# __name__ represents the name of current module (built in)

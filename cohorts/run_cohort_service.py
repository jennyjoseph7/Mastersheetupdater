from flask import Flask
from api import cohort_bp, gryd_orchestration_bp

app = Flask(__name__)
app.register_blueprint(cohort_bp)
app.register_blueprint(gryd_orchestration_bp)

if __name__ == "__main__":
    app.run(port=5001, debug=True)
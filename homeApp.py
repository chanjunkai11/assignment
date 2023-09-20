from flask import Flask, render_template, request
from student import student_bp 
from lecturer import lecturer_bp 
from company import company_bp 
from admin import admin_bp 
import os
from datetime import timedelta
from flask_session import Session

app = Flask(__name__, static_folder='assets')
app.secret_key = 'GCw0dD2*HW0pX@=7'

app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
Session(app)

app.register_blueprint(student_bp, url_prefix="/student")
app.register_blueprint(lecturer_bp , url_prefix="/lecturer")
app.register_blueprint(company_bp , url_prefix="/company")
app.register_blueprint(admin_bp, url_prefix="/admin")

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

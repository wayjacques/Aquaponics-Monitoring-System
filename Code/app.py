from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import csv

app = Flask(__name__)
app.secret_key = "secure-aquaponics"

USERNAME = "admin"
PASSWORD = "pass123"

CSV_FILE = 'logs/sensor_log.csv'

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            session['user'] = USERNAME
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/data')
def data():
    try:
        with open(CSV_FILE, 'r') as f:
            rows = list(csv.reader(f))[-1]
            return jsonify({
                'time': rows[0],
                'temperature': rows[1],
                'humidity': rows[2],
                'watertemp': rows[3],
                'soil': rows[4],
                'water': rows[5]
            })
    except:
        return jsonify({
            'error': 'No data available'
        })

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

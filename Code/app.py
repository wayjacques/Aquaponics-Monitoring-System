from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import csv

app = Flask(__name__)
app.secret_key = "secure-aquaponics"

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'pass123':
            session['user'] = 'admin'
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
        with open('logs/sensor_log.csv', 'r') as f:
            last_row = list(csv.reader(f))[-1]
            return jsonify({
                'time': last_row[0],
                'watertemp': last_row[3]
            })
    except:
        return jsonify({'error': 'No water temp data found'})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

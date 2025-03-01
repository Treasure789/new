import hashlib
import json
import time
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.secret_key = 'supersecretkey'
limiter = Limiter(get_remote_address, app=app)

# Load and save helper functions
def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Load blockchain and users
blockchain = load_data('blockchain.json') or [{
    'index': 0, 'previous_hash': '0', 'transactions': [], 'proof': 100, 'timestamp': time.time()
}]
users = load_data('users.json') or {}

# Helper functions
def create_user(username, password):
    if username in users:
        return False
    users[username] = {'password': password, 'balance': 0}
    save_data('users.json', users)
    return True

def verify_user(username, password):
    return username in users and users[username]['password'] == password

def get_balance(username):
    return users.get(username, {}).get('balance', 0)

def update_balance(username, amount):
    users[username]['balance'] += amount
    save_data('users.json', users)

def add_transaction(sender, recipient, amount):
    blockchain[-1]['transactions'].append({
        'sender': sender, 'recipient': recipient, 'amount': amount
    })
    save_data('blockchain.json', blockchain)

def proof_of_work(last_proof):
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1
    return proof

def valid_proof(last_proof, proof, difficulty=4):
    guess = f'{last_proof}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:difficulty] == '0' * difficulty

def mine_block(miner):
    last_block = blockchain[-1]
    proof = proof_of_work(last_block['proof'])
    add_transaction('Network', miner, 10)  # Reward
    new_block = {
        'index': len(blockchain),
        'previous_hash': hashlib.sha256(json.dumps(last_block, sort_keys=True).encode()).hexdigest(),
        'transactions': blockchain[-1]['transactions'],
        'proof': proof,
        'timestamp': time.time()
    }
    blockchain.append(new_block)
    save_data('blockchain.json', blockchain)
    update_balance(miner, 10)

# Routes
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['user'], balance=get_balance(session['user']))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if create_user(username, password):
            return redirect(url_for('login'))
        return 'User already exists.'
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if verify_user(username, password):
            session['user'] = username
            return redirect(url_for('home'))
        return 'Invalid credentials.'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/mine', methods=['POST'])
def mine():
    if 'user' not in session:
        return redirect(url_for('login'))
    miner = session['user']
    mine_block(miner)
    return redirect(url_for('home'))

@app.route('/transfer', methods=['POST'])
def transfer():
    if 'user' not in session:
        return redirect(url_for('login'))

    sender = session['user']
    recipient = request.form['recipient']
    amount = float(request.form['amount'])

    if recipient not in users:
        return 'Recipient does not exist.'

    if get_balance(sender) < amount:
        return 'Insufficient funds.'

    update_balance(sender, -amount)
    update_balance(recipient, amount)
    add_transaction(sender, recipient, amount)

    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

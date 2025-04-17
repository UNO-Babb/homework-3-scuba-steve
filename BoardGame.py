from flask import Flask, render_template_string, request, redirect, url_for, session
import random
app = Flask(__name__)
app.secret_key = 'supersecretkey'

# CONFIG
GRID_ROWS = 18
GRID_COLS = 18

# GAME DATA (to be loaded or defined later)
event_map = {}

# Populate event_map with loot, traps, and trolls
from collections import defaultdict
zone_labels = {}  # Will be loaded below  # Load zone_labels from spreadsheet instead of string literal
import pandas as pd

sheet = pd.read_excel("TileZoneTemplate.xlsx")
columns = {
    "Cave": ("Cave_x", "Cave_y"),
    "Cave-entry": ("CaveEntrance_x", "CaveEntrance_y"),
    "Mountains": ("Mountains_x", "Mountains_y"),
    "Mountains-entry": ("MountainsEntrance_x", "MountainsEntrance_y"),
    "Village": ("Village_x", "Village_y"),
    "Village-entry": ("VillageEntrance_x", "VillageEntrance_y"),
    "Road": ("Road_x", "Road_y")
}
zone_labels = {}
for zone, (x_col, y_col) in columns.items():
    for x, y in zip(sheet[x_col], sheet[y_col]):
        if pd.notna(x) and pd.notna(y):
            coord = (int(y), int(x)) 
            if coord in zone_labels and 'entry' not in zone:
                continue
            zone_labels[coord] = zone
for zone, (x_col, y_col) in columns.items():
    for x, y in zip(sheet[x_col], sheet[y_col]):
        if pd.notna(x) and pd.notna(y):
            coord = (int(y), int(x))
            if coord in zone_labels and 'entry' not in zone:
                continue
            zone_labels[coord] = zone
zone_tiles = defaultdict(list)
for coord, zone in zone_labels.items():
    base_zone = zone.replace('-entry', '')
    if base_zone in ['Cave', 'Mountains', 'Village'] and 'Road' not in zone:
        zone_tiles[base_zone].append(coord)

zone_event_config = {
    'Cave': {'loot': 0.2, 'trap': 0.6, 'troll': 2},
    'Mountains': {'loot': 0.25, 'trap': 0.4, 'troll': 2},
    'Village': {'loot': 0.3, 'trap': 0.2, 'troll': 3},
}

for zone, coords in zone_tiles.items():
    config = zone_event_config[zone]
    random.shuffle(coords)
    loot_count = round(len(coords) * config['loot'])
    trap_count = round(len(coords) * config['trap'])
    troll_count = config['troll']

    for i, coord in enumerate(coords):
        if i < loot_count:
            event_map[coord] = ['Loot']
        elif i < loot_count + trap_count:
            event_map[coord] = ['Trap']
    for coord in random.sample(coords, troll_count):
        event_map.setdefault(coord, []).append('Troll')

zone_labels = {}  # now loaded only from Excel

player_positions = {1: (17, 5), 2: (17, 5)}
player_scores = {1: 0, 2: 0}
player_stats = {1: {'loot': 0, 'traps': 0, 'gold_lost': 0}, 2: {'loot': 0, 'traps': 0, 'gold_lost': 0}}
current_player = 1
game_log = []
NAME_TEMPLATE = """
<!doctype html>
<html>
<head><title>Enter Player Names</title></head>
<body>
<h1>Treasure Hunter 2025</h1>
<form method="POST">
  Player 1 Name: <input name="player1_name"><br>
  Player 2 Name: <input name="player2_name"><br>
  <button type="submit">Start Game</button>
</form>
</body>
</html>
"""

GAME_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Treasure Hunter 2025</title>
  <style>
    .board { position: relative; width: 1200px; height: 1200px; border: 1px solid #000; background-color: #e0e0e0; margin-bottom: 20px; }
    .tile {
      position: absolute;
      width: 60px; height: 60px;
      border: 2px solid black;
      text-align: center;
      font-size: 11px;
      box-sizing: border-box;
      background-color: #fff;
    }
    .Cave { border-color: #3498db; }
    .Mountains { border-color: #28b463; }
    .Village { border-color: #f1c40f; }
    .Cave-entry { background-color: #85c1e9; }
    .Mountains-entry { background-color: #abebc6; }
    .Village-entry { background-color: #f9e79f; }
    .Road { background-color: #bbb; }
    .tile .players span { font-weight: bold; display: block; }
  </style>
</head>
<body>
<h1>Treasure Hunter 2025</h1>
<h2>Current Turn: {{ player1 if current_player == 1 else player2 }}</h2>
<div class="board">
  {% for row_index in range(grid|length) %}
    {% for col_index in range(grid[0]|length) %}
      {% set cell = grid[row_index][col_index] %}
      {% if cell %}
        <div class="tile {{ cell[3] }}" style="top: {{ row_index * 62 }}px; left: {{ col_index * 62 }}px">
          <div>{{ cell[0] }}</div>
          <div>
            {% for event in cell[1] %}
              {% if event == 'Loot' %}💰{% elif event == 'Trap' %}☠️{% elif event == 'Troll' %}👹{% endif %}
            {% endfor %}
          </div>
          <div class="players">{{ cell[2]|safe }}</div>
          <div>{{ cell[3].replace('-entry', '') }}</div>
        </div>
      {% endif %}
    {% endfor %}
  {% endfor %}
</div>
<form action="/roll" method="POST">
  <button type="submit">🎲 Roll Dice ({{ player1 if current_player == 1 else player2 }})</button>
</form>
<h2>Scores</h2>
<ul>
  <li>{{ player1 }}: {{ player_scores[1] }} gold</li>
  <li>{{ player2 }}: {{ player_scores[2] }} gold</li>
</ul>
<h2>Stats</h2>
<ul>
  <li>{{ player1 }} — Loot Found: {{ player_stats[1]['loot'] }}, Traps Hit: {{ player_stats[1]['traps'] }}, Gold Lost: {{ player_stats[1]['gold_lost'] }}</li>
  <li>{{ player2 }} — Loot Found: {{ player_stats[2]['loot'] }}, Traps Hit: {{ player_stats[2]['traps'] }}, Gold Lost: {{ player_stats[2]['gold_lost'] }}</li>
</ul>
<form action="/reset" method="POST">
  <button type="submit">🔄 Reset Game</button>
</form>
<h2>Log</h2>
<ul>
{% for line in game_log[:10] %}
  <li>{{ line }}</li>
{% endfor %}
</ul>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['player1_name'] = request.form.get('player1_name', 'Player 1')
        session['player2_name'] = request.form.get('player2_name', 'Player 2')
        return redirect(url_for('game'))

    return render_template_string(NAME_TEMPLATE)




@app.route('/game')
def game():
    if player_scores[1] >= 100 or player_scores[2] >= 100:
        winner = session.get('player1_name', 'Player 1') if player_scores[1] >= 100 else session.get('player2_name', 'Player 2')
        return f"<h1>{winner} wins the game with 100+ gold!</h1><br><a href='/'>Play Again</a>"

    grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            coord = (r, c)
            if coord not in zone_labels:
                continue
            zone = zone_labels.get(coord, '')
            events = event_map.get(coord, [])
            players_here = []
            if player_positions[1] == coord:
                players_here.append("<span style='color:red'>P1</span>")
            if player_positions[2] == coord:
                players_here.append("<span style='color:blue'>P2</span>")
            grid[r][c] = (coord, events, players_here, zone)

    return render_template_string(GAME_TEMPLATE, grid=grid, player_scores=player_scores, player1=session.get('player1_name', 'Player 1'), player2=session.get('player2_name', 'Player 2'), current_player=current_player, player_stats=player_stats, game_log=game_log)

@app.route('/roll', methods=['POST'])
def roll():
    r, c = player_positions[current_player]
    die1 = random.randint(1, 6)
    die2 = random.randint(1, 6)
    options = [die1, die2, die1 + die2]
    session['roll_options'] = options
    session['player_coord'] = (r, c)
    return redirect(url_for('choose'))

@app.route('/choose', methods=['GET', 'POST'])
def choose():
    global current_player
    if request.method == 'POST':
        choice = int(request.form.get('choice'))
        session['chosen_distance'] = choice
        r, c = session['player_coord']
        move_map = {'N': (-1, 0), 'S': (1, 0), 'E': (0, 1), 'W': (0, -1)}
        valid_directions = []
        for d, (dr, dc) in move_map.items():
            nr, nc = r + dr * choice, c + dc * choice
            if (0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS and (nr, nc) in zone_labels):
                valid_directions.append(d)
        session['valid_directions'] = valid_directions
        return redirect(url_for('choose_direction'))

    options = session.get('roll_options', [1, 2, 3])
    return render_template_string("""
        <h1>Choose Your Move</h1>
        <form method='POST'>
            {% for option in options %}
                <button name='choice' value='{{ option }}'>Move {{ option }}</button><br>
            {% endfor %}
        </form>
    """, options=options)

@app.route('/choose_direction', methods=['GET', 'POST'])
def choose_direction():
    global current_player
    options = session.get('valid_directions', [])
    if request.method == 'POST':
        move = request.form.get('move')
        choice = int(session['chosen_distance'])
        r, c = session['player_coord']
        move_map = {'N': (-1, 0), 'S': (1, 0), 'E': (0, 1), 'W': (0, -1)}
        dr, dc = move_map[move]
        nr, nc = r + dr * choice, c + dc * choice
        chosen_tile = (nr, nc)
        session.pop('valid_directions', None)
        session.pop('chosen_distance', None)

        # Zone entrance check
        tile_type = zone_labels.get(chosen_tile, '')
        if 'entry' in tile_type:
            session['entrances'] = [chosen_tile]
            session['movement_choice'] = [chosen_tile]
            return redirect(url_for('enter_zone'))

        return process_movement(chosen_tile)

    return render_template_string("""
    <h1>Choose Direction</h1>
    <form method='POST'>
        {% for d in options %}
            <button name='move' value='{{ d }}'>{{ d }}</button><br>
        {% endfor %}
    </form>
    """, options=options)

@app.route('/enter_zone', methods=['GET', 'POST'])
def enter_zone():
    global current_player
    entrances = session.get('entrances', [])
    options = session.get('movement_choice', [])
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'enter':
            chosen_tile = random.choice(entrances)
        else:
            chosen_tile = random.choice(options)
        return process_movement(chosen_tile)

    return render_template_string("""
        <h1>Entrance Tile Reached!</h1>
        <form method='POST'>
            <button name='action' value='enter'>Enter the Zone</button><br>
            <button name='action' value='continue'>Stay on the Road</button>
        </form>
    """)

@app.route('/reset', methods=['POST'])
def reset():
    global player_positions, player_scores, player_stats, current_player, game_log
    player_positions = {1: (17, 5), 2: (17, 5)}
    player_scores = {1: 0, 2: 0}
    player_stats = {1: {'loot': 0, 'traps': 0, 'gold_lost': 0}, 2: {'loot': 0, 'traps': 0, 'gold_lost': 0}}
    game_log = []
    current_player = 1
    return redirect(url_for('index'))

def process_movement(chosen_tile):
    global current_player
    player_positions[current_player] = chosen_tile
    events = event_map.get(chosen_tile, [])
    zone = zone_labels.get(chosen_tile, '').replace('-entry', '')
    log = f"{session.get(f'player{current_player}_name', f'Player {current_player}')} moved to {chosen_tile}"

    for event in events:
        if event == 'Loot':
            gold = random.randint(10, 20) if zone == 'Cave' else random.randint(5, 10) if zone == 'Mountains' else random.randint(1, 5)
            player_scores[current_player] += gold
            player_stats[current_player]['loot'] += 1
            log += f" and found {gold} gold!"
        elif event == 'Trap':
            damage = 3 if zone == 'Cave' else 2 if zone == 'Mountains' else 1
            original = player_scores[current_player]
            player_scores[current_player] = max(0, original - damage)
            player_stats[current_player]['traps'] += 1
            player_stats[current_player]['gold_lost'] += (original - player_scores[current_player])
            log += f" and hit a trap! Lost {damage} gold."
        elif event == 'Troll':
            roll = random.randint(1, 20)
            target = random.randint(0, 20)
            if roll <= target:
                lost = player_scores[current_player] // 2
                player_scores[current_player] -= lost
                player_stats[current_player]['gold_lost'] += lost
                log += f" and faced a troll! Roll: {roll} vs Target: {target}. Lost half gold."
            else:
                log += f" and faced a troll! Roll: {roll} vs Target: {target}. Survived!"

    game_log.insert(0, log)
    current_player = 2 if current_player == 1 else 1
    return redirect(url_for('game'))

if __name__ == "__main__":
    app.run(debug=True)
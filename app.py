import random
import asyncio
from flask import Flask, render_template, request, session, redirect, url_for
import aiohttp

MAXCONCURRENT = 25
BASEURL = "https://pokeapi.co/api/v2/pokemon?limit=1351"

app = Flask(__name__)
# Secret key required to use Flask sessions securely
app.secret_key = "super_secret_pokemon_key"

# Global database to cache API responses across requests
pokemon_db = {}

async def fetch_json(session_aio, url, semaphore):
    async with semaphore:
        try:
            async with session_aio.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            print(f"Error caught fetching {url}: {e}")
            return None

async def load_data():
    global pokemon_db
    print("Fetching Pokemon API Data...")
    semaphore = asyncio.Semaphore(MAXCONCURRENT)
    async with aiohttp.ClientSession() as session_aio:
        indexdata = await fetch_json(session_aio, BASEURL, semaphore)
        if not indexdata or 'results' not in indexdata:
            print("Failed to return base data.")
            return
        
        tasks = [fetch_json(session_aio, item['url'], semaphore) for item in indexdata['results']]
        results = await asyncio.gather(*tasks)
        
        for detail in results:
            if detail:
                name = detail.get('name', '').title()
                if name:
                    pokemon_db[name] = {
                        'name': name,
                        'height': detail.get('height', 0) / 10,
                        'weight': detail.get('weight', 0) / 10,
                        'base_experience': detail.get('base_experience', 0),
                        'types': [t['type']['name'].title() for t in detail.get('types', [])]
                    }
    print(f"Loaded {len(pokemon_db)} Pokemon into database.")

@app.route('/', methods=['GET', 'POST'])
def index():
    # If the database hasn't loaded yet, run the async population function
    if not pokemon_db:
        asyncio.run(load_data())

    # Initialize a new game session if it doesn't exist
    if 'target' not in session:
        random_pokemon, pokeinfo = random.choice(list(pokemon_db.items()))
        session['target'] = random_pokemon
        session['guesses'] = []
        session['game_over'] = False

    message = None
    target_info = pokemon_db[session['target']]

    if request.method == 'POST':
        # Check if user clicked the "Reset" button
        if 'reset' in request.form:
            session.pop('target', None)
            return redirect(url_for('index'))

        # Process user guess
        guess = request.form.get('guess', '').strip().title()

        if not session['game_over']:
            if guess not in pokemon_db:
                message = "Not a valid Pokémon! Try again!"
            elif any(g['name'] == guess for g in session['guesses']):
                message = "You already guessed that one!"
            else:
                guessed_info = pokemon_db[guess]
                
                # Check metrics against target Pokémon
                height_match = guessed_info['height'] == target_info['height']
                weight_match = guessed_info['weight'] == target_info['weight']
                xp_match = guessed_info['base_experience'] == target_info['base_experience']
                
                # Type logic matching colorama's strict color structure
                colored_types = []
                for type_name in guessed_info['types']:
                    if type_name in target_info['types']:
                        colored_types.append({'name': type_name, 'match': 'correct'})
                    else:
                        colored_types.append({'name': type_name, 'match': 'incorrect'})

                # Build evaluated guess structure
                guess_result = {
                    'name': guess,
                    'height': guessed_info['height'],
                    'height_match': height_match,
                    'weight': guessed_info['weight'],
                    'weight_match': weight_match,
                    'base_experience': guessed_info['base_experience'],
                    'xp_match': xp_match,
                    'types': colored_types
                }

                # Save history into session cookies (session modification flag required for lists)
                guesses_list = session['guesses']
                guesses_list.append(guess_result)
                session['guesses'] = guesses_list

                if guess == session['target']:
                    message = "Correct! You won!"
                    session['game_over'] = True

    return render_template('index.html', guesses=session['guesses'], message=message, game_over=session['game_over'])

if __name__ == '__main__':
    # Initialize the cache synchronously on first startup
    asyncio.run(load_data())
    app.run(debug=True)

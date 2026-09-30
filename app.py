import random
from colorama import init, Back, Style
import asyncio
from typing import Any
import aiohttp

MAXCONCURRENT = 25
BASEURL =  "https://pokeapi.co/api/v2/pokemon?limit=1351"

async def fetch_json(session, url, semaphore):
    async with semaphore:
        try: 
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e: 
            print(f"Error caught fetching {url}: {e}")
            return None
        
async def load_data():
    semaphore = asyncio.Semaphore(MAXCONCURRENT)

    async with aiohttp.ClientSession() as session:
        indexdata = await fetch_json(session, BASEURL, semaphore)
        if not indexdata or "results" not in indexdata:
            print("Failed to return.")
            return []

        tasks = [fetch_json(session, item["url"], semaphore) for item in indexdata["results"]]
        results = await asyncio.gather(*tasks)
        pokemon_db = {}
        for detail in results:
            if detail:
                name = detail.get("name", "").title()
                if name:
                    pokemon_db[name] = {
                        "name": detail.get("name"),
                        "height": detail.get("height"),
                        "weight": detail.get("weight"),
                        "base_experience": detail.get("base_experience"),
                        "types": [t["type"]["name"] for t in detail.get("types", [])]
                    }
        return pokemon_db
    
def poke_random(pokemon_db):
    random_pokemon, pokeinfo = random.choice(list(pokemon_db.items()))
    print("-----POKEDLE!-----")
    while True:
        guess = input("Guess a pokemon: ").strip().title()

        if guess not in pokemon_db:
            print("Loser! Try again!")
            continue
        guessed = pokemon_db[guess]
        types = guessed["types"]
        types_correct = pokeinfo["types"]
        if guess == random_pokemon.title():
             print(f"Correct! \n")
             print(f"Name: {Back.GREEN}{random_pokemon.title()}{Style.RESET_ALL}, Height:  {Back.GREEN}{guessed["height"]}{Style.RESET_ALL}, "
                f"Weight: {Back.GREEN}{guessed["weight"]}{Style.RESET_ALL}, Base XP: {Back.GREEN}{guessed["base_experience"]}{Style.RESET_ALL}, "
                f"Types: {Back.GREEN}{", ".join(types)}{Style.RESET_ALL}")
             break
        elif guess in pokemon_db:
            print("Not quite!")
            p_height_final = f"{Back.GREEN}{guessed["height"]/10}m{Style.RESET_ALL}" if guessed["height"] == pokeinfo["height"] else f"{Back.RED}{guessed["height"]/10}m{Style.RESET_ALL}"
            p_weight_final = f"{Back.GREEN}{guessed["weight"]/10}kg{Style.RESET_ALL}" if guessed["weight"] == pokeinfo["weight"] else f"{Back.RED}{guessed["weight"]/10}kg{Style.RESET_ALL}"
            p_xp_final = f"{Back.GREEN}{guessed["base_experience"]}{Style.RESET_ALL}" if guessed["base_experience"] == pokeinfo["base_experience"] else f"{Back.RED}{guessed["base_experience"]}{Style.RESET_ALL}"
            colored_types = []
            for type_name in types:
                    if type_name in types_correct:
                        colored_types.append(f"{Back.GREEN}{type_name.title()}{Style.RESET_ALL}")
                    else:
                        colored_types.append(f"{Back.RED}{type_name.title()}{Style.RESET_ALL}")
            p_types_final = ", ".join(colored_types)
            print(f"Name: {guess}, Height: {p_height_final}, Weight: {p_weight_final}, Base Experience: {p_xp_final}, Types: {p_types_final}")
            continue

async def main():
    print("Fetching Pokemon API Data...")
    pokemon_db = await load_data()

    if pokemon_db:
        poke_random(pokemon_db)

if __name__ == "__main__":
    asyncio.run(main())
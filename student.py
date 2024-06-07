import asyncio
import getpass
import json
import os
import websockets
from consts import Direction
from characters import *
import random


def agent_getRocks(digdug, rocks):
    dists = {}
    for rock in rocks:
        dist = abs(rock["pos"][0] - digdug[0]) + abs(rock["pos"][1] - digdug[1])
        dists[tuple(rock["pos"])] = dist

    rockpos = min(dists, key=dists.get)
    rockdist = dists[rockpos]
    return rockpos, rockdist

def agent_updateifrock(instruction, digdug, rockpos):
    if instruction["key"] == "a" and (digdug[0] == rockpos[0]+1) and (digdug[1] == rockpos[1]):
        instruction["key"] = random.choice(["w", "s","a"])
    elif instruction["key"] == "d" and (digdug[0] == rockpos[0]-1) and (digdug[1] == rockpos[1]):
        instruction["key"] = random.choice(["w", "s","d"])
    elif instruction["key"] == "w" and (digdug[0] == rockpos[0]) and (digdug[1] == rockpos[1]+1):
        instruction["key"] = random.choice(["w", "d","a"])
    elif instruction["key"] == "s" and (digdug[0] == rockpos[0]) and (digdug[1] == rockpos[1]-1):
        instruction["key"] = random.choice(["a", "d","s"])

def agent_wheretoShoot(digdug, enemy):
    x, y = enemy[0] - digdug[0], enemy[1] - digdug[1]

    if abs(y) > abs(x):
        aim = 's' if digdug[1] < enemy[1] else 'w'
        run = 'w' if aim == 's' else 's' 
    else:
        aim = 'd' if digdug[0] < enemy[0] else 'a'
        run = 'a' if aim == 'd' else 'd'
    return aim, run
 
def agent_distancehelp(aim, current_aim, run, listDir, enemyDir):
    if aim != current_aim:
        if run == listDir[enemyDir]:
            safe = set(listDir) - {aim, run}
            instruction = safe.pop()
        else: 
            instruction = run
    else:
        instruction = "A"
    return instruction

def agent_distance(aim, current_aim, run, listDir, enemyDir, enemies, digdug):
    if len(enemies)>1: 
        enemy1 = enemies[1]["pos"] 
        dx, dy = abs(enemy1[0] - digdug[0]), abs(enemy1[1] - digdug[1])
        distance = dx + dy 
        if (distance == 1):
            aimaux = agent_wheretoShoot(digdug, enemy1)
            if aim != current_aim or aimaux != current_aim:
                if run == listDir[enemyDir]:
                    safe = set(listDir) - {aim, run}
                    instruction = safe.pop()
                else: 
                    instruction = run
            else:
                instruction = "A"
        else:
            return agent_distancehelp(aim, current_aim, run, listDir, enemyDir)
    else:
        return agent_distancehelp(aim, current_aim, run, listDir, enemyDir)
    return instruction

async def agent_loop(server_address="localhost:8000", agent_name="student"):
    async with websockets.connect(f"ws://{server_address}/player") as websocket:
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))
        instruction = {"cmd": "key", "key": "key"}
        current_aim = "" # initial aim, not existing, used to compare with aim
        listDir = ["w","d","s","a"] # list of directions 

        while True:
            try:
                state = json.loads(await websocket.recv())
                enemies = [
                    {
                        "pos": enemy["pos"],
                        "type": enemy["name"],
                        "dir": enemy["dir"],
                        "transverse": enemy.get("traverse"),
                        "name": enemy["name"],
                    }
                    for enemy in state.get("enemies", [])
                ]

                if enemies:
                    digdug = state["digdug"] # get dig pos
                    rocks = state['rocks'] # get rocks pos
                    rockpos, rockDistance = agent_getRocks(digdug, rocks)
                    enemies = sorted(enemies, key=lambda enemy: abs(enemy["pos"][0] - digdug[0]) + abs(enemy["pos"][1] - digdug[1]))
                    first = enemies[0]
                    enemy = first["pos"]
                    enemyName = first['name']
                    enemyDir = first["dir"]
                    transversing = first["transverse"]

                    x = abs(enemy[0] - digdug[0])
                    y = abs(enemy[1] - digdug[1])
                    distance = x + y

                    aim, run = agent_wheretoShoot(digdug, enemy)

                    if (distance <= 3 and transversing):
                        instruction["key"] = run 
                    elif distance == 1:
                        instruction["key"] = agent_distance(aim, current_aim, run, listDir, enemyDir, enemies, digdug)
                    elif distance <= 3 and aim != current_aim and current_aim == run == listDir[enemyDir]:
                        if enemyDir == 0:
                            instruction["key"] = "d"
                        elif enemyDir == 1:
                            instruction["key"] = "w"
                        elif enemyDir == 2:
                            instruction["key"] = "a"
                        elif enemyDir == 3:
                            instruction["key"] = "s"
                    elif x <= 3 and y == 0:
                        if aim != current_aim:
                            instruction["key"] = aim
                        else:
                            instruction["key"] = "A"
                    elif y <= 3 and x == 0:
                        if aim != current_aim:
                            instruction["key"] = aim
                        else:
                            instruction["key"] = "A"
                    elif (enemyName == "Pooka" and digdug[0] == enemy[0]-1 and distance <= 8):
                        instruction["key"] = "A"
                    elif enemyName == "Pooka" and digdug[0] == enemy[0]+1 and distance <= 8:
                        instruction["key"] = "A"
                    elif enemyName == "Pooka" and digdug[1] == enemy[1]-1 and distance <= 8:
                        instruction["key"] = "A"
                    elif enemyName == "Pooka" and digdug[1] == enemy[1]+1 and distance <= 8:
                        instruction["key"] = "A"
                    elif digdug[0] == enemy[0]-1 and distance <= 2:
                        instruction["key"] = "A"
                    elif digdug[0] == enemy[0]+1 and distance <= 2:
                        instruction["key"] = "A"
                    else:
                        x = enemy[0] - digdug[0]
                        y = enemy[1] - digdug[1]
                        if enemyName != "Fygar":
                            if abs(x) > abs(y):
                                instruction["key"] = "d" if x > 0 else "a"
                            else:
                                instruction["key"] = "s" if y > 0 else "w"
                        else:
                            if y == 0:
                                instruction["key"] = "w" if y > 0 else "s"
                            elif x != 0:
                                instruction["key"] = "d" if x > 0 else "a"
                            else:
                                instruction["key"] = "s" if y > 0 else "w"
                    if rockDistance == 1:
                        agent_updateifrock(instruction, digdug, rockpos)
                    
                if instruction["key"] != "A":
                    current_aim = instruction["key"]
 
                direcao = {"cmd": "key", "key": instruction["key"]} 
                await websocket.send(json.dumps(direcao))
                    
            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                return
    
#DO NOT CHANGE THE LINES BELOW
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))   

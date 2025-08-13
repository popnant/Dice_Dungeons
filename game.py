import pygame
import random
import sys
import pickle
import os

pygame.init()
pygame.mixer.init() # Initialize the mixer

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("RPG Dungeon Game")
font = pygame.font.Font(None, 36)
# โหลดภาพตัวละครตามคลาส
player_images = {
    "Warrior": pygame.image.load("assets/players/warrior.png"),
    "Mage": pygame.image.load("assets/players/mage.png"),
    "Rogue": pygame.image.load("assets/players/rogue.png")
}

# โหลดภาพศัตรูตามชื่อ
enemy_images = {
    "Goblin": pygame.image.load("assets/enemies/goblin.png"),
    "Skeleton": pygame.image.load("assets/enemies/skeleton.png"),
    "Orc": pygame.image.load("assets/enemies/orc.png"),
    "Ghost": pygame.image.load("assets/enemies/ghost.png"),
    "Dragon": pygame.image.load("assets/enemies/dragon.png"),
    "BOSS DEMON": pygame.image.load("assets/enemies/boss_demon.png"),
}

# --- ตั้งค่าหน้าจอ ---
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("RPG Dungeon Turn-Based")

# --- สี ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW= (255, 255, 0)
CYAN  = (0, 255, 255)
GREY  = (100, 100, 100)
BLUE  = (0, 100, 255)
PURPLE= (128, 0, 128)

# --- ฟอนต์ ---
font = pygame.font.SysFont("arial", 24)

# --- โหลดภาพเต๋า (ถ้ามีไฟล์จริง) ---
dice_images = []
for i in range(1,7):
    try:
        img = pygame.image.load(f"assets/dice_{i}.png")
        img = pygame.transform.scale(img, (64,64))
    except:
        img = pygame.Surface((64,64))
        img.fill(GREY)
        pygame.draw.rect(img, BLACK, img.get_rect(), 3)
        text = font.render(str(i), True, BLACK)
        img.blit(text, (24, 15))
    dice_images.append(img)

# --- โหลดไฟล์เสียง (แก้ไข path ให้ตรงกับไฟล์ของคุณ) ---
try:
    bg_music = pygame.mixer.Sound("assets/sounds/dungeon_theme.mp3")
    battle_music = pygame.mixer.Sound("assets/sounds/battle_theme.mp3")
except pygame.error as e:
    print(f"Error loading sound files: {e}")
    bg_music = None
    battle_music = None

# --- Player Class ---
class Player:
    def __init__(self, char_class):
        self.char_class = char_class

        if char_class == "Warrior":
            self.hp = 150
            self.mp = 20
            self.attack = 15
            self.magic = 5
            self.mana_regen = 5
        elif char_class == "Mage":
            self.hp = 80
            self.mp = 80
            self.attack = 5
            self.magic = 20
            self.mana_regen = 5
        elif char_class == "Rogue":
            self.hp = 90
            self.mp = 40
            self.attack = 12
            self.magic = 8
            self.mana_regen = 5
        else:
            self.hp = 100
            self.mp = 30
            self.attack = 10
            self.magic = 10
            self.mana_regen = 5

        self.max_hp = self.hp
        self.max_mp = self.mp

    def regen_mana(self):
        self.mp = min(self.max_mp, self.mp + self.mana_regen)

# --- Enemy Class ---
class Enemy:
    def __init__(self, name, hp, attack):
        self.name = name
        self.hp = hp
        self.attack = attack
        self.poison_turns = 0
        self.burn_turns = 0

# --- ตัวแปรเกม ---
player_pos = [0,0]
player = None
player_hp = 0
player_mp = 0
player_max_hp = 0
player_max_mp = 0
keys_collected = 0
inventory = []
game_state = "start_screen"
current_enemies = []
enemy_index = 0
meat_buff_turns = 0
player_image = None
player_rect = None
player_class = None
player_speed = 5
current_music = None

def play_music(music_file, loop=True):
    global current_music
    if current_music != music_file:
        if music_file:
            pygame.mixer.stop()
            music_file.play(-1 if loop else 0)
            current_music = music_file
        else:
            pygame.mixer.stop()
            current_music = None

def draw_text(text, font, color, surface, x, y):
    textobj = font.render(text, True, color)
    textrect = textobj.get_rect()
    textrect.topleft = (x, y)
    surface.blit(textobj, textrect)
# --- สร้างแผนที่ดันเจี้ยน ---
dungeon_map = {}
empty_rooms = []
boss_room = None

def create_new_dungeon():
    global dungeon_map, empty_rooms, boss_room, player_pos
    dungeon_map = {}
    empty_rooms = []
    for x in range(8):
        for y in range(8):
            dungeon_map[(x,y)] = {
                "enemy": [],
                "trap": False,
                "item": None,
                "visited": False
            }
            empty_rooms.append((x,y))

    # --- วางบอส ---
    boss_room = random.choice(empty_rooms)
    dungeon_map[boss_room]["enemy"].append(Enemy("BOSS DEMON", 120, 25))
    empty_rooms.remove(boss_room)

    # --- กำหนดโอกาสเกิดของศัตรู (เป็นเปอร์เซ็นต์) ---
    enemy_spawn_list = [
        {"name": "Goblin", "hp": 40, "attack": 10, "weight": 40},
        {"name": "Skeleton", "hp": 30, "attack": 20, "weight": 30},
        {"name": "Orc", "hp": 50, "attack": 30, "weight": 10},
        {"name": "Ghost", "hp": 30, "attack": 25, "weight": 15},
        {"name": "Dragon", "hp": 100, "attack": 40, "weight": 5}
    ]
    
    enemy_names = [e["name"] for e in enemy_spawn_list]
    enemy_weights = [e["weight"] for e in enemy_spawn_list]
    enemy_templates = {e["name"]: Enemy(e["name"], e["hp"], e["attack"]) for e in enemy_spawn_list}

    # --- วางศัตรูในห้อง (1-3 ตัว) ---
    for pos in random.sample(empty_rooms, 12):
        num_enemies = random.randint(1,3)
        
        # สุ่มศัตรูตามน้ำหนักที่กำหนด
        spawned_enemies = random.choices(enemy_names, weights=enemy_weights, k=num_enemies)
        
        dungeon_map[pos]["enemy"] = [Enemy(e, enemy_templates[e].hp, enemy_templates[e].attack) for e in spawned_enemies]


    # --- วางกับดัก ---
    for pos in random.sample(empty_rooms, 10):
        dungeon_map[pos]["trap"] = True

    # --- วางกุญแจ 3 ดอก ---
    key_rooms = random.sample(empty_rooms, 3)
    for pos in key_rooms:
        dungeon_map[pos]["item"] = "Key"
        empty_rooms.remove(pos)

    # --- วาง Potion และ Meat ---
    for pos in empty_rooms:
        if random.random() < 0.4:
            dungeon_map[pos]["item"] = "Potion"
    for pos in empty_rooms:
        if random.random() < 0.2:
            dungeon_map[pos]["item"] = "Meat"
    # --- วาง Mana Potion ---
    for pos in empty_rooms:
        if random.random() < 0.4:
            dungeon_map[pos]["item"] = "Mana Potion"
    
    player_pos = [0,0]
    
create_new_dungeon()

# --- ฟังก์ชันช่วยเหลือ ---
def draw_text(text, x, y, color=WHITE):
    screen.blit(font.render(text, True, color), (x, y))

def draw_hp_bar(x, y, current, max_hp, width=100, height=15):
    pygame.draw.rect(screen, RED, (x, y, width, height))
    green_width = max(0, int(width * current / max_hp))
    pygame.draw.rect(screen, GREEN, (x, y, green_width, height))

def draw_mp_bar(x, y, current, max_mp, width=100, height=10):
    pygame.draw.rect(screen, GREY, (x, y, width, height))
    blue_width = max(0, int(width * current / max_mp))
    pygame.draw.rect(screen, BLUE, (x, y, blue_width, height))

def draw_dice(x, y, dice_value):
    if 1 <= dice_value <= 6:
        screen.blit(dice_images[dice_value-1], (x,y))

def dice_roll():
    return random.randint(1, 6)

def draw_player_and_map():
    tile_size = 64
    for x in range(8):
        for y in range(8):
            rect = pygame.Rect(x*tile_size, y*tile_size, tile_size, tile_size)
            color = (50,50,50) if dungeon_map[(x,y)]["visited"] else (20,20,20)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, WHITE, rect, 1)

    # วาดตำแหน่งผู้เล่น
    px = player_pos[0] * tile_size + (tile_size - player_image.get_width()) // 2
    py = player_pos[1] * tile_size + (tile_size - player_image.get_height()) // 2
    screen.blit(player_image, (px, py))

def show_enemy_icon(enemy, x, y):
    # วาดภาพศัตรู
    if enemy.name in enemy_images:
        img = pygame.transform.scale(enemy_images[enemy.name], (64, 64))
        screen.blit(img, (x+16, y+16))
    
    # แสดงสถานะผิดปกติ
    if enemy.burn_turns > 0:
        draw_text(f"🔥", x + 80, y + 20, RED)
    if enemy.poison_turns > 0:
        draw_text(f"💀", x + 80, y + 40, GREEN)

# --- หน้าจอ Game Over ---
def game_over_screen():
    global game_state
    play_music(None)
    screen.fill(BLACK)
    draw_text("💀 You died! Game Over!", 280, 280, RED)
    draw_text("Press 'R' to Restart or 'Q' to Quit", 250, 320, WHITE)
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game_state = "start_screen"
                    return
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()


# --- หน้าจอเริ่มเกม ---
def start_game_screen():
    global game_state, player, player_hp, player_mp, player_max_hp, player_max_mp, keys_collected, inventory, meat_buff_turns, player_image, enemy_index
    running = True
    play_music(None)
    while running:
        screen.fill(BLACK)
        draw_text("Drice Dungeon", 290, 150, CYAN)
        draw_text("Press any key to start", 265, 250, WHITE)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                game_state = "class_select"
                # Reset game variables
                player = None
                player_hp = 0
                player_mp = 0
                player_max_hp = 0
                player_max_mp = 0
                keys_collected = 0
                inventory = []
                current_enemies = []
                enemy_index = 0
                meat_buff_turns = 0
                player_image = None
                create_new_dungeon()
                return

# --- ระบบเลือกคลาส ---
def class_selection_screen():
    global player, player_hp, player_max_hp, player_mp, player_max_mp, game_state, player_image
    selecting = True
    play_music(None)
    while selecting:
        screen.fill(BLACK)
        draw_text("Select Your Class:", 300, 150, WHITE)
        draw_text("1) Warrior (HP: 120, MP: 20)", 280, 190, GREEN)
        draw_text("2) Mage    (HP: 70,  MP: 80)", 280, 220, BLUE)
        draw_text("3) Rogue   (HP: 90,  MP: 40)", 280, 250, YELLOW)
        draw_text("Press Q to Quit", 320, 300, RED)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    player = Player("Warrior")
                    selecting = False
                    player_image = pygame.transform.scale(player_images["Warrior"], (64, 64))
                elif event.key == pygame.K_2:
                    player = Player("Mage")
                    selecting = False
                    player_image = pygame.transform.scale(player_images["Mage"], (64, 64))
                elif event.key == pygame.K_3:
                    player = Player("Rogue")
                    selecting = False
                    player_image = pygame.transform.scale(player_images["Rogue"], (64, 64))
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

    player_hp = player.hp
    player_max_hp = player.max_hp
    player_mp = player.mp
    player_max_mp = player.max_mp
    return "exploration"

# --- การย้ายผู้เล่น ---
def move_player(dx, dy):
    global player_pos
    nx, ny = player_pos[0]+dx, player_pos[1]+dy
    if 0 <= nx < 8 and 0 <= ny < 8:
        player_pos[0], player_pos[1] = nx, ny

# --- เช็คเหตุการณ์ห้อง ---
def check_room_event():
    global keys_collected, player_hp, game_state, current_enemies, enemy_index, inventory, meat_buff_turns
    
    play_music(bg_music) # เล่นเพลงพื้นหลังเมื่ออยู่ในโหมดสำรวจ

    room = dungeon_map[tuple(player_pos)]
    room["visited"] = True

    # ตรวจสอบบอสต้องมีกุญแจครบก่อนเข้า
    if tuple(player_pos) == boss_room and keys_collected < 3:
        screen.fill(BLACK)
        draw_text("🚫 Need 3 keys to enter the Boss room!", 200, 280, RED)
        pygame.display.flip()
        pygame.time.delay(1500)
        # เดินกลับห้องเก่า
        return False

    # กับดัก
    if room["trap"]:
        damage = random.randint(1,5)
        player_hp -= damage
        screen.fill(BLACK)
        draw_text(f"💥 Trap! You take {damage} damage!", 50, 50, RED)
        pygame.display.flip()
        pygame.time.delay(1200)
        room["trap"] = False

    # เก็บไอเทม
    if room["item"]:
        inventory.append(room["item"])
        if room["item"] == "Key":
            keys_collected += 1
        screen.fill(BLACK)
        draw_text(f"🎁 Found {room['item']}!", 50, 90, YELLOW)
        pygame.display.flip()
        pygame.time.delay(1000)
        room["item"] = None

    # เจอศัตรู
    if room["enemy"]:
        current_enemies.clear()
        for e in room["enemy"]:
            current_enemies.append(Enemy(e.name, e.hp, e.attack))
        enemy_index = 0
        room["enemy"] = []
        game_state = "battle"
        play_music(battle_music) # สลับไปเล่นเพลงต่อสู้
        
    return True

# --- ใช้ไอเท็ม ---
def use_item(item_name):
    global player_hp, player_mp, meat_buff_turns, inventory
    if item_name == "Potion":
        if "Potion" in inventory:
            if player_hp < player_max_hp:
                player_hp = min(player_hp + 30, player_max_hp)
                inventory.remove("Potion")
                return f"🧪 Used Potion! +30 HP"
            else:
                return f"💬 HP already full!"
        else:
            return f"❌ No Potion!"

    elif item_name == "Mana Potion":
        if "Mana Potion" in inventory:
            if player_mp < player_max_mp:
                player_mp = min(player_mp + 20, player_max_mp)
                inventory.remove("Mana Potion")
                return f"✨ Used Mana Potion! +20 MP"
            else:
                return f"💬 MP already full!"
        else:
            return f"❌ No Mana Potion!"

    elif item_name == "Meat":
        if "Meat" in inventory:
            meat_buff_turns = 3
            inventory.remove("Meat")
            return f"🍖 Used Meat! +10 Damage 3 turns"
        else:
            return f"❌ No Meat!"
    return ""

# --- ระบบต่อสู้ ---
def battle_screen():
    global player_hp, player_mp, player_max_hp, player_max_mp
    global current_enemies, game_state, enemy_index, meat_buff_turns, player_mp
    
    player_dice = None
    enemy_dice = None
    dodge_dice = None
    message = ""

    while True:
        screen.fill(BLACK)
        
        # Check if all enemies in the room are defeated
        if enemy_index >= len(current_enemies):
            # Check for win condition
            if tuple(player_pos) == boss_room:
                draw_text("🎉 CONGRATULATIONS! You defeated the boss!", 50, 280, YELLOW)
                draw_text("🎉 YOU WIN!", 300, 320, YELLOW)
                pygame.display.flip()
                pygame.time.delay(5000)
                game_state = "start_screen"
                play_music(None)
                return
            else:
                draw_text(f"🏆 You defeated all enemies in this room!", 220, 280, GREEN)
                pygame.display.flip()
                pygame.time.delay(3000)
                game_state = "exploration"
                play_music(bg_music) # สลับกลับไปเพลงพื้นหลัง
                return
        
        enemy = current_enemies[enemy_index]
        
        # Draw all UI elements for the battle
        show_enemy_icon(enemy, 50, 80)
        draw_text(f"{enemy.name} (HP: {enemy.hp})", 50, 170, RED)
        draw_text(f"Player HP: {player_hp}/{player_max_hp}", 400, 50, GREEN)
        draw_hp_bar(400, 80, player_hp, player_max_hp)
        draw_text(f"Player MP: {player_mp}/{player_max_mp}", 400, 110, BLUE)
        draw_mp_bar(400, 140, player_mp, player_max_mp)
        
        if player.char_class == "Warrior":
            draw_text("1) Normal Attack (DMG 10, roll >= 2)", 50, 220)
            draw_text("2) Heavy Attack (DMG 50, roll >= 3, -5 HP)", 50, 250)
            draw_text("3) Special Attack (DMG 70, roll >= 5)", 50, 280)
        elif player.char_class == "Mage":
            draw_text("1) Magic Attack (DMG 20, roll >= 2, -10 MP)", 50, 220)
            draw_text("2) Special Magic (DMG 60, roll >= 4, -35 MP)", 50, 250)
            draw_text("3) Fire Magic (DMG 40, roll >= 4, -20 MP, Burn)", 50, 280)
        elif player.char_class == "Rogue":
            draw_text("1) Normal Attack (DMG 35, roll >= 2)", 50, 220)
            draw_text("2) Quick Attack (DMG 10, roll >= 1)", 50, 250)
            draw_text("3) Poison Attack (DMG 30, roll >= 4, Poison)", 50, 280)
        
        draw_text("4) Use Potion", 50, 310)
        draw_text("5) Use Meat", 50, 340)
        draw_text("6) Use Mana Potion", 50, 370)
        draw_text(f"Inventory: {', '.join(inventory)}", 50, 420)
        draw_text(f"Damage buff turns left: {meat_buff_turns}", 50, 450)
        
        # Display dice rolls
        if player_dice is not None:
            draw_text(f"Your Roll: {player_dice}", 550, 220, YELLOW)
            draw_dice(550, 240, player_dice)
        if enemy_dice is not None:
            draw_text(f"Enemy Roll: {enemy_dice}", 550, 300, YELLOW)
            draw_dice(550, 320, enemy_dice)
        if dodge_dice is not None:
            draw_text(f"Dodge Roll: {dodge_dice}", 550, 380, YELLOW)
            draw_dice(550, 400, dodge_dice)

        if message:
            draw_text(message, 50, 500, WHITE)
            
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                damage = 0
                player_dice = None
                enemy_dice = None
                dodge_dice = None
                action_taken = False
                message = ""
                
                # Universal actions
                if event.key == pygame.K_4:
                    message = use_item("Potion")
                    action_taken = True
                elif event.key == pygame.K_5:
                    message = use_item("Meat")
                    action_taken = True
                elif event.key == pygame.K_6:
                    message = use_item("Mana Potion")
                    action_taken = True

                # Warrior attacks
                elif player.char_class == "Warrior":
                    if event.key == pygame.K_1:
                        player_dice = dice_roll()
                        if player_dice >= 2:
                            damage = 10
                            if meat_buff_turns > 0: damage += 10; meat_buff_turns -= 1
                            enemy.hp -= damage
                            message = f"You hit {enemy.name} for {damage} damage!"
                        else:
                            message = "Your attack missed!"
                        action_taken = True
                    elif event.key == pygame.K_2:
                        if player_hp > 5:
                            player_dice = dice_roll()
                            player_hp -= 5
                            if player_dice >= 3:
                                damage = 50
                                if meat_buff_turns > 0: damage += 10; meat_buff_turns -= 1
                                enemy.hp -= damage
                                message = f"You perform a Heavy Attack and hit {enemy.name} for {damage} damage!"
                            else:
                                message = "Your Heavy Attack missed!"
                            action_taken = True
                        else:
                            message = "Not enough HP for Heavy Attack!"
                    elif event.key == pygame.K_3:
                        player_dice = dice_roll()
                        if player_dice >= 5:
                            damage = 70
                            if meat_buff_turns > 0: damage += 10; meat_buff_turns -= 1
                            enemy.hp -= damage
                            message = f"You perform a Special Attack and hit {enemy.name} for {damage} damage!"
                        else:
                            message = "Your Special Attack missed!"
                        action_taken = True
                
                # Mage attacks
                elif player.char_class == "Mage":
                    if event.key == pygame.K_1:
                        if player_mp >= 10:
                            player_dice = dice_roll()
                            player.mp -= 10
                            player_mp = player.mp
                            if player_dice >= 2:
                                damage = 20
                                if meat_buff_turns > 0: damage += 10; meat_buff_turns -= 1
                                enemy.hp -= damage
                                message = f"You cast Magic Attack and hit {enemy.name} for {damage} damage!"
                            else:
                                message = "Your Magic Attack missed!"
                            action_taken = True
                        else:
                            message = "Not enough MP for Magic Attack!"
                    elif event.key == pygame.K_2:
                        if player_mp >= 35:
                            player_dice = dice_roll()
                            player.mp -= 35
                            player_mp = player.mp
                            if player_dice >= 4:
                                damage = 60
                                if meat_buff_turns > 0: damage += 10; meat_buff_turns -= 1
                                enemy.hp -= damage
                                message = f"You cast Special Magic and hit {enemy.name} for {damage} damage!"
                            else:
                                message = "Your Special Magic missed!"
                            action_taken = True
                        else:
                            message = "Not enough MP for Special Magic!"
                    elif event.key == pygame.K_3:
                        if player_mp >= 20:
                            player_dice = dice_roll()
                            player.mp -= 20
                            player_mp = player.mp
                            if player_dice >= 4:
                                damage = 40
                                if meat_buff_turns > 0: damage += 10; meat_buff_turns -= 1
                                enemy.hp -= damage
                                enemy.burn_turns = 4
                                message = f"You cast Fire Magic! {enemy.name} is now burning!"
                            else:
                                message = "Your Fire Magic missed!"
                            action_taken = True
                        else:
                            message = "Not enough MP for Fire Magic!"

                # Rogue attacks
                elif player.char_class == "Rogue":
                    if event.key == pygame.K_1:
                        player_dice = dice_roll()
                        if player_dice >= 2:
                            damage = 35
                            if meat_buff_turns > 0: damage += 10; meat_buff_turns -= 1
                            enemy.hp -= damage
                            message = f"You hit {enemy.name} for {damage} damage!"
                        else:
                            message = "Your attack missed!"
                        action_taken = True
                    elif event.key == pygame.K_2:
                        player_dice = dice_roll()
                        if player_dice >= 1: # Always hits
                            damage = 10
                            if meat_buff_turns > 0: damage += 10; meat_buff_turns -= 1
                            enemy.hp -= damage
                            message = f"You perform a Quick Attack and hit {enemy.name} for {damage} damage!"
                        action_taken = True
                    elif event.key == pygame.K_3:
                        player_dice = dice_roll()
                        if player_dice >= 4:
                            damage = 30
                            if meat_buff_turns > 0: damage += 10; meat_buff_turns -= 1
                            enemy.hp -= damage
                            enemy.poison_turns = 3
                            message = f"You perform a Poison Attack! {enemy.name} is now poisoned!"
                        else:
                            message = "Your Poison Attack missed!"
                        action_taken = True

                # Enemy turn
                if action_taken:
                    # Check if enemy is defeated
                    if enemy.hp <= 0:
                        screen.fill(BLACK)
                        draw_text(f"You defeated {enemy.name}!", 50, 500, CYAN)
                        pygame.display.flip()
                        pygame.time.delay(1500)
                        enemy_index += 1
                        if enemy_index >= len(current_enemies):
                            if tuple(player_pos) == boss_room:
                                # This block will be handled by the main battle loop check
                                pass
                            else:
                                game_state = "exploration"
                                play_music(bg_music)
                                return
                    else:
                        enemy_dice = dice_roll()
                        dodge_dice = dice_roll()
                        if enemy_dice > dodge_dice:
                            damage_to_player = enemy.attack + random.randint(0, 5)
                            player_hp -= damage_to_player
                            message += f"\nEnemy hits you for {damage_to_player} damage!"
                        else:
                            message += "\nYou dodged the enemy attack!"

                    # Apply status effects and regen mana
                    player.regen_mana()
                    player_mp = player.mp
                    
                    if enemy.burn_turns > 0:
                        burn_damage = 7
                        enemy.hp -= burn_damage
                        enemy.burn_turns -= 1
                        message += f"\n🔥 Burn deals {burn_damage} damage to {enemy.name}!"
                    
                    if enemy.poison_turns > 0:
                        poison_damage = 10
                        enemy.hp -= poison_damage
                        enemy.poison_turns -= 1
                        message += f"\n💀 Poison deals {poison_damage} damage to {enemy.name}!"

                    # Check again if enemy is defeated after status effects
                    if enemy.hp <= 0:
                        screen.fill(BLACK)
                        draw_text(f"You defeated {enemy.name}!", 50, 500, CYAN)
                        pygame.display.flip()
                        pygame.time.delay(1500)
                        enemy_index += 1
                        if enemy_index >= len(current_enemies):
                            if tuple(player_pos) == boss_room:
                                # This block will be handled by the main battle loop check
                                pass
                            else:
                                game_state = "exploration"
                                play_music(bg_music)
                                return

        # Check for game over
        if player_hp <= 0:
            game_over_screen()
            return

# --- Main Loop ---
game_state = "start_screen"
play_music(None) # หยุดเพลงเมื่อเริ่มเกม

while True:
    if game_state == "start_screen":
        start_game_screen()
    elif game_state == "class_select":
        game_state = class_selection_screen()
    elif game_state == "exploration":
        play_music(bg_music) # ตรวจสอบและเล่นเพลงพื้นหลัง
        screen.fill(BLACK)
        draw_text(f"Position: {player_pos}", 600, 40)
        draw_player_and_map()
        draw_text(f"HP: {player_hp}/{player_max_hp}", 520, 500, GREEN)
        draw_hp_bar(520, 530, player_hp, player_max_hp)
        draw_text(f"MP: {player_mp}/{player_max_mp}", 520, 560, BLUE)
        draw_mp_bar(520, 590, player_mp, player_max_mp)
        draw_text(f"Keys: {keys_collected} / 3", 50, 540, YELLOW)
        draw_text("Inventory: " + ", ".join(inventory), 50, 560, CYAN)
        draw_text("Arrow keys to move, Q=Quit", 550, 10, WHITE)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                old_pos = player_pos[:]
                if event.key == pygame.K_LEFT:
                    move_player(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    move_player(1, 0)
                elif event.key == pygame.K_UP:
                    move_player(0, -1)
                elif event.key == pygame.K_DOWN:
                    move_player(0, 1)
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

                if old_pos != player_pos:
                    valid = check_room_event()
                    if not valid:
                        player_pos[:] = old_pos  # กลับตำแหน่งเดิม

    elif game_state == "battle":
        play_music(battle_music) # ตรวจสอบและเล่นเพลงต่อสู้
        battle_screen()
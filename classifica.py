import socket
import threading
import pygame
import re
import random  # Per generare elementi grafici del terreno
import time    # Per gestire l'aggiornamento temporizzato della velocità

# Impostazioni per il socket UDP
#213.209.192.164
UDP_IP = "0.0.0.0"
UDP_PORT = 4141

# Crea il socket UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# Struttura dati condivisa per memorizzare la classifica
standings = []
standings_lock = threading.Lock()

def receive_packets():
    """Funzione in un thread separato per ricevere pacchetti UDP."""
    while True:
        data, addr = sock.recvfrom(1024)
        packet = data.decode('utf-8')
        parse_packet(packet)

def parse_packet(packet):
    """Analizza il pacchetto ricevuto e aggiorna la classifica."""
    global standings
    if not packet.startswith('CLASSIFICA'):
        return
    # Rimuove 'CLASSIFICA' dal pacchetto
    packet = packet[len('CLASSIFICA'):]
    # Rimuove eventuali virgole iniziali
    packet = packet.lstrip(',')
    # Estrae i campi usando le espressioni regolari
    fields = re.findall(r'\(([^)]+)\)', packet)
    new_standings = []
    for field in fields:
        parts = field.split(',')
        if len(parts) != 6:
            continue
        horse_id_str, distance_or_name_str, meters_to_finish_str, y_coordinate_str, speed_str, time_str = parts
        try:
            horse_id = int(horse_id_str)
        except ValueError:
            continue
        distance_or_name = distance_or_name_str.strip()
        try:
            meters_to_finish = float(meters_to_finish_str)
        except ValueError:
            continue
        try:
            y_coordinate = float(y_coordinate_str)
        except ValueError:
            continue
        # Gestisce 'distance' e 'last one'
        if distance_or_name.lower() == 'last one':
            distance = None
        else:
            try:
                distance = float(distance_or_name)
            except ValueError:
                distance = None  # Dati non validi
        try:
            speed = float(speed_str)
        except ValueError:
            speed = None  # Dati non validi
        new_standings.append({
            'horse_id': horse_id,
            'distance': distance,  # Gap rispetto al cavallo successivo (dietro)
            'distance_or_name': distance_or_name,
            'meters_to_finish': meters_to_finish,
            'y_coordinate': y_coordinate,
            'speed': speed
            # Campo 'time' rimosso
        })
    # Aggiorna la classifica in modo thread-safe
    with standings_lock:
        standings = new_standings

# Avvia il thread per ricevere pacchetti UDP
udp_thread = threading.Thread(target=receive_packets)
udp_thread.daemon = True
udp_thread.start()

# Inizializza Pygame
pygame.init()

# Impostazioni della finestra
WINDOW_WIDTH = 1920  # Larghezza totale della finestra
WINDOW_HEIGHT = 1080
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.NOFRAME)
pygame.display.set_caption('Classifica Corse Cavalli')

# Aumenta la risoluzione di rendering
RENDER_SCALE = 4  # Aumenta questo valore per una definizione più alta
RENDER_WIDTH = WINDOW_WIDTH * RENDER_SCALE
RENDER_HEIGHT = WINDOW_HEIGHT * RENDER_SCALE

# Crea una superficie ad alta risoluzione
render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))

# Impostazioni dei font
font = pygame.font.Font(None, int(24 * RENDER_SCALE))
large_font = pygame.font.Font(None, int(48 * RENDER_SCALE))  # Per testo più grande

# Costanti di posizionamento scalate
LEFT_PANEL_WIDTH = int(250 * RENDER_SCALE)  # Larghezza del pannello sinistro
TRACK_START_X = LEFT_PANEL_WIDTH + int(50 * RENDER_SCALE)
TRACK_END_X = RENDER_WIDTH - int(50 * RENDER_SCALE)
TRACK_TOP_Y = int(20 * RENDER_SCALE)
TRACK_BOTTOM_Y = int(220 * RENDER_SCALE)

# Posizioni dei cavalli
positions = {}
alpha = 0.1  # Fattore di smorzamento per le posizioni

position_size = int(30 * RENDER_SCALE)        # Dimensione del quadrato della posizione
position_padding = int(10 * RENDER_SCALE)     # Spazio tra il quadrato della posizione e l'ID del cavallo

# Inizializza gli elementi grafici del terreno
terrain_elements = []
terrain_element_speed = int(5 * RENDER_SCALE)  # Velocità degli elementi del terreno
for i in range(20):
    x = random.randint(TRACK_START_X, TRACK_END_X)
    y = random.randint(TRACK_TOP_Y + int(5 * RENDER_SCALE), TRACK_BOTTOM_Y - int(5 * RENDER_SCALE))
    terrain_elements.append({'x': x, 'y': y})

# Limiti per la mappatura delle coordinate Y
Y_MIN = 0    # Parte inferiore della pista in metri
Y_MAX = 20   # Parte superiore della pista in metri

running = True
clock = pygame.time.Clock()

# Inizializza le variabili per l'aggiornamento della velocità
last_speed_update_time = 0
displayed_speed = None

# Variabili per controllare la visibilità
show_standings = True
show_track = True
show_info_boxes = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Controlla la pressione dei tasti per attivare/disattivare gli elementi
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                show_standings = not show_standings
            elif event.key == pygame.K_2:
                show_track = not show_track
            elif event.key == pygame.K_3:
                show_info_boxes = not show_info_boxes

    # Pulisce la superficie di rendering
    render_surface.fill((0, 255, 0))  # Colore di sfondo impostato su green screen

    # Disegna il pannello sinistro in green screen
    if show_standings:
        pygame.draw.rect(render_surface, (0, 255, 0), (0, 0, LEFT_PANEL_WIDTH, RENDER_HEIGHT))
    else:
        pygame.draw.rect(render_surface, (0, 255, 0), (0, 0, LEFT_PANEL_WIDTH, RENDER_HEIGHT))

    # Ottiene una copia della classifica corrente
    with standings_lock:
        current_standings = standings.copy()

    # Disegna la classifica se abilitata
    if show_standings:
        y_offset = int(20 * RENDER_SCALE)
        entry_height = int(50 * RENDER_SCALE)
        entry_spacing = int(10 * RENDER_SCALE)

        for idx, horse in enumerate(current_standings):
            position_number = idx + 1

            # Disegna il quadrato arrotondato per la posizione
            position_rect_x = int(10 * RENDER_SCALE)
            position_rect_y = y_offset + (entry_height - position_size) // 2
            position_rect = pygame.Rect(position_rect_x, position_rect_y, position_size, position_size)
            pygame.draw.rect(render_surface, (150, 150, 150), position_rect, border_radius=int(5 * RENDER_SCALE))  # Angoli arrotondati

            # Scrive il numero di posizione all'interno del quadrato con il simbolo '°'
            position_text = font.render(str(position_number) + '°', True, (255, 255, 255))
            position_text_rect = position_text.get_rect(center=position_rect.center)
            render_surface.blit(position_text, position_text_rect)

            # Disegna il rettangolo esterno per il cavallo con angoli arrotondati
            entry_rect_x = position_rect.right + position_padding  # Sposta entry_rect a destra di position_rect
            entry_rect_width = LEFT_PANEL_WIDTH - entry_rect_x - int(10 * RENDER_SCALE)  # Sottrae il margine destro
            entry_rect = pygame.Rect(entry_rect_x, y_offset, entry_rect_width, entry_height)
            pygame.draw.rect(render_surface, (70, 70, 70), entry_rect, border_radius=int(10 * RENDER_SCALE))

            # Disegna il rettangolo arrotondato con l'ID del cavallo
            pill_width = int(60 * RENDER_SCALE)
            pill_height = int(30 * RENDER_SCALE)
            pill_x = entry_rect.x + int(10 * RENDER_SCALE)  # Posizionato a sinistra in entry_rect
            pill_y = entry_rect.y + (entry_height - pill_height) // 2
            pill_rect = pygame.Rect(pill_x, pill_y, pill_width, pill_height)
            pygame.draw.rect(render_surface, (200, 200, 200), pill_rect, border_radius=int(15 * RENDER_SCALE))

            # Scrive l'ID del cavallo all'interno del rettangolo arrotondato
            horse_id_text = font.render(str(horse['horse_id']), True, (0, 0, 0))
            horse_id_rect = horse_id_text.get_rect(center=pill_rect.center)
            render_surface.blit(horse_id_text, horse_id_rect)

            # Mostra la distanza a destra del rettangolo arrotondato
            if horse['distance'] is not None:
                distance_text = f"+{int(horse['distance'])} m"
            else:
                distance_text = f"{horse['distance_or_name']}"

            distance_surface = font.render(distance_text, True, (255, 255, 255))

            # Disegna un rettangolo arrotondato dietro la distanza
            distance_bg_width = distance_surface.get_width() + int(10 * RENDER_SCALE)
            distance_bg_height = distance_surface.get_height() + int(4 * RENDER_SCALE)
            distance_bg_x = pill_x + pill_width + int(10 * RENDER_SCALE)  # A destra del pill
            distance_bg_y = entry_rect.y + (entry_height - distance_bg_height) // 2
            distance_bg_rect = pygame.Rect(distance_bg_x, distance_bg_y, distance_bg_width, distance_bg_height)
            pygame.draw.rect(render_surface, (100, 100, 100), distance_bg_rect, border_radius=int(10 * RENDER_SCALE))

            # Posiziona il testo della distanza
            distance_rect = distance_surface.get_rect(center=distance_bg_rect.center)
            render_surface.blit(distance_surface, distance_rect)

            y_offset += entry_height + entry_spacing  # Passa all'entry successivo

    # Disegna la pista se abilitata
    if show_track:
        # Disegna la pista sabbiosa
        sandy_color = (194, 178, 128)
        pygame.draw.rect(render_surface, sandy_color, (TRACK_START_X, TRACK_TOP_Y, TRACK_END_X - TRACK_START_X, TRACK_BOTTOM_Y - TRACK_TOP_Y))

        # Aggiorna e disegna gli elementi grafici del terreno
        for element in terrain_elements:
            element['x'] -= terrain_element_speed
            if element['x'] < TRACK_START_X:
                element['x'] = TRACK_END_X
                element['y'] = random.randint(TRACK_TOP_Y + int(5 * RENDER_SCALE), TRACK_BOTTOM_Y - int(5 * RENDER_SCALE))
            # Disegna l'elemento del terreno (ad es. piccole linee)
            pygame.draw.rect(render_surface, (160, 82, 45), (element['x'], element['y'], int(5 * RENDER_SCALE), int(5 * RENDER_SCALE)))

        # Disegna la pista (linee orizzontali) sopra il terreno
        pygame.draw.line(render_surface, (0, 0, 0), (TRACK_START_X, TRACK_TOP_Y), (TRACK_END_X, TRACK_TOP_Y), int(5 * RENDER_SCALE))
        pygame.draw.line(render_surface, (0, 0, 0), (TRACK_START_X, TRACK_BOTTOM_Y), (TRACK_END_X, TRACK_BOTTOM_Y), int(5 * RENDER_SCALE))

    # Calcola computed_meters_to_finish per ogni cavallo basato sui gap cumulativi
    computed_meters_to_finish = {}
    if current_standings:
        # Inizia dall'ultimo cavallo
        last_horse = current_standings[-1]
        cumulative_meters_to_finish = last_horse['meters_to_finish']
        computed_meters_to_finish[last_horse['horse_id']] = cumulative_meters_to_finish

        # Processa i cavalli dal penultimo al primo
        for i in range(len(current_standings) - 2, -1, -1):
            horse = current_standings[i]
            horse_id = horse['horse_id']
            distance = horse['distance']
            if distance is None:
                distance = 0  # Supponendo gap zero se mancante
            cumulative_meters_to_finish -= distance
            computed_meters_to_finish[horse_id] = cumulative_meters_to_finish

        # Ottiene i valori min e max di meters_to_finish per il scaling
        meters_to_finish_values = list(computed_meters_to_finish.values())
        max_meters_to_finish = max(meters_to_finish_values)
        min_meters_to_finish = min(meters_to_finish_values)
    else:
        max_meters_to_finish = 0
        min_meters_to_finish = 0

    # Definisce la distanza di margine (in metri)
    MARGIN_DISTANCE = 50  # Regola secondo necessità

    # Calcola la distanza totale per il scaling
    total_distance = (max_meters_to_finish - min_meters_to_finish) + 2 * MARGIN_DISTANCE

    # Evita la divisione per zero
    if total_distance == 0:
        SCALE = 1
    else:
        SCALE = (TRACK_END_X - TRACK_START_X) / total_distance

    # Mappa le posizioni dei cavalli
    if current_standings:
        # Aggiorna le posizioni con smorzamento
        for horse in current_standings:
            horse_id = horse['horse_id']
            meters_to_finish = computed_meters_to_finish[horse_id]
            # Calcola la posizione x target con margini
            target_x = TRACK_START_X + SCALE * (max_meters_to_finish - meters_to_finish + MARGIN_DISTANCE)
            y_coordinate = horse['y_coordinate']
            # Mappa y_coordinate a screen_y
            screen_y = TRACK_BOTTOM_Y - ((y_coordinate - Y_MIN) / (Y_MAX - Y_MIN)) * (TRACK_BOTTOM_Y - TRACK_TOP_Y)
            # Assicura che screen_y sia entro i limiti
            screen_y = max(TRACK_TOP_Y, min(TRACK_BOTTOM_Y, screen_y))

            if horse_id in positions:
                prev_x = positions[horse_id]['x']
                prev_y = positions[horse_id]['y']
                positions[horse_id]['x'] = prev_x + alpha * (target_x - prev_x)
                positions[horse_id]['y'] = prev_y + alpha * (screen_y - prev_y)
            else:
                positions[horse_id] = {'x': target_x, 'y': screen_y}  # Prima volta, imposta direttamente

        # Disegna i cavalli sulla pista se la pista è visibile
        if show_track:
            for horse in current_standings:
                horse_id = horse['horse_id']
                horse_pos = positions[horse_id]
                horse_x = horse_pos['x']
                horse_y = horse_pos['y']
                # Disegna il cavallo come un cerchio
                pygame.draw.circle(render_surface, (0, 0, 255), (int(horse_x), int(horse_y)), int(15 * RENDER_SCALE))
                # Scrive l'ID del cavallo al centro del cerchio
                horse_text = font.render(str(horse_id), True, (255, 255, 255))
                text_rect = horse_text.get_rect(center=(int(horse_x), int(horse_y)))
                render_surface.blit(horse_text, text_rect)

        # Disegna i box informativi se abilitati
        if show_info_boxes:
            # Disegna il box "AL TRAGUARDO" per il primo cavallo
            first_horse = current_standings[0]
            meters_to_finish_first_horse = int(computed_meters_to_finish[first_horse['horse_id']])

            # Definisce le dimensioni del box
            box_width = int(203 * RENDER_SCALE)
            box_height = int(75 * RENDER_SCALE)
            box_x = RENDER_WIDTH - box_width - int(10 * RENDER_SCALE)  # Angolo in basso a destra
            box_y = RENDER_HEIGHT - box_height - int(100 * RENDER_SCALE)

            # Disegna il box con colore originale
            pygame.draw.rect(render_surface, (100, 100, 100), (box_x, box_y, box_width, box_height), border_radius=int(10 * RENDER_SCALE))

            # Disegna il testo "AL TRAGUARDO"
            al_traguardo_text = font.render("AL TRAGUARDO", True, (255, 255, 255))
            al_traguardo_rect = al_traguardo_text.get_rect(center=(box_x + box_width / 2, box_y + int(20 * RENDER_SCALE)))
            render_surface.blit(al_traguardo_text, al_traguardo_rect)

            # Disegna i metri al traguardo o "FINITA!" se la gara è terminata
            if meters_to_finish_first_horse > 0:
                meters_text = large_font.render(f"{meters_to_finish_first_horse}m", True, (255, 255, 255))
            else:
                meters_text = large_font.render("FINITA!", True, (255, 255, 255))
            meters_rect = meters_text.get_rect(center=(box_x + box_width / 2, box_y + box_height / 2 + int(10 * RENDER_SCALE)))
            render_surface.blit(meters_text, meters_rect)

            # Aggiorna la velocità visualizzata una volta al secondo
            current_time = time.time()
            if current_time - last_speed_update_time >= 1:
                # Aggiorna la velocità visualizzata
                speed_first_horse = first_horse['speed']
                if speed_first_horse is not None:
                    displayed_speed = speed_first_horse
                else:
                    displayed_speed = None
                last_speed_update_time = current_time  # Aggiorna il tempo dell'ultimo aggiornamento

            # Disegna il box "VELOCITÀ IN TESTA"
            speed_box_width = int(203 * RENDER_SCALE)
            speed_box_height = int(75 * RENDER_SCALE)
            speed_box_x = box_x - speed_box_width - int(10 * RENDER_SCALE)
            speed_box_y = box_y

            # Disegna il box della velocità
            pygame.draw.rect(render_surface, (100, 100, 100), (speed_box_x, speed_box_y, speed_box_width, speed_box_height), border_radius=int(10 * RENDER_SCALE))

            # Disegna il testo "VELOCITÀ IN TESTA"
            velocita_text = font.render("VELOCITÀ IN TESTA", True, (255, 255, 255))
            velocita_rect = velocita_text.get_rect(center=(speed_box_x + speed_box_width / 2, speed_box_y + int(20 * RENDER_SCALE)))
            render_surface.blit(velocita_text, velocita_rect)

            # Disegna il valore della velocità
            if displayed_speed is not None:
                speed_display_text = large_font.render(f"{displayed_speed:.1f} km/h", True, (255, 255, 255))
            else:
                speed_display_text = large_font.render("N/A", True, (255, 255, 255))
            speed_rect = speed_display_text.get_rect(center=(speed_box_x + speed_box_width / 2, speed_box_y + speed_box_height / 2 + int(10 * RENDER_SCALE)))
            render_surface.blit(speed_display_text, speed_rect)

            # Disegna la linea del traguardo quando appropriato
            FINISH_LINE_THRESHOLD = 150  # Mostra la linea del traguardo quando entro 150 metri
            if meters_to_finish_first_horse <= FINISH_LINE_THRESHOLD and meters_to_finish_first_horse > -300:
                finish_line_x = TRACK_START_X + SCALE * (max_meters_to_finish - 0 + MARGIN_DISTANCE)
                if finish_line_x <= TRACK_END_X and show_track:
                    pygame.draw.line(render_surface, (255, 0, 0), (int(finish_line_x), TRACK_TOP_Y), (int(finish_line_x), TRACK_BOTTOM_Y), int(5 * RENDER_SCALE))
    else:
        positions = {}

    # Ridimensiona la superficie di rendering ad alta risoluzione alla dimensione dello schermo
    scaled_surface = pygame.transform.smoothscale(render_surface, (WINDOW_WIDTH, WINDOW_HEIGHT))
    screen.blit(scaled_surface, (0, 0))

    # Aggiorna lo schermo
    pygame.display.flip()
    # Limita il frame rate
    clock.tick(30)

pygame.quit()

import socket
import threading
import pygame
import re
import random  # For generating random terrain elements

# Settings for the UDP socket
UDP_IP = "213.209.192.164"
UDP_PORT = 4141

# Create the UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# Shared data structure to store the standings
standings = []
standings_lock = threading.Lock()

def receive_packets():
    """Function in a separate thread to receive UDP packets."""
    while True:
        data, addr = sock.recvfrom(1024)
        packet = data.decode('utf-8')
        parse_packet(packet)

def parse_packet(packet):
    """Parse the received packet and update the standings."""
    global standings
    if not packet.startswith('CLASSIFICA'):
        return
    # Remove 'CLASSIFICA' from the packet
    packet = packet[len('CLASSIFICA'):]
    # Remove any leading commas
    packet = packet.lstrip(',')
    # Extract fields using regular expressions
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
        # Handle 'distance' and 'last one'
        if distance_or_name.lower() == 'last one':
            distance = None
        else:
            try:
                distance = float(distance_or_name)
            except ValueError:
                distance = None  # Invalid data
        try:
            speed = float(speed_str)
        except ValueError:
            speed = None  # Invalid data
        new_standings.append({
            'horse_id': horse_id,
            'distance': distance,  # Gap to the next horse (behind)
            'distance_or_name': distance_or_name,
            'meters_to_finish': meters_to_finish,
            'y_coordinate': y_coordinate,
            'speed': speed
            # 'time' field removed
        })
    # Update the standings in a thread-safe manner
    with standings_lock:
        standings = new_standings

# Start the thread to receive UDP packets
udp_thread = threading.Thread(target=receive_packets)
udp_thread.daemon = True
udp_thread.start()

# Initialize Pygame
pygame.init()

# Window settings
WINDOW_WIDTH = 1200  # Total window width
WINDOW_HEIGHT = 700
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('Classifica Corse Cavalli')

# Increase rendering resolution
RENDER_SCALE = 4  # Increase this value for higher definition
RENDER_WIDTH = WINDOW_WIDTH * RENDER_SCALE
RENDER_HEIGHT = WINDOW_HEIGHT * RENDER_SCALE

# Create a high-resolution surface
render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))

# Font settings
font = pygame.font.Font(None, int(24 * RENDER_SCALE))
large_font = pygame.font.Font(None, int(48 * RENDER_SCALE))  # For larger text

# Positioning constants scaled
LEFT_PANEL_WIDTH = int(250 * RENDER_SCALE)  # Width of the left panel
TRACK_START_X = LEFT_PANEL_WIDTH + int(50 * RENDER_SCALE)
TRACK_END_X = RENDER_WIDTH - int(50 * RENDER_SCALE)
TRACK_TOP_Y = int(200 * RENDER_SCALE)
TRACK_BOTTOM_Y = int(400 * RENDER_SCALE)

# Horse positions
positions = {}
alpha = 0.1  # Smoothing factor for positions

position_size = int(30 * RENDER_SCALE)        # Size of the position square
position_padding = int(10 * RENDER_SCALE)     # Space between position square and horse ID

# Initialize terrain graphic elements
terrain_elements = []
terrain_element_speed = int(5 * RENDER_SCALE)  # Speed of terrain elements
for i in range(20):
    x = random.randint(TRACK_START_X, TRACK_END_X)
    y = random.randint(TRACK_TOP_Y + int(5 * RENDER_SCALE), TRACK_BOTTOM_Y - int(5 * RENDER_SCALE))
    terrain_elements.append({'x': x, 'y': y})

# Limits for mapping Y coordinates
Y_MIN = 0    # Bottom of the track in meters
Y_MAX = 20   # Top of the track in meters

running = True
clock = pygame.time.Clock()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Clear the render surface
    render_surface.fill((0, 255, 0))  # Background color changed to green screen

    # Draw the left panel in green screen
    pygame.draw.rect(render_surface, (0, 255, 0), (0, 0, LEFT_PANEL_WIDTH, RENDER_HEIGHT))

    # Get a copy of the current standings
    with standings_lock:
        current_standings = standings.copy()

    # Draw the standings
    y_offset = int(20 * RENDER_SCALE)
    entry_height = int(50 * RENDER_SCALE)
    entry_spacing = int(10 * RENDER_SCALE)

    for idx, horse in enumerate(current_standings):
        position_number = idx + 1

        # Draw the rounded square for the position
        position_rect_x = int(10 * RENDER_SCALE)
        position_rect_y = y_offset + (entry_height - position_size) // 2
        position_rect = pygame.Rect(position_rect_x, position_rect_y, position_size, position_size)
        pygame.draw.rect(render_surface, (150, 150, 150), position_rect, border_radius=int(5 * RENDER_SCALE))  # Rounded corners

        # Write the position number inside the square with the '°' symbol
        position_text = font.render(str(position_number) + '°', True, (255, 255, 255))
        position_text_rect = position_text.get_rect(center=position_rect.center)
        render_surface.blit(position_text, position_text_rect)

        # Draw the outer rectangle for the horse with rounded corners
        entry_rect_x = position_rect.right + position_padding  # Shift entry_rect to the right of position_rect
        entry_rect_width = LEFT_PANEL_WIDTH - entry_rect_x - int(10 * RENDER_SCALE)  # Subtract right margin
        entry_rect = pygame.Rect(entry_rect_x, y_offset, entry_rect_width, entry_height)
        pygame.draw.rect(render_surface, (70, 70, 70), entry_rect, border_radius=int(10 * RENDER_SCALE))

        # Draw the rounded rectangle with the horse ID
        pill_width = int(60 * RENDER_SCALE)
        pill_height = int(30 * RENDER_SCALE)
        pill_x = entry_rect.x + int(10 * RENDER_SCALE)  # Positioned to the left in entry_rect
        pill_y = entry_rect.y + (entry_height - pill_height) // 2
        pill_rect = pygame.Rect(pill_x, pill_y, pill_width, pill_height)
        pygame.draw.rect(render_surface, (200, 200, 200), pill_rect, border_radius=int(15 * RENDER_SCALE))

        # Write the horse ID inside the rounded rectangle
        horse_id_text = font.render(str(horse['horse_id']), True, (0, 0, 0))
        horse_id_rect = horse_id_text.get_rect(center=pill_rect.center)
        render_surface.blit(horse_id_text, horse_id_rect)

        # Show the distance to the right of the rounded rectangle
        if horse['distance'] is not None:
            distance_text = f"+{int(horse['distance'])} m"
        else:
            distance_text = f"{horse['distance_or_name']}"

        distance_surface = font.render(distance_text, True, (255, 255, 255))

        # Draw a rounded rectangle behind the distance
        distance_bg_width = distance_surface.get_width() + int(10 * RENDER_SCALE)
        distance_bg_height = distance_surface.get_height() + int(4 * RENDER_SCALE)
        distance_bg_x = pill_x + pill_width + int(10 * RENDER_SCALE)  # To the right of the pill
        distance_bg_y = entry_rect.y + (entry_height - distance_bg_height) // 2
        distance_bg_rect = pygame.Rect(distance_bg_x, distance_bg_y, distance_bg_width, distance_bg_height)
        pygame.draw.rect(render_surface, (100, 100, 100), distance_bg_rect, border_radius=int(10 * RENDER_SCALE))

        # Position the distance text
        distance_rect = distance_surface.get_rect(center=distance_bg_rect.center)
        render_surface.blit(distance_surface, distance_rect)

        y_offset += entry_height + entry_spacing  # Move to the next entry

    # Draw the sandy track
    sandy_color = (194, 178, 128)
    pygame.draw.rect(render_surface, sandy_color, (TRACK_START_X, TRACK_TOP_Y, TRACK_END_X - TRACK_START_X, TRACK_BOTTOM_Y - TRACK_TOP_Y))

    # Update and draw the terrain graphic elements
    for element in terrain_elements:
        element['x'] -= terrain_element_speed
        if element['x'] < TRACK_START_X:
            element['x'] = TRACK_END_X
            element['y'] = random.randint(TRACK_TOP_Y + int(5 * RENDER_SCALE), TRACK_BOTTOM_Y - int(5 * RENDER_SCALE))
        # Draw the terrain element (e.g., small lines)
        pygame.draw.rect(render_surface, (160, 82, 45), (element['x'], element['y'], int(5 * RENDER_SCALE), int(5 * RENDER_SCALE)))

    # Draw the track (horizontal lines) over the terrain
    pygame.draw.line(render_surface, (0, 0, 0), (TRACK_START_X, TRACK_TOP_Y), (TRACK_END_X, TRACK_TOP_Y), int(5 * RENDER_SCALE))
    pygame.draw.line(render_surface, (0, 0, 0), (TRACK_START_X, TRACK_BOTTOM_Y), (TRACK_END_X, TRACK_BOTTOM_Y), int(5 * RENDER_SCALE))

    # Calculate computed_meters_to_finish for each horse based on cumulative gaps
    computed_meters_to_finish = {}
    if current_standings:
        # Start from the last horse
        last_horse = current_standings[-1]
        cumulative_meters_to_finish = last_horse['meters_to_finish']
        computed_meters_to_finish[last_horse['horse_id']] = cumulative_meters_to_finish

        # Process the horses from second last to first
        for i in range(len(current_standings) - 2, -1, -1):
            horse = current_standings[i]
            horse_id = horse['horse_id']
            distance = horse['distance']
            if distance is None:
                distance = 0  # Assuming zero gap if missing
            cumulative_meters_to_finish -= distance
            computed_meters_to_finish[horse_id] = cumulative_meters_to_finish

        # Get the min and max meters_to_finish for scaling
        meters_to_finish_values = list(computed_meters_to_finish.values())
        max_meters_to_finish = max(meters_to_finish_values)
        min_meters_to_finish = min(meters_to_finish_values)
    else:
        max_meters_to_finish = 0
        min_meters_to_finish = 0

    # Define margin distance (in meters)
    MARGIN_DISTANCE = 50  # Adjust as needed

    # Calculate total distance for scaling
    total_distance = (max_meters_to_finish - min_meters_to_finish) + 2 * MARGIN_DISTANCE

    # Avoid division by zero
    if total_distance == 0:
        SCALE = 1
    else:
        SCALE = (TRACK_END_X - TRACK_START_X) / total_distance

    # Map horse positions
    if current_standings:
        # Update positions with smoothing
        for horse in current_standings:
            horse_id = horse['horse_id']
            meters_to_finish = computed_meters_to_finish[horse_id]
            # Calculate target x position with margins
            target_x = TRACK_START_X + SCALE * (max_meters_to_finish - meters_to_finish + MARGIN_DISTANCE)
            y_coordinate = horse['y_coordinate']
            # Map y_coordinate to screen_y
            screen_y = TRACK_BOTTOM_Y - ((y_coordinate - Y_MIN) / (Y_MAX - Y_MIN)) * (TRACK_BOTTOM_Y - TRACK_TOP_Y)
            # Ensure screen_y is within limits
            screen_y = max(TRACK_TOP_Y, min(TRACK_BOTTOM_Y, screen_y))

            if horse_id in positions:
                prev_x = positions[horse_id]['x']
                prev_y = positions[horse_id]['y']
                positions[horse_id]['x'] = prev_x + alpha * (target_x - prev_x)
                positions[horse_id]['y'] = prev_y + alpha * (screen_y - prev_y)
            else:
                positions[horse_id] = {'x': target_x, 'y': screen_y}  # First time, set directly

        # Draw the horses on the track
        for horse in current_standings:
            horse_id = horse['horse_id']
            horse_pos = positions[horse_id]
            horse_x = horse_pos['x']
            horse_y = horse_pos['y']
            # Draw the horse as a circle
            pygame.draw.circle(render_surface, (0, 0, 255), (int(horse_x), int(horse_y)), int(15 * RENDER_SCALE))
            # Write the horse ID at the center of the circle
            horse_text = font.render(str(horse_id), True, (255, 255, 255))
            text_rect = horse_text.get_rect(center=(int(horse_x), int(horse_y)))
            render_surface.blit(horse_text, text_rect)

        # Draw the "AL TRAGUARDO" box for the first horse
        first_horse = current_standings[0]
        meters_to_finish_first_horse = int(computed_meters_to_finish[first_horse['horse_id']])

        # Define box dimensions
        box_width = int(203 * RENDER_SCALE)
        box_height = int(75 * RENDER_SCALE)
        box_x = RENDER_WIDTH - box_width - int(10 * RENDER_SCALE)  # Bottom right corner
        box_y = RENDER_HEIGHT - box_height - int(10 * RENDER_SCALE)

        # Draw the box with original color
        pygame.draw.rect(render_surface, (100, 100, 100), (box_x, box_y, box_width, box_height), border_radius=int(10 * RENDER_SCALE))

        # Draw the "AL TRAGUARDO" text
        al_traguardo_text = font.render("AL TRAGUARDO", True, (255, 255, 255))
        al_traguardo_rect = al_traguardo_text.get_rect(center=(box_x + box_width / 2, box_y + int(20 * RENDER_SCALE)))
        render_surface.blit(al_traguardo_text, al_traguardo_rect)

        # Draw the meters to finish or "FINITA!" if race is over
        if meters_to_finish_first_horse > 0:
            meters_text = large_font.render(f"{meters_to_finish_first_horse}m", True, (255, 255, 255))
        else:
            meters_text = large_font.render("FINITA!", True, (255, 255, 255))
        meters_rect = meters_text.get_rect(center=(box_x + box_width / 2, box_y + box_height / 2 + int(10 * RENDER_SCALE)))
        render_surface.blit(meters_text, meters_rect)

        # Draw the "VELOCITÀ IN TESTA" box
        speed_box_width = int(203 * RENDER_SCALE)
        speed_box_height = int(75 * RENDER_SCALE)
        speed_box_x = box_x - speed_box_width - int(10 * RENDER_SCALE)
        speed_box_y = box_y

        # Draw the speed box
        pygame.draw.rect(render_surface, (100, 100, 100), (speed_box_x, speed_box_y, speed_box_width, speed_box_height), border_radius=int(10 * RENDER_SCALE))

        # Draw the "VELOCITÀ IN TESTA" text
        velocita_text = font.render("VELOCITÀ IN TESTA", True, (255, 255, 255))
        velocita_rect = velocita_text.get_rect(center=(speed_box_x + speed_box_width / 2, speed_box_y + int(20 * RENDER_SCALE)))
        render_surface.blit(velocita_text, velocita_rect)

        # Draw the speed value
        speed_first_horse = first_horse['speed']
        if speed_first_horse is not None:
            speed_display_text = large_font.render(f"{speed_first_horse:.1f} km/h", True, (255, 255, 255))
        else:
            speed_display_text = large_font.render("N/A", True, (255, 255, 255))
        speed_rect = speed_display_text.get_rect(center=(speed_box_x + speed_box_width / 2, speed_box_y + speed_box_height / 2 + int(10 * RENDER_SCALE)))
        render_surface.blit(speed_display_text, speed_rect)

        # Draw the finish line when appropriate
        FINISH_LINE_THRESHOLD = 150  # Show finish line when within 150 meters
        if meters_to_finish_first_horse <= FINISH_LINE_THRESHOLD and meters_to_finish_first_horse > -300:
            finish_line_x = TRACK_START_X + SCALE * (max_meters_to_finish - 0 + MARGIN_DISTANCE)
            if finish_line_x <= TRACK_END_X:
                pygame.draw.line(render_surface, (255, 0, 0), (int(finish_line_x), TRACK_TOP_Y), (int(finish_line_x), TRACK_BOTTOM_Y), int(5 * RENDER_SCALE))
    else:
        positions = {}

    # Scale down the high-resolution render surface to the screen size
    scaled_surface = pygame.transform.smoothscale(render_surface, (WINDOW_WIDTH, WINDOW_HEIGHT))
    screen.blit(scaled_surface, (0, 0))

    # Update the screen
    pygame.display.flip()
    # Limit the frame rate
    clock.tick(30)

pygame.quit()

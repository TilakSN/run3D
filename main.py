#!/usr/bin/env python2

#################################################
#                   Run: 3D                     #
#################################################

# imports
import numpy as np
import pygame as pg
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from collections import deque
import random

# globals
Size = None                 # size of display
Active = True               # check if current window is in focus
FPS = 40                    # speed of execution
Speed = 0.1                 # speed of Z movement
# Angle = 0                   # angle made by actual tunnel with current view
Cube_size = 0.25            # size of Cube
Clock = pg.time.Clock()     # Clock to control speed of execution
Default_matrix = None       # restore settings at the beginning of the game

# vertices of cube
R_U_F = (Cube_size, Cube_size, Cube_size, 1)        # R = Right
R_U_B = (Cube_size, Cube_size, -Cube_size, 1)       # U = Up
R_D_F = (Cube_size, -Cube_size, Cube_size, 1)       # F = Front
R_D_B = (Cube_size, -Cube_size, -Cube_size, 1)      # B = Back
L_U_F = (-Cube_size, Cube_size, Cube_size, 1)       # D = Down
L_U_B = (-Cube_size, Cube_size, -Cube_size, 1)      # L = Left
L_D_F = (-Cube_size, -Cube_size, Cube_size, 1)
L_D_B = (-Cube_size, -Cube_size, -Cube_size, 1)

# faces of cube
R_Face = np.array((R_U_F, R_U_B, R_D_B, R_D_F))
L_Face = np.array((L_U_F, L_D_F, L_D_B, L_U_B))
U_Face = np.array((R_U_F, L_U_F, L_U_B, R_U_B))
D_Face = np.array((R_D_F, R_D_B, L_D_B, L_D_F))
F_Face = np.array((R_U_F, R_D_F, L_D_F, L_U_F))
B_Face = np.array((R_U_B, L_U_B, L_D_B, R_D_B))

# cube
Cube = np.array((R_Face, L_Face, U_Face, D_Face, F_Face, B_Face))

# texture mapping
Texture_corners = ((0, 0), (0, 1), (1, 1), (1, 0))
texture = None
Play_button_texture = None

Boundaries = deque()                    # update and delete boundaries
Bound = Cube_size * 7 / 5.0             # limit value
x_low = y_low = -Bound                  # limits for viewing
x_high = y_high = Bound
Current_X = Current_Y = Current_Z = 0   # viewing position
Gap_Z = 0                               # gap between beginning of the game and scoring
Obstacles = deque()                     # update and delete from front when passed
Deleted_obstacles = []                  # to reuse
Next_Obstacle = random.randint(0, 5)    # time for the next obstacle

# colors
game_color = np.array((0.0, 0.3, 0.8))      # color of boundary and obstacles
Color_change = random.randint(100, 200)     # time for next color
Next_color = random.randint(50, 100)        # time for transition from current color to next
# the amount by which the color must change each time
Color_difference = ((random.random() - game_color[0]) / Next_color,
                    (random.random() - game_color[1]) / Next_color,
                    (random.random() - game_color[2]) / Next_color)


def set_defaults():
    """Set the default values for all global variables on restart.
    :return: nothing."""

    global Default_matrix, Gap_Z, Current_X, Current_Y, Current_Z, FPS, Next_Obstacle, texture, Speed
    global x_low, x_high, y_low, y_high
    glLoadMatrixf(Default_matrix)               # reset MODEL VIEW MATRIX
    Speed = 0.1                                 # reset speed
    Next_Obstacle = random.randint(0, 5)        # reset time for next obstacle
    Boundary.X = Boundary.Y = Boundary.Z = 0    # reset boundary parameters
    Current_X = Current_Y = Current_Z = 0       # reset player position
    Gap_Z = 0                                   # gap between beginning of the game and scoring
    x_low = y_low = -Bound                      # set bounds
    x_high = y_high = Bound
    glBindTexture(GL_TEXTURE_2D, texture)       # bind the texture to 2D surface
    glEnable(GL_TEXTURE_2D)                     # enable the texture


class Obstacle:
    """Each object of this class is a static or moving obstacle that the player has to dodge.
    It is a collection of cubes."""

    def __init__(self):
        # store x, y, z for creating obstacle and deleting after it is passed
        self.x, self.y, self.z = Boundary.X, Boundary.Y, Boundary.Z + 1
        # type of obstacle
        self.type = random.randint(1, 15)
        # moving cubes if any
        self.moving_faces = []
        # when to start move
        self.start_move = 0
        # transformation matrix for animating moving obstacles
        self.move = translation_matrix((0, 0, 0))
        # static cubes
        self.faces = []
        # bool to check if object has passed
        self.has_passed = False

        if self.type < 16:  # checking so that if any new obstacle is added, this code won't be executed for them
            # bitwise: 1-15 are all 4 bit numbers b3,b2,b1,b0
            # create Cubes for all bits that are 1's
            if self.type & 1:
                self.faces.append(Cube.dot(translation_matrix((self.x - Cube_size,  # b0 - bottom left
                                                               self.y - Cube_size, self.z))))
            if self.type & 2:
                self.faces.append(Cube.dot(translation_matrix((self.x - Cube_size,  # b1 - top left
                                                               self.y + Cube_size, self.z))))
            if self.type & 4:
                self.faces.append(Cube.dot(translation_matrix((self.x + Cube_size,  # b2 - top right
                                                               self.y + Cube_size, self.z))))
            if self.type & 8:
                self.faces.append(Cube.dot(translation_matrix((self.x + Cube_size,  # b3 - bottom right
                                                               self.y - Cube_size, self.z))))
        if self.type == 15:
            # if all 4 are blocked, set it to open as player approaches.
            self.start_move = 16    # starts opening after these many update calls from the time of creation
            k = random.randint(0, 3)    # choose the block to move
            # choose the direction for it to move out of view. Only 2 ways to move out from corner
            l = random.randint(0, 1)
            # set the direction and speed at which it should move out
            dx, dy = [[0, -Speed / 6], [-Speed / 6, 0], [0, Speed / 6], [Speed / 6, 0]][(k + l) & 3]
            # set that face as moving and choose the corresponding transformation matrix
            self.moving_faces.append(self.faces.pop(k))
            self.move = translation_matrix((dx, dy, 0))
        elif random.random() > 0.7:
            # set moving obstacles
            self.start_move = 12
            self.move = translation_matrix((0, 0, Speed / 2))
            # set the moving faces and make them reach the position on time
            while self.faces:
                self.moving_faces.append(self.faces.pop().dot(translation_matrix((0, 0, -13.0 * Speed))))
            # add gap after current object
            global Next_Obstacle
            Next_Obstacle += 3

    def update(self):
        """Update the status of the obstacle, used to delete.
        :return: nothing."""

        global Gap_Z, Current_Z
        self.has_passed = self.z > Gap_Z - Current_Z - Cube_size * 2 / 3

    def draw(self):
        """Draw the obstacle.
        Requires glBegin(GL_QUADS) before call and glEnd() after call for the drawing to actually take place.
        :return: nothing."""

        # move the moving_faces
        if self.start_move:
            self.start_move -= 1
        else:
            self.moving_faces = [face.dot(self.move) for face in self.moving_faces]
        # draw all cubes
        for cube in self.faces + self.moving_faces:
            draw_cube(cube)

    def collide(self):
        """Check if the current position collides with the obstacle.
        :return: True if collision takes place, false otherwise."""

        return any(collide_cube(cube) for cube in self.faces + self.moving_faces)


class Boundary:
    """Each Boundary object has 8 quads / squares, 2 on each of the 4 sides (Right, Left, Up, Down)"""
    # variables to store the X, Y, Z positions of last boundary
    X = Y = Z = 0

    def __init__(self):
        # update location for current boundary
        Boundary.Z -= 0.5
        # store the positions for future use
        self.x, self.y, self.z = Boundary.X, Boundary.Y, Boundary.Z
        # use the defined faces and multiply with transformation matrix to get the required faces
        self.faces = [R_Face.dot(translation_matrix((self.x - 3 * Cube_size, self.y - Cube_size, self.z))),
                      R_Face.dot(translation_matrix((self.x - 3 * Cube_size, self.y + Cube_size, self.z))),
                      L_Face.dot(translation_matrix((self.x + 3 * Cube_size, self.y - Cube_size, self.z))),
                      L_Face.dot(translation_matrix((self.x + 3 * Cube_size, self.y + Cube_size, self.z))),
                      U_Face.dot(translation_matrix((self.x - Cube_size, self.y - 3 * Cube_size, self.z))),
                      U_Face.dot(translation_matrix((self.x + Cube_size, self.y - 3 * Cube_size, self.z))),
                      D_Face.dot(translation_matrix((self.x - Cube_size, self.y + 3 * Cube_size, self.z))),
                      D_Face.dot(translation_matrix((self.x + Cube_size, self.y + 3 * Cube_size, self.z)))]
        # helps to check if the boundary is out of the frame
        self.z -= Cube_size
        # boolean value which is True when the boundary is behind the current position
        self.has_passed = False

    def update(self):
        """Update the status of the boundary, used to delete.
        :return: nothing."""

        global Current_Z, Gap_Z
        self.has_passed = self.z > Gap_Z - Current_Z

    def draw(self):
        """Draw the boundary.
        Requires glBegin(GL_QUADS) before call and glEnd() after call for the drawing to actually take place.
        :return: nothing."""

        # draw_cube draws the quads in the list irrespective of size. so, it can be used
        draw_cube(self.faces)


def start(title):
    """Initialize the game.
    :param title: Caption to be set for the window.
    :return: nothing."""

    global Size, Boundaries, Speed, Gap_Z, Default_matrix
    # initialize
    pg.init()
    # avoid unnecessary events
    pg.event.set_allowed(None)
    pg.event.set_allowed((QUIT, KEYDOWN, MOUSEBUTTONDOWN, ACTIVEEVENT))

    # # No full screen
    # # size
    # Size = (800, 600)
    # # screen
    # pg.display.set_mode(Size, OPENGL | DOUBLEBUF)

    # Full screen
    # size
    Size = pg.display.list_modes()[0]
    # screen
    pg.display.set_mode(Size, OPENGL | DOUBLEBUF | FULLSCREEN)

    # caption
    pg.display.set_caption(title)
    # view (field of view in degrees, aspect ratio, near clipping plane, far clipping plane)
    # only the objects that lie in between the clipping planes are drawn
    gluPerspective(90, float(Size[0]) / Size[1], 0.1, 50)
    # background color when cleared - black, opaque
    glClearColor(0, 0, 0, 1)
    # set game color (color of whatever is drawn till it is changed)
    glColor(game_color)
    # generate the play button
    generate_play_button()
    # generate, bind and enable textured drawing
    generate_texture()
    glBindTexture(GL_TEXTURE_2D, texture)
    glEnable(GL_TEXTURE_2D)
    # front face. decides which of the 2 sides of the plane is front side. Clockwise = left hand rule
    glFrontFace(GL_CW)
    # culling. draws only if the camera is viewing the object's front face
    glEnable(GL_CULL_FACE)
    # depth test. Does not draw farther objects in front of near ones
    glEnable(GL_DEPTH_TEST)
    # store matrix to restore current state on restart
    Default_matrix = glGetFloatv(GL_MODELVIEW_MATRIX)
    # function to decide transparency values
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    # generate boundary
    for i in range(20):
        Boundaries.append(Boundary())


def restart():
    """Restart the game. Similar to start, but some parameters are already set.
    :return: nothing."""

    global Gap_Z, Speed, Boundaries, Obstacles, Deleted_obstacles, texture, Play_button_texture
    # set the default values of game and animation parameters
    set_defaults()
    # delete all Boundary objects. Remove from deque and reinitialise and reuse later
    deleted_boundaries = []
    while Boundaries:
        deleted_boundaries.append(Boundaries.pop())
    # delete obstacles. will be reused from Deleted_obstacles while updating and creating obstacles
    while Obstacles:
        Deleted_obstacles.append(Obstacles.pop())
    # set some boundaries
    for i in range(6):
        Boundaries.append(deleted_boundaries.pop())
        Boundary.__init__(Boundaries[-1])
    # set all the boundaries while moving
    while deleted_boundaries:
        Clock.tick(18)
        # append from deleted
        Boundaries.append(deleted_boundaries.pop())
        # initialize
        Boundary.__init__(Boundaries[-1])
        # move, set Gap_Z so that scoring starts only at the end of this function
        glTranslatef(0, 0, Speed)
        Gap_Z -= Speed
        # clear display and draw boundaries in the new view
        clear()
        update_boundaries()
        # update display
        pg.display.flip()
    # get mouse button click to start playing
    while True:
        # limit execution speed
        Clock.tick(15)
        # check events
        for event in pg.event.get():
            # quit
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                return 0
            # check if mouse click
            if event.type == MOUSEBUTTONDOWN:
                return 1
        clear()
        # move and set Gap_Z
        glTranslatef(0, 0, Speed)
        Gap_Z -= Speed
        # get new color, apply it and update boundaries
        change_color()
        glColor(game_color)
        update_boundaries()
        # enable transparency for background for button
        glEnable(GL_BLEND)
        # set texture
        glBindTexture(GL_TEXTURE_2D, Play_button_texture)
        # negative color to enhance visibility
        glColor((1, 1, 1) - game_color)
        # draw a quad with Play button texture
        glBegin(GL_QUADS)
        draw_quad([(-0.5, -0.5, Gap_Z - 2),
                   (-0.5, +0.5, Gap_Z - 2),
                   (+0.5, +0.5, Gap_Z - 2),
                   (+0.5, -0.5, Gap_Z - 2)])
        glEnd()
        # disable transparency for next loop
        glDisable(GL_BLEND)
        # retain the texture
        glBindTexture(GL_TEXTURE_2D, texture)
        # update display
        pg.display.flip()


def play():
    """Main game loop. Handles all game parameters.
    :return: State of the game. 0 for quit, 1 for continue, 2 for restart."""

    global Current_Z, Speed, Active
    # limit execution speed
    Clock.tick(FPS)
    # check events
    for event in pg.event.get():
        # quit
        if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
            return 0
        # check if current event lost focus (gain=0 and state=2)
        if event.type == ACTIVEEVENT:
            Active = not (event.gain == 0 and event.state == 2)

    # do not continue if this game is not active
    if not Active:
        return 1
    # increase speed with time
    Speed += 5e-5
    # get new color and apply it
    change_color()
    glColor(game_color)
    # get camera movement and apply it. always move in Z direction
    dx, dy = get_dx_dy()
    glTranslatef(dx, dy, Speed)
    Current_Z += Speed
    # clear display
    clear()
    # update boundaries and obstacles
    update_boundaries()
    if update_obstacles():
        # collided with an obstacle :'(
        return game_over()
    # update display
    pg.display.flip()
    # repeat this loop
    return 1


def game_over():
    """Game over. Ask the user for restart or quit.
    :return: integer 0 for quit and 2 for restart."""

    global Current_Z
    # display all obstacles and boundaries updated at the time of collision
    pg.display.flip()
    pg.time.delay(500)
    clear()
    # display score in console
    print("Score:", int(Current_Z))
    # create a texture containing score
    t1, r1 = string_to_texture(str(int(Current_Z)))
    # adjust the width and height of texture to fit in a 1x1 box
    if r1 > 1:
        # height is greater. set it to max and adjust width to maintain ratio
        ry = 0.5
        rx = ry / r1
    else:
        # width is greater. set it to max and adjust height to maintain ratio
        rx = 0.5
        ry = rx * r1
    # create a texture containing the text "again" and "quit"
    t2, r2 = string_to_texture("again")
    t3, r3 = string_to_texture("quit")

    # definite loop (30 seconds), to avoid the game to stay idle in this screen
    for i in range(FPS * 30):
        # limit execution speed
        Clock.tick(FPS)
        # clear screen
        clear()
        # change the color and set it for the boundary
        change_color()
        glColor(game_color)
        # get movement and move the camera
        dx, dy = get_dx_dy()
        glTranslatef(dx, dy, Speed)
        # change current location (X & Y changed in get_dx_dy)
        Current_Z += Speed
        # bind the glowing box texture and draw boundaries
        glBindTexture(GL_TEXTURE_2D, texture)
        update_boundaries()
        # enable transparency for background for score and messages
        glEnable(GL_BLEND)
        # set texture (score)
        glBindTexture(GL_TEXTURE_2D, t1)
        # negative color to enhance visibility
        glColor((1, 1, 1) - game_color)
        # draw a quad with score texture
        glBegin(GL_QUADS)
        draw_quad([(-rx, -ry, Gap_Z - Current_Z - 5),
                   (-rx, +ry, Gap_Z - Current_Z - 5),
                   (+rx, +ry, Gap_Z - Current_Z - 5),
                   (+rx, -ry, Gap_Z - Current_Z - 5)])
        glEnd()
        # green color for "again"
        glColor((0.1, 0.9, 0.2))
        # set texture
        glBindTexture(GL_TEXTURE_2D, t2)
        # draw quad with "again" texture
        glBegin(GL_QUADS)
        draw_quad([(-0.49,   -0.49,   Gap_Z - Current_Z - 0.5),
                   (-0.49,   0,      Gap_Z - Current_Z - 0.5),
                   (-0.49,   0,      Gap_Z - Current_Z - 1.5),
                   (-0.49,   -0.49,   Gap_Z - Current_Z - 1.5)])
        glEnd()
        # draw "quit" in red, similar to "again"
        glColor((0.9, 0.1, 0.2))
        glBindTexture(GL_TEXTURE_2D, t3)
        glBegin(GL_QUADS)
        draw_quad([(0.49,   0,   Gap_Z - Current_Z - 1.5),
                   (0.49,   0.49, Gap_Z - Current_Z - 1.5),
                   (0.49,   0.49, Gap_Z - Current_Z - 0.5),
                   (0.49,   0,   Gap_Z - Current_Z - 0.5)])
        glEnd()
        # disable transparency for next loop
        glDisable(GL_BLEND)
        # update display
        pg.display.flip()
        # check for key press
        for event in pg.event.get():
            # quit
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                return 0
            # mouse click
            if event.type == MOUSEBUTTONDOWN:
                # mouse click position
                x, y = event.pos
                # quit if click position above the principal diagonal
                if x * Size[1] > y * Size[0]:
                    return 0
                # restart if it is below the diagonal
                return 2
    return 0


def stop():
    """Close the modules that were initialised, before stopping execution.
    :return: nothing."""

    pg.quit()


def get_dx_dy():
    """Get a weak vector to decide how the camera must move in the current frame.
    :returns : dx, dy indicating the distance to be moved in x and y directions respectively."""

    global Current_X, Current_Y, Size, x_low, x_high, y_low, y_high
    # current mouse pointer position
    x, y = pg.mouse.get_pos()

    # center of screen is reference
    # Note that y axis of pygame and OpenGL are opposite to each other. So minus not required
    dx = -round((x - Size[0] // 2) / (2.0 * Size[0]), 4)
    dy = round((y - Size[1] // 2) / (2.0 * Size[1]), 4)

    # keep Current_X and Current_Y in bounds
    # moving left
    if dx < 0 and Current_X + dx < x_low:
        dx = x_low - Current_X
    # moving right
    if dx > 0 and Current_X + dx > x_high:
        dx = x_high - Current_X
    # moving down
    if dy < 0 and Current_Y + dy < y_low:
        dy = y_low - Current_Y
    # moving up
    if dy > 0 and Current_Y + dy > y_high:
        dy = y_high - Current_Y

    # update current position
    Current_X += dx
    Current_Y += dy
    return dx, dy


def update_boundaries():
    """Update the boundaries and draw them.
    :return: nothing."""

    global Boundaries
    # update boundaries to check if the player has crossed them
    for boundary in Boundaries:
        boundary.update()
    # delete passed boundaries and initialize them to new ones
    while Boundaries[0].has_passed:
        Boundaries.append(Boundaries.popleft())
        Boundary.__init__(Boundaries[-1])
    # draw all boundaries
    glBegin(GL_QUADS)
    for boundary in Boundaries:
        boundary.draw()
    glEnd()


def update_obstacles():
    """Update the obstacles and delete the ones that are behind and check if any obstacle is hit.
    :return: True if any obstacle is hit, False otherwise."""

    global Obstacles, Next_Obstacle, Deleted_obstacles
    if abs(Next_Obstacle) < Speed / 2:
        # set timer for next obstacle
        Next_Obstacle = random.randint(2, 5)
        # create a new obstacle
        if not Deleted_obstacles:
            # no obstacle available to reuse, create new
            Obstacles.append(Obstacle())
        else:
            # reinitialise and use a deleted obstacle
            Obstacle.__init__(Deleted_obstacles[-1])
            Obstacles.append(Deleted_obstacles.pop())
    else:
        # reduce waiting time
        Next_Obstacle -= Speed
    k = False
    for obstacle in Obstacles:
        # check if current position collides with an obstacle
        if obstacle.collide():
            k = True
        # update the obstacle
        obstacle.update()
    while Obstacles and Obstacles[0].has_passed:
        # it's out of the field of view, delete
        Deleted_obstacles.append(Obstacles.popleft())
    # draw all obstacles
    glBegin(GL_QUADS)
    for obstacle in Obstacles:
        obstacle.draw()
    glEnd()
    return k


def generate_play_button():
    """Generate the play button.
    :return: nothing."""

    global Play_button_texture
    # set size and create surface
    size = (100, 100)
    t = pg.Surface(size, SRCALPHA)
    # clear background
    t.fill((0, 0, 0, 0))
    # draw circle and triangle
    pg.draw.circle(t, (200, 200, 200, 200), (50, 50), 40, 10)
    pg.draw.polygon(t, (200, 200, 200, 200), ((70, 50), (40, 70), (40, 30)), 0)
    
    # convert image to string
    t = pg.image.tostring(t, "RGBA", True)
    # create new texture
    Play_button_texture = glGenTextures(1)
    # bind it
    glBindTexture(GL_TEXTURE_2D, Play_button_texture)
    # set parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    # add image to texture
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, size[0], size[1], 0, GL_RGBA, GL_UNSIGNED_BYTE, t)


def generate_texture():
    """Generate the shaded texture to be mapped to boundary and obstacles.
    :return: nothing."""

    global texture
    # size
    size = (100, 100)
    # white surface reflects the color indicated by glColor
    t = pg.Surface(size)
    t.fill((255, 255, 255))
    # another surface to draw patterns with transparency
    m = pg.Surface(size, SRCALPHA)
    # draw black transparent squares to get shades
    for i in range(9, 31):
        m.fill((0, 0, 0, 0))
        pg.draw.rect(m, (0, 0, 0, 30 + i / 2.0),
                     (i * size[0] / 100.0, i * size[1] / 100.0,
                      size[0] - size[0] / 50.0 * i,
                      size[1] - size[1] / 50.0 * i), 0)
        t.blit(m, (0, 0))
    # convert image to string
    t = pg.image.tostring(t, "RGBA", True)
    # create new texture
    texture = glGenTextures(1)
    # bind it
    glBindTexture(GL_TEXTURE_2D, texture)
    # set parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    # add image to texture
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, size[0], size[1], 0, GL_RGBA, GL_UNSIGNED_BYTE, t)


def string_to_texture(s):
    """Create a texture of the string that can be displayed on a quad.
    :param s: string to be displayed.
    :returns: texture object and aspect ratio."""

    # create a font object and render the text on a pygame surface
    font = pg.font.Font("font"+str(random.randint(0, 4))+".ttf", 150).render(s, True, (255, 255, 255, 255))
    # size of surface
    sx, sy = font.get_width(), font.get_height()
    # convert the surface to RGBA string
    data = pg.image.tostring(font, "RGBA", True)
    # create new texture
    text = glGenTextures(1)
    # bind it to 2D texture
    glBindTexture(GL_TEXTURE_2D, text)
    # set parameters for different sized mapping
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    # add image to texture
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, sx, sy, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    return text, float(sy) / sx


def change_color():
    """Change color of boundary and obstacles with time.
    :return: nothing."""

    global game_color, Color_change, Next_color, Color_difference
    if Color_change:        # wait to change
        Color_change -= 1   # reduce wait time
    else:
        if Next_color:          # if transition going on
            Next_color -= 1     # modify color
            game_color += Color_difference
            # check if it is black
            if (game_color < np.array((0.2,))).all():
                game_color += 0.5
        else:   # transition complete
            Color_change = random.randint(100, 200)     # set new color and transition parameters
            Next_color = random.randint(50, 100)
            Color_difference = ((random.random() - game_color[0]) / Next_color,
                                (random.random() - game_color[1]) / Next_color,
                                (random.random() - game_color[2]) / Next_color)


def clear():
    """Utility function to clear buffers.
    :return: nothing."""

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


def draw_quad(face):
    """Draws a quad with corresponding texture.
    :param face: the quad to be drawn.
    :return: nothing."""

    for i in range(4):
        # indicate the texture point
        glTexCoord2fv(Texture_corners[i])
        # draw the corresponding vertex
        glVertex3fv(face[i][:3])


def draw_cube(cube):
    """Draws all faces of cube.
    :param cube: list of faces.
    :return: nothing."""

    for face in cube:
        # use draw_quad to draw the faces
        draw_quad(face)


def collide_cube(cube):
    """Test if the current position collides with an obstacle.
    :parameter cube: the boundary of an obstacle.
    :return: boolean value which is true if any of the points corresponding to current position is inside cube."""

    global Current_X, Current_Y, Current_Z
    # points to be tested
    points = [(-Current_X + x, -Current_Y + y)
              for x in [Cube_size * 2 - Bound, Bound - Cube_size * 2]
              for y in [Cube_size * 2 - Bound, Bound - Cube_size * 2]]

    # get min and max values of x, y, z
    x, y, z = set(), set(), set()
    for face in cube:
        for vertex in face:
            x.add(vertex[0])
            y.add(vertex[1])
            z.add(vertex[2])
    x1, x2 = sorted(x)
    y1, y2 = sorted(y)
    z1, z2 = sorted(z)

    # check if Current_Z is relevant
    if z1 + Cube_size / 3.0 <= Gap_Z - Current_Z <= z2 - Cube_size / 3.0:
        # test if points are in the square
        for x, y in points:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return True
    return False


def translation_matrix(d):
    """Transformation matrix to move a point from (x, y, z) to (dx, dy, dz).
    :parameter d: packed dx, dy, dz.
    :return: transformation matrix."""

    dx, dy, dz = d
    return np.array(((1,        0,      0,      0),
                     (0,        1,      0,      0),
                     (0,        0,      1,      0),
                     (dx,       dy,     dz,     1)))


if __name__ == "__main__":
    start("No Fire, No Mountain. But RUN RUN RUN :P")
    kl = 1
    while kl:
        kl = play()
        if kl == 2:
            restart()
    stop()

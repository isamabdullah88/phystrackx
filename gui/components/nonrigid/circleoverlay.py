from math import floor, ceil
import cv2
import numpy as np
from PIL import Image, ImageDraw

def circilize(width, height):
    """Create a fully transparent image (RGBA)"""
    if width < 5: width = 5
    if height < 5: height = 5

    image = Image.new("RGB", (width, height), (0, 0, 0, 0))

    # Create a drawing context
    draw = ImageDraw.Draw(image)

    # Define circle parameters
    circle_bounds = (0, 0, width, height)  # (left, top, right, bottom)
    circle_color = (255, 255, 255)     # Red color with 50% opacity

    # Draw the circle (ellipse) on the transparent background
    draw.ellipse(circle_bounds, fill=circle_color)

    matte = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
    matte[matte < 150] = 0

    circle_color = (255, 0, 0)     # Red color with 50% opacity
    draw.ellipse(circle_bounds, fill=circle_color)

    return np.array(image), matte



def fcrop_coords(frame, center, x):
    """
    Generates dynamic circle based on user's position x and center. Handles out of view cases.
    """
    cx, cy = center
    ex, ey = x

    radx = 2*abs(ex - cx)
    rady = 2*abs(ey - cy)
    
    circ, matte = circilize(radx, rady)
    
    height, width = frame.shape[:2]
    
    frame = frame.copy()

    cysrt = cy-floor(rady/2)
    cyend = cy+ceil(rady/2)
    cxsrt = cx-floor(radx/2)
    cxend = cx+ceil(radx/2)

    if cxsrt < 0:
        circ = circ[:,-cxsrt:]
        matte = matte[:,-cxsrt:]
        cxsrt = 0

    if cxend > width:
        cxend = width
        circ = circ[:,:cxend-cxsrt]
        matte = matte[:,:cxend-cxsrt]

    if cysrt < 0:
        circ = circ[-cysrt:,:]
        matte = matte[-cysrt:,:]
        cysrt = 0

    if cyend > height:
        cyend = height
        circ = circ[:cyend-cysrt, :radx]
        matte = matte[:cyend-cysrt, :radx]

    frame_crop = frame[cysrt:cyend, cxsrt:cxend]

    frame_cropbd = cv2.addWeighted(frame_crop, 0.6, circ, 0.4, 0)
    frame_cropbd[matte < 150] = frame_crop[matte < 150]
    
    matte_frame = np.zeros((height, width), np.uint8)
    matte_frame[cysrt:cyend, cxsrt:cxend] = matte
    frame[cysrt:cyend, cxsrt:cxend] = frame_cropbd

    return frame, matte_frame

def drawcircle(self):
        
    def ondown(event):
        self.ccoords = (event.x-self.fx, event.y-self.fy)
        
        self.photo = ImageTk.PhotoImage(circilize(10, 10))
        
        self.videoview.itemconfig(self.imgview, image=self.photo)
        
    def incircle(event):
        ex = (event.x-self.fx)
        ey = (event.y-self.fy)

        frame, mask = fcrop_coords(self._frame, self.ccoords, (ex, ey))

        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._mask = mask

        self.videoview.itemconfig(self.imgview, image=self.photo)
        

    self.videoview.bind("<Button-1>", ondown)
    self.videoview.bind("<B1-Motion>", incircle)
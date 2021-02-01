# functions used in tem.ipynb
# Akshay Trikha, Katie Partington
# 4th November, 2020

import cv2 as cv                   # OpenCV for image processing
import matplotlib.pyplot as plt    # Matplotlib for visualizing
import numpy as np                 # NumPy for quick maths
from collections import Counter    # dictionary quick maths

### constants
# nm_per_pixel = 100 / 46   # In Challenge_1.jpg there are 92 pixels per 200nm = 46 pixels per 100 nm
# nm_per_pixel = 100 / 95 	
# nm_per_pixel = 1000 / 131 # In 500nm_epoxy_2.jpg there are 131 pixels per 1 micrometer 
# nm_per_pixel = 100 / 113 	# In TES-II-36a.tif there are 113 pixels per 100 nm
nm_per_pixel = 500 / 108 	# In 500nm_epoxy_15.jpg there are 108 pixels per 0.5 micrometer
expected_radius = 250 # in nm


def display_images(images, titles, grayscales):
    """takes in list of images, list of titles, list of boolean grayscales and displays them"""
    if len(images) == 1:
        fig, axs = plt.subplots(1, 1, figsize=(10,10))
        plt.imshow(images[0], cmap=plt.cm.gray)
        axs.set_title(titles[0])
    else:
        fig, axs = plt.subplots(1, len(images), figsize=(15,15))

        # loop through images and display
        for i in range(len(images)):
            # axs[i].imshow(images[i], cmap=plt.cm.gray)
            # axs[i].set_title(titles[i])
            if grayscales[i]:
                axs[i].imshow(images[i], cmap=plt.cm.gray)
                axs[i].set_title(titles[i])
            else:
                axs[i].imshow(images[i])
                axs[i].set_title(titles[i])


# TODO: delete since it's context based?
def save_images(images, titles):
    for i in range(len(images)):
        plt.savefig(str(images[i]) + "_" + titles[i] + ".png", dpi=500)


def get_threshold(threshold):
    """TODO: returns automatic thresholding of grayscale image"""
    return threshold


def setup(image_name, threshold, extra_display):
    """perform setup steps: grayscale, gaussian blur, binary threshold, noise removel, dilation, distance transform"""

    # get color and grayscale images
    color_image = cv.imread(image_name)
    gray_image = cv.cvtColor(color_image, cv.COLOR_BGR2GRAY)

    # apply gaussian blur transformation to grayscale image
    blur = cv.GaussianBlur(gray_image, (0,0) ,cv.BORDER_DEFAULT) 
        
    # apply binary threshold transformation to grayscale image
    ret, thresh = cv.threshold(blur, get_threshold(threshold), 255, cv.THRESH_BINARY_INV)

    # noise removal
    kernel = np.ones((10,10),np.uint8)
    opening = cv.morphologyEx(thresh, cv.MORPH_OPEN, kernel, iterations=2)

    # Finding distance transform - lighter spots mean further away from contours
    dist_transform = cv.distanceTransform(opening,cv.DIST_L2, 5) # mask size needs to be 0 or 3 or 5

    # sure background area
    sure_bg = cv.dilate(opening, kernel, iterations=3)

    # display all substeps if desired 
    if extra_display:
        display_images([color_image, gray_image], ["Color Image", "Grayscale Image"], [0,1])
        display_images([blur], ["Gaussian Blur"], [1])
        display_images([thresh], ["Binary Threshold of " + str(ret)], [1])
    display_images([dist_transform, sure_bg], ["Distance Transform", "Sure Background"], [0, 1])

    return color_image, dist_transform, sure_bg


def get_watershed_markers(dist_transform, dist_transform_thresh, sure_bg, color_image, display):
    """obtains watershed markers by thresholding distance transform"""
    threshold, fg = cv.threshold(dist_transform, dist_transform_thresh*dist_transform.max(), 255, 0)

    # Finding unknown region
    fg = np.uint8(fg)
    unknown_2 = cv.subtract(sure_bg, fg)
    
    # Marker labelling
    threshold, pre_watershed_markers = cv.connectedComponents(fg)
    # Add one to all labels so that sure background is not 0, but 1
    pre_watershed_markers = pre_watershed_markers+1
    # Now, mark the region of unknown with zero
    pre_watershed_markers[unknown_2==255] = 0

    # copy input image
    watershed_color_copy = color_image.copy()

    watershed_markers = cv.watershed(watershed_color_copy, pre_watershed_markers)

    if display:
        display_images([pre_watershed_markers, watershed_markers], ["Pre-Watershed Markers", "Watershed Markers"], [0,0])

    return watershed_markers


def get_areas(watershed_markers):
    """get the areas of the particles"""

    # dictionary mapping colors to their areas
    particle_areas = {}

    # loop through pixels in watershed markers and count the number of pixels for each color
    for row in range(1, len(watershed_markers) - 1):
        for col in range(1, len(watershed_markers[0]) - 1):
            # if pixel not in background
            if watershed_markers[row][col] != 1:
                # get current pixel and its neighbours 
                current = watershed_markers[row][col]
                # add current pixel to dictionary
                if current not in particle_areas:
                    particle_areas[current] = 1
                else:
                    particle_areas[current] += 1

    # remove -1 key from particle_areas because it represents contours drawn by cv.watershed()
    if -1 in particle_areas:
        del particle_areas[-1]

    # loop to adjust areas from number of pixels to nm^2
    for particle in particle_areas:
        current_area = particle_areas[particle] * nm_per_pixel**2
        particle_areas[particle] = current_area

    return particle_areas


# TODO: differentiate parameters and variable names
def get_watershed_threshold(dist_transform, sure_bg, color_image, expected_radius):
    """outputs optimal threshold for thresholding distance transform to obtain separated particles (not agglomerates)"""
    max_radius = 3*expected_radius
    dist_transform_thresh = 0.25
    while max_radius > (2*expected_radius):

        watershed_markers = get_watershed_markers(dist_transform, dist_transform_thresh, sure_bg, color_image, 0)
        
        # dictionary mapping colors to their pixels
        particle_colors = {}

        # loop through pixels in watershed markers
        for row in range(1, len(watershed_markers) - 1):
            for col in range(1, len(watershed_markers[0]) - 1):
                # if pixel not in background
                if watershed_markers[row][col] != 1:
                    # get current pixel and its neighbours 
                    current = watershed_markers[row][col]
                    # add current pixel to dictionary
                    if current not in particle_colors:
                        particle_colors[current] = 1
                    else:
                        particle_colors[current] += 1

        # remove -1 key from particle_colors because it represents bad contours drawn by cv.watershed()
        if -1 in particle_colors:
            del particle_colors[-1]

        # loop to adjust areas from number of pixels to nm^2
        max_radius = 0
        for particle in particle_colors:
            current_area = particle_colors[particle] * nm_per_pixel**2
            particle_colors[particle] = [current_area, (current_area/np.pi)**0.5]
            if (current_area/np.pi)**0.5 > max_radius:
                max_radius = (current_area/np.pi)**0.5
                
        # print(dist_transform_thresh, max_radius)
                
        dist_transform_thresh += 0.05

    return dist_transform_thresh - 0.05 # TODO this seems bad

    # TODO: just loop through the output of watershed markers, where the border pixel are already marked with -1 and see what pixels they neighbor
def get_contour_colors(watershed_markers, color_image):
    """returns dictionary mapping colors to their pixels"""
    # copy input image
    chords_color_copy = color_image.copy() 

    # output
    contour_colors = {}

    contour_size = 0
    # loop through pixels in watershed markers
    for row in range(1, len(watershed_markers) - 1):		# TODO: don't ignore border particles
        for col in range(1, len(watershed_markers[0]) - 1):	# TODO: don't ignore border particles
            # if pixel not in background
            if watershed_markers[row][col] != 1:
                # get current pixel and its neighbours 
                current = watershed_markers[row][col]	
                up = watershed_markers[row-1][col]
                down = watershed_markers[row+1][col]
                left = watershed_markers[row][col-1]
                right = watershed_markers[row][col+1]
                # if not surrounded by uniform pixels
                if ((up != current) or (down != current) or (left != current) or (right != current)):
                    # if the right pixel is different
                    if (right != current):
                        # add current pixel to dictionary
                        if current not in contour_colors:
                            contour_colors[current] = [(col, row)]	# pixels are appended as (col, row) in order to feed to cv.lines() later on
                        else:
                            contour_colors[current] += [(col,row)]
                        
                        # if the right pixel is not in background, add it to the dictionary
                        if (right != 1):
                            if right not in contour_colors:
                                contour_colors[right] = [(col+1, row)]
                            else:
                                contour_colors[right] += [(col+1,row)]
                            chords_color_copy[row][col+1] = [255, 0, 0]
                            contour_size += 1
                            
                        chords_color_copy[row][col] = [255, 0, 0]	# TODO: why do we need chord_color_copy if we already have watershed_color_copy
                        contour_size += 1
                        
                    # if the down pixel is different
                    elif (down != current):
                        # add current pixel to dictionary
                        if current not in contour_colors:
                            contour_colors[current] = [(col, row)]
                        else:
                            contour_colors[current] += [(col,row)]
                        
                        # if the down pixel is not in background, add it to the dictionary
                        if (down != 1):
                            if down not in contour_colors:
                                contour_colors[down] = [(col, row+1)]
                            else:
                                contour_colors[down] += [(col,row+1)]
                            chords_color_copy[row+1][col] = [255, 0, 0]
                            contour_size += 1
                            
                        chords_color_copy[row][col] = [255, 0, 0]
                        contour_size += 1
                    
                    # if the up or left pixel is different than the current pixel and is not a border pixel
                    elif (((up != 255) and (up != current)) or ((left != 255) and (left != current))):
                        # add current pixel to dictionary
                        if current not in contour_colors:
                            contour_colors[current] = [(col, row)]
                        else:
                            contour_colors[current] += [(col,row)]
                            
                        chords_color_copy[row][col] = [255, 0, 0]                    
                        contour_size += 1

    # remove -1 key from contour_colors because it represents contours drawn by cv.watershed()
    if -1 in contour_colors:
        del contour_colors[-1]

    return contour_colors, chords_color_copy


def find_centerpoints(contour_colors):
    """calculates the centerpoint for each color"""

    # maps each particle to its extracted information
    particles = {}

    # loop through the particles
    for color in contour_colors:
        color_pixels = contour_colors[color]
        sum_x = 0
        sum_y = 0

        # add x and y coordinates to running sum for particle
        for pixel in color_pixels:
            sum_x += pixel[0]
            sum_y += pixel[1]

        # add x and y centerpoints to particles dictionary, accounting for nm per pixel
        center_x = sum_x / len(color_pixels)
        center_y = sum_y / len(color_pixels)
        particles[color] = [("x", center_x*nm_per_pixel)]
        particles[color] += [("y", center_y*nm_per_pixel)]

    return particles


def match_images(particles, contour_colors, agg_particles, agg_contour_colors, agg_areas):
    """Replaces agglomerates with particles and outputs a single dictionary"""
    out_contour_colors = {}
    out_particles = {}
    max_color = np.max(list(agg_particles.keys()))

    # loop through agglomerate particles
    for agg_particle in agg_particles:

        # if particle has a radius more than twice expected size
        if agg_areas[agg_particle] > np.pi*(expected_radius*2)**2:
            # then particle is agglomerate
        
            # find max and min x and y for given agglomerate
            # TODO: make this 100000000x better using numpy
            max_x = 0
            max_y = 0
            min_x = 10000
            min_y = 10000
            for pixel in agg_contour_colors[agg_particle]:
                if pixel[0] > max_x:
                    max_x = pixel[0]
                if pixel[1] > max_y:
                    max_y = pixel[1]
                if pixel[0] < min_x:
                    min_x = pixel[0]
                if pixel[1] < min_y:
                    min_y = pixel[1]

            # collect list of particles in particles dictionary that fall within agglomerate
            replacements = []
            for particle in particles:
                x = particles[particle][0][1]
                y = particles[particle][1][1]
                if ((x < max_x) and (x > min_x) and (y < max_y) and (y > min_y)):
                    replacements += [particle]

            # add particles to output dictionaries
            for i in range(len(replacements)):
                out_particles[max_color+i] = particles[replacements[i]]
                out_contour_colors[max_color+i] = contour_colors[replacements[i]]

            # update max color
            max_color += len(replacements)
        
        else:
            out_particles[agg_particle] = agg_particles[agg_particle]
            out_contour_colors[agg_particle] = agg_contour_colors[agg_particle]
        
    return out_particles, out_contour_colors


    # input pixels as tuples
def pixel_distance(pixel1, pixel2):
    """finds the distance between two pixels"""
    return np.power(np.power(pixel1[0] - pixel2[0], 2) + np.power(pixel1[1] - pixel2[1], 2), 0.5)


    #TODO: adjust output to account for change in the order in which extracted information is added to the dictionary
def get_long_chord_lengths(particles, contour_colors):
    """finds the long chord lengths for the contours and returns them as pairs of pixel coordinates"""

    # keep track of maximum chord length found
    max_chord = 0

    # store long pairs as [[color, (start pixel), (end pixel)]]
    long_pairs = []
    # loop through all colors
    for color in contour_colors:
        # loop through all pixels in a color
        color_pixels = contour_colors[color]
        current_max = 0
        for i in range(len(color_pixels)):
            for j in range(len(color_pixels[i:])):
                distance = pixel_distance(color_pixels[i], color_pixels[j])
                if distance > current_max:
                    current_max = distance
                    long_pair = [color, color_pixels[i], color_pixels[j]]
        # keep track of long chord length pair for each color 
        long_pairs += [long_pair]
        # add to particles dictionary, accounting for nm per pixel
        particles[color] += [("a", (current_max / 2) * nm_per_pixel)]
        
        if current_max > max_chord:
            max_chord = current_max

    return long_pairs, particles


def get_short_chord_lengths(particles, contour_colors, long_pairs):
    """finds the short chord lengths for the contours given the long pairs and returns them as pairs of pixel coordinates"""

    # store short chord length pair of points once found
    short_pixels = []
    # store scores (observed perpendicular slope vs. actual perpendicular slope)
    scores = []
    # keep track of each particle's centerpoints
    centerpoints = []
    # keep track of max x,y coordinates
    max_x = 0
    max_y = 0

    # loop through long pairs to get midpoint for each pair and then perpendicular short pairs
    for pair in long_pairs:
        # get all pixels of a color
        current_pixels = contour_colors[pair[0]]
        # get start & end x,y coordinates
        x1 = pair[1][0]
        y1 = pair[1][1]
        x2 = pair[2][0]
        y2 = pair[2][1]
        # calculate slope as rise over run
        slope = (y2-y1) / (x2-x1)
        # calculate orthogonal slope
        orthogonal_slope = -1 / slope
        # check which pixel start, which is end and calculate midpoint accordingly 
        if x1 > x2:
            mid_x = x2 + int((x1-x2) / 2)
        else:
            mid_x = x1 + int((x2-x1) / 2)
        if y1 > y2:
            mid_y = y2 + int((y1-y2) / 2)
            # calculate rotation in X-Y plane with long length's slope
            if x1 > x2:
                theta = 360 - np.arctan((y1-y2)/(x1-x2))*(180/np.pi)
            else:
                theta = 180 + np.arctan((y1-y2)/(x2-x1))*(180/np.pi)
        else:
            mid_y = y1 + int((y2-y1) / 2)
            # calculate rotation in X-Y plane with long length's slope
            if slope > 0:
                theta = -1*(180 - (np.arctan(slope)*(180/np.pi)))
            else:
                theta = np.arctan(slope)*(180/np.pi)
        
        # add X-Y rotation angle to particles dictionary
        particles[pair[0]] += [("theta", theta)]
        
        short_pixel = []
        current_score = []
        # loop through all pixels for a color
        for pixel in current_pixels:
            # calculate change in x and y with respect to midpoint for pixel
            dx = pixel[0] - mid_x
            dy = pixel[1] - mid_y
            # change in x cannot be 0
            if dx != 0:
                # compute slope between pixel and midpoint
                comp_slope = dy/dx
                # score ~= ratio of pixel slope / orthogonal slope from long chord length
                score = np.abs(1 - comp_slope / orthogonal_slope)
                # set threshold that pixel slope / orthogonal slope must be < 0.5
                if (score < 0.5):
                    # if pixel isn't already in short_pixel
                    if pixel not in short_pixel:
                        short_pixel += [pixel]
                        current_score += [score]
        
        # record pair of points of short chord length
        short_pixels += [short_pixel]
        # record each pair of points' scores
        scores += [current_score]

    # store min pixel pairs to visualize lines
    short_pairs = []

    # process pairs to keep ones with min score
    for i in range(len(short_pixels)):
        if len(short_pixels[i]) >= 2:
            # first find pixel with overall minimum
            min_index_1 = np.argmin(scores[i])
            min_pixel_1 = short_pixels[i][min_index_1]
            
            # set the minimum distance in pixels to be 3/5 of the expected diameter
            min_distance = (6/5) * expected_radius * (1/nm_per_pixel)

            # now loop through rest of pixels to find far away pixel with low score
            for j in range(len(short_pixels[i])):
                distance = pixel_distance(min_pixel_1, short_pixels[i][j])
                if distance > min_distance:
                    min_pixel_2 = short_pixels[i][j]
                    
                    # store pixels for cv.line() later
                    short_pairs += [(min_pixel_1, min_pixel_2)]
                    
                    # long_pairs[i][0] is current color
                    # add short distance to particles dictionary, accounting for nm per pixel
                    particles[long_pairs[i][0]] += [("b", (distance/2)*nm_per_pixel)]
                    break

    return short_pairs, particles


def draw_long_lengths(image, long_pairs):
    """draws long chord lengths on an image"""
    for long_pair in long_pairs:
        cv.line(image, long_pair[1], long_pair[2], [255,255,0])


def draw_short_lengths(image, short_pairs):
    """draws short chord lengths on an image"""
    for short_pair in short_pairs:
        cv.line(image, short_pair[0], short_pair[1], [0,255,255])


def get_c(particles):
    """sets the c radius for each of the particles to be the average of the a and b radii for that particle"""
    # loop through all the particles
    for particle in particles:
        # get particle data
        particle_data = particles[particle]
        # if the particle has an x and y position, a and b radii, and an angle
        if len(particle_data) == 5:
            # set c radius to be average of a and b radii
            c_radius = (particle_data[2][1] + particle_data[4][1]) / 2
            # add c radius to the particles dictionary
            particles[particle] += [("c", c_radius)]
    return particles


def set_max_c(particles):
    """sets the c radius for each of the particles to be the maximum average of the a and b radii for all of the particles"""
    # keep track of maximum c radius
    max_c = 0
    
    # loop through particles
    for particle in particles:
        # get particle data
        particle_data = particles[particle]
        # if the particle has an x and y position, a and b radii, and an angle
        if len(particle_data) == 5:
            # set c radius to be average of a and b radii
            c_radius = (particle_data[2][1] + particle_data[4][1]) / 2
            # if c radius is the biggest yet
            if c_radius > max_c:
                # update the maximum c radius
                max_c = c_radius
    
    # loop through particles
    for particle in particles:
        particle_data = particles[particle]
        # if the particle has an x and y position, a and b radii, and an angle, set each particle to have the maximum c radius
        if len(particle_data) == 5:
            # add c radius to the particles dictionary
            particles[particle] += [("c", max_c)]
    return particles


def get_layer_info(particles):
    """gets the relevant info from a particle dictionary representing a single layer so that it can be combined with other layers"""
    # keeping track of maximum and minimum x and y positions
    max_x = 0
    min_x = 10000
    max_y = 0
    min_y = 10000
    # keeping track of maximum c radius and the volume of particles in the layer
    max_c = 0
    layer_volume = 0

    # loop through particles
    for particle in particles:
        # get particle data
        particle_data = particles[particle]
        # if the particle has an x and y position, a, b, and c radii, and an angle
        if len(particle_data) == 6:
            # extract particle info
            x = particle_data[0][1]
            y = particle_data[1][1]
            a = particle_data[2][1]
            b = particle_data[4][1]
            c = particle_data[5][1]
            # add the volume of the particle to the layer volume
            layer_volume += (4/3)*np.pi*a*b*c
            
            # update minimum and maximum x and y values
            if (x - a) < min_x:
                min_x = x-a
            if (x + a) > max_x:
                max_x = x+a
            if (y - a) < min_y:
                min_y = y-a
            if (y + a) > max_y:
                max_y = y+a
            # update maximum c radius
            if c > max_c:
                max_c = c

    # set x and y lengths of the layer 
    x_length = max_x - min_x
    y_length = max_y - min_y
    
    # find volume fraction of the layer
    volume_fraction = layer_volume/(x_length*y_length*max_c*2)

    return [x_length, y_length, min_x, min_y, max_c, layer_volume, volume_fraction]


def plot_ellipsoid(a_radius, b_radius, c_radius, center_x, center_y, center_z, theta, ax, rendering_type):
    """plots an ellipsoid with the given properties"""
    
    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, np.pi, 100)

    # converting theta from degrees to radians
    theta = theta/180*np.pi

    x1_1 = np.outer(a * np.cos(u), np.sin(v)) + center_x
    y1_1 = np.outer(b * np.sin(u), np.sin(v)) + center_y
    z = np.outer(c * np.ones(np.size(u)), np.cos(v)) + center_z
    x = np.cos(theta) * (x1_1 - cx) - np.sin(theta) * (y1_1 - cy) + center_x
    y = np.sin(theta) * (x1_1 - cx) + np.cos(theta) * (y1_1 - cy) + center_y

    if rendering_type == "surface":
    #colored ellipsoid -- here the particles look like colored balloons: pretty but takes a couple extra seconds to run.
        ax[0].plot_surface(x, y, z, linewidth=0.0)
        ax[1].plot_surface(x, y, z, linewidth=0.0)
        ax[2].plot_surface(x, y, z, linewidth=0.0)

    if renering_type == "wireframe":
    #wireframe rendering -- this is a mesh sort of look. Runs more quickly.
        ax[0].plot_wireframe(x, y, z, rstride=25, cstride=25, color='b', alpha=0.3)
        ax[1].plot_wireframe(x, y, z, rstride=25, cstride=25, color='b', alpha=0.3)
        ax[2].plot_wireframe(x, y, z, rstride=25, cstride=25, color='b', alpha=0.3)


def layer_render(particles, particle_info, rendering_type="wireframe"):
    """renders a dictionary of particles"""
    fig1 = plt.figure(1)
    fig2 = plt.figure(2)
    fig3 = plt.figure(3)

    # ax = fig1.add_subplot(111, projection='3d')
    ax = Axes3D(fig1)
    ax.set_xlabel("$X$", fontsize = 20, rotation = 150)
    ax.set_ylabel("$Y$", fontsize = 20, rotation = 150)
    ax.set_zlabel("$Z$", fontsize = 20, rotation = 150)

    # ay = fig2.add_subplot(111, projection='3d')
    ay = Axes3D(fig2)
    ay.set_xlabel("$X$", fontsize = 20, rotation = 150)
    ay.set_ylabel("$Y$", fontsize = 20, rotation = 150)
    ay.set_zlabel("$Z$", fontsize = 20, rotation = 150)

    # az = fig3.add_subplot(111, projection='3d')
    az = Axes3D(fig3)
    az.set_xlabel("$X$", fontsize = 20, rotation = 150)
    az.set_ylabel("$Y$", fontsize = 20, rotation = 150)
    az.set_zlabel("$Z$", fontsize = 20, rotation = 150)

    ax.view_init(elev=0, azim=0)
    ay.view_init(elev=0, azim=-90)
    az.view_init(elev=90, azim=-90)

    for particle in particles:
        # get particle data
        particle_data = particles[particle]
        # if the particle has an x and y position, a, b, and c radii, and an angle
        if len(particle_data) == 6:
            # extract particle info
            x = particle_data[0][1]
            y = particle_data[1][1]
            a = particle_data[2][1]
            b = particle_data[4][1]
            c = particle_data[5][1]
            theta = particle_data[6][1]
            z = (particle_info[4]/2)+1
            
            # plot the ellipsoid
            plot_ellipsoid(a, b, c, x, y, z, theta, [ax, ay, az], rendering_type)

    for axis in 'xyz':
        getattr(ax, 'set_{}lim'.format(axis))((0, 1817.9594305919986-52.63010653047917))
        getattr(ay, 'set_{}lim'.format(axis))((0, 1817.9594305919986-52.63010653047917))
        getattr(az, 'set_{}lim'.format(axis))((0, 1817.9594305919986-52.63010653047917))

    plt.show()


def combine_layers(particle_layers, layer_infos, filename):
    """creating a text file from layer(s)"""
    # open the file to write in
    with open(filename, "w") as output_file:
        # keeping track height, volume, and x and y lengths of prism
        total_height = 1
        total_volume = 0
        x_length_prism = 0
        y_length_prism = 0
        # keeping track of the height of each layer
        layer_heights = []
        # TODO: do this better
        x_position_prism = 100000000000
        y_position_prism = 100000000000
        # looping through the layer(s)
        for info in layer_infos:
            total_height += ((info[4]*2) + 1)
            layer_heights += [info[4]*2]
            total_volume += info[5]
            # TODO: record max and min x and y values of prism and recalculate x and y lengths
            if info[0] > x_length_prism:
                x_length_prism = info[0]
            if info[1] > y_length_prism:
                y_length_prism = info[1]
            # if x and/or y position are the lowest yet, update the prism x and/or y postion 
            if info[2] < x_position_prism:
                x_position_prism = info[2]
            if info[3] < y_position_prism:
                y_position_prism = info[3]
        # calculate prism volume fraction
        volume_fraction = total_volume/(x_length_prism*y_length_prism*total_height)

        particleID = 1
        layer_counter = 0
        height_adjustment = 1
        # loop through the layers
        for layer in particle_layers:
            # update the current height at which to place particles by adding in half the height of new layer
            current_height = height_adjustment + (layer_heights[layer_counter]/2)
            # loop through the particles
            for particle in layer:
                # get particle data
                particle_data = layer[particle]
                # if the particle has an x and y position, a, b, and c radii, and an angle
                if len(particle_data) == 6:
                    # write all the data for the particle to the text file
                    output_file.writelines(particle_data[2][0] + str(particleID) + " " + str(particle_data[2][1]) + "[nm]" + "\n")       # a
                    output_file.writelines(particle_data[4][0] + str(particleID) + " " + str(particle_data[4][1]) + "[nm]" + "\n")       # b
                    output_file.writelines(particle_data[5][0] + str(particleID) + " " + str(particle_data[5][1]) + "[nm]" + "\n")       # c
                    output_file.writelines(particle_data[0][0] + str(particleID) + " " + str(particle_data[0][1]) + "[nm]" + "\n")       # x
                    output_file.writelines(particle_data[1][0] + str(particleID) + " " + str(particle_data[1][1]) + "[nm]" + "\n")       # y
                    output_file.writelines("z" + str(particleID) + " " + str(current_height) + "[nm]" + "\n")                            # z
                    output_file.writelines(particle_data[3][0] + str(particleID) + " " + str(particle_data[3][1]) + "[degrees]" + "\n")  # theta
                    # increment particleID
                    particleID += 1

            # add the height of the layer we just looped through and a space between layers to the height adjustment
            height_adjustment += (layer_heights[layer_counter] + 1)
            # increment layer counter
            layer_counter += 1

        # write the information for the composite to the end of the file
        output_file.writelines("*****************\n")
        output_file.writelines("total_particles " + str(particleID-1) + "\n")                    # number of particles
        output_file.writelines("total_volume_ellipsoids " + str(total_volume) + "[nm^3]" + "\n") # total volume
        output_file.writelines("x_length_prism " + str(x_length_prism) + "[nm]" + "\n")          # x length prism
        output_file.writelines("y_length_prism " + str(y_length_prism) + "[nm]" + "\n")          # y length prism
        output_file.writelines("z_length_prism " + str(total_height) + "[nm]" + "\n")            # z length prism
        output_file.writelines("x_position_prism " + str(x_position_prism) + "[nm]" + "\n")      # x position prism
        output_file.writelines("y_position_prism " + str(y_position_prism) + "[nm]" + "\n")      # x position prism
        output_file.writelines("volume_fraction " + str(volume_fraction))                        # volume fraction

        # close output file
        output_file.close()

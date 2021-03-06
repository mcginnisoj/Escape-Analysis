﻿import csv
import os
import numpy as np
import math
from matplotlib import pyplot as pl
from matplotlib.cm import ScalarMappable
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.image import AxesImage
from matplotlib.colors import Colormap
import seaborn
import cv2
import toolz
import scipy.ndimage
import imageio
import pickle
from collections import deque
from toolz.itertoolz import sliding_window, partition
from scipy.ndimage import gaussian_filter
from scipy.signal import argrelmin, argrelmax, argrelextrema


# THIS CAN BE USED BUT IT WILL TAKE A LIST OF ESCAPE OBJECTS AND ITERATE THROUGH IT.
# Also much of its current data is useless. 


class Escapes:

    def __init__(self, exp_type, directory, area_thresh):
        self.pre_c = 10
        self.area_thresh = area_thresh
        self.directory = directory
        self.timerange = [100, 150]
        self.condition = exp_type
        self.xy_coords_by_trial = []
    # this asks whether there is a bias in direction based on the HBO. 
        self.pre_escape_bouts = []
        self.stim_init_times = []
        self.escape_latencies = []
        if exp_type in ['l', 'd']:
            bstruct_and_br_label = 'b'
        elif exp_type in ['v', 'i']:
            bstruct_and_br_label = 'v'
        self.barrier_file = np.loadtxt(
            directory + '/barrierstruct_' + bstruct_and_br_label + '.txt',
            dtype='string')
        self.barrier_coordinates = []
        self.barrier_diam = 0
        self.barrier_xy_by_trial = []
        print self.directory
        back_color = cv2.imread(
            directory + '/background_' + bstruct_and_br_label + '.tif')
        print(back_color.shape)
        self.background = cv2.cvtColor(back_color, cv2.COLOR_BGR2GRAY)
        pre_escape_files = sorted([directory + '/' + f_id
                                   for f_id in os.listdir(directory)
                                   if f_id[0:15] == 'fishcoords_gray'
                                   and f_id[-5:-4] == exp_type])
        self.pre_escape = [
            np.loadtxt(pe, dtype='string') for pe in pre_escape_files]
        xy_files = sorted([directory + '/' + f_id
                           for f_id in os.listdir(directory)
                           if f_id[0:4] == 'tapr' and f_id[-5:-4] == exp_type])
        self.xy_escapes = [np.loadtxt(xyf, dtype='string') for xyf in xy_files]
        stim_files = sorted([directory + '/' + f_id
                             for f_id in os.listdir(directory)
                             if f_id[0:4] == 'stim'
                             and f_id[-5:-4] == exp_type])
        self.stim_data = [np.loadtxt(st, dtype='string') for st in stim_files]
        self.movie_id = sorted([directory + '/' + f_id
                                for f_id in os.listdir(directory)
                                if (f_id[-5:] == exp_type+'.AVI'
                                    and f_id[0] == 't')])

# Make these dictionaries so you can put in arbitrary trial / value bindings

        self.cstart_angles = []
        self.cstart_rel_to_barrier = []
        self.collision_prob = []
        self.all_tailangles = []
        self.tailangle_sums = []
        self.ha_in_timeframe = []
        self.ba_in_timeframe = []
        self.h_vs_b_by_trial = []
        self.initial_conditions = []
        self.load_experiment()

    def load_experiment(self):
        self.get_xy_coords()
        self.load_barrier_info()
        self.get_correct_barrier()
        self.get_stim_times(False)

    def exporter(self):
        with open('escapes' + self.condition + '.pkl', 'wb') as file:
            pickle.dump(self, file)

    def load_barrier_info(self):
        barrier_file = self.barrier_file
        xylist = []
        diam_list = []
        for line, j in enumerate(barrier_file[2:]):
            if line % 2 == 0:
                xylist.append(x_and_y_coord(j))
            else:
                diam_list.append(float(j))
        self.barrier_coordinates = xylist
        self.barrier_diam = np.round(np.mean(diam_list))

    def get_xy_coords(self):
        print self.condition
        for filenum, xy_file in enumerate(self.xy_escapes):
            xcoords = []
            ycoords = []
            for coordstring in xy_file:
                x, y = x_and_y_coord(coordstring)
                xcoords.append(x)
                ycoords.append(y)
            self.xy_coords_by_trial.append([xcoords, ycoords])

#MAKE THIS A NEW FUNCTION THAT CALCULATES THE MOST RECENT 3 BOUTS. 
#         stim_onset = self.timerange[0]
#         for filenum, pre_xy_file in enumerate(self.pre_escape):
#             pre_xcoords = []
#             pre_ycoords = []
#             for coordstring in pre_xy_file:
#                 x, y = x_and_y_coord(coordstring)
#                 pre_xcoords.append(x)
#                 pre_ycoords.append(y)
#             pre_xcoords += self.xy_coords_by_trial[
#                 filenum][0][stim_onset-100:stim_onset]
#             pre_ycoords += self.xy_coords_by_trial[
#                 filenum][1][stim_onset-100:stim_onset]
#             vel_vector = [np.sqrt(
#                 np.dot(
#                     [v2[0]-v1[0], v2[1]-v1[1]],
#                     [v2[0]-v1[0], v2[1]-v1[1]])) for v1, v2 in sliding_window(
#                         2, zip(pre_xcoords, pre_ycoords))]
#             vv_filtered = gaussian_filter(vel_vector, 4)
#             bout_inds = argrelextrema(
#                 np.array(vv_filtered), np.greater_equal,  order=5)[0]
#             if len(bout_inds) != 0:
#                 bi_thresh = [arg for arg in bout_inds if vv_filtered[arg] > 1]
#                 if len(bi_thresh) != 0:
#                     fi = [bi_thresh[0]]
#                 else:
#                     fi = []
#                 bi_norepeats = fi + [b for a, b in sliding_window(
#                     2, bi_thresh) if b-a > 20]
# #                pl.plot(vv_filtered)
#  #               pl.plot(bi_norepeats,
#   #                      np.zeros(len(bi_norepeats)), marker='.')
# #            pl.show()
#             bout_init_position = [[np.nanmean(pre_xcoords[bi-60:bi-10]),
#                                    np.nanmean(pre_ycoords[bi-60:bi-10])]
#                                   for bi in bi_norepeats]
#             bout_post_position = [[np.nanmean(pre_xcoords[bi+50:bi+100]),
#                                    np.nanmean(pre_ycoords[bi+50:bi+100])]
#                                   for bi in bi_norepeats]
#             disp_vecs = [[b[0]-a[0], b[1]-a[1]] for a,
#                          b in zip(bout_init_position, bout_post_position)]
#             dots = [np.dot(i, j) / (magvector(i) * magvector(j))
#                     for i, j in sliding_window(2, disp_vecs)]
#             ang = [np.arccos(a) for a in dots]
#             crosses = [np.cross(i, j) for i, j in sliding_window(2, disp_vecs)]
#             self.pre_escape_bouts.append([ang, crosses])


    def get_stim_times(self, plot_stim):
# There is a 100 pixel wide window surrounding the LED. At first, the LED is in the leftmost 50 pixels. After stim, in rightmost. Have
#        2000 frames of 100 pixel windows, Stim happens after 100 frames. Get exact timing using when the LED reaches steady state.
        # The stimulus itself is 200ms long, and lasts for ~100 frames. The steady state should be taken around 50 frames into the stimulus. 
        stim_times = []
        for stim_file in self.stim_data:
            stimdata = np.genfromtxt(stim_file)
            first_half = [np.mean(a[0:50]) for a in partition(100, stimdata)]
            second_half = [np.mean(a[50:]) for a in partition(100, stimdata)]
            steady_state_resting = np.mean(second_half[140:160])
            indices_greater_than_ss = [i for i, j in enumerate(second_half)
                                       if j > steady_state_resting]
            first_cross = indices_greater_than_ss[0]
            zero_first_half = first_half.index(0)
#            print first_cross
#            print zero_first_half
            #raw image really does hit absolute zero as a mean. that's incredible. 
            stim_times.append(
                np.ceil(np.median([first_cross, zero_first_half])))
            if plot_stim:
                pl.plot(first_half)
                pl.plot(second_half)
                pl.show()
        self.stim_init_times = [x-self.timerange[0] for x in stim_times]

    def get_correct_barrier(self):
        for coords in self.xy_coords_by_trial:
            mag_distance = []
            init_x = coords[0][self.timerange[0]]
            init_y = coords[1][self.timerange[0]]
            for barr_xy in self.barrier_coordinates:
                temp_distance = np.sqrt(
                    (barr_xy[0]-init_x)**2 + (barr_xy[1] - init_y)**2)
                mag_distance.append(temp_distance)
            correct_barrier_index = np.argmin(mag_distance)
            self.barrier_xy_by_trial.append(self.barrier_coordinates[
                    correct_barrier_index])

    def plot_xy_trial(self, trialnum):
        fig = pl.figure()
        barrier_x = self.barrier_xy_by_trial[trialnum][0]
        barrier_y = self.barrier_xy_by_trial[trialnum][1]
        barrier_diameter = self.barrier_diam
        xcoords = self.xy_coords_by_trial[trialnum][0]
        ycoords = self.xy_coords_by_trial[trialnum][1]
        axes = fig.add_subplot(111, axisbg='.75')
        barrier_plot = pl.Circle((barrier_x, barrier_y),
                                 barrier_diameter / 2, fc='r')
        axes.add_artist(barrier_plot)
        axes.grid(False)

# see if you can use colorline for more than just the xy coords. would be nice to plot all escapes this way, and be able to pass the cmap as an arg to colorline
        colorline(
            np.array(xcoords[self.timerange[0]:self.timerange[1]]),
            np.array(ycoords[self.timerange[0]:self.timerange[1]]))
        axes.set_xlim(barrier_x - 200, barrier_x + 200)
        axes.set_ylim(barrier_y - 200, barrier_y + 200)
        axes.set_aspect('equal')
        colo = ScalarMappable(cmap='afmhot')
        colo.set_array(
            np.arange(
                float(self.timerange[0]) / 500, float(self.timerange[1]) / 500,
                .1))
        pl.colorbar(colo)
        pl.title('Trial' + str(trialnum))
        pl.show()

    def get_orientation(self, makevid):
        for trial, (vid_file, xy) in enumerate(
                zip(self.movie_id, self.xy_coords_by_trial)):
            heading_vec_list = []
            fps = 500
            vid = imageio.get_reader(vid_file, 'ffmpeg')
            fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
            dr = self.directory
            if makevid:
                ha_vid = cv2.VideoWriter(
                    dr + '/ha' + str(trial) + self.condition + '.AVI',
                    fourcc, fps, (80, 80), True)
                thresh_vid = cv2.VideoWriter(
                    dr + '/thresh' + str(trial) + self.condition + '.AVI',
                    fourcc, fps, (80, 80), True)
            xcoords = xy[0][self.timerange[0]:self.timerange[1]]
            ycoords = xy[1][self.timerange[0]:self.timerange[1]]
    # the arrays are indexed in reverse from how you'd like to plot.
            for frame, (x, y) in enumerate(zip(xcoords, ycoords)):
                y = 1024 - y
                im_color = vid.get_data(self.timerange[0] + frame)
                im = cv2.cvtColor(im_color, cv2.COLOR_BGR2GRAY)
                background_roi = slice_background(self.background, x, y)
                brsub = cv2.absdiff(im, background_roi).astype(np.uint8)

                    # fig = pl.figure()
                    # ax = fig.add_subplot(121)
                    # ax2 = fig.add_subplot(122)
                    # ax.imshow(background_roi, 'gray', vmin=0, vmax=255)
                    # ax2.imshow(im, 'gray', vmin=0, vmax=255)
                    # pl.show()
                fishcont, mid_x, mid_y, th = self.contourfinder(brsub, 30)
                th = cv2.cvtColor(th, cv2.COLOR_GRAY2RGB)
                if math.isnan(mid_x):
                    if makevid:
                        ha_vid.write(im_color)
                        thresh_vid.write(th)
                    heading_vec_list.append([mid_x, mid_y])
                    continue
                fish_xy_moments = cv2.moments(fishcont)
                fish_com_x = int(fish_xy_moments['m10']/fish_xy_moments['m00'])
                fish_com_y = int(fish_xy_moments['m01']/fish_xy_moments['m00'])
                mask = np.ones(im.shape, dtype=np.uint8)
                winsize = 3
                for i in range(fish_com_y - winsize, fish_com_y + winsize):
                    for j in range(fish_com_x - winsize, fish_com_x + winsize):
                        mask[i, j] = 0
                cv2.multiply(brsub, mask, brsub)
                eyes_x, eyes_y = find_darkest_pixel(brsub)
                cv2.circle(im_color, (eyes_x, eyes_y), 1, (255, 0, 0), 1)
    # com actually comes out red, mid blue
                cv2.circle(im_color,
                           (fish_com_x, fish_com_y), 1, (0, 0, 255), 1)
                cv2.drawContours(im_color, [fishcont], -1, (0, 255, 0), 1)
                vec_heading = np.array(
                    [eyes_x, eyes_y]) - np.array([fish_com_x, fish_com_y])
                heading_vec_list.append(vec_heading)
                if makevid:
                    ha_vid.write(im_color)
                    thresh_vid.write(th)

            vid.close()
            if makevid:
                ha_vid.release()

            filt_heading_vec_list = filter_uvec(heading_vec_list, 1)
            heading_angles = [np.arctan2(vec[1], vec[0])
                              if not math.isnan(vec[0])
                              else float('nan') for vec
                              in filt_heading_vec_list]

# yields coords with some negatives in a reverse unit circle (i.e clockwise)
# have to normalize to put in unit circle coords.

            norm_orientation = [-ang if ang < 0 else 2 * np.pi - ang
                                for ang in heading_angles]
            self.ha_in_timeframe.append(norm_orientation)

    def vec_to_barrier(self):
        for trial, xy in enumerate(self.xy_coords_by_trial):
            vecs_to_barrier = []
            x = xy[0][self.timerange[0]:self.timerange[1]]
            y = xy[1][self.timerange[0]:self.timerange[1]]
            barr_xy = np.array(self.barrier_xy_by_trial[trial])
            for fish_x, fish_y in zip(x, y):
                fish_xy = np.array([fish_x, fish_y])
                b_vec = barr_xy - fish_xy
                vecs_to_barrier.append(b_vec)
            angles = [np.arctan2(vec[1], vec[0])
                      if not math.isnan(vec[0]) else float('nan')
                      for vec in vecs_to_barrier]
            transformed_angles = [2*np.pi + ang if ang < 0 else ang
                                  for ang in angles]
            self.ba_in_timeframe.append(transformed_angles)

    def heading_v_barrier(self):
        for h_angles, b_angles in zip(self.ha_in_timeframe,
                                      self.ba_in_timeframe):
            diffs = []
            right_or_left = []
            for ha, ba in zip(h_angles, b_angles):
                if ha > ba:
                    diff = ha - ba
                    if diff > np.pi:
                        diff = 2 * np.pi - ha + ba
                        right_or_left.append('l')
                    else:
                        right_or_left.append('r')
                elif ba > ha:
                    diff = ba - ha
                    if diff > np.pi:
                        diff = 2 * np.pi - ba + ha
                        right_or_left.append('r')
                    else:
                        right_or_left.append('l')
                elif math.isnan(ha) or math.isnan(ba):
                    diff = float('nan')
                    right_or_left.append('nan')
                else:
                    diff = 0
                    right_or_left.append('n')
                diffs.append(diff)
            diffs = [-df if dirc == 'l' else df
                     for df, dirc in zip(diffs, right_or_left)]
            self.h_vs_b_by_trial.append(diffs)

# Think of barrier axis as the X axis of the unit circle. ha to the right of the barrier are negative (barrier is left of the fish), while ha to the left of the barrier are positive (barrier is on the right of the fish). 

    def find_initial_conditions(self):
        for trial in range(len(self.xy_coords_by_trial)):
            ha_avg = np.nanmean(self.ha_in_timeframe[trial][0:self.pre_c])
            ba_avg = np.nanmean(self.ba_in_timeframe[trial][0:self.pre_c])
            h_to_b = np.nanmean(self.h_vs_b_by_trial[trial][0:self.pre_c])
            barr_xy = np.array(self.barrier_xy_by_trial[trial])
            xy = self.xy_coords_by_trial[trial]
            fish_x = np.nanmean(
                xy[0][self.timerange[0]:self.timerange[0]+self.pre_c])
            fish_y = np.nanmean(
                xy[1][self.timerange[0]:self.timerange[0]+self.pre_c])
            fish_xy = np.array([int(fish_x), int(fish_y)])
            vec = barr_xy - fish_xy
            mag = math.sqrt(np.sum([i*i for i in vec]))
            self.initial_conditions.append([h_to_b, mag, ha_avg, ba_avg])

# initial conditions will be input into next two functions


# outside main line will find the ha and ba for a given trial in the  barrier escape object. for each barrier trial, run through EVERY control trial. 

    def trial_analyzer(self, plotc):
        self.get_orientation(True)
        self.vec_to_barrier()
        self.heading_v_barrier()
        self.find_initial_conditions()
        self.body_curl()
        self.find_cstart(plotc)
                
    def infer_collisions(self, barrier_escape_object, plotornot):

        def collision(xb, yb, bd, x, y):
            vec = np.sqrt((x - xb)**2 + (y - yb)**2)
            if math.isnan(x):
                return False
            elif vec < (bd / 2) + 2:
                return True
            else:
                return False
            
        angle = barrier_escape_object.initial_conditions[0]
        mag = barrier_escape_object.initial_conditions[1]
        if plotornot:
            turn_fig = pl.figure()
            turn_ax = turn_fig.add_subplot(111)
            turn_ax.set_xlim([-100, 100])
            turn_ax.set_ylim([-100, 100])
            turn_ax.set_aspect('equal')
        timerange = self.timerange
        if 0 <= angle < np.pi / 2:
            barrier_x = np.sin(angle) * mag
            barrier_y = np.cos(angle) * mag
        elif angle >= np.pi / 2:
            barrier_x = np.sin(np.pi - angle) * mag
            barrier_y = -np.cos(np.pi - angle) * mag
        elif 0 >= angle > -np.pi / 2:
            barrier_x = -np.sin(-angle) * mag
            barrier_y = np.cos(-angle) * mag
        elif angle <= -np.pi / 2:
            barrier_x = -np.sin(np.pi + angle) * mag
            barrier_y = -np.cos(np.pi + angle) * mag
        barr = pl.Circle((barrier_x, barrier_y),
                         barrier_escape_object.barrier_diam / 2,
                         fc='r')

        collision_trials = []
        for trial_counter, xy_coords in enumerate(self.xy_coords_by_trial):
            self.get_orientation(trial_counter, False)
            self.find_initial_conditions(trial_counter)
            ha_init = self.initial_conditions[0]
            if not math.isnan(ha_init):
                zipped_coords = zip(xy_coords[0], xy_coords[1])
                escape_coords = rotate_coords(zipped_coords, -ha_init)
                x_escape = np.array(
                    [x for [x, y] in escape_coords[timerange[0]:timerange[1]]])
                x_escape = x_escape - x_escape[0]
                y_escape = np.array(
                    [y for [x, y] in escape_coords[timerange[0]:timerange[1]]])
                y_escape = y_escape - y_escape[0]
                for x_esc, y_esc in zip(x_escape, y_escape):
                    collide = collision(barrier_x,
                                        barrier_y,
                                        barrier_escape_object.barrier_diam,
                                        x_esc, y_esc)
                    if collide and trial_counter not in collision_trials:
                        collision_trials.append(trial_counter)
                if plotornot:
                    turn_ax.plot(
                        outlier_filter(x_escape),
                        outlier_filter(y_escape), 'g')
                    turn_ax.text(
                        x_escape[-1],
                        y_escape[-1],
                        str(trial_counter),
                        size=10,
                        backgroundcolor='w')
        if plotornot:
            turn_ax.add_patch(barr)
            pl.show()
        print(len(collision_trials))
        print('out of')
        print(len(self.xy_coords_by_trial))
        barrier_escape_object.collision_prob.append(
            float(len(collision_trials)) / len(self.xy_coords_by_trial))



# this function finds the orientation to the barrier at the beginning of every barrier trial. will be called once for every trial. THEN call the above function "infer collision"

    def control_escapes(self):
        turn_fig = pl.figure()
        turn_ax = turn_fig.add_subplot(111)
        turn_ax.set_xlim([-100, 100])
        turn_ax.set_ylim([-100, 100])
        timerange = self.timerange
        for trial, xy_coords in enumerate(self.xy_coords_by_trial):
            ha_init = self.initial_conditions[trial][0]
            if not math.isnan(ha_init):
                zipped_coords = zip(xy_coords[0], xy_coords[1])
                escape_coords = rotate_coords(zipped_coords, -ha_init)
                x_escape = np.array(
                    [x for [x, y] in escape_coords[timerange[0]:timerange[1]]])
#                print(x_escape[0:10])
                x_escape = x_escape - x_escape[0]
                y_escape = np.array(
                    [y for [x, y] in escape_coords[timerange[0]:timerange[1]]])
                y_escape = y_escape - y_escape[0]
                turn_ax.plot(
                    outlier_filter(x_escape),
                    outlier_filter(y_escape), 'g')
                turn_ax.text(
                    x_escape[-1],
                    y_escape[-1],
                    str(trial),
                    size=10,
                    backgroundcolor='w')
        pl.show()
        
    def escapes_vs_barrierloc(self):
        turn_fig = pl.figure()
        turn_ax = turn_fig.add_subplot(111)
        turn_ax.set_xlim([-100, 100])
        turn_ax.set_ylim([-100, 100])
        timerange = self.timerange
        l_or_r = []
        for trial in range(len(self.xy_coords_by_trial)):
            to_barrier_init = self.initial_conditions[trial][0]
            ha_init = self.initial_conditions[trial][2]
            xy_coords = self.xy_coords_by_trial[trial]
            if not math.isnan(ha_init):
                zipped_coords = zip(xy_coords[0], xy_coords[1])
                escape_coords = rotate_coords(zipped_coords, -ha_init)
                x_escape = np.array(
                    [x for [x, y] in escape_coords[timerange[0]:timerange[1]]])
                x_escape = x_escape - x_escape[0]
                y_escape = np.array(
                    [y for [x, y] in escape_coords[timerange[0]:timerange[1]]])
                y_escape = y_escape - y_escape[0]
                if to_barrier_init < 0:
                    l_or_r.append('l')
                    turn_ax.plot(
                        outlier_filter(x_escape),
                        outlier_filter(y_escape), 'b')
                    turn_ax.text(
                        x_escape[-1],
                        y_escape[-1],
                        str(trial),
                        size=10,
                        backgroundcolor='w')
                elif to_barrier_init > 0:
                    l_or_r.append('r')
                    turn_ax.plot(
                        outlier_filter(x_escape),
                        outlier_filter(y_escape), 'm')
                    turn_ax.text(
                        x_escape[-1],
                        y_escape[-1],
                        str(trial),
                        size=10,
                        backgroundcolor='w')
        print l_or_r
        pl.show()

# MUST BE CALLED AFTER FINDING CSTART ANGLES        
    def find_cstart(self, plotornot):
        for trial in range(len(self.xy_coords_by_trial)):
            stim_init = self.stim_init_times[trial]
            c_thresh = 30
            ta = gaussian_filter(self.tailangle_sums[trial], 1)
            avg_curl_init = np.nanmean(ta[0:self.pre_c])
            ta = ta - avg_curl_init
            c_start_angle = float('nan')
            ta_min = argrelmin(ta)[0].tolist()
            ta_max = argrelmax(ta)[0].tolist()
            ta_maxandmin = [x for x in sorted(ta_min + ta_max) if (
                x > stim_init and abs(ta[x]) > c_thresh)]
            if not ta_maxandmin:
                return []
            if plotornot:
                pl.plot(ta)
                pl.plot([ta_maxandmin[0]], [0], marker='.', color='r')
                pl.title('trial' + str(trial))
                pl.show()
            c_start_angle = ta[ta_maxandmin[0]]
            c_start_ind = ta_maxandmin[0]
            self.cstart_angles.append(c_start_angle)
            self.escape_latencies.append(c_start_ind - stim_init)
    # Get latency here based on stim index and c_start_index

            if not math.isnan(c_start_angle):
                if np.sum(
                        np.sign(
                            [c_start_angle,
                             self.initial_conditions[trial][0]])) == 0:
                    print('away')
                    self.cstart_rel_to_barrier.append(1)
                else:
                    print('towards')
                    self.cstart_rel_to_barrier.append(0)
            else:
                self.cstart_rel_to_barrier.append(np.nan)

    def contourfinder(self, im, threshval):

        # good params at 120 low area and dilate at 3x3
        # try dilate 5x5. works ok with 250.
        r, th = cv2.threshold(im, threshval, 255, cv2.THRESH_BINARY)
        th = cv2.erode(th, np.ones([3, 3]))
        th = cv2.dilate(th, np.ones([3, 3]))
        # cv2.namedWindow('thresh', cv2.WINDOW_AUTOSIZE)
        # cv2.imshow('thresh', th)
        # cv2.waitKey(20)
        rim, contours, hierarchy = cv2.findContours(
            th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        cvx_hull_by_area = [cv2.convexHull(cnt) for cnt in contours]
        areamin = self.area_thresh
        areamax = 600
        contcomp = [x for x in
                    cvx_hull_by_area if areamin < cv2.contourArea(x) < areamax]
        if contcomp:
            rect = cv2.minAreaRect(contcomp[0])
            box = cv2.boxPoints(rect)
            x, y = np.mean(box, axis=0).astype(np.int)
            return contours[0], x, y, th
    # this is a catch for missing the fish
        if threshval < 3:
            if areamin * .75 < cv2.contourArea(cvx_hull_by_area[0]) < areamax:
                rect = cv2.minAreaRect(contours[0])
                box = cv2.boxPoints(rect)
                x, y = np.mean(box, axis=0).astype(np.int)
                return contours[0], x, y, th
            else:
                print('thresh too low')
                return np.array([]), float('NaN'), float('NaN'), np.zeros(
                    [im.shape[0], im.shape[1]]).astype(np.uint8)
        else:
            return self.contourfinder(im, threshval-1)


    def body_curl(self):

        def body_points(seg1, seg2):
            right = [unpack[0] for unpack in seg1]
            left = [unpack[0] for unpack in seg2]
            bp = [[int(np.mean([a[0], b[0]])), int(np.mean([a[1], b[1]]))]
                  for a, b in zip(right, left[::-1])]
            return bp

        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        fps = 500
        for trial in range(len(self.xy_coords_by_trial)):
            cstart_vid = cv2.VideoWriter(
                self.directory + '/cstart' + str(
                    trial) + self.condition + '.AVI',
                fourcc, fps, (80, 80), True)
            threshvid = imageio.get_reader(self.directory + '/thresh' + str(
                trial)+self.condition+'.AVI', 'ffmpeg')
            sum_angles = []
            all_angles = []
            ha_adjusted = deque([np.mod(90-(np.degrees(angle)), 360)
                                 for angle in self.ha_in_timeframe[trial]])
            cnt = 0
            # make this a variable -- 25 should be added to timeframe multiple times. 
            for frame in range(self.timerange[1] - self.timerange[0]):
                ha_adj = ha_adjusted.popleft()
                im_color = threshvid.get_data(frame)
                im = cv2.cvtColor(im_color, cv2.COLOR_BGR2GRAY)
                r, im_thresh = cv2.threshold(im, 120, 255, cv2.THRESH_BINARY)
                im_thresh, m, c = rotate_image(im_thresh, ha_adj)
                im_thresh_color = cv2.cvtColor(im_thresh, cv2.COLOR_GRAY2RGB)
# refinding here is easier than storing the contour then rotating both the image and the contour.                 
                r, body_cont, hier = cv2.findContours(im_thresh,
                                                      cv2.RETR_EXTERNAL,
                                                      cv2.CHAIN_APPROX_NONE)
                size_filtered_contours = [j for j in body_cont
                                          if self.area_thresh * .5 < cv2.contourArea(j) < 500]
                if not size_filtered_contours:
                    sum_angles.append(float('nan'))
                    cstart_vid.write(im_thresh_color)
                    continue
# now find the point on the contour that has the smallest y coord (i.e. is closest to the top). may be largest y coord?
                body = size_filtered_contours[0]
                body_perimeter = cv2.arcLength(body, True)
                highest_pt = np.argmin([bp[0][1] for bp in body])
                body = np.concatenate([body[highest_pt:], body[0:highest_pt]])
                body_segment1 = []
                body_segment2 = []
                segment = 1.0
                numsegs = 18.0
                for i in range(len(body)):
                    if cv2.arcLength(body[0:i+1],
                                     False) > body_perimeter*(segment/numsegs):
                        if segment < (numsegs/2):
                            body_segment1.append(body[i])
                        elif segment > (numsegs/2):
                            body_segment2.append(body[i])
                        elif segment == (numsegs/2):
                            endpoint = body[i].tolist()                       
                        segment += 1
                avg_body_points = body_points(body_segment1, body_segment2)[1:]

# First point inside head is unreliable. take 1:
                for bp in avg_body_points:
                    cv2.ellipse(im_thresh_color,
                                (bp[0], bp[1]),
                                (1, 1), 0, 0, 360, (255, 0, 255), -1)
                cstart_vid.write(im_thresh_color)
            
                body_gen = toolz.itertoolz.sliding_window(2, avg_body_points)
                body_point_diffs = [
                    (0, 1)] + [
                        (b[0]-a[0], b[1]-a[1]) for a, b in body_gen]
    #            print body_point_diffs

                angles = []
                # Angles are correct given body_points. 
                for vec1, vec2 in toolz.itertoolz.sliding_window(
                        2, body_point_diffs):
                    dp = np.dot(vec1, vec2)
                    mag1 = np.sqrt(np.dot(vec1, vec1))
                    mag2 = np.sqrt(np.dot(vec2, vec2))
                    ang = np.arccos(dp / (mag1*mag2))
                    if np.cross(vec1, vec2) > 0:
                        ang *= -1
                    print ang
                    angles.append(np.degrees(ang))
                cnt += 1
                all_angles.append(angles)
        
            cstart_vid.release()
            threshvid.close()
            self.tailangle_sums.append([np.nansum(i) for i in all_angles])
            self.all_tailangles.append(all_angles)



# this function will realign all the escapes during barrier_free conditions vertically (i.e. fish pointing at pi/2). 
# for barrier conditions, will realign all escapes vertically, and put blue when barrier is to the right, pink when barrier to the left. 
# have to write an external function that takes a barrier Escape object and a no barrier Escape object and maps  the barrier locations onto 
# the no barrier trajectories. the function will identify how many trajectories cross or come within 2 pixels of hitting the barrier, meaning the 
# center of mass would dictate a collision (i.e. center of mass is ~ 2 pixels from the edge of the fish). 


# FIRST MAKE A CALL TO INIT HEADING AND BARRIER. THEN FIGURE OUT ORIENTATION TO BARRIER BASED ON THIS (ALREADY A FUNCTION FOR THIS DOWN BELOW). 

def csv_data(headers, datavals):
    with open('output.csv', 'wb') as csvfile:
        output_data = csv.writer(csvfile)
        output_data.writerow(headers)
        for dt in datavals:
            output_data.writerow(dt)


def find_darkest_pixel(im):
    boxfiltered_im = cv2.boxFilter(im, 0, (3, 3))
    boxfiltered_im = cv2.boxFilter(boxfiltered_im, 0, (3, 3))
    max_y, max_x = np.unravel_index(boxfiltered_im.argmax(),
                                    boxfiltered_im.shape)
    return max_x, max_y





def make_segments(x, y):
    '''
    Create list of line segments from x and y coordinates, in the correct format for LineCollection:
    an array of the form   numlines x (points per line) x 2 (x and y) array
    '''
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    return segments

# Interface to LineCollection:


def colorline(x,
              y,
              z=None,
              cmap=pl.get_cmap('afmhot'),
              norm=pl.Normalize(0.0, 1.0),
              linewidth=3,
              alpha=1.0):
    '''
    Plot a colored line with coordinates x and y
    Optionally specify colors in the array z
    Optionally specify a colormap, a norm function and a line width
    '''
    # Default colors equally spaced on [0,1]:
    if z is None:
        z = np.linspace(0.0, 1.0, len(x))
    # Special case if a single number:
    if not hasattr(
            z, "__iter__"):  # to check for numerical input -- this is a hack
        z = np.array([z])
    z = np.asarray(z)
    segments = make_segments(x, y)
    lc = LineCollection(
        segments,
        array=z,
        cmap=cmap,
        norm=norm,
        linewidth=linewidth,
        alpha=alpha)
    ax = pl.gca()
    ax.add_collection(lc)
    return lc


def clear_frame(ax=None):
    # Taken from a post by Tony S Yu
    if ax is None:
        ax = pl.gca()
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    for spine in ax.spines.itervalues():
        spine.set_visible(False)


#this forces the coordinate system to be facing upward at 0 rad.

def rotate_coords(coords, angle):
    angle = angle + np.pi / 2
    center = [640, 512]
    rotated_coords = []
    for x, y in coords:
        xcoord = x - center[0]
        ycoord = y - center[1]
        xcoord_rotated = (xcoord * np.cos(angle) - ycoord * np.sin(angle)
                          ) + center[0]
        ycoord_rotated = (xcoord * np.sin(angle) + ycoord * np.cos(angle)
                          ) + center[1]
        if not math.isnan(xcoord_rotated) and not math.isnan(ycoord_rotated):
            rotated_coords.append([int(xcoord_rotated), int(ycoord_rotated)])
#    else:
#  rotated_coords.append([float('NaN'), float('NaN')])
    return rotated_coords


def outlier_filter(coords):
    coords = [a if abs(b - a) < 100 else float('nan')
              for a, b in toolz.itertoolz.sliding_window(2, coords)]
    return coords


def filter_list(templist):
    filtlist = scipy.ndimage.filters.gaussian_filter(templist, 2)
    return filtlist


def filter_uvec(vecs, sd):
    
    filt_sd = sd
    npvecs = np.array(vecs)
    filt_vecs = np.copy(npvecs)
    for i in range(npvecs[0].shape[0]):
        filt_vecs[:, i] = gaussian_filter(npvecs[:, i], filt_sd)
    return filt_vecs


def slice_background(br, xcrd, ycrd):
    br_roi = np.array(
        br[int(ycrd)-40:int(ycrd)+40,
           int(xcrd)-40:int(xcrd)+40]).astype(np.uint8)
    return br_roi


def x_and_y_coord(coord):
    xcoord = ''
    ycoord = ''
    x_incomplete = True
    y_incomplete = True
    for char in coord:
        if char == ',':
            x_incomplete = False
            continue
        if char == '}':
            y_incomplete = False
        if x_incomplete and char != '{' and char != 'X' and char != '=':
            xcoord += char
        if not x_incomplete and y_incomplete and char != 'Y' and char != '=':
            ycoord += char
    return float(xcoord), 1024 - float(ycoord)


def rotate_image(image, angle):
    image_center = tuple(np.array(image.shape) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, scale=1.0)
    result = cv2.warpAffine(
        image, rot_mat, image.shape, flags=cv2.INTER_LINEAR)
    return result, rot_mat, image_center


def plot_h_vs_b(obj):
    for x in obj.h_vs_b_by_trial.items():
        pl.plot(np.abs(x[1]))
    pl.show()

    
def magvector(vec):
    mag = np.sqrt(np.dot(vec, vec))
    return mag


# PUT A TIMEOUT IN THE ESCAPE RIG WHEN THE FISH GOES INTO THE BARRIER. WAIT 3 SECONDS OR SOMETHING. THEN YOU WONT GET TRIALS WHERE THEY SWIM
# THROUGH THE BARRIER.

''' 2/22/18: This is the program that you'll use for analyzing all minefield data. Your first pass will be to get 40 fish (wik day 10-12) that experience barriers projected onto the floor of the tank. Start with red, then invert to gray, then do a set of no barrier trials. Do want to answer a couple more questions. Can I address Rob's question of whether they are turning right or left prior to right or left escapes? Also, am I sure the experiment is running at 500Hz?Try to use a timing function because I'm not convinced that the j_out is relevant. It showed no dropped frames when I was drawing the barriers every frame, and it was clearly slowed down by at least a factor of 5.'''


# all you have to do to study inverted vs normal vs control is change the letters input to an Escape object. it really is nice code! i don't like
# how the infer functions at the end overwrite member variables. maybe change this at some point. 



#instead of using l, n, d notation, use cond1, cond2, nb. 

if __name__ == '__main__':

# 130 works best for 102818_3
    
    fish_id = '/102318_2'
    pl.ioff()
    os.chdir('/Users/nightcrawler2/Escape-Analysis/')
    area_thresh = 130
    esc_dir = os.getcwd() + fish_id
    escape_cond1 = Escapes('v', esc_dir, area_thresh)
    escape_cond2 = Escapes('i', esc_dir, area_thresh)
    escape_nb = Escapes('n', esc_dir, area_thresh)
    plotcstarts = True

    escape_cond1.trial_analyzer(plotcstarts)
#    escape_nb.infer_collisions(escape_cond1, False)

    escape_cond2.trial_analyzer(plotcstarts)
 #   escape_nb.infer_collisions(escape_cond2, False)
    
    escape_nb.trial_analyzer(plotcstarts)

# # MAKE SURE THESE ALWAYS COME LAST. IF NOT, HA_IN_TIMEFRAME REMAINS THE LAST TRIAL.

    escape_cond1.escapes_vs_barrierloc()
    escape_cond2.escapes_vs_barrierloc()
    escape_nb.control_escapes()
#    data_output(escape_cond1, escape_nb, escape_cond2, esc_dir)





# # These functions are specific for a given trial. Orientation for a trial is obtained by finding the eye midpoint and the sb
# # True / False arg to get_orientation specifies if you want to make videos with eye and sb labeled for accuracy readout.

# # Get_orientation finds the orientation of the fish per trial on a unit circle basis.
# # Vec_to_barrier finds the angle on a unit circle of the fish between its center of mass and the barrier, pointing from the fish
# # to the barrier.
# # Heading_vs_barrier asks how the heading angle changes through the escape with relation to the barrier. 







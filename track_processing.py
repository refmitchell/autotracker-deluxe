import numpy as np
import numpy.ma as ma
import pandas as pd
import cv2
from scipy.interpolate import UnivariateSpline

import matplotlib.pyplot as plt


def calibrate_tracks(camera_matrix, 
                     distortion_coefficients, 
                     raw_track_file, 
                     dest_filepath,
                     homography=None):
    """
    Calibrate raw tracks from autotracking to store them in world coordinates.
    The raw track file is assumed to be a csv.

    :param camera_matrix: The camera calibration matrix
    :param distance_coefficients: The distance coefficients computed during 
                                  calibration.
    :param raw_track_file: The raw track in pixelcoordinates (csv)
    :param dest_filepath: The output file for the calibrated tracks
    :param homography: The transformation matrix required to project into 
                       world coordinates. If not supplied, the conversion will
                       not be performed.
    """
    raw_data = pd.read_csv(raw_track_file, index_col=[0])
    calibrated_data = pd.DataFrame(columns=raw_data.columns, 
                                   index=raw_data.index)
    columns = list(raw_data.columns)

    # Transform back to world coordinates?
    H_inv = np.linalg.inv(homography)

    # Iterate over raw data and calibrate each set of x,y points
    col_idx = 0
    while col_idx < len(columns):
        # Extract datapoints and convert to numpy arrays
        x_data = raw_data.loc[:,columns[col_idx]]
        y_data = raw_data.loc[:,columns[col_idx+1]]
        x_data = x_data.to_numpy(dtype=np.float64, na_value=np.nan)
        y_data = y_data.to_numpy(dtype=np.float64, na_value=np.nan)

        # Check lengths match (fail otherwise)
        assert len(x_data) == len(y_data)

        # Pack into 2xN array for calibration
        points = np.stack((x_data, y_data))

        # Calibrate points, returns Nx1x2
        calibrated_points =\
              cv2.undistortImagePoints(points, 
                                       cameraMatrix=camera_matrix,
                                       distCoeffs=distortion_coefficients)
        
        # Remove dimension added by OpenCV and transpose to 2XN
        calibrated_points = np.squeeze(calibrated_points)
        calibrated_points = calibrated_points.T

        # If we have the homography to translate into world coordinates.
        if not (H_inv is None):
            # Generate sequence of 1s to be added to each point
            ones = np.ones((1,calibrated_points.shape[1]))

            # Each coordinate now [x,y,1], full structure is Nx3
            calibrated_points = np.concatenate((calibrated_points, ones)).T
            
            # Map the homography transformation onto every point
            # Should return a 3xN matrix of the transformed points
            calibrated_points =\
                np.array(list(map(lambda x: np.dot(x, H_inv), calibrated_points)))
            
            calibrated_points = calibrated_points.T

        # Insert calibrated x and y values into new dataframe.
        calibrated_data.loc[:, columns[col_idx]] = calibrated_points[0]
        calibrated_data.loc[:, columns[col_idx+1]] = calibrated_points[1]

        col_idx += 2 # Iterate over pairs of columns

    # Write out new dataframe.
    calibrated_data.to_csv(dest_filepath)

def smooth_tracks(track_file, 
                  dest_filepath):
    """
    Apply smoothing to tracks.

    If dest_file == None then the destination filename will be based on the
    track_file.    

    :param track_file: The csv track file you wish to use
    :param dest_file: A destination file
    """
    data = pd.read_csv(track_file, index_col=[0])

    smoothed_index = np.arange(data.index.size)
    smoothed_data = pd.DataFrame(columns=data.columns, index=smoothed_index)

    columns = list(data.columns)    

    # Iterate over raw data and calibrate each set of x,y points
    col_idx = 0
    while col_idx < len(columns):
        # Extract datapoints and convert to numpy arrays
        x_data = data.loc[:,columns[col_idx]]
        y_data = data.loc[:,columns[col_idx+1]]
        x_data = x_data.to_numpy(dtype=np.float64, na_value=np.nan)
        y_data = y_data.to_numpy(dtype=np.float64, na_value=np.nan)

        # Filter out NaN values, but retain count for re-augmentation
        full_len_x = x_data.size

        x_data = x_data[~np.isnan(x_data)]
        y_data = y_data[~np.isnan(y_data)]

        # Check lengths match (fail otherwise)
        assert len(x_data) == len(y_data)

        # Work in arbitrary time units. Can combine with FPS later to get
        # true time.
        duration = x_data.size
        t = np.arange(duration)

        # Create a smoothing spline for the data
        degree = 3
        x_spline = UnivariateSpline(t, x_data, k=degree)
        y_spline = UnivariateSpline(t, y_data, k=degree)

        # Compute spline for given time points.
        x_smooth = x_spline(t)
        y_smooth = y_spline(t)

        # Re-augment tracks with NaN values to preserve length and avoid index
        # problems with pandas.
        padding_size = (full_len_x - x_data.size)
        padding = np.array([np.nan for n in range(padding_size)])

        x_smooth = np.concatenate((x_smooth, padding))
        y_smooth = np.concatenate((y_smooth, padding))

        # Insert x with smoothed y values
        smoothed_data.loc[:, columns[col_idx]] = x_smooth
        smoothed_data.loc[:, columns[col_idx+1]] = y_smooth

        col_idx += 2 # Iterate over pairs of columns    
    
    # Write out new dataframe.
    smoothed_data.to_csv(dest_filepath)        

def zero_tracks(raw_track_file, dest_filepath, origin=(0,0)):
    """
    Normalise all tracks in a file such that they start from origin. The first
    point in a track is assumed to be the origin.

    :param track_file: The csv track file you wish to use
    :param dest_file: A destination file
    :param origin: The desired origin point
    """
    data = pd.read_csv(raw_track_file, index_col=[0])
    zeroed_data = pd.DataFrame(columns=data.columns, index=data.index)
    columns = list(data.columns)

    # Iterate over raw data and calibrate each set of x,y points
    col_idx = 0
    while col_idx < len(columns):
        # Extract datapoints and convert to numpy arrays
        x_data = data.loc[:,columns[col_idx]]
        y_data = data.loc[:,columns[col_idx+1]]
        x_data = x_data.to_numpy(dtype=np.float64, na_value=np.nan)
        y_data = y_data.to_numpy(dtype=np.float64, na_value=np.nan)

        # Check lengths match (fail otherwise)
        assert len(x_data) == len(y_data)

        # Determine X and Y offset from desired origin
        x_offset = x_data[0] - origin[0]
        y_offset = y_data[0] - origin[1]
        
        # Apply translate all points
        norm_x = x_data - x_offset
        norm_y = y_data - y_offset

        # Insert calibrated x and y values into new dataframe.
        zeroed_data.loc[:, columns[col_idx]] = norm_x
        zeroed_data.loc[:, columns[col_idx+1]] = norm_y

        col_idx += 2 # Iterate over pairs of columns

    # Write out new dataframe.
    zeroed_data.to_csv(dest_filepath)


def plot_tracks(input_file, 
                draw_arena=True, 
                arena_radius=35, 
                draw_mean_displacement=False):
    """
    Helper method to test calibration, this is only intended to check distance
    tranformations have been performed successfully, this is not for any 
    formal analysis.

    :param input_file: The CSV file you want to use as the underlying data.
    :param draw_arena: Draw a circle on the plot of the same radius as the
                       arena used in the experiment.
    :param arena_radius: The radius of the arena in cm.
    """

    data = pd.read_csv(input_file, index_col=[0])
    columns = list(data.columns)

    # Convert to metres
    arena_radius = arena_radius * 10
    
    mosaic = [['si_tracks']]
    fig, axs = plt.subplot_mosaic(mosaic)
    ax = axs['si_tracks']

    if draw_arena:
        def define_circle(radius):
            ths = np.linspace(0, 2*np.pi, 100)     
            rs = radius * np.ones(100)
            xs = [r*np.cos(th) for (th, r) in zip(ths, rs)]
            ys = [r*np.sin(th) for (th, r) in zip(ths, rs)]
            return xs, ys

        arena = define_circle(arena_radius)
        starter = define_circle(50) # 5cm starting circle 
        ax.plot(arena[0], arena[1], color='k')
        ax.plot(starter[0], starter[1], color='k')
        ax.set_aspect('equal') # If we're drawing the arena, fair assumption
        
    displacements = []
    # Iterate over raw data and calibrate each set of x,y points
    col_idx = 0    
    while col_idx < len(columns):
        # Extract datapoints and convert to numpy arrays
        x_data = data.loc[:,columns[col_idx]]
        y_data = data.loc[:,columns[col_idx+1]]
        x_data = x_data.to_numpy(dtype=np.float64, na_value=np.nan)
        y_data = y_data.to_numpy(dtype=np.float64, na_value=np.nan)

        # Check lengths match (fail otherwise)
        assert len(x_data) == len(y_data)

        ax.plot(x_data, y_data, alpha=0.5)
        
        # Track average displacement

        # Find last non NaN element 
        x_end = x_data[~np.isnan(x_data)][-1]        
        y_end = y_data[~np.isnan(y_data)][-1]        
        x_disp = (x_data[0] - x_end)**2
        y_disp = (y_data[0] - y_end)**2

        # Compute and store displacement
        disp = np.sqrt(x_disp + y_disp)
        displacements.append(disp)

        col_idx += 2 # Iterate over pairs of columns

    print("MEAN DISPLACEMENT: {}".format(np.mean(displacements)))
    print("This should roughly equal your arena radius, if it doesn't, then" + 
          " you will need to adjust your calibration.")
    print("Plotted: {}".format(input_file))

    plt.show()
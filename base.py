"""Functions for analyzing whiski data"""
import traj, trace
import numpy as np, pandas

def load_whisker_traces(whisk_file):
    """Load the traces, return as frame2segment_id2whisker_seg"""
    frame2segment_id2whisker_seg = trace.Load_Whiskers(whisk_file)
    return frame2segment_id2whisker_seg

def load_whisker_identities(measure_file):
    """Load the correspondence between traces and identified whiskers
    
    Return as whisker_id2frame2segment_id
    """
    tmt = traj.MeasurementsTable(measure_file)
    whisker_id2frame2segment_id = tmt.get_trajectories()
    return whisker_id2frame2segment_id

def load_whisker_positions(whisk_file, measure_file, side='left'):
    """Load whisker data and return angle at every frame.
    
    This algorithm needs some work. Not sure the best way to convert to
    an angle. See comments.
    
    Uses `side` to disambiguate some edge cases.
    
    Returns DataFrame `angl_df` with columns:
        frame: frame #
        wid: whisker #
        angle: angle calculated by fitting a polynomial to trace
        angle2: angle calculated by slope between endpoints.

    `angle2` is noisier overall but may be more robust to edge cases.
    
    You may wish to pivot:
    piv_angle = angl_df.pivot_table(rows='frame', cols='wid', 
        values=['angle', 'angle2'])    
    """
    
    
    # Load whisker traces and identities
    frame2segment_id2whisker_seg = load_whisker_traces(whisk_file)
    whisker_id2frame2segment_id = load_whisker_identities(measure_file)
    
    # It looks like it numbers them from Bottom to Top for side == 'left'
    # whiski colors them R, G, B

    # Iterate over whiskers
    rec_l = []
    for wid, frame2segment_id in whisker_id2frame2segment_id.items():
        # Iterate over frames
        for frame, segment_id in frame2segment_id.items():
            # Get the actual segment for this whisker and frame
            ws = frame2segment_id2whisker_seg[frame][segment_id]
            
            # Fit angle two ways
            angle = angle_meth1(ws.x, ws.y, side)
            angle2 = angle_meth2(ws.x, ws.y, side)

            # Store
            rec_l.append({
                'frame': frame, 'wid': wid, 'angle': angle, 'angle2': angle2})

    # DataFrame it
    angl_df = pandas.DataFrame.from_records(rec_l)
    #~ piv_angle = angl_df.pivot_table(rows='frame', cols='wid', 
        #~ values=['angle', 'angle2'])
    
    return angl_df


def angle_meth1(wsx, wsy, side):
    """Fit angle by lstsqs line fit, then arctan, then pin.
    
    This will fail for slopes close to vertical.
    """
    # fit a line and calculate angle of whisker
    # in the video, (0, 0) is upper left, so we need to take negative of slope
    # This will fail for slopes close to vertical, for instance if it
    # has this shape: (  because least-squares fails here
    # eg Frame 5328 in 0509A_cropped_truncated_4
    p = np.polyfit(wsx, wsy, deg=1)
    slope = -p[0]

    # Arctan gives values between -90 and 90
    # Basically, we cannot discriminate a SSW whisker from a NNE whisker
    # Can't simply use diff_x because the endpoints can be noisy
    # Similar problem occurs with ESE and WNW, and then diff_y is noisy
    # Easiest way to do it is just pin the data to a known range
    angle = np.arctan(slope) * 180 / np.pi    
    
    # pin
    pinned_angle = pin_angle(angle, side)
    
    return pinned_angle

def angle_meth2(wsx, wsy, side):
    """Fit angle by arctan of tip vs follicle, then pin"""
    # Separate angle measurement: tip vs follicle
    # This will be noisier
    # Remember to flip up/down here
    # Also remember that ws.x and ws.y go from tip to follicle (I think?)
    # Actually the go from tip to follicle in one video and from follicle
    # to tip in the other; and then occasional exceptions on individual frames
    angle = np.arctan2(
        -(wsy[0] - wsy[-1]), wsx[0] - wsx[-1]) * 180 / np.pi

    # On rare occasions it seems to be flipped, 
    # eg Frame 9 in 0509A_cropped_truncated_4
    # So apply the same fix, even though it shouldn't be necessary here
    # pin
    pinned_angle = pin_angle(angle, side)
    
    return pinned_angle    

def pin_angle(angle, side):
    """Pins angle to normal range, based on side"""
    # side = left, so theta ~-90 to +90
    # side = top, so theta ~ -180 to 0    
    
    if side == 'top':
        if angle > 0:
            return angle - 180
    elif side == 'left':
        if angle > 90:
            return angle - 180
    return angle
    
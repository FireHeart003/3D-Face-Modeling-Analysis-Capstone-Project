import numpy as np

#############
#  FUNCTIONS TO MANIPULATE MHM FILES
#############


# Function that makes a dictionary of shape features into an MHM file
# material is a string with skin for the model
# filename is a string with path and filename to output mhm file
# d is a dictionary with MH parameter values (parameter names are keys)
def dict_to_mhm(filename, d, material="young_caucasian_male"):
    if "young_caucasian" in material:
        mfolder = material.replace("2","")
    else:
        mfolder = material
    
    file = open(filename, "w") 
    file.writelines(["# Written by MakeHuman 1.1.0 \n",
                     "version v1.1.0 \n",
                     "tags rc_id_model \n",
                     "camera 0.0 0.0 -0.00976801788413 0.839224815951 0.0199519524326 7.6875 \n"])
    
    for x,y in d.items():
        file.write("modifier "+x+" "+str(y)+" \n")

    file.writelines(["tongue tongue01 52ad91a3-caad-4e50-8c38-67634e5e789c \n",
                     "teeth Teeth_Base 0a5ec82a-0d5f-43ce-a765-8f076f95692d \n",
                     "eyebrows eyebrow012 1c16325c-7831-4166-831a-05c5b609c219 \n",
                     "eyes HighPolyEyes 2c12f43b-1303-432c-b7ce-d78346baf2e6 \n",
                     "clothesHideFaces True \n",
                     "skinMaterial skins/"+mfolder+"/"+material+".mhmat \n",
                     "material HighPolyEyes 2c12f43b-1303-432c-b7ce-d78346baf2e6 eyes/materials/brown.mhmat \n",
                     "subdivide True \n",])

    file.close()



def read_params(filename):
    import re
    modifier_pattern = re.compile("modifier\s([^\s]+)\s([^\s]+)")
    modifiers = {}
    with open(filename, 'r') as f:
        for line in f:
            import re
            m = re.search(modifier_pattern, line)
            if m:
                modifiers[m.group(1)] = float(m.group(2))
    return modifiers

def write_mimic_file(mimic_file, out_file, keys, face_data):
    d = dict(zip(keys, list(face_data)))
    s = ""
    import re
    modifier_pattern = re.compile("modifier\s([^\s]+)\s([^\s]+)")
    with open(mimic_file, 'r') as f:
        for line in f:
            import re
            m = re.search(modifier_pattern, line)
            if m and m.group(1) in d:
                s += "modifier {} {}\n".format(m.group(1), d[m.group(1)])
            else:
                s += line
    with open(out_file, 'w') as f:
        f.write(s)

## Convert mhm files to the same format/order of parameters
def convert_all_params(mh_dir, mimic_file):
    import os
    
    #all_params = read_params("C:/Users/eremarti/Downloads/new-models (1)/all_params.mhm")
    all_params = read_params(mimic_file)
    mh_files = os.listdir(mh_dir)
    params_list = []
    for key in range(0,len(all_params)):
        params_list.append(list(all_params)[key])
    for filename in mh_files:
        for x in range(0,len(params_list)):
            file_params = read_params(os.path.join(mh_dir,filename))
            f_list = []
            for k in range(0,len(list(file_params))):
                f_list.append(list(file_params)[k])
            if params_list[x] in f_list:
                continue
            else:      
                # open the sample file used 
                with open(os.path.join(mh_dir,filename), 'r') as file:
                # read the content of the file opened 
                    content = file.readlines() 
                    content[x+2] += ("modifier " + params_list[x] +" "+ str(0)+"\n")
                    with open(os.path.join(mh_dir,filename), 'w') as f:
                        f.writelines(content)
                        f.close()

## Return vector of parameter values from mhm file
def mhm_2_vector(f):
    f_file = read_params(f)
    f_key = []
    for key in range(0,len(f_file)):
        f_key.append(list(f_file)[key])
    f_vector = []
    for i in f_key:
        f_vector.append(f_file[i])
    return f_vector,f_key

## Transform mhm file to vector of parameters that have either subtracted (operation=0) or added (operation=1) the average model
def mhm_2_norm(filename, avg, operation=0): #operation 0 = subtract avg, operation 1 = add avg
    file_params = read_params(filename)
    avg_params = read_params(avg)
    vector_a = []
    vector = []
    for key in range(0,len(list(file_params))):
        value = list(file_params)[key]
        keys = file_params[value]
        vector.append(keys)
    for k in range(0,len(list(avg_params))):
        value = list(avg_params)[k]
        keys = avg_params[value]
        vector_a.append(keys)
    vector_np = np.array(vector)
    vector_a_np = np.array(vector_a)
    if operation == 0:
        normalized_v = np.subtract(vector_np,vector_a_np)
    elif operation == 1:
        normalized_v = np.add(vector_np,vector_a_np)
    return normalized_v

# scale all values in an MHM file
def mult_keys(filename, outfile, scale = 2):
    file_params = read_params(filename)
    vector = []
    list_params = list(file_params)
    for key in range(0,len(list(file_params))):
        value = list(file_params)[key]
        keys = file_params[value]
        vector.append(keys)
    vector_np = np.array(vector)
    mult_v = vector_np*scale
    write_mimic_file(filename, outfile, list_params, mult_v)


#############
#  FUNCTIONS TO MANIPULATE LISTS
#############

def keep_keys_with_prefixes(d, prefixes):
    """
    Modifies the dictionary `d` in place to keep only keys that start with any of the given `prefixes`.

    Parameters:
    - d (dict): The dictionary to modify.
    - prefixes (list of str): List of prefixes to keep.

    Returns:
    - dict: The modified dictionary with only matching keys retained.
    """
    keys_to_keep = {
        key: value for key, value in d.items()
        if any(key.startswith(prefix) for prefix in prefixes)
    }
    d.clear()
    d.update(keys_to_keep)
    return d

# takes a dictionary with parameter/value pairs and keeps only parameters with face info
def keep_only_face_data(d):
    prefixes = ["head", "forehead", "eyebrows", "eyebrows", "neck", "eyes",
               "nose", "mouth", "ears", "chin", "cheek", "macrodetails"]
    
    d = keep_keys_with_prefixes(d, prefixes)
    return d

# takes a dictionary with shape values and expands it to have all
# other parameters in MH with default values
# for a new model with default parameters use my_shapes={}
def make_full_shape_dict(my_shapes):
    all_shape_keys = ['head/head-age-decr|incr', 'head/head-angle-in|out', 'head/head-fat-decr|incr', 'head/head-oval', 'head/head-round', 'head/head-rectangular', 'head/head-square', 'head/head-triangular', 'head/head-invertedtriangular', 'head/head-diamond', 'head/head-scale-depth-decr|incr', 'head/head-scale-horiz-decr|incr', 'head/head-scale-vert-decr|incr', 'head/head-trans-in|out', 'head/head-trans-down|up', 'head/head-trans-backward|forward', 'head/head-back-scale-depth-decr|incr', 'forehead/forehead-trans-backward|forward', 'forehead/forehead-scale-vert-decr|incr', 'forehead/forehead-nubian-decr|incr', 'forehead/forehead-temple-decr|incr', 'eyebrows/eyebrows-trans-backward|forward', 'eyebrows/eyebrows-angle-down|up', 'eyebrows/eyebrows-trans-down|up', 'neck/neck-double-decr|incr', 'neck/neck-scale-depth-decr|incr', 'neck/neck-scale-horiz-decr|incr', 'neck/neck-scale-vert-decr|incr', 'neck/neck-trans-in|out', 'neck/neck-trans-down|up', 'neck/neck-trans-backward|forward', 'neck/neck-back-scale-depth-decr|incr', 'eyes/l-eye-bag-decr|incr', 'eyes/r-eye-bag-decr|incr', 'eyes/l-eye-bag-in|out', 'eyes/r-eye-bag-in|out', 'eyes/l-eye-bag-height-decr|incr', 'eyes/r-eye-bag-height-decr|incr', 'eyes/l-eye-eyefold-angle-down|up', 'eyes/r-eye-eyefold-angle-down|up', 'eyes/l-eye-epicanthus-in|out', 'eyes/r-eye-epicanthus-in|out', 'eyes/l-eye-eyefold-concave|convex', 'eyes/r-eye-eyefold-concave|convex', 'eyes/l-eye-eyefold-down|up', 'eyes/r-eye-eyefold-down|up', 'eyes/l-eye-height1-decr|incr', 'eyes/r-eye-height1-decr|incr', 'eyes/l-eye-height2-decr|incr', 'eyes/r-eye-height2-decr|incr', 'eyes/l-eye-height3-decr|incr', 'eyes/r-eye-height3-decr|incr', 'eyes/l-eye-push1-in|out', 'eyes/r-eye-push1-in|out', 'eyes/l-eye-push2-in|out', 'eyes/r-eye-push2-in|out', 'eyes/l-eye-trans-in|out', 'eyes/r-eye-trans-in|out', 'eyes/l-eye-trans-down|up', 'eyes/r-eye-trans-down|up', 'eyes/l-eye-scale-decr|incr', 'eyes/r-eye-scale-decr|incr', 'eyes/l-eye-corner1-down|up', 'eyes/r-eye-corner1-down|up', 'eyes/l-eye-corner2-down|up', 'eyes/r-eye-corner2-down|up', 'nose/nose-trans-down|up', 'nose/nose-trans-backward|forward', 'nose/nose-trans-in|out', 'nose/nose-scale-vert-decr|incr', 'nose/nose-scale-horiz-decr|incr', 'nose/nose-scale-depth-decr|incr', 'nose/nose-nostrils-width-decr|incr', 'nose/nose-point-width-decr|incr', 'nose/nose-base-down|up', 'nose/nose-width1-decr|incr', 'nose/nose-width2-decr|incr', 'nose/nose-width3-decr|incr', 'nose/nose-compression-compress|uncompress', 'nose/nose-curve-concave|convex', 'nose/nose-greek-decr|incr', 'nose/nose-hump-decr|incr', 'nose/nose-volume-decr|incr', 'nose/nose-nostrils-angle-down|up', 'nose/nose-point-down|up', 'nose/nose-septumangle-decr|incr', 'nose/nose-flaring-decr|incr', 'mouth/mouth-scale-horiz-decr|incr', 'mouth/mouth-scale-vert-decr|incr', 'mouth/mouth-scale-depth-decr|incr', 'mouth/mouth-trans-in|out', 'mouth/mouth-trans-down|up', 'mouth/mouth-trans-backward|forward', 'mouth/mouth-lowerlip-height-decr|incr', 'mouth/mouth-lowerlip-width-decr|incr', 'mouth/mouth-upperlip-height-decr|incr', 'mouth/mouth-upperlip-width-decr|incr', 'mouth/mouth-cupidsbow-width-decr|incr', 'mouth/mouth-dimples-in|out', 'mouth/mouth-laugh-lines-in|out', 'mouth/mouth-lowerlip-ext-down|up', 'mouth/mouth-angles-down|up', 'mouth/mouth-lowerlip-middle-down|up', 'mouth/mouth-lowerlip-volume-decr|incr', 'mouth/mouth-philtrum-volume-decr|incr', 'mouth/mouth-upperlip-volume-decr|incr', 'mouth/mouth-upperlip-ext-down|up', 'mouth/mouth-upperlip-middle-down|up', 'mouth/mouth-cupidsbow-decr|incr', 'ears/r-ear-trans-backward|forward', 'ears/r-ear-scale-decr|incr', 'ears/r-ear-trans-down|up', 'ears/r-ear-scale-vert-decr|incr', 'ears/r-ear-lobe-decr|incr', 'ears/r-ear-shape-pointed|triangle', 'ears/r-ear-rot-backward|forward', 'ears/r-ear-shape-square|round', 'ears/r-ear-scale-depth-decr|incr', 'ears/r-ear-wing-decr|incr', 'ears/r-ear-flap-decr|incr', 'ears/l-ear-trans-backward|forward', 'ears/l-ear-scale-decr|incr', 'ears/l-ear-trans-down|up', 'ears/l-ear-scale-vert-decr|incr', 'ears/l-ear-lobe-decr|incr', 'ears/l-ear-shape-pointed|triangle', 'ears/l-ear-rot-backward|forward', 'ears/l-ear-shape-square|round', 'ears/l-ear-scale-depth-decr|incr', 'ears/l-ear-wing-decr|incr', 'ears/l-ear-flap-decr|incr', 'chin/chin-jaw-drop-decr|incr', 'chin/chin-cleft-decr|incr', 'chin/chin-prominent-decr|incr', 'chin/chin-width-decr|incr', 'chin/chin-height-decr|incr', 'chin/chin-bones-decr|incr', 'chin/chin-prognathism-decr|incr', 'cheek/r-cheek-volume-decr|incr', 'cheek/l-cheek-volume-decr|incr', 'cheek/r-cheek-bones-decr|incr', 'cheek/l-cheek-bones-decr|incr', 'cheek/r-cheek-inner-decr|incr', 'cheek/l-cheek-inner-decr|incr', 'cheek/r-cheek-trans-down|up', 'cheek/l-cheek-trans-down|up', 'torso/torso-scale-depth-decr|incr', 'torso/torso-scale-horiz-decr|incr', 'torso/torso-scale-vert-decr|incr', 'torso/torso-trans-in|out', 'torso/torso-trans-down|up', 'torso/torso-trans-backward|forward', 'torso/torso-vshape-decr|incr', 'torso/torso-muscle-dorsi-decr|incr', 'torso/torso-muscle-pectoral-decr|incr', 'hip/hip-scale-depth-decr|incr', 'hip/hip-scale-horiz-decr|incr', 'hip/hip-scale-vert-decr|incr', 'hip/hip-trans-in|out', 'hip/hip-trans-down|up', 'hip/hip-trans-backward|forward', 'hip/hip-waist-down|up', 'stomach/stomach-navel-in|out', 'stomach/stomach-tone-decr|incr', 'stomach/stomach-pregnant-decr|incr', 'stomach/stomach-navel-down|up', 'buttocks/buttocks-volume-decr|incr', 'pelvis/pelvis-tone-decr|incr', 'pelvis/bulge-decr|incr', 'armslegs/r-hand-fingers-distance-decr|incr', 'armslegs/r-hand-fingers-diameter-decr|incr', 'armslegs/r-hand-fingers-length-decr|incr', 'armslegs/r-hand-scale-decr|incr', 'armslegs/r-hand-trans-in|out', 'armslegs/l-hand-fingers-distance-decr|incr', 'armslegs/l-hand-fingers-diameter-decr|incr', 'armslegs/l-hand-fingers-length-decr|incr', 'armslegs/l-hand-scale-decr|incr', 'armslegs/l-hand-trans-in|out', 'armslegs/r-foot-scale-decr|incr', 'armslegs/r-foot-trans-in|out', 'armslegs/r-foot-trans-backward|forward', 'armslegs/l-foot-scale-decr|incr', 'armslegs/l-foot-trans-in|out', 'armslegs/l-foot-trans-backward|forward', 'armslegs/r-lowerarm-scale-depth-decr|incr', 'armslegs/r-lowerarm-scale-horiz-decr|incr', 'armslegs/r-lowerarm-scale-vert-decr|incr', 'armslegs/r-lowerarm-fat-decr|incr', 'armslegs/r-lowerarm-muscle-decr|incr', 'armslegs/r-upperarm-scale-depth-decr|incr', 'armslegs/r-upperarm-scale-horiz-decr|incr', 'armslegs/r-upperarm-scale-vert-decr|incr', 'armslegs/r-upperarm-fat-decr|incr', 'armslegs/r-upperarm-shoulder-muscle-decr|incr', 'armslegs/r-upperarm-muscle-decr|incr', 'armslegs/l-lowerarm-scale-depth-decr|incr', 'armslegs/l-lowerarm-scale-horiz-decr|incr', 'armslegs/l-lowerarm-scale-vert-decr|incr', 'armslegs/l-lowerarm-fat-decr|incr', 'armslegs/l-lowerarm-muscle-decr|incr', 'armslegs/l-upperarm-scale-depth-decr|incr', 'armslegs/l-upperarm-scale-horiz-decr|incr', 'armslegs/l-upperarm-scale-vert-decr|incr', 'armslegs/l-upperarm-fat-decr|incr', 'armslegs/l-upperarm-shoulder-muscle-decr|incr', 'armslegs/l-upperarm-muscle-decr|incr', 'armslegs/r-leg-valgus-decr|incr', 'armslegs/r-lowerleg-scale-depth-decr|incr', 'armslegs/r-lowerleg-scale-horiz-decr|incr', 'armslegs/r-lowerleg-fat-decr|incr', 'armslegs/r-lowerleg-muscle-decr|incr', 'armslegs/r-upperleg-scale-depth-decr|incr', 'armslegs/r-upperleg-scale-horiz-decr|incr', 'armslegs/r-upperleg-scale-vert-decr|incr', 'armslegs/r-upperleg-fat-decr|incr', 'armslegs/r-upperleg-muscle-decr|incr', 'armslegs/l-leg-valgus-decr|incr', 'armslegs/l-lowerleg-scale-depth-decr|incr', 'armslegs/l-lowerleg-scale-horiz-decr|incr', 'armslegs/l-lowerleg-fat-decr|incr', 'armslegs/l-lowerleg-muscle-decr|incr', 'armslegs/l-upperleg-scale-depth-decr|incr', 'armslegs/l-upperleg-scale-horiz-decr|incr', 'armslegs/l-upperleg-scale-vert-decr|incr', 'armslegs/l-upperleg-fat-decr|incr', 'armslegs/l-upperleg-muscle-decr|incr', 'armslegs/lowerlegs-height-decr|incr', 'armslegs/upperlegs-height-decr|incr', 'breast/BreastSize', 'breast/BreastFirmness', 'breast/breast-trans-down|up', 'breast/breast-dist-decr|incr', 'breast/breast-point-decr|incr', 'breast/breast-volume-vert-down|up', 'breast/nipple-size-decr|incr', 'breast/nipple-point-decr|incr', 'genitals/penis-length-decr|incr', 'genitals/penis-circ-decr|incr', 'genitals/penis-testicles-decr|incr', 'macrodetails/Gender', 'macrodetails/Age', 'macrodetails/African', 'macrodetails/Asian', 'macrodetails/Caucasian', 'macrodetails-universal/Muscle', 'macrodetails-universal/Weight', 'macrodetails-height/Height', 'macrodetails-proportions/BodyProportions', 'measure/measure-neck-circ-decr|incr', 'measure/measure-neck-height-decr|incr', 'measure/measure-upperarm-circ-decr|incr', 'measure/measure-upperarm-length-decr|incr', 'measure/measure-lowerarm-length-decr|incr', 'measure/measure-wrist-circ-decr|incr', 'measure/measure-frontchest-dist-decr|incr', 'measure/measure-bust-circ-decr|incr', 'measure/measure-underbust-circ-decr|incr', 'measure/measure-waist-circ-decr|incr', 'measure/measure-napetowaist-dist-decr|incr', 'measure/measure-waisttohip-dist-decr|incr', 'measure/measure-shoulder-dist-decr|incr', 'measure/measure-hips-circ-decr|incr', 'measure/measure-upperleg-height-decr|incr', 'measure/measure-thigh-circ-decr|incr', 'measure/measure-lowerleg-height-decr|incr', 'measure/measure-calf-circ-decr|incr', 'measure/measure-knee-circ-decr|incr', 'measure/measure-ankle-circ-decr|incr']
    
    # make full shape dictionary
    shape = dict.fromkeys(all_shape_keys, 0.0)
    #macrodetails are the only parameters with nonzero defaults
    shape["macrodetails/Gender"] = 0.5
    shape["macrodetails/Age"] = 0.5
    shape["macrodetails/African"] = 0.33333
    shape["macrodetails/Asian"] = 0.33333
    shape["macrodetails/Caucasian"] = 0.33333
    shape["macrodetails-universal/Muscle"] = 0.5
    shape["macrodetails-universal/Weight"] = 0.5
    shape["macrodetails-height/Height"] = 0.5
    shape["macrodetails-proportions/BodyProportions"] = 0.5
    
    # update shape dictionary with provided values
    shape.update(my_shapes)
    
    return shape

# takes a dictionary with pose values and expands it to have all
# other parameters in MH with default values
# for a new model with default parameters use my_poses={}
def make_full_pose_dict(my_poses):
    all_pose_keys = ['Rest', 'LeftBrowDown', 'RightBrowDown', 'LeftOuterBrowUp', 'RightOuterBrowUp', 'LeftInnerBrowUp', 'RightInnerBrowUp', 'NoseWrinkler', 'LeftUpperLidOpen', 'RightUpperLidOpen', 'LeftUpperLidClosed', 'RightUpperLidClosed', 'LeftLowerLidUp', 'RightLowerLidUp', 'LeftEyeDown', 'RightEyeDown', 'LeftEyeUp', 'RightEyeUp', 'LeftEyeturnRight', 'RightEyeturnRight', 'LeftEyeturnLeft', 'RightEyeturnLeft', 'LeftCheekUp', 'RightCheekUp', 'CheeksPump', 'CheeksSuck', 'NasolabialDeepener', 'ChinLeft', 'ChinRight', 'ChinDown', 'ChinForward', 'lowerLipUp', 'lowerLipDown', 'lowerLipBackward', 'lowerLipForward', 'UpperLipUp', 'UpperLipBackward', 'UpperLipForward', 'UpperLipStretched', 'JawDrop', 'JawDropStretched', 'LipsKiss', 'MouthMoveLeft', 'MouthMoveRight', 'MouthLeftPullUp', 'MouthRightPullUp', 'MouthLeftPullSide', 'MouthRightPullSide', 'MouthLeftPullDown', 'MouthRightPullDown', 'MouthLeftPlatysma', 'MouthRightPlatysma', 'TongueOut', 'TongueUshape', 'TongueUp', 'TongueDown', 'TongueLeft', 'TongueRight', 'TonguePointUp', 'TonguePointDown']
    
    # make full shape dictionary
    poses = dict.fromkeys(all_pose_keys, 0.0)
    
    # update shape dictionary with provided values
    poses.update(my_poses)
    
    return poses


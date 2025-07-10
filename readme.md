# phystrackx
An open source python tool for detecting and automating basic physics lab experiment videos.

# phystrack-python
Object Tracking For Physics

## Installation
Clone the repository and install the required packages with:
```
pip3 install -r requirements.txt
```
## How To Run
To start Phystrack, open the terminal in the cloned directory and run `src/main.py`, execute the following command:

```
python3 src/main.py
```
![PhysTrack Logo](http://i.imgur.com/5YFi1E8.png)

## What is PhysTrack?

PhysTrack is a Matlab based video tracking solution for analyzing kinematics of moving bodies. Since Matlab is a very popular analysis tool in physics laboratories around the globe, we have tried to combine the robustness of Matlab computation power with such a friendly user interface which can be found in commercial video tracking software.

## Who should use it?

PhysTrack is used in numerous physics experiments of [Smart Physics Lab](http://physlab.org/smart-physics/) section of [PhysLab](http://physlab.org/smart-physics/). 

Physics teachers, students and researchers can use PhysTrack to track the motion of moving bodies and investigate the underlying physics in many kinds of experiments. Typical examples of these experiments are rotating and translating discs [1], spring pendulum systems [2], bodies colliding on a plane and projectiles [3], microspheres exhibiting Brownian motion [4], liquid droplets falling down a stream and the movement of a fruitfly [5].

Examples of some experiments can be viewed on the Smart Physics Lab website on [This Link](http://physlab.org/smart-physics/).

[June 2015] EJP (European Journal of Physics) publishes ["PhysTrack: A Matlab based environment for video tracking of kinematics in physics laboratory"](http://iopscience.iop.org/article/10.1088/1361-6404/aa747a/meta;jsessionid=EA876E543596F17F173DA7C593F6F86D.c3.iopscience.cld.iop.org), a paper which discusses PhysTrack and related concepts in detail.

## Requirements for performing an experiment with PhysTrack

* In addition to having primary knowledge of kinematics, we assume that the user is accustomed with the basics of Matlab as well.

* To capture videos a good slow motion camera is required. In PhysLab, we usually use a [Canon PowerShot SX280HS](https://www.cnet.com/products/canon-powershot-sx280-hs/review/) mounted on a tripod stand which works very well with most of the mechanics experiments. This camera can capture video at as high a frame rate as 240fps with a frame size of 320x240 pixels.

* For investigating microscopic motion, a video microscope is also required. In PhysLab, we usually use a [Motic BA210 Trinocular](http://www.motic.com/As_LifeSciences_UM_BA210/product_240.html) for investigating the Brownian motion of micro particles.

* Usually, to move the objects in required fashion, an apparatus is also recommended.

* A computer with RAM >=3GB and an installation of Matlab 2006 (or above) with [Image Acquisition Toolbox](https://www.mathworks.com/products/imaq.html) and [Computer Vision Toolbox](https://www.mathworks.com/products/computer-vision.html) is also required.

## Getting started

You are only a couple of steps away from using PhysTrack for your own experiments. 

* Download and extract the latest PhysTrack source from the downloads section. It also contains some additional experiment scripts which serve as an example for creating your own experiments.

* Also, choose and download a sample video from the [this link](https://github.com/umartechboy/PhysTrack/tree/master/SampleVideos) or  download all as zip from [this link.](https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/umartechboy/PhysTrack/tree/master/SampleVideos)

* Open Matlab and change the current directory to the downloaded package. You should see the _"+PhysTrack"_ and _"GUIs"_ directory along with some _"analyze motion"_ scripts in the current address window.

* Option 1. (V3.0 and later) Type in "RunWizard" and hit _"Enter"_. Depending upon the type of experiment required, select any script from the window and run it. A wizard will popup with the experiment sequential steps splitted in separate buttons.

* Option 2. (Depreciated) Depending upon the type of experiment required, select any script from the window and run it. (Or you can type in the name of that experiment in the command window and hit _"Enter"_.

* The scripts are designed to be user interactive. They communicate with the user through GUI's and message boxes and guide through the whole process. The script will also ask to load the experiment video you downloaded in the previous steps.

* Once done, peruse the sample "analyzeMotionX" scripts, which are well commented, and try to understand how you can modify the codes for your own experiment. You will also find help on the usage of each function from the [PhysTrack Wiki](https://github.com/umartechboy/PhysTrack/wiki).

* Capture your own experiment's video and start making robust video tracking experiment scripts.

## Downloads

<a href="https://github.com/umartechboy/PhysTrack/archive/master.zip" target="_blank"><img src="https://raw.githubusercontent.com/umartechboy/PhysTrack/master/download.PNG" 
alt="PhysTrack Package" width="20" height="20" border="10" /></a> [Complete package including the sample videos (this Git)](https://github.com/umartechboy/PhysTrack/archive/master.zip)

<a href="https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/umartechboy/PhysTrack/tree/master/Source%20Code" target="_blank"><img src="https://raw.githubusercontent.com/umartechboy/PhysTrack/master/download.PNG" 
alt="PhysTrack Package" width="20" height="20" border="10" /></a> [The latest PhysTrack Package (without videos)](https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/umartechboy/PhysTrack/tree/master/Source%20Code)

<a href="https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/umartechboy/PhysTrack/tree/master/SampleVideos" target="_blank"><img src="https://raw.githubusercontent.com/umartechboy/PhysTrack/master/download.PNG" 
alt="PhysTrack Package" width="20" height="20" border="10" /></a> [Sample Videos](https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/umartechboy/PhysTrack/tree/master/SampleVideos)

<a href="https://github.com/umartechboy/PhysTrack/blob/master/PhysTrack%20--%20Experimenter's%20Reference%20Manual%202017-1.pdf" target="_blank"><img src="https://raw.githubusercontent.com/umartechboy/PhysTrack/master/download.PNG" 
alt="PhysTrack Package" width="20" height="20" border="10" /></a> [Experimenter's Reference Manual](https://github.com/umartechboy/PhysTrack/blob/master/PhysTrack%20--%20Experimenter's%20Reference%20Manual%202017-1.pdf)

## Release Updates
* V3.0 Added a new way of running the MotionScripts, the PhysTrack Wizard. The main function is PhysTrack.Wizard.RunWizard. It presents a GUI which runs the same motion scripts in sequential parts.

## Performing a physics experiment with PhysTrack

![Process Flow](http://i.imgur.com/iYiVtuD.png)

Performing a classical mechanics experiments using video tracking and performing advance analysis is very simple.

* We capture video of the moving object using a digital camera, 
* use one of the automated trackers of PhysTrack to track the objects and generate position and orientation data,
* to investigate the motion, use the in-built Matlab tools or those included in PhysTrack like numerical differentiation, curve fitting, object stitching and coordinate system transformation and
* present the results using Matlab plots and video plots included in PhysTrack.

## Sample experiments
| Experiment Title | Student manual and resources | Sample Analysis Codes| Sample Videos|
| ------------------ |:----------:| :----------:|:----------:|
|	Spring pendulum	|	[Link]	(http://physlab.org/experiment/spring-pendulum/)	|	[analyze1DSHM.m]	(https://github.com/umartechboy/PhysTrack/blob/master/Source%20Code/analyze1DSHM.m)	|	[Link]	(https://github.com/umartechboy/PhysTrack/tree/master/SampleVideos/SpringPendulum) 	|
|	2D Collisions	|	[Link]	(http://physlab.org/experiment/colliding-pucks-on-a-carom-board/)	|	[analyze2DCollision.m]	(https://github.com/umartechboy/PhysTrack/blob/master/Source%20Code/analyze2DCollision.m)	|	[Link]	(https://github.com/umartechboy/PhysTrack/tree/master/SampleVideos/CaromPuck)	|
|	Projectile Motion	|	[Link]	(http://physlab.org/experiment/projectile-motion/)	|	[analyzeProjectileMotion.m]	(https://github.com/umartechboy/PhysTrack/blob/master/Source%20Code/analyzeProjectileMotion.m)	|	[Link]	(https://github.com/umartechboy/PhysTrack/tree/master/SampleVideos/Projectile%20Motion)	|
|	Sliding Friction	|	[Link]	(http://physlab.org/experiment/sliding-friction-2/)	|	[analyzeSlidingFriction.m]	(https://github.com/umartechboy/PhysTrack/blob/master/Source%20Code/analyzeSlidingFriction.m)	|	[Link]	(https://github.com/umartechboy/PhysTrack/tree/master/SampleVideos/SlidingFriction)	|
|	Rotation on a Fixed Pivot	|	[Link]	(http://physlab.org/experiment/rotational-motion-about-a-fixed-axis/)	|	[analyzeRotationOnAFixedPivot.m]	(https://github.com/umartechboy/PhysTrack/blob/master/Source%20Code/analyzeRotationOnAFixedPivot.m)	|	[Link]	(https://github.com/umartechboy/PhysTrack/tree/master/SampleVideos/RotationOnAFixedPivot)	|
|	Brownian Motion	|	[Link]	(http://physlab.org/experiment/tracking-brownian-motion-through-video-microscopy/)	|	[analyzeBrownianMotion.m]	(https://github.com/umartechboy/PhysTrack/blob/master/Source%20Code/analyzeBrownianMotion.m)	|	[Link]	(https://github.com/umartechboy/PhysTrack/tree/master/SampleVideos/BrownianMotion)	|
|	Rotational Friction	|			|	[analyzeRotationalFriction.m]	(https://github.com/umartechboy/PhysTrack/blob/master/Source%20Code/analyzeRotationalFriction.m)	|	[Link]	(https://github.com/umartechboy/PhysTrack/blob/master/SampleVideos/RollingCylinder.MP4)	|
|	Wilberforce Pendulum|			|	[analyzeWilberforcePendulum.m]	(https://github.com/umartechboy/PhysTrack/blob/master/Source%20Code/analyzeWilberforcePendulum.m)	|	[Link]	(https://www.youtube.com/watch?v=UNhr9W0W-JE&list=PLImGVzFaOSBwp81p6VPLUukONhXLhCnB8)	|



## Video demonstration

Once the video is captured, PhysTrack is used in Matlab for extracting data, performing analysis and presenting the results. When using the sample _"analyze motion"_ scripts from the previous section, the process is similar for all the experiments. Users can also take these experiments as a base for creating new scrips and automated experiments.

<a href="http://www.youtube.com/watch?feature=player_embedded&v=tSQxx-jpT-Q" target="_blank"><img src="http://i.imgur.com/VrLSe5p.png" 
alt="Video Demonstration on YouTube" width="650" height="360" border="10" /></a>

## Resources

* [PhysTrack Wiki](https://github.com/umartechboy/PhysTrack/wiki).
* Primer: [Investigating kinematics with PhysTrack](http://physlab.org/wp-content/uploads/2016/03/primer_videoTracking-1.pdf).
* [Examples of mechanics experiments](http://physlab.org/tag/mechanics/).
* [Example of experiment with video microscopy](http://physlab.org/experiment/tracking-brownian-motion-through-video-microscopy/).
* [PhysLab website](http://physlab.org/).
* PhysTrack paper published in EJP (European Journal of Physics): ["PhysTrack": a Matlab based environment for video tracking of kinematics in the physics laboratory](http://iopscience.iop.org/article/10.1088/1361-6404/aa747a/meta;jsessionid=EA876E543596F17F173DA7C593F6F86D.c3.iopscience.cld.iop.org).

## Credits

The whole work is an effort of <a href="http://physlab.org/">PhysLab</a> of the Lahore University of Management Sciences (<a href="https://lums.edu.pk/">LUMS</a>), Lahore, Pakistan. Kindly feel free to contact in case you wish to contribute in the development and improvement of this library.

### Authors

M. Umar Hassan, [M. Sabieh Anwar](http://physlab.org/muhammad-sabieh-anwar-personal/).

## References

[1] J. Poonyawatpornkul and P. Wattanakasiwich, "High-speed video analysis of a rolling disc in three dimensions", Eur. J. Phys. 36 065027 (2015).

[2] J. Poonyawatpornkul and P. Wattanakasiwich, _"High-speed video analysis of damped harmonic motion"_, Eur. J. Phys. 48 6 (2013).

[3] Loo Kang Wee, Charles Chew, Giam Hwee Goh, Samuel Tan and Tat Leong Lee, _"Using Tracker as a pedagogical tool for understanding projectile motion"_ Eur. J. Phys. 47 448 (2012).

[4] Paul Nakroshis, Matthew Amoroso, Jason Legere and Christian Smith, _"Measuring Boltzmann’s constant using video microscopy of Brownian motion"_, Am. J. Phys, 71, 568 (2003).

[5] [_"Tracking kinematics of a fruitfly using video analysis"_](http://goo.gl/ljypdC).

The first version uploaded on GitHub is v2.1 and a comprehensive documentation of this code can be viewed on PhysTrack Wiki on <a href="https://github.com/umartechboy/PhysTrack/wiki">This Link</a>. 


# Lucas-Kanade Optical Flow Implementation in PhysTrackerX

## Overview of Tracking System
The tracking system in PhysTrackerX uses the Lucas-Kanade optical flow algorithm to track points across video frames. The implementation is primarily handled in the `strack()` method of the VideoApp and VideoApp2 class, with support from the VideoProcessor class for frame processing and point/filter management.

The object tracking is done by `cv2.calcOpticalFlowPyrLK` in the `strack()` method of the VideoApp classes.

The filters are only to assist the LK method perform better tracking.

Dr. Sabieh needed a robust tracker that adapts to multiple setups and lightings, so the most of the filters are to cater more precise object tracking, please play around with them, especially with the Puck, Candle, and Balloon Videos for a better understanding of how each filter functions. 

Some filters have very specific uses which I have outlined below:

1. The GMM filters are Gaussian Mixture Models that Auto Detect Objects and attempt to Auto Track them. Dr. Sabieh wanted an AutoTracker as well but GMM is highly sensitive and tends to track alot of noise as well, try using it on the Puck videos to see its effect. It requires thresholding for each scenario, you can setup dynamic parameters (allowing the user to adjust them in the GUI with a slider like interface), I did not get time to implement that, maybe you can.

2. Moreover, the Object Separation filter tries to differentiate by color, use it on the spring pendulum videos or the puck videos to see it in effect. Again you  may need to adjust its sensitivity parameters.

3. The Optical Flow filter is more of an educational tool that tries to show what Optical Flow is and how it can track object based on Gradient flow.


## Lucas-Kanade (LK) Algorithm Implementation

In my last meeting with Dr. Sabieh, we saw that PhystrackX was not tracking at all in certain scenarios. To fix that, please either try adjusting the parameters of `cv2.calcOpticalFlowPyrLK` or try other versions of the LK Algorithm or even other Object Tracking Algorithms. You can look them up in the cv2 documentation. I think adjusting the parameters will be enough but extensive experimentation will point you in the right direction.

The flow of the tracking functionality is described in the following sections.

I have also added detailed comments to the `strack()` function in both `rigid.py` and `nonrigid.py`.

### 1. Theory and Mathematical Foundation
The Lucas-Kanade method assumes that the flow is essentially constant in a local neighborhood of pixels. It solves the basic optical flow equations:

I(x,y,t) = I(x + dx, y + dy, t + dt)

Where:
- I(x,y,t) is the image intensity at point (x,y) at time t
- dx, dy are the pixel displacements
- dt is the time step between frames

### 2. Pyramidal Implementation
The application uses a pyramidal implementation with the following characteristics:

- **Pyramid Levels**: 2 levels of image pyramids
  - Enables tracking of both large and small movements
  - Each level reduces image size by factor of 2
  - Tracking starts at coarsest level and refines at each level

- **Window Size**: 15x15 pixels
  - Balances between accuracy and computational load
  - Large enough to capture feature context
  - Small enough to maintain local motion assumption

### 3. Point Selection and Initialization
The tracking process begins with point selection, handled by the `mark_points_to_track()` method:

- Users manually select points on rigid objects
- Points are stored as (x,y) coordinates
- Initial points serve as reference for tracking
- Each point selection is validated for tracking suitability

### 4. Frame-to-Frame Tracking Process

#### a. Preprocessing
For each frame pair:
1. Convert frames to grayscale
2. Apply any selected filters from VideoProcessor
3. Prepare point arrays for tracking

#### b. Core Tracking Steps
The main tracking loop (in `strack()`):

1. **Point Prediction**:
   - Estimate new point locations based on previous motion
   - Use multi-scale pyramid for initial estimates
   - Handle both small and large displacements

2. **Point Refinement**:
   - Iterative refinement at each pyramid level
   - Maximum 10 iterations per level
   - Convergence threshold of 0.03

3. **Status Checking**:
   - Track quality assessment for each point
   - Point status validation
   - Error threshold monitoring

#### c. Point Update System
After tracking computation:
1. Filter out points with poor tracking quality
2. Update successful point positions
3. Store trajectory history in points_tracked dictionary

### 5. Error Handling and Quality Control

#### Tracking Quality Metrics:
- Status array indicates tracking success/failure
- Error measurements for each point
- Confidence thresholds for point acceptance

#### Error Prevention:
- Lost point detection
- Motion consistency checking
- Boundary condition handling


### Critical Parameters:
- Window size (15x15) optimized for typical motion scales
- Pyramid levels (2) balanced for range of motions
- Iteration limits (10) for convergence control
- Error threshold (0.03) for quality control


### Limitations:
- Assumes brightness constancy
- Requires textured surfaces
- Limited to local motion model
- Sensitive to rapid lighting changes
- May lose track during occlusions

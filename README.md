# Image Segmenter

This is a python-based segmenter tool for png and jpg images.

## To set up environment
1. Install [Anaconda](https://www.anaconda.com/distribution/#download-section)
2. On Mac/Linux open **Terminal**. On Windows open **Anaconda Prompt**.
3. Enter the following to create the environment:

```
conda create --name Segmenter -c conda-forge python=3.7 opencv=3.4.2 pyside2
    
conda activate Segmenter
```

You should see `(Segmenter)` at the left side of the bottom line in the terminal/prompt window.

4. Download the code:

    git clone https://github.com/Mullans/ImageSegmenter
    
5. Open the project and run the code:
```
cd ImageSegmenter
    
python main.py
```
When running after the first time you only need steps 2 and 5.


## TLDR

Select the folder of images to annotate with the *Set Image Folder* button on the bottom left. Select the type of label to annotate with the drop-down menu in the top right (*Current Segmentation Mask*). Left click and drag to paint on the image. Click *Run GrabCut Segmenter* to autocomplete. Use the mouse wheel to zoom in (if you have it), and pan around using right click and drag. 

## Features

To quit, either Ctrl+Q, closing the window, or going to the *File* menu and selecting *Quit* will work.

### Image Area
* Left click and drag to paint using whichever brush is currently chosen
* Scroll up with a mouse wheel to zoom in or down to zoom out
* Right click and drag to pan across a zoomed image

### Right Toolbar
* *Current Segmentation Mask* dropdown to select what type of label is currently being worked on
* *Brush Options* to change the current brush.
    * Foreground/Background - What they say. These will not be changed by GrabCut
    * Possible Foreground - You can use this on edges if you want GrabCut to refine them (see below). 
    * Erase - Erases any other marks. Empty area can be changed by GrabCut.
* *Undo* - You can undo up to 10 steps from the current label session (resets when changing label/image). This includes drawing, erasing, GrabCut, or clear mask.
* *Redo* - Redo anything undone.
* *Run GrabCut Segmenter* - Tries to autocomplete the current segmentation. This only changes empty area or possible foreground. This may be a little slow depending on your machine.
* *Save Mask* - Saves the current segmentation. These are saved into a folder inside the image directory you are working on. The folder will have the same name as your current segmentation mask type.
* *Clear Mask* - Clear the current segmenetation. This can be undone if you need.

### Bottom Toolbar
* *Pen Size* - Slider to change the pen size from 1px up to 100px.
* *Mask Opacity* - Slider to change the opacity of the segmentation over the image from 0% (totally clear) to 100% (solid color). 
* *Set Image Folder* - Set the directory of images that you want to work on. The text box to the right of this shows the current directory, and can also be clicked on.
* *Current Image* - Shows the index of the current image and the total number of images found in the working directory. The up and down arrows will let you navigate images, and you can also type the image number you want to go to.
* *Previous Image* / *Next Image* - Navigate to the previous/next images in the directory.
* *Next Unlabeled Image* - Navigate to the next image in the directory that does not have a label for the currently selected segmentation mask type.

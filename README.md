
# Welcome to PENGUIN

Penguin is a web application used to track the position reproducibility of an image plane detector (or electronic portal imaging device, EPID) used to acquire x-ray images with a linear accelerator (LINAC).

It is intended for medical physicists who want to follow
[AAPM TG 307](https://aapm.onlinelibrary.wiley.com/doi/10.1002/mp.16536)
recommendations about tests to ensure the EPID will function accurately as a dosimeter (Table 6 - EPID Positioning).

<hr>

> Note: This work is the result of my final project from the [Harvard University CS50x course](https://cs50.harvard.edu/x/2024/).

# Usage

The analysis is based on acquired images with the panel detector.

> The app has been tested with images acquired with a Varian (R) aS1000 system, Clinac-iX linear accelerator with 6MV, and ECLIPSE (R) V16 as the TPS used to export the images.

Workflow:
1. Move the detector to the position to be tracked.
2. Perform an image acquisition.
3. Export the image from the treatment planning system (TPS).
4. Open the PENGUIN app and upload the image.
5. A plot with the computed variations will be displayed.

> Notes:

> * The maximum file size that can be uploaded is 6 MB.
> * The allowed dicom file extension is **.dcm**.
> * The app does not store the uploaded images, just the result of the analysis.

In order to use the web app locally, see [Project](#project-structure) structure section.

## Reference position reproducibility

Reproducibility analysis is performed by tracking the position of the detector center, using the radiation beam center as a reference system (origin). The variation is computed as the difference in panel position with the first image uploaded to the app (reference).

As input from the user, a maximum of one image per day is expected.


## Reproducibility with SID

As before, the analysis is performed by tracking the center of the panel when the source to image plane (SID) is varying. The variation is computed as the difference between the panel center position of an image acquired at a given SID and the image aquired on the same day at reference position.

As input, commonly three images could be uploaded, acquired with SID [mm] of 100, 120 and 140 for example.


## Assumptions

1. For EPID position analysis, the first image uploaded to the app is used as the reference image. Therefore it is recommended to acquire the image after EPID calibration at the same reference position (usually with gantry angle at 0 degrees, a source to image plane distance, or SID, to 100 cm and field size of 10 cm x 10 cm).
2. Beam center is used as the origin of a reference system position. Since the center of the field is computed from the field edges, the jaws of the collimator should be correctly calibrated.


# Project structure
The project uses the flask framework.
To run the app locally, just download the source code, install dependencies (requirements.txt) and run it.

```
flask run
```

## Folders
* **/static** is used to store CSS files for styling.
* **/templates** is used to store html templates.
    * **apology.html** is used to inform the user if something were wrong.
    * **epid.html** is used to get images from the user. It also shows a graph with the variations for reference position and for SID deployments.
    * **layout.html** is used to define the main view shared between all the html files.
    * **login.html** and **register.html** are used to manage user sessions.
* **/uploads** is used as a temporary folder to store the images uploaded by the user. After the analysis is done, all files and folders inside it are deleted.

 ## Files
* The entry point to the app is ```app.py```.
    * **/register** route is used to validate and add a user to the database.
    * **/epid** route is used to show the epid.html template. By default, a plot of the reference position variation is shown if there is already data in the database. The user can use the ```select``` form with name "plot_type" to see the reproducibility with SID deployments.
    * **/epid_input_img** route is used to validate the images uploaded by the user, perform an analysis of the images, and save the results to the database.
* The ```helpers.py``` file has the core functions used to perform input user validation, image analysis and management of the results storage to the database.
    * **get_data_for_positions()** function is used to get the position of the panel center using the beam center as a coordinate reference system. It uses the FieldProfileAnalysis module from the pylinac package. Additionally the date when the file was created, SID and gantry angle used to acquire the image are obtained to be returned by the function as a dictionary.
    * **create_epid_position_figure()** function has the charge of creating a plot of the data using the matplotlib library.
* The ```penguin.db``` file is used as the database. It contains two tables: users and positions, used for user sessions, and to track image panel positions.

## Future work

To add new sections in the app to track for:
* Linearity of dose-response.
* Uniformity.
* Response reproducibility.

## Technologies used in this project

* Flask as the controller of the app.
* Pylinac for image analysis.
* Numpy for data manipulation.
* SQLite for data storage.
* Matplotlib for data visualization.
* HTML, CSS and JS for graphical user interface.

## Disclosures
1. This project uses the CS50 "finance" [project](https://cs50.harvard.edu/x/2024/psets/9/finance/) as a template.
2. This work is a continuation of a project (made by myself) named Pyportal. The source code is available on [GitHub](https://github.com/LuisOlivaresJ/Pyportal/tree/main?tab=readme-ov-file)

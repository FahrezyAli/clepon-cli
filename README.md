# Commit-Level-Error-Prediction-on-Python

clepon is a combination of cli frontend and fastapi backend to leverage large language models for commit-based defect prediction and automated whitebox testing

#### Setup Project

1. Setup mise\
   This project use [mise-en-place](https://mise.jdx.dev/), install the tool, then do

   ```
   mise trust
   mise install
   ```

   A .venv folder will be created on the working project directory automatically

2. Setup poetry\
   This project use [poetry](https://python-poetry.org/), install the tool, then do

   ```
   poetry env use .venv/bin/python
   poetry install
   ```

   This will install all the project dependencies

3. Debugging\
   When you run `poetry install`, this cli app will be installed to the project environment (the .venv folder). So do all of the modification you want, then run `poetry install`. Then you can copy the .venv folder to other python project, activate the environment `.venv/bin/activate`, then run clepon cli program to test the functionallity of this cli app on that python project, the app should automatically create clepon.toml config file in the working directory, as well as the .json file that will be sent to the backend on future version

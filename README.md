# InfoLabTakeHome2
Air quality data project

Project purpose
The purpose of this project was to demonstrate the full data pipeline, from acquisition, to cleaning and analysis.

About me
My name is Gabi Fabiyi, I'm a current MSc Computer Science student (2026) with a study focus on Big Data Analytics and Machine Learning.

I am currently attending Birkbeck College, University of London and have recently submitted my thesis project Harness Engineering for Agentic Code Generation. I am interested in Data Science/Engineering, Machine Learning and Robotics and I am currently conducting personal research into World Modelling and Gait Phase analysis for Geospacial Data/Intent Generation.

I have internship experience as a full stack developer and as a systems and data developer (current employment), and personal project experience of web development, model training and desktop application development.

I am interested in this role as a consultant with the Information Lab as I believe it would be a great opportunity to deepen my knowledge by learning directly from industry professionals and experts. I believe that learning industry practices from seasoned professionals and senior developers, along with the mentorship I would receive, would set me up for an ideal start to my career. I would relish the opportunity to provide tangible insights and benefits for clients through the application of the knowledge I gain from the Information Lab.

End to end data pipeline and visualisation
For this project, I built an air quality map for journalists to be able to easily locate information of pollutants and readings in London.

I built the pipeline using python and pandas, the script uses a back up to download only the latest data. 

The analysis stage prints a number of statistics about the dataset to the terminal.

Bash
The code can be run by first activating a python virtual environment:

python -m venv .venv

Then activate the virtual environment:

source .venv/bin/activate

Download the dependencies:

pip install -r requirements.txt

Then initialise the database:

PYTHONPATH=. python data_pipeline/main.py

Then run the server:

uvicorn backend.main:app --reload

Split your terminal

In the second terminal console, run:

cd frontend

then

npm install

and

npm update

Then run the frontend in your local developer environment:

npm run dev

The frontend page should be active, visit [http://localhost:5173/] to view it.

When done you can stop the servers using crtl + C and deactivate the virtual environment using deactivate


Future improvements
Further improvements could be made to this product by matching the sites and their index data to health trend data from outside api's eg NHS data or tfl air quality data.

AI use
AI was used for speed to create the client side and as a continuous aid throughout the writing of the pipeline
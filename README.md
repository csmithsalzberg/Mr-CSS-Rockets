# Mr-CSS-Rockets
## Terry Guan, Michael Ruvenshtein, Khyber Sen, Caleb Smith-Salzberg

### Summary
We are developing a site where users can update, create, and view stories. The catch is that when editing, the user can only see the most recent update, and a user can only view a full story once the user has edited it.


### Dependencies
  * Flask
  * typing
  * passlib
  * python-dateutil
  * virtualenv  
  These dependencies (except virtualenv) are listed in `requirements.txt` 
  and can be installed by running `pip install -r requirements.txt`.

### Launch Instructions
 1. Clone this repo using HTTPS:

     `git clone https://github.com/csmithsalzberg/Mr-CSS-Rockets.git`

      or SSH:

      `git clone git@github.com:csmithsalzberg/Mr-CSS-Rockets.git`

 2. To sandbox the dependencies, create a Python virtual environment 
    using virtualenv.

 3. Once you have a virtualenv running for Python 2.7, 
    first you must install the dependencies:  
    
        pip install -r requirements.txt  
    Then run app.py:  
    
        python app.py
 
 4. Navigate to [localhost:5000](http://localhost:5000) and follow the displayed prompts!  
    The database already comes with a 100 stories written by various 'users', 
    so you can check out and add to those stories, too, 
    or create your own new one if you want. 

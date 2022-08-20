import sqlite3
import qrcode
import wx
import wx.aui
import wx.lib.agw.aui as aui
import wx.adv
from datetime import datetime
from dateutil.relativedelta import relativedelta
import bcrypt
import cv2
import phonenumbers
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type
import smtplib, ssl
from email.mime.text import MIMEText
from random import randint
import re
server_port = 465
regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Global for the current user
currentUser = []
# Global for the current visit id
currentVisitId = None
# Global for the current exercises list
currentExercises = []
# Global for the visit ids for the current user
visitsIds = []

# Connecting to the database and allowing foreign kets
conn = sqlite3.connect('FitnessManiaDb')
conn.execute("PRAGMA foreign_keys = 1")

# Adding cursor of the database
c = conn.cursor()

# Creating tables of the database: users, users_memberships, users_visits and users_training
c.execute('''
          CREATE TABLE IF NOT EXISTS users
          ([id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, [username] TEXT, [password] TEXT, [firstname] TEXT, [lastname] TEXT, [sex] TEXT, [age] TEXT, [email] TEXT, [phone_number] TEXT, [admin_flag] BOOL)
          ''')
c.execute('''
          CREATE TABLE IF NOT EXISTS users_memberships
          ([mem_id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL ,[users_id] INTEGER , [mem_start] TEXT, [mem_end] TEXT, [purchase_date] TEXT, [mem_type] TEXT,
          [money_paid] INTEGER, [is_valid] INTEGER,
          FOREIGN KEY (users_id) REFERENCES users (id))
          ''')
c.execute('''
          CREATE TABLE IF NOT EXISTS users_visits
          ([visits_id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL ,[users_id] INTEGER , [visits_start] TEXT, [visits_end] TEXT, [weight_start] TEXT, [weight_end] TEXT,
          FOREIGN KEY (users_id) REFERENCES users (id))
          ''')
c.execute('''
          CREATE TABLE IF NOT EXISTS users_training
          ([training_id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, [visits_id] INTEGER, [users_id] INTEGER , [category] TEXT, [exercise] TEXT, [sets] TEXT, [reps] TEXT, [mins] TEXT,
          FOREIGN KEY (users_id) REFERENCES users (id),
          FOREIGN KEY (visits_id) REFERENCES users_visits (visits_id))
          ''')
c.execute('''
          CREATE TABLE IF NOT EXISTS exercises
          ([exercise_id] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, [exercise_name] TEXT, [exercise_type] TEXT, [sets_reps] BOOL, [exercise_img] TEXT)
          ''')

# Class that contains the logic for registering and logging in/out of a user


class Login(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # BUTTONS-START
        self.registerBtn = wx.Button(
            self, label='Register', pos=(500, 350), size=(200, 26))
        self.loginBtn = wx.Button(
            self, label='Login', pos=(500, 240), size=(200, 26))
        self.scanQrBtn = wx.Button(
            self, label='Scan QR', pos=(500, 400), size=(200, 26))
        # BUTTONS-END

        # STATICTEXT-START
        self.usernameTxt = wx.StaticText(
            self, label="Username:", pos=(370, 161), size=(100, 26))
        self.passwordTxt = wx.StaticText(
            self, label="Password:", pos=(370, 201), size=(100, 26))
        self.not_regi_text = wx.StaticText(
            self, label="Not Registered?", pos=(513, 310), size=(200, 26))
        self.fail_login = wx.StaticText(
            self, label="", pos=(520, 100), size=(200, 26))
        self.welcomeUser = wx.StaticText(
            self, label="", pos=(440, 50), size=(200, 26))
        self.firstNameTxt = wx.StaticText(
            self, label="", pos=(370, 241), size=(100, 26))
        self.lastNameTxt = wx.StaticText(
            self, label="", pos=(370, 281), size=(100, 26))
        self.sexTxt = wx.StaticText(
            self, label="", pos=(370, 321), size=(100, 26))
        self.ageTxt = wx.StaticText(
            self, label="", pos=(370, 361), size=(100, 26))
        self.emailTxt = wx.StaticText(
            self, label="", pos=(370, 401), size=(100, 26))
        self.phoneNumberTxt = wx.StaticText(
            self, label="", pos=(370, 441), size=(100, 26))
        # STATICTEXT-END

        # TEXTCTRL-START
        self.usernameCtrl = wx.TextCtrl(self, pos=(500, 160), size=(200, 26))
        self.passwordCtrl = wx.TextCtrl(self, pos=(
            500, 200), style=(wx.TE_PASSWORD), size=(200, 26))
        # TEXTCTRL-END

        # FONTS-START
        self.font = wx.Font(15, family=wx.FONTFAMILY_MODERN, style=0, weight=70,
                            underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        self.font.SetWeight(wx.BOLD)

        self.usernameTxt.SetFont(self.font)
        self.passwordTxt.SetFont(self.font)
        self.not_regi_text.SetFont(self.font)
        self.fail_login.SetFont(self.font)
        self.welcomeUser.SetFont(self.font)
        self.firstNameTxt.SetFont(self.font)
        self.lastNameTxt.SetFont(self.font)
        self.sexTxt.SetFont(self.font)
        self.ageTxt.SetFont(self.font)
        self.emailTxt.SetFont(self.font)
        self.phoneNumberTxt.SetFont(self.font)
        self.loginBtn.SetFont(self.font)
        self.registerBtn.SetFont(self.font)
        self.scanQrBtn.SetFont(self.font)
        # FONTS-END

        # BINDING-START
        self.loginBtn.Bind(wx.EVT_BUTTON, self.onLogin)
        self.registerBtn.Bind(wx.EVT_BUTTON, self.onRegister)
        self.scanQrBtn.Bind(wx.EVT_BUTTON, self.onScanQR)
        # self.loginBtn.Bind(wx.EVT_BUTTON, self.onValidEmail)
        # BINDING-END

    def onAllowPhone(self, event): #Allow only nums and + charecter for the phone number field
        key = event.GetKeyCode()
        if ord('0') <= key <= ord('9'): #all nums
            event.Skip()
            return

        if key == ord('+'): #allow + 
            event.Skip()
            return

        if key == ord('\010'): #allow backspace
            event.Skip()
            return
        
        return #disable everything else

    def randomCode(self, num): #We generate random number for the email validation key
        start = 10**(num-1)
        end = (10**num)-1
        return randint(start, end)

    def onValidation(self, event): #We show the user the checkCTRL and the button of the check
        try:
            self.checkCtrl.Destroy()
            self.checkBtn.Destroy()
        except:
            pass
        self.checkBtn = wx.Button(
            self, label='Check', pos=(370, 521), size=(150, 26))
        self.checkCtrl = wx.TextCtrl(self, pos=(370, 481), size=(150, 26))
        self.checkBtn.SetFont(self.font)
        self.checkBtn.Bind(wx.EVT_BUTTON, self.onValidEmail) #we bind it with onValidEmail 
        self.acceptRegisterBtn.SetLabel("Send again")


    def onValidEmail(self, event): 
        getCode = int(self.checkCtrl.GetValue())

        if getCode == self.code:#We check if the code is valid
            self.checkCtrl.Destroy()
            self.checkBtn.Destroy()
            strPassowrd = str(self.passwordCtrl.GetValue()).encode()
            genSalt = bcrypt.gensalt() 
            hashedPassword = bcrypt.hashpw(strPassowrd, genSalt) #we hash the registration password
            finalPass =  hashedPassword.decode('utf8')
            QUERY = "SELECT * FROM USERS"
            c.execute(QUERY)
            checkFirst = c.fetchall()
            if len(checkFirst) == 0: #if its first registred user we give admin rights for the admin panel
                c.execute("INSERT INTO USERS VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (None, self.usernameCtrl.GetValue(), finalPass, self.firstNameCtrl.GetValue(
                ), self.lastNameCtrl.GetValue(), self.sexCombo.GetValue(), self.ageCtrl.GetValue(), self.emailCtrl.GetValue(), self.phoneNumberCtrl.GetValue(), True))
                conn.commit()
            else:# if its not the first user we register as normal user
                c.execute("INSERT INTO USERS VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (None, self.usernameCtrl.GetValue(), finalPass, self.firstNameCtrl.GetValue(
                ), self.lastNameCtrl.GetValue(), self.sexCombo.GetValue(), self.ageCtrl.GetValue(), self.emailCtrl.GetValue(), self.phoneNumberCtrl.GetValue(), False))
                conn.commit()
          
            # Destroys the objects not needed for the view
            try:
                self.firstNameCtrl.Destroy()
                self.lastNameCtrl.Destroy()
                self.sexCombo.Destroy()
                self.ageCtrl.Destroy()
                self.emailCtrl.Destroy()
                self.phoneNumberCtrl.Destroy()
                self.acceptRegisterBtn.Destroy()
                self.firstNameTxt.Destroy()
                self.lastNameTxt.Destroy()
                self.sexTxt.Destroy()
                self.ageTxt.Destroy()
                self.emailTxt.Destroy()
                self.phoneNumberTxt.Destroy()
                self.backBtn.Destroy()
            except:
                pass
            self.onLogin(None) #we get the user to the login screen
        else:
            self.welcomeUser.SetLabel("Wrong validation code, try again") #fail on inputing validation code

    def onScanQR(self, event):
        try:
            #We try to open the webcam and wait for data
            decodedData = ""
            capture = cv2.VideoCapture(0)
            detectQR = cv2.QRCodeDetector()
            cam = True
            while cam: #while the webcam is on
              cam, shownImg = capture.read()
              data, _, _ = detectQR.detectAndDecode(shownImg)
              if data: #if there is any data we get it
                  decodedData=data 
                  break #break after data is granted
              cv2.imshow("Scan your QR", shownImg)
              if cv2.waitKey(1) == ord('x'):
                  break
            if decodedData: #since the decoded data is username and hashed password we get them
              decodedData = decodedData.split('\n')
              username = decodedData[0]
              password = decodedData[1]
              #
              QUERY = "SELECT * FROM USERS WHERE username = " + "'" + username + \
              "'" + " AND password = " + "'" + password + "'"
              c.execute(QUERY)
              resultUser = c.fetchall()
              if len(resultUser) == 1: #if we have such data in the database, we continue to welcome page
                  global currentUser
                  currentUser = resultUser #we set the currentuser
                  try:
                      self.loginBtn.Destroy()
                      self.registerBtn.Destroy()
                      self.not_regi_text.Destroy()
                      self.fail_login.Destroy()
                  except:
                      pass
                  self.usernameCtrl.Destroy()
                  self.usernameTxt.Destroy()
                  self.passwordCtrl.Destroy()
                  self.passwordTxt.Destroy()
                  # Setting labels or creating new static texts for the updated view
                  self.welcomeUser.SetLabel(
                      "Welcome")
                  self.userDetailsTxt = wx.StaticText(
                      self, label='', pos=(520, 80), size=(300, 26))
                  self.userDetailsTxt.SetLabel(
                      "" + currentUser[0][3] + " " + currentUser[0][4] + "!")
                  welcomeUserPosition = wx.Point(560, 50)
                  self.welcomeUser.SetPosition(welcomeUserPosition)
                  self.logoutBtn = wx.Button(
                      self, label='Logout', pos=(500, 130), size=(200, 26))
                  # Binding the logoutBtn to the onLogout function
                  self.logoutBtn.Bind(wx.EVT_BUTTON, self.onLogout)
                  # Setting fonts
                  self.logoutBtn.SetFont(self.font)
                  self.userDetailsTxt.SetFont(self.font)
                  # Enabling tabs and setting the Login tab to be Logout along with image change
                  notebook.EnableTab(1, True)
                  notebook.EnableTab(2, True)
                  notebook.SetPageText(0, 'Logout')
                  notebook.SetPageImage(0, 4)

                  if currentUser[0][9]==1: #if the user has admin rights, we enable admin panel to the user
                      Sport_club.adminTab = AdminPanel(notebook)
                      notebook.AddPage(Sport_club.adminTab, "AdminPanel")
                      notebook.EnableTab(4, True)
                  # QR Code is generated
                  self.qrUser(event) #we show the user the qr code

                  # We refresh the list of visits in the visits tab by simulating an event
                  evt = wx.FocusEvent(
                      wx.EVT_LIST_ITEM_MIDDLE_CLICK.evtType[0], dateList.GetId())
                  wx.PostEvent(dateList.GetEventHandler(), evt)
                  cv2.destroyAllWindows() #close all cv widnows

              else:
                   self.fail_login.SetLabel("Failed to scan QR Code, Try again")

                   cv2.destroyAllWindows() #close all cv widnows
        except:
            self.fail_login.SetLabel("Failed to scan QR Code, Try again")

    def qrUser(self, event):
        try:
            try:
                    self.scanQrBtn.Destroy()
            except:
                pass
            qrcodeStr = ""
            #get the data of the current user
            QUERY = "SELECT username, password From users Where id = " + str(currentUser[0][0])
            c.execute(QUERY)
            resultInfo = c.fetchall()
            for x in resultInfo:
                qrcodeStr = x[0] +"\n"+ x[1]
            qr = qrcode.QRCode(version=1, box_size=5, border=5)
            qr.add_data(qrcodeStr) #add the data to the qr
            qr.make(fit=True)
            Qrimg = qr.make_image(fill='black', back_color='white')
            Qrimg.save('qrcodeCurrentUser.png') #save it as a image
            self.png = wx.StaticBitmap(
                self, -1, wx.Bitmap("qrcodeCurrentUser.png", wx.BITMAP_TYPE_ANY), pos=(470, 200)) # show it using stataticBitmap
        except:
            pass

    def onLogin(self, event):
            # Getting the values from the username and password fields
            self.username_inp = self.usernameCtrl.GetValue()
            self.password_inp = self.passwordCtrl.GetValue()

            global currentUser
            strPassowrd = str(self.passwordCtrl.GetValue()).encode() #we get the inputed password and we encode it
            QUERY = "SELECT password FROM USERS WHERE username = " + "'" + self.username_inp + "'" #we get the hashed password by the inputed username
            c.execute(QUERY)
            getHashedPass = c.fetchall()

            if(len(getHashedPass) == 1): # we check if there is any users with this username
                for x in getHashedPass:
                    passW = x[0].encode('utf8') #we get and encode the hashed password to utf8
                    if bcrypt.checkpw(strPassowrd, passW):# if the inputed password matchs the hashed password
                        print("Match")
                        # Querying the database for the current user 
                        QUERY = "SELECT * FROM USERS WHERE username = " + "'" + self.username_inp + \
                            "'" + " AND password = " + "'" + str(x[0]) + "'"
                        c.execute(QUERY)
                        queryResult = c.fetchall()
                        # If there is a match then we will continue with the login
                        # Setting the global of the current user to be equal to the result of the query
                        currentUser = queryResult 
                        # Destroy the login texts/buttons

                        # If currentUser is admin, create AdminPanel
                        if currentUser[0][9]==1:
                            Sport_club.adminTab = AdminPanel(notebook)
                            notebook.AddPage(Sport_club.adminTab, "AdminPanel")
                            notebook.EnableTab(4, True)
                        # we get the user to the welcome page
                        try:
                            self.loginBtn.Destroy()
                            self.registerBtn.Destroy()
                            self.not_regi_text.Destroy()
                            self.fail_login.Destroy()
                            self.scanQrBtn.Destroy()
                        except:
                            pass

                        self.usernameCtrl.Destroy()
                        self.usernameTxt.Destroy()
                        self.passwordCtrl.Destroy()
                        self.passwordTxt.Destroy()
                        # Setting labels or creating new static texts for the updated view
                        self.welcomeUser.SetLabel(
                            "Welcome")
                        self.userDetailsTxt = wx.StaticText(
                            self, label='', pos=(520, 80), size=(300, 26))
                        self.userDetailsTxt.SetLabel(
                            "" + currentUser[0][3] + " " + currentUser[0][4] + "!")
                        welcomeUserPosition = wx.Point(560, 50)
                        self.welcomeUser.SetPosition(welcomeUserPosition)
                        self.logoutBtn = wx.Button(
                            self, label='Logout', pos=(500, 130), size=(200, 26))
                        # Binding the logoutBtn to the onLogout function
                        self.logoutBtn.Bind(wx.EVT_BUTTON, self.onLogout)
                        # Setting fonts
                        self.logoutBtn.SetFont(self.font)
                        self.userDetailsTxt.SetFont(self.font)
                        # Enabling tabs and setting the Login tab to be Logout along with image change
                        notebook.EnableTab(1, True)
                        notebook.EnableTab(2, True)
                        notebook.SetPageText(0, 'Logout')
                        notebook.SetPageImage(0, 4)
                        # QR Code is generated
                        self.qrUser(event)
                        # We refresh the list of visits in the visits tab by simulating an event
                        evt = wx.FocusEvent(
                            wx.EVT_LIST_ITEM_MIDDLE_CLICK.evtType[0], dateList.GetId())
                        wx.PostEvent(dateList.GetEventHandler(), evt)
                    else:
                        self.fail_login.SetLabel("Failed Login")
            else:
                self.fail_login.SetLabel("Failed Login")


    def onRegister(self, event):
        # We destroy the objects that are not needed for the register display
        self.loginBtn.Destroy()
        self.registerBtn.Destroy()
        self.not_regi_text.Destroy()
        self.fail_login.Destroy()
        self.scanQrBtn.Destroy()

        # We set labels or create if necessary the required objects
        try:
            self.welcomeUser.SetLabel(
                "Please fill in your registration details.")
            self.welcomeUser.SetPosition(wx.Point(370, 100))
            self.firstNameTxt.SetLabel("First name:")
            self.lastNameTxt.SetLabel("Last name:")
            self.sexTxt.SetLabel("Sex:")
            self.ageTxt.SetLabel("Age:")
            self.emailTxt.SetLabel("Email:")
            self.phoneNumberTxt.SetLabel("Phone Number:")
        except:
            self.firstNameTxt = wx.StaticText(
                self, label="First name:", pos=(370, 241), size=(100, 26))
            self.lastNameTxt = wx.StaticText(
                self, label="Last name:", pos=(370, 281), size=(100, 26))
            self.sexTxt = wx.StaticText(
                self, label="Sex:", pos=(370, 321), size=(100, 26))
            self.ageTxt = wx.StaticText(
                self, label="Age:", pos=(370, 361), size=(100, 26))
            self.emailTxt = wx.StaticText(
                self, label="Email:", pos=(370, 401), size=(100, 26))
            self.phoneNumberTxt = wx.StaticText(
                self, label="Phone number:", pos=(370, 441), size=(100, 26))
            self.welcomeUser.SetFont(self.font)
            self.firstNameTxt.SetFont(self.font)
            self.lastNameTxt.SetFont(self.font)
            self.sexTxt.SetFont(self.font)
            self.ageTxt.SetFont(self.font)
            self.emailTxt.SetFont(self.font)
            self.phoneNumberTxt.SetFont(self.font)

        # Setting the position of the controls
        self.usernameCtrl.SetPosition(wx.Point(550, 160))
        self.passwordCtrl.SetPosition(wx.Point(550, 201))

        # Making new TextCtrls for the view
        self.firstNameCtrl = wx.TextCtrl(self, pos=(550, 241), size=(200, 26))
        self.lastNameCtrl = wx.TextCtrl(self, pos=(550, 281), size=(200, 26))
        self.sexCombo = wx.ComboBox(self, pos=(550, 321), size=(
            200, 26), style=(wx.CB_READONLY), choices=['Male', 'Female'])
        self.ageCtrl = wx.SpinCtrl(self, pos=(550, 355), size=(200, 35), style=(wx.CB_READONLY))
        self.emailCtrl = wx.TextCtrl(self, pos=(550, 401), size=(200, 26))
        self.phoneNumberCtrl = wx.TextCtrl(
            self, pos=(550, 441), size=(200, 26))
        self.phoneNumberCtrl.Bind(wx.EVT_CHAR, self.onAllowPhone)

        # Making new Buttons for the view
        self.acceptRegisterBtn = wx.Button(
            self, label='Register', pos=(550, 481), size=(200, 26))
        self.acceptRegisterBtn.Bind(wx.EVT_BUTTON, self.acceptRegister)
        self.backBtn = wx.Button(
            self, label='Back', pos=(550, 521), size=(200, 26))

        # Setting fonts
        self.backBtn.SetFont(self.font)
        self.acceptRegisterBtn.SetFont(self.font)

        # Binding the backBtn button
        self.backBtn.Bind(wx.EVT_BUTTON, self.onBackBtn)

    def onEmailcheck(self, input): #return True if the email passes the regex check otherwise False

        if(re.fullmatch(regex, input)):
            return True
        else:
            return False

    def acceptRegister(self, event):
        # Checking if the inputs are empty
        inputValues = [self.usernameCtrl.GetValue(), self.passwordCtrl.GetValue(), self.firstNameCtrl.GetValue(
        ), self.lastNameCtrl.GetValue(), self.sexCombo.GetValue(), self.ageCtrl.GetValue(), self.emailCtrl.GetValue(), self.phoneNumberCtrl.GetValue()]

        isEmpty = False
        for x in inputValues:
            if len(str(x)) < 1:
                isEmpty = True
        if not isEmpty: #if all the fields are written
            try: #check if the phone number is a valid
                carrier._is_mobile(number_type(phonenumbers.parse(self.phoneNumberCtrl.GetValue())))
                #check if the email is valid
                if self.onEmailcheck(self.emailCtrl.GetValue()):
                    #check if the username already exsist
                    QUERY = "SELECT username FROM users WHERE username = '" + \
                        self.usernameCtrl.GetValue() + "'"
                    c.execute(QUERY)
                    isRegistered = c.fetchall()
                    if not isRegistered:
                        smtp_server = "smtp.gmail.com" #server domain
                        senderEmail = "YourEmail@gmail.com" #the email of the club
                        receiverEmail = self.emailCtrl.GetValue() #we get the users email
                        password = "Your password" #hardcoded password of the email of the club
                        randomActivCode = self.randomCode(4) #generate a code for the receiver
                        self.code = randomActivCode
                        #The message for the reciver
                        message = MIMEText("Hello, " + self.firstNameCtrl.GetValue()+ " " + self.lastNameCtrl.GetValue() + '\n\n'+ "Welcome to Sport Mania Club" + "\n" + "Your code is " + "[" + str(randomActivCode) + "]"
                            + "\n" + "Please insert your code in the newly appeared text box and press on Check!" + "\n\n" + "We wish you a good day." +"\n" + "NOTE: (If you didn't register, please disregard this message)" + "\n\n" + "Kind regards,"
                            + "\n" + "Sport Mania Club.")
                        message['Subject'] = "Validation Code from Sport Mania"
                        message['From'] = "sportmclub@gmail.com"
                        message['To'] = receiverEmail

                        serverContext = ssl.create_default_context() #Create a new context with secure default settings

                        with smtplib.SMTP_SSL(smtp_server, server_port, context=serverContext) as access :
                            access.login(senderEmail, password) #login using the club email
                            access.sendmail(senderEmail, receiverEmail, message.as_string()) # send the msg to the user on the email

                        self.welcomeUser.SetLabel("Please insert the code from your email inbox")
                        self.onValidation(None) #we call the validation function
                    else:
                        self.welcomeUser.SetLabel(
                        "User is already registered.")
                else:
                    self.welcomeUser.SetLabel(
                        "Email is not valid.")
            except:
                self.welcomeUser.SetLabel(
                "Phone number is not valid.")
        else:
            self.welcomeUser.SetLabel(
                "Please fill in all fields.")

    def onBackBtn(self, event):
        # Destroys the objects not needed for the view
        self.firstNameCtrl.Destroy()
        self.lastNameCtrl.Destroy()
        self.sexCombo.Destroy()
        self.ageCtrl.Destroy()
        self.emailCtrl.Destroy()
        self.phoneNumberCtrl.Destroy()
        self.acceptRegisterBtn.Destroy()
        self.welcomeUser.Destroy()
        self.firstNameTxt.Destroy()
        self.lastNameTxt.Destroy()
        self.sexTxt.Destroy()
        self.ageTxt.Destroy()
        self.emailTxt.Destroy()
        self.phoneNumberTxt.Destroy()
        self.backBtn.Destroy()
        try:
            self.checkBtn.Destroy()
            self.checkCtrl.Destroy()
        except:
            pass

        # Sets position of controls
        self.usernameCtrl.SetPosition(wx.Point(500, 160))
        self.passwordCtrl.SetPosition(wx.Point(500, 200))

        # Recreates the login and register buttons
        self.loginBtn = wx.Button(
            self, label='Login', pos=(500, 240), size=(200, 26))
        self.registerBtn = wx.Button(
            self, label='Register', pos=(500, 350), size=(200, 26))
        self.scanQrBtn = wx.Button(
            self, label='Scan QR', pos=(500, 400), size=(200, 26))


        # Recreates the static texts for the current view
        self.not_regi_text = wx.StaticText(
            self, label="Not registered?", pos=(513, 310), size=(200, 26))
        self.fail_login = wx.StaticText(
            self, label="", pos=(520, 100), size=(200, 26))
        self.welcomeUser = wx.StaticText(
            self, label="", pos=(440, 50), size=(200, 26))
        self.firstNameTxt = wx.StaticText(
            self, label="", pos=(370, 241), size=(100, 26))
        self.lastNameTxt = wx.StaticText(
            self, label="", pos=(370, 281), size=(100, 26))
        self.sexTxt = wx.StaticText(
            self, label="", pos=(370, 321), size=(100, 26))
        self.ageTxt = wx.StaticText(
            self, label="", pos=(370, 361), size=(100, 26))
        self.emailTxt = wx.StaticText(
            self, label="", pos=(370, 401), size=(100, 26))
        self.phoneNumberTxt = wx.StaticText(
            self, label="", pos=(370, 441), size=(100, 26))

        # Sets fonts
        self.not_regi_text.SetFont(self.font)
        self.fail_login.SetFont(self.font)
        self.welcomeUser.SetFont(self.font)
        self.firstNameTxt.SetFont(self.font)
        self.lastNameTxt.SetFont(self.font)
        self.sexTxt.SetFont(self.font)
        self.ageTxt.SetFont(self.font)
        self.emailTxt.SetFont(self.font)
        self.phoneNumberTxt.SetFont(self.font)
        self.loginBtn.SetFont(self.font)
        self.registerBtn.SetFont(self.font)
        self.scanQrBtn.SetFont(self.font)

        # Binding buttons
        self.registerBtn.Bind(wx.EVT_BUTTON, self.onRegister)
        self.loginBtn.Bind(wx.EVT_BUTTON, self.onLogin)
        self.scanQrBtn.Bind(wx.EVT_BUTTON, self.onScanQR)

    def onLogout(self, event):
        #if the AdminPanel exists, delete it
        if notebook.GetPageText(4)=="AdminPanel":
            notebook.DeletePage(4)

        self.welcomeUser.SetLabel("")
        # Sets Buttons for the current view
        self.loginBtn = wx.Button(
            self, label='Login', pos=(500, 240), size=(200, 26))
        self.registerBtn = wx.Button(
            self, label='Register', pos=(500, 350), size=(200, 26))
        self.scanQrBtn = wx.Button(
            self, label='Scan QR', pos=(500, 400), size=(200, 26))

        # Sets StaticTexts for the current view
        self.not_regi_text = wx.StaticText(
            self, label="Not registered?", pos=(513, 310), size=(200, 26))
        self.fail_login = wx.StaticText(
            self, label="", pos=(520, 100), size=(200, 26))
        self.usernameTxt = wx.StaticText(
            self, label="Username:", pos=(370, 161), size=(100, 26))
        self.passwordTxt = wx.StaticText(
            self, label="Password:", pos=(370, 201), size=(100, 26))

        # Sets TextCtrls for the current view
        self.usernameCtrl = wx.TextCtrl(self, pos=(500, 160), size=(200, 26))
        self.passwordCtrl = wx.TextCtrl(self, pos=(
            500, 200), style=(wx.TE_PASSWORD), size=(200, 26))

        # Sets fonts
        self.usernameTxt.SetFont(self.font)
        self.passwordTxt.SetFont(self.font)
        self.not_regi_text.SetFont(self.font)
        self.fail_login.SetFont(self.font)
        self.welcomeUser.SetFont(self.font)
        self.loginBtn.SetFont(self.font)
        self.registerBtn.SetFont(self.font)
        self.scanQrBtn.SetFont(self.font)
        # Destroys the logoutBtn
        self.logoutBtn.Destroy()


        # Binds the Buttons
        self.registerBtn.Bind(wx.EVT_BUTTON, self.onRegister)
        self.loginBtn.Bind(wx.EVT_BUTTON, self.onLogin)
        self.scanQrBtn.Bind(wx.EVT_BUTTON, self.onScanQR)
        # Sets the currentUser to be empty
        global currentUser
        currentUser = []

        # Disables the other tabs after logging out
        notebook.EnableTab(1, False)
        notebook.EnableTab(2, False)
        notebook.EnableTab(3, False)

        # Destroys the QR Code and StaticText for the first and lastname
        self.png.Destroy()
        self.userDetailsTxt.Destroy()

        # Changes the tab text to Login and returns the login image
        notebook.SetPageText(0, 'Login')
        notebook.SetPageImage(0, 0)

# Class that contains the logic for buying a membership, checkin in and out and displaying the membership history


class Memberships(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # STATICTEXT-START
        self.buyTxt = wx.StaticText(
            self, label="Please choose the type of the Membership:", pos=(10, 10), size=(500, 26))
        self.dateTxt = wx.StaticText(
            self, label="Select start date:", pos=(10, 60), size=(230, 26))
        self.memTypeTxt = wx.StaticText(
            self, label="Select Membership:", pos=(10, 120), size=(230, 26))
        self.monthCountTxt = wx.StaticText(
            self, label="Number of Months:", pos=(10, 180), size=(230, 26))
        self.priceTxt = wx.StaticText(
            self, label="Total Price($): 8", pos=(10, 240), size=(230, 26))
        self.checkInTxt = wx.StaticText(
            self, label="Already a Client? Check IN!", pos=(10, 360), size=(400, 26))
        self.checkOutTxt = wx.StaticText(
            self, label="Check OUT after each visit!", pos=(10, 480), size=(400, 26))
        self.weightStartTxt = wx.StaticText(
            self, label="Weight:", pos=(10, 400), size=(100, 26))
        self.weightEndTxt = wx.StaticText(
            self, label="Weight:", pos=(10, 520), size=(100, 26))
        self.failBuyTxt = wx.StaticText(
            self, label="", pos=(200, 300), size=(100, 26))
        # STATICTEXT-END

        # TEXTCTRL-START
        self.weightStartCtrl = wx.TextCtrl(self, pos=(10, 440), size=(100, 26))
        self.weightEndCtrl = wx.TextCtrl(self, pos=(10, 560), size=(100, 26))
        # TEXTCTRL-END

        # DATEPICKERCTRL-START
        self.datepickerStart = wx.adv.DatePickerCtrl(
            self, pos=(250, 60), size=(200, 26), style=wx.adv.DP_DROPDOWN)

        # Sets the range of the datepicker so the user can't choose a date that is before today
        self.datepickerStart.SetRange(
            datetime.date(datetime.now()), datetime.max)
        # DATEPICKERCTRL-END

        # COMBOBOX-START
        self.MonthsChoice = wx.SpinCtrl(self, pos=(250, 176), size=(200, 35), style=(wx.CB_READONLY))
        self.MonthsChoice.SetRange(1, 11)
        self.MembershipType = wx.ComboBox(self, pos=(250, 120), style=(wx.CB_READONLY), size=(
            200, 26), choices=['One time use', 'Monthly', 'Yearly'])
        # Setting the choices to be the first of every list
        self.MembershipType.SetSelection(0)
        # Disabling MonthsChoice since first selection is One time use
        self.MonthsChoice.Disable()
        # COMBOBOX-START

        # LISTCTRL-START
        self.userHist = wx.ListCtrl(self, pos=(650, 20), size=(
            600, 400), style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        # Inserting the columns for the ListCtrl
        self.userHist.InsertColumn(0, 'Type', width=100)
        self.userHist.InsertColumn(1, 'Activation Date', width=100)
        self.userHist.InsertColumn(2, 'End Date', width=100)
        self.userHist.InsertColumn(3, 'Purchase Date', width=150)
        self.userHist.InsertColumn(4, 'Valid')
        self.userHist.InsertColumn(5, 'Price')
        # LISTCTRL-END

        # BUTTONS-START
        self.buyBtn = wx.Button(
            self, label='Buy', pos=(10, 300), size=(130, 30))
        self.checkInBtn = wx.Button(
            self, label='Check IN', pos=(150, 440), size=(130, 30))
        self.checkOutBtn = wx.Button(
            self, label='Check OUT', pos=(150, 560), size=(130, 30))
        # BUTTONS-END

        # FONTS-START
        self.font = wx.Font(15, family=wx.FONTFAMILY_MODERN, style=0, weight=70,
                            underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        self.font.SetWeight(wx.BOLD)

        self.buyBtn.SetForegroundColour(wx.Colour(204, 127, 50))
        self.checkInBtn.SetForegroundColour(wx.Colour(0, 255, 0))
        self.checkOutBtn.SetForegroundColour(wx.Colour(255, 0, 0))

        self.buyTxt.SetFont(self.font)
        self.priceTxt.SetFont(self.font)
        self.dateTxt.SetFont(self.font)
        self.memTypeTxt.SetFont(self.font)
        self.monthCountTxt.SetFont(self.font)
        self.buyBtn.SetFont(self.font)
        self.checkInTxt.SetFont(self.font)
        self.checkOutTxt.SetFont(self.font)
        self.checkInBtn.SetFont(self.font)
        self.checkOutBtn.SetFont(self.font)
        self.weightStartTxt.SetFont(self.font)
        self.weightEndTxt.SetFont(self.font)
        self.failBuyTxt.SetFont(self.font)
        # FONTS-END

        # BINDING-START
        self.buyBtn.Bind(wx.EVT_BUTTON, self.onBuy)
        self.checkInBtn.Bind(wx.EVT_BUTTON, self.onCheckIn)
        self.checkOutBtn.Bind(wx.EVT_BUTTON, self.onCheckOut)
        self.MembershipType.Bind(wx.EVT_TEXT, self.onMemberType)
        self.MonthsChoice.Bind(wx.EVT_TEXT, self.onPriceChange)

        # Refreshes the membership history list when the tab changes
        notebook.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.onHistory)
        # BINDING-END

        # Sets default, default monthCount and checks if the memberships are valid
        self.price = 8
        self.monthCount = int(self.MonthsChoice.GetValue())
        self.checkValid(self)

        # Disabling objects that are not needed yet
        self.checkOutBtn.Disable()
        self.weightEndCtrl.Disable()
        self.datepickerStart.Disable()

    def checkValid(self, event):
        # Query for getting the id and end dates from the memberships
        QUERY = "SELECT mem_end, mem_id FROM users_memberships"
        c.execute(QUERY)
        resultDatesQuery = c.fetchall()
        # The time the user logged in
        timeLogIn = datetime.now()
        validDates = []
        for x in resultDatesQuery:
            # Checks if the end date in the query list is passed, then appends the ids to a list
            # Since the database returns dates at midnight and datetime.now returns with hours and minutes, we add a day to the end date for correct calculation
            if (datetime.strptime(x[0], "%Y-%m-%d") + relativedelta(days=1)) < timeLogIn:
                validDates.append(x[1])

        validDates = str(validDates)
        validDates = validDates.replace('[', '(')
        validDates = validDates.replace(']', ')')

        # Updates the database so the memberships that have passed end dates are set to not valid
        updateQuery = "Update users_memberships set is_valid = 0 where mem_id IN" + validDates
        c.execute(updateQuery)
        conn.commit()

    def onCheckIn(self, event):
        initialWeight = self.weightStartCtrl.GetValue()

        # Query to check if there is a valid membership for the current user
        QUERY = "SELECT is_valid FROM users_memberships WHERE is_valid = 1 AND users_id = " + \
            str(currentUser[0][0])
        c.execute(QUERY)
        validMem = c.fetchall()
        # If there is a valid membership the check in continues, otherwise we don't do anything
        if validMem:
            timeCheckIn = datetime.now()
            timeCheckIn = str(timeCheckIn).split('.')
            timeCheckIn = timeCheckIn[0]

            # Inserts into the database the details except the visits end and ending weight
            c.execute("INSERT INTO USERS_VISITS VALUES (?, ?, ?, ?, ?, ?)",
                      (None, currentUser[0][0], timeCheckIn, "", str(initialWeight), ""))
            conn.commit()

            # We get the id of the last inserted visit and set it to the global currentVisitId
            QUERY = "SELECT last_insert_rowid()"
            c.execute(QUERY)
            visitIdQuery = c.fetchall()
            global currentVisitId
            currentVisitId = visitIdQuery[0][0]

            # Disabling and enabling the necessary objects
            self.checkInBtn.Disable()
            self.weightStartCtrl.Disable()
            self.checkOutBtn.Enable()
            self.weightEndCtrl.Enable()

            notebook.EnableTab(3, True)
            notebook.EnableTab(0, False)

            self.failBuyTxt.SetLabel("")
        else:
            pass

    def onCheckOut(self, event):

        endingWeight = self.weightEndCtrl.GetValue()
        try:
            # Query that updates the database where the mem_type is One time use to make it not valid
            updateValid = """Update users_memberships set is_valid = ? WHERE mem_type = ? AND users_id = ?"""
            updateValidData = (0, 'One time use', str(currentUser[0][0]))
            c.execute(updateValid, updateValidData)
            conn.commit()

            # Gets the time of the check out
            timeCheckOut = datetime.now()
            timeCheckOut = str(timeCheckOut).split('.')
            timeCheckOut = timeCheckOut[0]

            # Updates the users_visits table to set the end date and end weight
            global currentVisitId
            updateQuery = """Update USERS_VISITS set visits_end = ?, weight_end = ? where visits_id = ?"""
            updateData = (timeCheckOut, endingWeight, currentVisitId)
            c.execute(updateQuery, updateData)
            conn.commit()

            # Empties the currentVisitId
            currentVisitId = None
            # Enabling and disabling the required objects
            self.checkInBtn.Enable()
            self.weightStartCtrl.Enable()
            notebook.EnableTab(3, False)
            self.checkOutBtn.Disable()
            self.weightEndCtrl.Disable()

            # Deleting the exercises that were in the exercise tab
            exerHist.DeleteAllItems()

            # Updating the membership history
            self.onHistory(event)

            # Updating the visit list in the visit tab
            evt = wx.FocusEvent(
                wx.EVT_LIST_ITEM_MIDDLE_CLICK.evtType[0], dateList.GetId())
            wx.PostEvent(dateList.GetEventHandler(), evt)

            # Enabling the logout tab
            notebook.EnableTab(0, True)
            self.failBuyTxt.SetLabel("")

            # If the check out is caused by closing the program we exit
            if event.GetEventType() == wx.EVT_CLOSE.typeId:
                wx.Exit()
        except:
            # If the check out is caused by closing the program we exit
            if event.GetEventType() == wx.EVT_CLOSE.typeId:
                wx.Exit()

    def onBuy(self, event):
        # Checks if there is a valid membership
        QUERY = "SELECT is_valid FROM users_memberships WHERE is_valid = 1 AND users_id = " + \
            str(currentUser[0][0])
        c.execute(QUERY)
        validMem = c.fetchall()
        # If there is no valid one we can proceed with buying
        if not validMem:
            # Since the datepicker returns the months like 2021-1-21 we need to add a 0 to the months for proper formatting
            resultDate = ''
            if (self.datepickerStart.GetValue().GetMonth() + 1) < 10:
                resultDate = '0' + \
                    str(self.datepickerStart.GetValue().GetMonth() + 1)
            else:
                resultDate = str(
                    self.datepickerStart.GetValue().GetMonth() + 1)
            datepickerValue = str(self.datepickerStart.GetValue().GetYear(
            )) + "-" + resultDate + "-" + str(self.datepickerStart.GetValue().GetDay())

            # Turning the resulting string to datetime
            dateStartObj = datetime.strptime(datepickerValue, '%Y-%m-%d')

            # Getting the membership type
            memberType = self.MembershipType.GetSelection()
            self.MembershipType.SetSelection(memberType)

            # Adds to the selected amount of months to calculate end date of monthly type
            dateAfterMonthEnd = (
                dateStartObj + relativedelta(months=self.monthCount))
            dateAfterMonthEnd = str(dateAfterMonthEnd).split(' ')
            dateAfterMonthEnd = dateAfterMonthEnd[0]

            # Adds a year to the end date of yearly type
            dateAfterYear = (dateStartObj + relativedelta(months=12))
            dateAfterYear = str(dateAfterYear).split(' ')
            dateAfterYear = dateAfterYear[0]

            # Converts the start date to string so we can input into database
            dateStartObj = str(dateStartObj).split(' ')
            dateStartObj = dateStartObj[0]

            # Gets the date of purchase along with hours, minutes and seconds
            dateOfPurchase = datetime.now()
            dateAfterDay = (dateOfPurchase + relativedelta(days=1))
            dateOfPurchase = str(dateOfPurchase).split('.')
            dateOfPurchase = dateOfPurchase[0]

            # Sets the one time use start date to be today
            dateOfOneTimeUse = dateOfPurchase.split(' ')
            dateOfOneTimeUse = dateOfOneTimeUse[0]

            # Sets the one time use to be valid for one day only
            dateAfterDay = str(dateAfterDay).split(' ')
            dateAfterDay = dateAfterDay[0]

            try:
                # Inserts into the database the required fields depending on the membership type
                if self.MembershipType.GetSelection() == 1:  # monthly
                    c.execute("INSERT INTO USERS_MEMBERSHIPS VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (None, currentUser[0][0], dateStartObj, dateAfterMonthEnd, dateOfPurchase, 'Monthly', self.price, 1))
                    conn.commit()

                elif self.MembershipType.GetSelection() == 2:  # yearly
                    c.execute("INSERT INTO USERS_MEMBERSHIPS VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (None, currentUser[0][0], dateStartObj, dateAfterYear, dateOfPurchase, 'Yearly', self.price, 1))
                    conn.commit()

                elif self.MembershipType.GetSelection() == 0:  # one time use
                    c.execute("INSERT INTO USERS_MEMBERSHIPS VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (None, currentUser[0][0], dateOfOneTimeUse, dateAfterDay, dateOfPurchase, 'One time use', self.price, 1))
                    conn.commit()
                # Refreshes the membership history list
                self.onHistory(event)
                self.failBuyTxt.SetLabel("")
            except:
                pass
        else:
            self.failBuyTxt.SetLabel("Already with valid Membership!")
            pass

    def onHistory(self, event):
        try:
            # Clears the membership list
            self.userHist.DeleteAllItems()
            # Selects the memberships for the current user
            QUERY = "SELECT mem_type, mem_start, mem_end, purchase_date, is_valid, money_paid FROM users_memberships WHERE users_id = " + \
                str(currentUser[0][0])
            c.execute(QUERY)
            histQuery = c.fetchall()
            index = 0
            for x in histQuery:
                # Inserts into the membership list the results from the query
                self.userHist.InsertItem(index, x[0])
                self.userHist.SetItem(index, 1, x[1])
                self.userHist.SetItem(index, 2, x[2])
                self.userHist.SetItem(index, 3, x[3])
                self.userHist.SetItem(index, 4, str(x[4]))
                self.userHist.SetItem(index, 5, str(x[5]))
                index += 1
        except:
            pass

    def onPriceChange(self, event):
        # Calculates the price depending on the membership type and month count when you change the month count
        self.monthCount = int(self.MonthsChoice.GetValue())
        if self.MembershipType.GetSelection() == 1:  # monthly
            self.price = 34 * self.monthCount
        elif self.MembershipType.GetSelection() == 2:  # yearly
            self.price = 377

        elif self.MembershipType.GetSelection() == 0:  # one time use
            self.price = 8
        self.priceTxt.SetLabel("Total Price($): " + str(self.price))

    def onMemberType(self, event):
        # Calculates the price depending on the membership type and month count when you change the membership type
        if self.MembershipType.GetSelection() == 1:
            self.MonthsChoice.Enable()
            self.monthCount = int(self.MonthsChoice.GetValue())
            self.price = 34 * self.monthCount
            self.priceTxt.SetLabel("Total Price($): " + str(self.price))
            self.datepickerStart.Enable()
        else:
            self.MonthsChoice.Disable()
            if self.MembershipType.GetSelection() == 2:  # yearly
                self.price = 377
                self.datepickerStart.Enable()

            elif self.MembershipType.GetSelection() == 0:  # one time use
                self.price = 8
                self.datepickerStart.Disable()

            self.priceTxt.SetLabel("Total Price($):" + str(self.price))

# Class that contains logic for displaying the visits history along with the exercises of each visit


class Visits(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # LISTCTRL-START
        # List for displaying the visits
        global dateList
        dateList = wx.ListCtrl(self, pos=(60, 26), size=(
            500, 500), style=wx.LC_REPORT | wx.BORDER_SUNKEN)

        dateList.InsertColumn(0, 'Start Date', width=150)
        dateList.InsertColumn(1, 'End Date', width=150)
        dateList.InsertColumn(2, 'Start Weight', width=100)
        dateList.InsertColumn(3, 'End Weight', width=100)

        # List for displaying the exercises on each visit
        self.exercisesList = wx.ListCtrl(self, pos=(700, 26), size=(
            500, 500), style=wx.LC_REPORT | wx.BORDER_SUNKEN)

        self.exercisesList.InsertColumn(0, 'Exercises', width=150)
        self.exercisesList.InsertColumn(1, 'Type', width=150)
        self.exercisesList.InsertColumn(2, 'Sets', width=50)
        self.exercisesList.InsertColumn(3, 'Reps', width=50)
        self.exercisesList.InsertColumn(4, 'Minutes', width=100)
        # LISTCTRL-END

        # BINDING-START
        dateList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onExercisesHist)
        dateList.Bind(wx.EVT_LIST_ITEM_MIDDLE_CLICK, self.onDatesHist)
        # BINDING-END

    def onDatesHist(self, event):
        # Clears the list before adding new items
        dateList.DeleteAllItems()
        # Selects only the visits that have ended(the current one won't be counted until it's checked out)
        QUERY = "Select visits_id, visits_start, visits_end, weight_start, weight_end from USERS_VISITS WHERE visits_end != '' AND users_id = " + \
            str(currentUser[0][0])
        c.execute(QUERY)
        wayInDates = c.fetchall()

        # Insert the results of the query into the visit list
        global visitsIds
        visitsIds = []
        index = 0
        for x in wayInDates:
            dateList.InsertItem(index, x[1])
            dateList.SetItem(index, 1, x[2])
            dateList.SetItem(index, 2, x[3])
            dateList.SetItem(index, 3, x[4])
            index += 1
            # Inserts into global all the visit ids
            visitsIds.append(x[0])

    def onExercisesHist(self, event):
        try:
            # We clear the exercises list
            self.exercisesList.DeleteAllItems()
            # We get the visit that was clicked
            clickedItem = dateList.GetFocusedItem()
            # We select the exercises that are with the visit id of the clicked item
            QUERY = "SELECT category, exercise, sets, reps, mins FROM users_training WHERE visits_id =" + \
                str(visitsIds[clickedItem])
            c.execute(QUERY)

            histQuery = c.fetchall()
            index = 0
            # We insert into the exercises list the results of the query
            for x in histQuery:
                self.exercisesList.InsertItem(index, x[0])
                self.exercisesList.SetItem(index, 1, x[1])
                self.exercisesList.SetItem(index, 2, x[2])
                self.exercisesList.SetItem(index, 3, x[3])
                self.exercisesList.SetItem(index, 4, x[4])
                index += 1
        except:
            pass

# Class that contains logic for saving exercises, along with removing and clearing them


class Exercises(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        #Select exercise names from exercises table, and edit them to put into ComboBox as list of strings
        c.execute('SELECT DISTINCT exercise_name FROM exercises')
        self.exercise_choices = []
        self.exercise_choices.append(str(c.fetchone()))
        i = 0
        while self.exercise_choices[i] != 'None':
            self.exercise_choices.append(str(c.fetchone()))
            size = len(self.exercise_choices[i])
            self.exercise_choices[i] = self.exercise_choices[i][2:size-3]
            i+=1
        self.exercise_choices.pop()

        # COMBOBOX-START
        self.exerciseChoices = wx.ComboBox(self, pos=(250, 60), size=(200, 26), style=(wx.CB_READONLY), choices=self.exercise_choices)
        self.variantChoice = wx.ComboBox(self, pos=(
            250, 130), size=(200, 26), style=(wx.CB_READONLY), choices=[])
        # COMBOBOX-END

        self.alternativeExercise = wx.TextCtrl(self, pos=(250, 60), size=(200, 26))
        self.alternativeType = wx.TextCtrl(self, pos=(250, 130), size=(200, 26))
        self.alternativeExercise.Hide()
        self.alternativeType.Hide()
        self.alternative_exercise_flag = False

        self.ImageToBit = wx.Image('images/default_image.jpeg', wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.MainPicture = wx.StaticBitmap(self, -1, self.ImageToBit, (700, 50), (self.ImageToBit.GetWidth(), self.ImageToBit.GetHeight()))

        self.workoutBox = wx.StaticBox(self, label='Workout Exercises', pos=(5, 420), size=(1272, 200))

        # BUTTONS-START
        self.saveEx = wx.Button(
            self, label='Save', pos=(10, 450), size=(150, 26))
        self.altEx = wx.Button(
            self, label='Alternative Exercise', pos=(5, 385), size=(200, 26))
        self.removeEx = wx.Button(
            self, label='Remove', pos=(10, 516), size=(150, 26))
        self.clearEx = wx.Button(
            self, label='Clear', pos=(10, 582), size=(150, 26))
        # BUTTONS-END

        # LISTCTRL-START
        global exerHist
        exerHist = wx.ListCtrl(self, pos=(170, 450), size=(1070, 160), style=wx.LC_REPORT | wx.BORDER_SUNKEN)

        exerHist.InsertColumn(0, 'Exercises', width=150)
        exerHist.InsertColumn(1, 'Type', width=150)
        exerHist.InsertColumn(2, 'Sets', width=50)
        exerHist.InsertColumn(3, 'Reps', width=50)
        exerHist.InsertColumn(4, 'Minutes', width=100)
        # LISTCTRL-END

        # STATICTEXT-START
        self.subjTxt = wx.StaticText(
            self, label="Please enter you Exercises:", pos=(5, 1), size=(500, 26))
        self.catagoryTxt = wx.StaticText(
            self, label="Choose a Category:", pos=(5, 60), size=(230, 26))
        self.exercisesTxt = wx.StaticText(
            self, label="Choose a Exercises:", pos=(5, 130), size=(230, 26))
        self.setsTxt = wx.StaticText(
            self, label="Number of Sets:", pos=(5, 200), size=(180, 26))
        self.repsTxt = wx.StaticText(
            self, label="Number of Reps:", pos=(5, 270), size=(180, 26))
        self.minsTxt = wx.StaticText(
            self, label="Time (Mins):", pos=(5, 340), size=(150, 26))
        # STATICTEXT-END

        # TEXTCTRL-START
        self.inputSets = wx.SpinCtrl(self, pos=(250, 196), size=(200, 35), style=(wx.CB_READONLY))
        self.inputReps = wx.SpinCtrl(self, pos=(250, 266), size=(200, 35), style=(wx.CB_READONLY))
        self.inputMins = wx.SpinCtrl(self, pos=(250, 337), size=(200, 35), style=(wx.CB_READONLY))
        # TEXTCTRL-END

        # FONTS-START
        self.font = wx.Font(15, family=wx.FONTFAMILY_MODERN, style=0, weight=70,
                            underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        self.font.SetWeight(wx.BOLD)

        self.subjTxt.SetFont(self.font)
        self.catagoryTxt.SetFont(self.font)
        self.exercisesTxt.SetFont(self.font)
        self.setsTxt.SetFont(self.font)
        self.repsTxt.SetFont(self.font)
        self.minsTxt.SetFont(self.font)
        self.saveEx.SetFont(self.font)
        self.removeEx.SetFont(self.font)
        self.clearEx.SetFont(self.font)
        # FONTS-START

        # DISABLE-START
        self.inputReps.Disable()
        self.inputSets.Disable()
        self.inputMins.Disable()
        self.variantChoice.Disable()
        # DISABLE-END

        # COLOUR-START
        self.saveEx.SetForegroundColour(wx.Colour(0, 255, 0))
        self.removeEx.SetForegroundColour(wx.Colour(255, 0, 0))
        self.clearEx.SetForegroundColour(wx.Colour(255, 0, 0))
        # COLOUR-END

        # BINDING-START
        self.exerciseChoices.Bind(wx.EVT_COMBOBOX, self.onExercises)
        self.variantChoice.Bind(wx.EVT_TEXT, self.onVariant)
        self.saveEx.Bind(wx.EVT_BUTTON, self.onSave)
        self.removeEx.Bind(wx.EVT_BUTTON, self.onRemove)
        self.clearEx.Bind(wx.EVT_BUTTON, self.onClearEx)
        self.altEx.Bind(wx.EVT_BUTTON, self.onAlternativeEx)
        # BINDING-END

    def onClearEx(self, event):
        # Deletes from the database the exercises for the current visit id
        QUERY = "DELETE FROM users_training WHERE visits_id = " + \
            str(currentVisitId)
        c.execute(QUERY)
        conn.commit()
        # Clears the exercises list and global currentExercises
        exerHist.DeleteAllItems()
        currentExercises.clear()

    def onRemove(self, event):
        try:
            # Gets the selected item from and deletes it from the list
            selecteditem = exerHist.GetFocusedItem()
            exerHist.DeleteItem(selecteditem)
            # Deletes the exercise with the training id of the selected item
            QUERY = "DELETE FROM users_training WHERE training_id = " + \
                str(currentExercises[selecteditem])
            currentExercises.pop(selecteditem)
            c.execute(QUERY)
        except:
            pass

    def onHistExercises(self, event):
        try:
            # Clears the exercises list
            exerHist.DeleteAllItems()
            # Selects the exercises for the current visit
            QUERY = "SELECT category, exercise, sets, reps, mins FROM users_training WHERE visits_id = " + \
                str(currentVisitId)
            c.execute(QUERY)
            histQuery = c.fetchall()
            index = 0
            # Inserts into the list the result of the query
            for x in histQuery:
                exerHist.InsertItem(index, x[0])
                exerHist.SetItem(index, 1, x[1])
                exerHist.SetItem(index, 2, x[2])
                exerHist.SetItem(index, 3, x[3])
                exerHist.SetItem(index, 4, x[4])
                index += 1
        except:
            pass

    def onSave(self, event):
        self.alternativeExercise.Hide()
        self.alternativeType.Hide()
        self.exerciseChoices.Show()
        self.variantChoice.Show()

        if not self.alternative_exercise_flag:
            if self.exerciseChoices.GetValue() != '':
                try:
                    # Inserts into the database the selected training
                    c.execute("INSERT INTO users_training VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (None, currentVisitId, currentUser[0][0], self.exerciseChoices.GetValue(), self.variantChoice.GetValue(), self.inputSets.GetValue(), self.inputReps.GetValue(), self.inputMins.GetValue()))
                    conn.commit()
                    # Refreshes the exercises list
                    self.onHistExercises(event)
                    # Appends into the global currentExercises the id of the last inserted row
                    QUERY = "SELECT last_insert_rowid()"
                    c.execute(QUERY)
                    exercisesQuery = c.fetchall()
                    global currentExercises
                    currentExercises.append(exercisesQuery[0][0])
                except:
                    pass
            else:
                pass
        else:
            alternative_exercise = str(self.alternativeExercise.GetValue())
            alternative_type = str(self.alternativeType.GetValue())
            if alternative_exercise and alternative_type:
                try:
                    # Inserts into the database the selected training
                    c.execute("INSERT INTO users_training VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (None, currentVisitId, currentUser[0][0], alternative_exercise, alternative_type, self.inputSets.GetValue(), self.inputReps.GetValue(), self.inputMins.GetValue()))
                    conn.commit()
                    # Refreshes the exercises list
                    self.onHistExercises(event)
                    # Appends into the global currentExercises the id of the last inserted row
                    QUERY = "SELECT last_insert_rowid()"
                    c.execute(QUERY)
                    exercisesQuery = c.fetchall()
                    #global currentExercises
                    currentExercises.append(exercisesQuery[0][0])
                except:
                    pass
            else:
                pass
        self.alternative_exercise_flag = False

    def onExercises(self, event):
        exerciseChoice = self.exerciseChoices.GetSelection()

        try:
            self.variantChoice.Destroy()
        except:
            pass
        # Creates new variantChoice depending on the selected category
        #Select exercise types from exercises table based on exercise name, and edit them to put into ComboBox as list of strings
        QUERY = "SELECT DISTINCT exercise_type FROM exercises WHERE exercise_name='"+self.exercise_choices[exerciseChoice]+"'"
        c.execute(QUERY)
        exercise_types = []
        exercise_types.append(str(c.fetchone()))
        i = 0
        while exercise_types[i] != 'None':
            exercise_types.append(str(c.fetchone()))
            size = len(exercise_types[i])
            exercise_types[i] = exercise_types[i][2:size-3]
            i+=1
        exercise_types.pop()

        self.variantChoice = wx.ComboBox(self, pos=(250, 130), size=(200, 26), style=(wx.CB_READONLY), choices=exercise_types)
        self.variantChoice.SetSelection(0)
        self.variantChoice.Bind(wx.EVT_TEXT, self.onVariant)

        exerciseType = self.variantChoice.GetSelection()
        QUERY = "SELECT sets_reps FROM exercises WHERE exercise_name='"+self.exercise_choices[exerciseChoice]+"' AND exercise_type='"+exercise_types[exerciseType]+"'"
        c.execute(QUERY)
        sr_flag = str(c.fetchone())
        sr_flag = sr_flag[1]
        self.onVariant(event)

        # Disables certain inputs for the cardio machines
        if sr_flag == '0':
            try:
                self.inputMins.Enable()
                self.inputSets.SetValue(0)
                self.inputReps.SetValue(0)
                self.inputReps.Disable()
                self.inputSets.Disable()
            except:
                pass

        # Enables inputs
        else:
            self.inputReps.Enable()
            self.inputSets.Enable()
            self.inputMins.Enable()
        

    def onAlternativeEx(self, event):
        self.alternative_exercise_flag = True
        self.exerciseChoices.Hide()
        self.variantChoice.Hide()
        self.alternativeExercise.Show()
        self.alternativeType.Show()
        self.inputReps.Enable()
        self.inputSets.Enable()
        self.inputMins.Enable()

    def onVariant(self, event):
        exercise_name = self.variantChoice.GetStringSelection()
        QUERY = "SELECT exercise_img FROM exercises WHERE exercise_type='"+exercise_name+"'"
        c.execute(QUERY)
        exercise_img_file = str(c.fetchone())
        size = len(exercise_img_file)
        exercise_img_file = exercise_img_file[2:size-3]

        if exercise_img_file == "None":
            try:
                self.MainPicture.Destroy()
                self.ImageToBit = wx.Image('images/default_image.jpeg', wx.BITMAP_TYPE_ANY).ConvertToBitmap()
                self.MainPicture = wx.StaticBitmap(self, -1, self.ImageToBit, (700, 50), (self.ImageToBit.GetWidth(), self.ImageToBit.GetHeight()))
            except:
                pass
        else:
            try:
                self.MainPicture.Destroy()
                self.ImageToBit = wx.Image(exercise_img_file, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
                self.MainPicture = wx.StaticBitmap(self, -1, self.ImageToBit, (700, 20), (self.ImageToBit.GetWidth(), self.ImageToBit.GetHeight()))
            except:
                pass

class AdminPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        #Create ListCtrl for exercise database
        self.exerciseList = wx.ListCtrl(self, pos=(10,10), size=(1260, 500), style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.exerciseList.InsertColumn(0, 'Exercise ID', width=100)
        self.exerciseList.InsertColumn(1, 'Exercise Name', width=345)
        self.exerciseList.InsertColumn(2, 'Exercise Type', width=345)
        self.exerciseList.InsertColumn(3, 'Sets&Reps Applicable?', width=170)
        self.exerciseList.InsertColumn(4, 'Exercise Image File', width=300)
        #Create buttons
        self.addexBtn = wx.Button(self, label="Add", pos=(10, 525), size=(100,26))
        self.editexBtn = wx.Button(self, label="Edit", pos=(120, 525), size=(100,26))
        self.delexBtn = wx.Button(self, label="Delete", pos=(230, 525), size=(100,26))
        self.refreshBtn = wx.Button(self, label="Refresh Exercises", pos=(340, 525), size=(150,26))
        self.grantBtn = wx.Button(self, label="Grant admin Rights", pos=(810, 525), size=(150,26))
        self.msgtxtTxt = wx.StaticText(self, label="", pos=(500,530), size=(300,26))
        #Create TextCtrls for input data
        self.additionGroup = wx.StaticBox(self, label="Add/Edit/Delete Exercise Parameters", pos=(10, 560), size=(1260, 60))
        self.exidCtrl = wx.TextCtrl(self, pos=(20, 585), size=(90,26))
        self.exnameCtrl = wx.TextCtrl(self, pos=(115, 585), size=(330,26))
        self.extypeCtrl = wx.TextCtrl(self, pos=(450, 585), size=(330,26))
        self.setsrepsCtrl = wx.TextCtrl(self, pos=(785, 585), size=(175,26))
        self.imageCtrl = wx.TextCtrl(self, pos=(965, 585), size=(295,26))
        self.grantCtrl = wx.TextCtrl(self, pos=(970, 525), size=(290,26))
        #Fill in the ListCtrl with existing exercises from exercise database
        c.execute("SELECT * FROM exercises ORDER BY exercise_name")
        exercise_ad = c.fetchall()
        index = 0
        for x in exercise_ad:
            self.exerciseList.InsertItem(index, str(x[0]))
            self.exerciseList.SetItem(index, 1, x[1])
            self.exerciseList.SetItem(index, 2, x[2])
            self.exerciseList.SetItem(index, 3, str(x[3]))
            self.exerciseList.SetItem(index, 4, x[4])
            index += 1
        #BINDING START
        self.exerciseList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.adminSelect)
        self.addexBtn.Bind(wx.EVT_BUTTON, self.adminAdd)
        self.editexBtn.Bind(wx.EVT_BUTTON, self.adminEdit)
        self.delexBtn.Bind(wx.EVT_BUTTON, self.adminDelete)
        self.refreshBtn.Bind(wx.EVT_BUTTON, self.adminRefresh)
        self.grantBtn.Bind(wx.EVT_BUTTON, self.adminGrant)
        #BINDING END

    def adminSelect(self, event):
        #Clear input fields
        self.exidCtrl.Clear()
        self.exnameCtrl.Clear()
        self.extypeCtrl.Clear()
        self.setsrepsCtrl.Clear()
        self.imageCtrl.Clear()
        #Get data from list item
        clickedItem = self.exerciseList.GetFocusedItem()
        id = self.exerciseList.GetItem(clickedItem, 0)
        name = self.exerciseList.GetItem(clickedItem, 1)
        type = self.exerciseList.GetItem(clickedItem, 2)
        flag = self.exerciseList.GetItem(clickedItem, 3)
        imgaddr = self.exerciseList.GetItem(clickedItem, 4)
        #Fill in the gotten data into corresponding input fields
        self.exidCtrl.write(id.GetText())
        self.exnameCtrl.write(name.GetText())
        self.extypeCtrl.write(type.GetText())
        self.setsrepsCtrl.write(flag.GetText())
        self.imageCtrl.write(imgaddr.GetText())

    def adminAdd(self, event):
        #Clear the message
        self.msgtxtTxt.SetLabel("")
        try:
        #Get values from input fields
            id = int(self.exidCtrl.GetValue())
            name = str(self.exnameCtrl.GetValue())
            type = str(self.extypeCtrl.GetValue())
            flag = str(self.setsrepsCtrl.GetValue())
            try:
                imgaddr = str(self.imageCtrl.GetValue())
            except:
                imgaddr = 'None'
        except:
            self.msgtxtTxt.SetLabel("Fields must be filled")
        else:
            #Check if all the fields are filled
            if name and type and flag and imgaddr:
                #Try to insert the given data into the exercises table
                try:
                    c.execute("INSERT INTO exercises VALUES (?, ?, ?, ?, ?)", (id, name, type, flag, imgaddr))
                    conn.commit()
                except:
                    #if there is an error with insertion(most likely ID is not unique), get the max ID value from the table, add 1 to it
                    #and suggest it as new id by filling it into id input field
                    c.execute("SELECT MAX(exercise_id) FROM exercises")
                    exercise_id = c.fetchone()
                    index = len(exercise_id) - 1
                    str_id = str(exercise_id)
                    size = len(str_id)
                    str_id = str_id[1:size-2]
                    id = int(str_id) + 1
                    self.exidCtrl.Clear()
                    self.exidCtrl.write(str(id))
                    self.msgtxtTxt.SetLabel("ID must be unique, here's a suggestion")
                else:
                    #if insertion was successful, update exercise list and show message of success
                    self.exerciseList.DeleteAllItems()
                    c.execute("SELECT * FROM exercises ORDER BY exercise_name")
                    exercise_ad = c.fetchall()

                    index = 0
                    for x in exercise_ad:
                        self.exerciseList.InsertItem(index, str(x[0]))
                        self.exerciseList.SetItem(index, 1, x[1])
                        self.exerciseList.SetItem(index, 2, x[2])
                        self.exerciseList.SetItem(index, 3, str(x[3]))
                        self.exerciseList.SetItem(index, 4, x[4])
                        index += 1

                    self.msgtxtTxt.SetLabel("New exercise added!")

            else:
                self.msgtxtTxt.SetLabel("All fields must be filled")

    def adminEdit(self, event):
        #Clear the message
        self.msgtxtTxt.SetLabel("")
        try:
            #Get values from input fields
            id = int(self.exidCtrl.GetValue())
            name = str(self.exnameCtrl.GetValue())
            type = str(self.extypeCtrl.GetValue())
            flag = self.setsrepsCtrl.GetValue()
            try:
                imgaddr = str(self.imageCtrl.GetValue())
            except:
                imgaddr = 'None'
        except:
            self.msgtxtTxt.SetLabel("Fields must be filled")
        else:
            #Check if all the fields are filled
            if name and type and flag and imgaddr:
                #Select row from exercises with input id
                QUERY = "SELECT exercise_id FROM exercises WHERE exercise_id='"+str(id)+"'"
                c.execute(QUERY)
                #If it exists, update it, and show success message
                if c.fetchall():
                    QUERY = "UPDATE exercises SET exercise_name='"+name+"', exercise_type='"+type+"', sets_reps='"+flag+"', exercise_img='"+imgaddr+"' WHERE exercise_id='"+str(id)+"'"
                    c.execute(QUERY)
                    conn.commit()
                    self.exerciseList.DeleteAllItems()
                    c.execute("SELECT * FROM exercises ORDER BY exercise_name")
                    exercise_ad = c.fetchall()
                    index = 0
                    for x in exercise_ad:
                        self.exerciseList.InsertItem(index, str(x[0]))
                        self.exerciseList.SetItem(index, 1, x[1])
                        self.exerciseList.SetItem(index, 2, x[2])
                        self.exerciseList.SetItem(index, 3, str(x[3]))
                        self.exerciseList.SetItem(index, 4, x[4])
                        index += 1
                    self.msgtxtTxt.SetLabel("Edit successful!")
                else:
                    #if row with input ID not found, show unsuccess message
                    self.msgtxtTxt.SetLabel("Exercise not found. Check ID!")

    def adminDelete(self, event):
        #Clear message
        self.msgtxtTxt.SetLabel("")
        try:
            #Get input id
            id = int(self.exidCtrl.GetValue())
        except:
            self.msgtxtTxt.SetLabel("Enter ID")
        else:
            #Select from exercises row with input id
            QUERY = "SELECT exercise_id FROM exercises WHERE exercise_id='"+str(id)+"'"
            c.execute(QUERY)
            #If it exists, delete the row, show success message, and clear input fields
            if c.fetchall():
                QUERY = "DELETE FROM exercises WHERE exercise_id='"+str(id)+"'"
                c.execute(QUERY)
                conn.commit()
                self.exerciseList.DeleteAllItems()
                c.execute("SELECT * FROM exercises ORDER BY exercise_name")
                exercise_ad = c.fetchall()

                index = 0
                for x in exercise_ad:
                    self.exerciseList.InsertItem(index, str(x[0]))
                    self.exerciseList.SetItem(index, 1, x[1])
                    self.exerciseList.SetItem(index, 2, x[2])
                    self.exerciseList.SetItem(index, 3, str(x[3]))
                    self.exerciseList.SetItem(index, 4, x[4])
                    index += 1

                self.exidCtrl.Clear()
                self.exnameCtrl.Clear()
                self.extypeCtrl.Clear()
                self.setsrepsCtrl.Clear()
                self.imageCtrl.Clear()
                self.msgtxtTxt.SetLabel("Exercise deleted successfully!")
            else:
                #if row with input ID not found, show unsuccess message
                self.msgtxtTxt.SetLabel("Exercise not found. Check ID!")

    def adminRefresh(self, event):
        notebook.DeletePage(3)
        Sport_club.exercisesTab = Exercises(notebook)
        notebook.InsertPage(3, Sport_club.exercisesTab, "Exercises")
        notebook.SetPageImage(3, 3)
        global currentVisitId
        if currentVisitId:
            notebook.EnableTab(3, True)
        else:
            notebook.EnableTab(3, False)

    def adminGrant(self, event):
        username = self.grantCtrl.GetValue()
        try:
            QUERY = "SELECT admin_flag FROM users WHERE username='"+username+"'"
            c.execute(QUERY)
            flag = c.fetchone()
            if flag[0]==0:
                QUERY = "UPDATE users SET admin_flag=1 WHERE username='"+username+"'"
                c.execute(QUERY)
            elif flag[0]==1:
                QUERY = "UPDATE users SET admin_flag=0 WHERE username='"+username+"'"
                c.execute(QUERY)
        except:
            self.msgtxtTxt.SetLabel("Something's wrong, didn't grant")

    #def inputCheck

# Main parent class that makes the notebook required for different pages and initializes every class other than it to be a page


class Sport_club(wx.Frame):
    def __init__(self, parent, title):
        super(Sport_club, self).__init__(parent, title=title, size=(1280, 720))

        # The notebook allows having pages that are changed when clicking on different tabs
        style = aui.AUI_NB_TAB_SPLIT
        global notebook
        notebook = aui.AuiNotebook(self, agwStyle=style)

        # The pages are instances of the Login, Memberships, Visits and Exercises classes
        self.loginTab = Login(notebook)
        self.membershipsTab = Memberships(notebook)
        self.visitsTab = Visits(notebook)
        self.exercisesTab = Exercises(notebook)


        # We add the pages to the notebook
        notebook.AddPage(self.loginTab, "Login")
        notebook.AddPage(self.membershipsTab, "Memberships")
        notebook.AddPage(self.visitsTab, "Visits")
        notebook.AddPage(self.exercisesTab, "Exercises")

        # Initially only the login tab is enabled
        notebook.EnableTab(1, False)
        notebook.EnableTab(2, False)
        notebook.EnableTab(3, False)

        # If the user exits the program before checking out, this calls the checkout function automatically before exiting
        self.Bind(wx.EVT_CLOSE, self.membershipsTab.onCheckOut)

        # Sets the icon of the program
        windowIcon = wx.Icon('icons/sportClubIcon.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(windowIcon)

        # Creates bitmaps of icons
        loginIcon = wx.Icon(
            'icons/loginIcon.ico', wx.BITMAP_TYPE_ICO)
        loginBitmap = wx.Bitmap(32, 32)
        loginBitmap.CopyFromIcon(loginIcon)

        membershipsIcon = wx.Icon(
            'icons/membershipsIcon.ico', wx.BITMAP_TYPE_ICO)
        membershipsBitmap = wx.Bitmap(32, 32)
        membershipsBitmap.CopyFromIcon(membershipsIcon)

        visitsIcon = wx.Icon(
            'icons/visitsIcon.ico', wx.BITMAP_TYPE_ICO)
        visitsBitmap = wx.Bitmap(32, 32)
        visitsBitmap.CopyFromIcon(visitsIcon)

        exercisesIcon = wx.Icon(
            'icons/exerciseIcon.ico', wx.BITMAP_TYPE_ICO)
        exercisesBitmap = wx.Bitmap(32, 32)
        exercisesBitmap.CopyFromIcon(exercisesIcon)

        logoutIcon = wx.Icon(
            'icons/logoutIcon.ico', wx.BITMAP_TYPE_ICO)
        logoutBitmap = wx.Bitmap(32, 32)
        logoutBitmap.CopyFromIcon(logoutIcon)

        # We add the bitmaps to an ImageList
        imageList = wx.ImageList(
            width=32, height=32, mask=False, initialCount=1)
        imageList.Add(loginBitmap)
        imageList.Add(membershipsBitmap)
        imageList.Add(visitsBitmap)
        imageList.Add(exercisesBitmap)
        imageList.Add(logoutBitmap)

        # We add the image list to the notebook
        notebook.SetImageList(imageList)

        # We set the icons in the corresponding tabs
        notebook.SetPageImage(0, 0)
        notebook.SetPageImage(1, 1)
        notebook.SetPageImage(2, 2)
        notebook.SetPageImage(3, 3)

        self.Show()

# Main loop of the program
app = wx.App()
sportClubWindow = Sport_club(None, 'Fitness Mania')
app.MainLoop()

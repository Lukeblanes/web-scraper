import scrapy
import bs4 as bs
import urllib.request
import os, errno
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
from glob import glob

# Change between Principiante, Intermedio, Avanzado as they're completed
downloadLevel = "Avanzado"

def createDir(dirName):
    try:
        os.makedirs(dirName)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

# Load File with login info and website. Format:
''' 
email=example@example.com
password=examplePass
website=https://www.examplewebsite.com
'''
def loadConfig(name):
    email, password, website = '', '', ''
    file = open(name, 'r')
    elems = file.read().split("\n")

    email = elems[0].split("=")[1]
    password = elems[1].split("=")[1]
    website = elems[2].split("=")[1]

    file.close()
    return email, password, website

# Loading file to variables
email, password, website = loadConfig("dataLoadExample.txt")

class LoginSpider(scrapy.Spider):
    
    name = website
    start_urls = [website + "/auth/login"]
    custom_settings = {
        'CONCURRENT_ITEMS': 1,
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_TIMEOUT': 600
    }

    def parse(self, response):
        return scrapy.FormRequest.from_response(
            response,
            formdata={'email': email, 'password': password},
            callback=self.after_login
        )

    def after_login(self, response):
        filename = response.url.split("/")[-1] + '.html'
        
        with open(filename, 'wb') as f:
            f.write(response.body)
        
        sauce = response.body
        soup = bs.BeautifulSoup(sauce, 'lxml')

        # all lesson numbers are in the login page but only one level out of three is accesible
        # This is why we will get the numbers of the lessons but only store the numbers and then
        # just append it to website + /course/lesson/

        # For example, we have lessons 525, 526 and 554 so the links generated are
        # website + /course/lesson/525
        # website + /course/lesson/526
        # website + /course/lesson/554

        # Ranges. Principiante: 525-549 Intermedio: 558-582  Avanzado: 591-615
        lesson_list = []

        for il in soup.find_all('a'):
            link_id = str(il.get('id'))
            if("lesson" in link_id):
                lesson_num = int(link_id.split("_")[1])
                if(lesson_num < 550 and downloadLevel == "Principiante"):
                    lesson_list.append(website + "/course/lesson/" + str(lesson_num) )
                elif(lesson_num < 583 and lesson_num > 550 and downloadLevel == "Intermedio"):
                    lesson_list.append(website + "/course/lesson/" + str(lesson_num) )
                elif(lesson_num > 583 and downloadLevel == "Avanzado"):
                    lesson_list.append(website + "/course/lesson/" + str(lesson_num) )

        # I've been changing lesson_list depending on what I want to download
        lesson_list =  lesson_list[21:22]
        
        for lesson_link in lesson_list:
            yield response.follow(lesson_link, callback=self.parse_link)
        

    def parse_link(self, response):
        audioExist = False
        videoExist = False
        exercisesExist = False # we have to change this manually since we can't check if exercises are downloaded.

        dirName = "WebPage/" + downloadLevel + "/" + response.url.split("/")[-1] + "/"
        createDir(dirName)
        
        # to indicate if the video or audio is created already so we don't download again. Not doable with exercises
        for elem in glob(dirName + "/*"):
            if(elem.split("/")[-1] == "Video"):
                for ins in glob(elem + "/*"):
                    if (ins.split(".")[-1] == "mp4"):
                        videoExist = True
            elif(elem.split("/")[-1] == "Audio"):
                for ins in glob(elem + "/*"):
                    if (ins.split(".")[-1] == "mp3"):
                        audioExist = True

        sauce = response.body
        soup = bs.BeautifulSoup(sauce, 'lxml')

        links = []
        for el in soup.find_all('a'):
            link_id = str(el.get('href'))
            if(website + "/course/page" in link_id):
                links.append(link_id)

        # make new list to know which link is the video, which the audio and which the exercises
        newL = []
        # split to list of lists containing "page"
        for el in links:
            newL.append(el.split("/")[-1])

        # Shouldn't have to do it. It's to make sure that video is first, audio is second and exercises are third
        sorted_links = [i[0] for i in sorted(zip(links, newL), key=lambda t: t[1])] 

        # WE HAVE TO INDICATE THE CHROMEDRIVER FOR SELENIUM
        driver = webdriver.Chrome("");
        
        driver.get(website + "/auth/login")
        emailSender = driver.find_element_by_xpath("//*[@id='login-block']/div/div/div[2]/form/div[1]/input")
        passwordSender = driver.find_element_by_xpath("//*[@id='login-block']/div/div/div[2]/form/div[2]/input")

        emailSender.send_keys(email)
        passwordSender.send_keys(password)

        driver.find_element_by_xpath("//*[@id='login-block']/div/div/div[2]/form/input[3]").click()

        # Video
        if(videoExist == False):
            url = sorted_links[0]
            driver.get(url)
            
            sauce = str(driver.page_source)

            dirNameVideo = dirName + "Video/"
            createDir(dirNameVideo)
            regex_video = website + "/course/loadfile/video/" + url.split("/")[-1] + "/"
            index_start = sauce.find(regex_video)
            end_find = sauce.find(".mp4", index_start)
            link_download = sauce[index_start:end_find] + ".mp4"

            dirNameVideo = dirNameVideo + link_download.split("/")[-1]
            if(link_download != ".mp4"):
                yield response.follow(link_download, callback=self.parse_video, meta={'thingy': dirNameVideo})
        else:
            print("Video already exist for " + dirName)

        # Audio
        if(audioExist == False):
            url = sorted_links[1]
            driver.get(url)
            
            sauce = str(driver.page_source)

            dirNameAudio = dirName + "Audio/"
            createDir(dirNameAudio)
            regex_video = website + "/course/loadfile/audio/" + url.split("/")[-1] + "/"# 5505/IT1.mp4"
            index_start = sauce.find(regex_video)
            end_find = sauce.find(".mp3", index_start)
            link_download = sauce[index_start:end_find] + ".mp3"

            dirNameAudio = dirNameAudio + link_download.split("/")[-1]
            if(link_download != ".mp3"):
                yield response.follow(link_download, callback=self.parse_audio, meta={'thingy': dirNameAudio})
        else:
            print("Audio already exist for " + dirName)

        
        if(exercisesExist == False):
            url = sorted_links[2]
            driver.get(url)
            time.sleep(2)
            driver.find_element_by_xpath("//*[@id='starttest']").click()

            foundLast = False
            numPaginas = 1
            while( foundLast == False ):
                dirNameEx = dirName + "Ejercicios/" + str(numPaginas)
                numPaginas = numPaginas + 1
                createDir(dirNameEx)

                time.sleep(3)

                # Enunciado
                write = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[1]/div/div[1]/h3").get_attribute('outerHTML')
                enunciado = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[1]/div/div[1]/h3").get_attribute('innerHTML')
                f = open(dirNameEx + "/enunciado.txt", 'w')
                f.write(write)
                f.close()

                enunciado = enunciado[enunciado.find("</i>")+4:].strip()
                enunciado = enunciado.strip(".")
                aux = enunciado.split()
                aux.pop()
                enunciadoSinPalabraFinal = " ".join(aux)

                # These are lists of the questions which will need a different treatment. I added them as I encountered them.
                # There's a better way to do this.

                # traduceIngles: case where thera are 2 boxes. One on the left with text in spanish and on the right input for answer
                traduceIngles =["Traduce al inglés", 
                "Traduce la frase", 
                "Traduce la frase al inglés", 
                "Convierte la siguiente frase en una pregunta",
                "Translate the sentence",
                "Translate to English"]

                # eligeTraduccionCorrecta: case where you choose the correct translation. could have image
                eligeTraduccionCorrectaSin = ["Elige la traducción correcta", 
                "Elige la traducción correcta de", 
                "Selecciona la traducción de",
                "Selección la traducción de",
                "Select the translation of"]
                eligeTraduccionCorrectaCon = ["Select the correct order of adjetives"]

                # eligeMultiple: case where you can choose more than one answer
                eligeMultipleSin = ["Selecciona todas las", "Selecciona todos los", "Elige todos los", "Elige todas las"]
                eligeMultipleCon = ["Elige la frase correcta"] 
     
                # audioEscribe: case where you listen to an audio and write it in input box
                audioEscribe = ["Escribe el audio. Para escuchar de nuevo, pincha en el altavoz", "Escribe lo que oyes", 
                "Escucha al audio y escribe lo que oyes. Pincha en el altavoz para escuchar de nuevo",
                "Escucha al audio y escribe lo que oyes", 
                "Escribe lo que oyes.  Pincha en el altavoz para escuchar de nuevo", # double space issua
                "Escribe lo que oyes. Pincha en el altavoz para escuchar de nuevo",
                "Escribe la palabra que oyes. Pincha en el altavoz para escuchar de nuevo",
                "Escribe la frase que oyes",
                "Type what you hear",
                "Write what you hear. Click on the blue button to listen again",
                "Listen to the audio. Type what you hear. Click to listen again",
                "Listen to the audio. Type what you hear",
                "Type what you hear. Click on the blue button to listen again",
                "Repeat what you hear. Click on the button button to listen again",
                "Translate to English. Click on the microphone and speak"]

                # audioElige: case where you listen to audio and choose a multiple answer.
                audioElige = ["Escucha el audio y contesta la pregunta", 
                "Escucha el audio y elige la respuesta correcta",
                "Escucha al audio y contesta la pregunta",
                "Escucha al audio y contesta la pregunta. Pincha en el altavoz para escuchar de nuevo",
                "Escucha al audio y selecciona la respuesta correcta", 
                "Convierte la frase una pregunta", "Convierte la frase en pregunta", 
                "Selecciona la traducción del audio",
                "Escucha la conversación y contesta la pregunta", 
                "Escucha la frase y contesta la pregunta",
                "Escucha y contesta la pregunta. Pincha en el altavoz para escuchar de nuevo",
                "Escucha el audio. Responde si la siguiente frase es verdadera o falsa",
                "Escucha al audio. Contesta la pregunta",
                "Escucha  el audio y responde a la pregunta",
                "Listen to the audio and answer the question",
                "Listen and answer the question. Click on the button to repeat",
                "Listen to the audio. Answer the question",
                "Listen to the conversation and answer the question"]

                # fotoElige: case where from a picture you answer multiple choice question
                fotoElige = ["Elige la frase que mejor describe la foto", 
                "Elige el verbo correcto", 
                "Selecciona la traducción correcta",
                "Selecciona la definición de la foto",
                "Selecciona la frase correcta",
                "Selecciona la frase que va con la foto",
                "Selecciona la frase que mejor describe la foto",
                "Selecciona la traducción correcta del verbo (conjugado al pasado simple)",
                "Elige la mejor traducción",
                "Contesta la pregunta fijándote en la foto",
                "Which sentence best describes the photo?",
                "Look at the picture and answer the question",
                "Select the correct translation",
                "Which sentence best describes the picture?",
                "¿Qué significa la expresión en la foto?",
                "Choose the correct translation",
                "Which sentence is correct?",
                "Which sentence best describes the picture?",
                "Choose the correct sentence"]

                # Depending on what exercise we find ourselves in, we grab what we're interested in.
                if(enunciado in traduceIngles): 
                    write = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[2]/div/div[1]/div/p").get_attribute('outerHTML') 
                    f = open(dirNameEx + "/pregunta.txt", 'w')
                    f.write(write)
                    f.close()

                    driver.find_element_by_xpath("//*[@id='answer']").send_keys("a")

                elif(enunciadoSinPalabraFinal in eligeTraduccionCorrectaSin or enunciado in eligeTraduccionCorrectaCon): 
                    write = driver.find_element_by_xpath("""//*[@id="slidecontainer"]/div/div[3]/div/div/div/div/ul/li[1]/label/div[1]""").get_attribute('outerHTML') 
                    f = open(dirNameEx + "/opciones.txt", 'w')
                    f.write(write)
                    f.close()

                    links = []
                    while write.find(website + "/course/loadfile/") != -1:
                        links.append(write[write.find("https"):write.find(".png")+4])
                        write = write[write.find(".png")+4:]

                    for link in links:
                        dirNamePic = dirNameEx + "/" + link.split("/")[-1]
                        yield response.follow(link, callback=self.parse_image, meta={'thingy': dirNamePic })

                    driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[3]/div/div/div/div/ul/li[3]/label/div[1]").click()

                elif(enunciadoSinPalabraFinal in eligeMultipleSin or enunciado in eligeMultipleCon): 
                    write = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[3]/div/div/div").get_attribute('outerHTML') 
                    f = open(dirNameEx + "/pregunta.txt", 'w')
                    f.write(write)
                    f.close()

                    if(enunciadoSinPalabraFinal == "Selecciona todas"):
                        driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[3]/div/div/div/div/ul/li[3]/label/div[1]").click()
                    
                elif(enunciado in audioEscribe):
                    write = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[2]/div/div[1]/div").get_attribute('outerHTML')
                    
                    link_download = write[write.find(website + "/course/loadfile/question_audio"):write.find(".mp3")+4]

                    dirNameAudio = dirNameEx + "/" + link_download.split("/")[-1]
                    yield response.follow(link_download, callback=self.parse_audio, meta={'thingy': dirNameAudio})

                    driver.find_element_by_xpath("//*[@id='answer']").send_keys("a")

                elif(enunciado in audioElige):
                    write = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[2]/h2").get_attribute('outerHTML') 
                    f = open(dirNameEx + "/pregunta.txt", 'w')
                    f.write(write)
                    f.close()

                    write = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[3]/div/div[2]/div").get_attribute('outerHTML') 
                    f = open(dirNameEx + "/opciones.txt", 'w')
                    f.write(write)
                    f.close()

                    write = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[3]/div/div[1]/div").get_attribute('outerHTML')
                    
                    link_download = write[write.find(website + "/course/loadfile/question_audio"):write.find(".mp3")+4]

                    dirNameAudio = dirNameEx + "/" + link_download.split("/")[-1]
                    if(link_download != ""):
                        yield response.follow(link_download, callback=self.parse_audio, meta={'thingy': dirNameAudio})

                    driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[3]/div/div[2]/div/div/div/label[1]").click()
                     
                elif(enunciado in fotoElige):
                    write = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[3]/div/div[1]").get_attribute('outerHTML')
                    
                    link_download = write[write.find(website + "/course/loadfile/question_image"):write.find(".png")+4]

                    dirNameImage = dirNameEx + "/" + link_download.split("/")[-1]
                    yield response.follow(link_download, callback=self.parse_image, meta={'thingy': dirNameImage})

                    write = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[3]/div/div[2]/div/div/div").get_attribute('innerHTML') 
                    f = open(dirNameEx + "/pregunta.txt", 'w')
                    f.write(write)
                    f.close()

                    driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[3]/div/div[2]/div/div/div/label[1]").click()
                     
                else:
                    write = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div[3]/div/div").get_attribute('outerHTML') 
                    f = open(dirNameEx + "/pregunta.txt", 'w')
                    f.write(write)
                    f.close()

                driver.find_element_by_id("check").click()

                write = driver.find_element_by_xpath("//*[@id='correctanswers']").get_attribute('outerHTML') 
                f = open(dirNameEx + "/respuesta.txt", 'w')
                f.write(write)
                f.close()

                time.sleep(2)
                driver.find_element_by_id("check").click()

                try:
                    checkLast = driver.find_element_by_xpath("//*[@id='slidecontainer']/div/div/div/div[2]/div/div/div[2]/div[2]/div[1]/a']").get_attribute('innerHTML') 
                    if(checkLast == "Volver a lecciones"):
                        foundLast = True
                except NoSuchElementException as ns:
                    print("we are not in last page")
                    pass
        else:
            print("Exercises already exist for " + dirName)


    def parse_video(self, response):
        new_filename = response.meta['thingy']
        f = open(new_filename, 'wb')
        f.write(response.body)
        f.close()

    def parse_audio(self, response):
        new_filename = response.meta['thingy']
        f = open(new_filename, 'wb')
        f.write(response.body)
        f.close()

    def parse_image(self, response):
        new_filename = response.meta['thingy']
        f = open(new_filename, 'wb')
        f.write(response.body)
        f.close()

import socket
import sys
import argparse
from urllib.parse import urlparse
from urllib.parse import urlsplit
from urllib.parse import urlunsplit
from bs4 import BeautifulSoup
from bs4.element import Comment
from urllib.parse import urljoin
import base64
import jason
import requests
#import httplib


error_codes={'400':'BAD REQUEST', '401': 'UNAUTHORIZED', '403': 'FORBIDDEN','404': 'NOT FOUND','410':' GONE','500': 'INTERNAL SERVER ERROR','501': 'NOT IMPLEMENTED','503':'SERVICE UNAVAILABLE','550':'PERMISSION DENIED'}

import re


links_depth={} #For BFS/DFS
sd_links_depth={} #For other subdomains

starting_page="http://songyy.pythonanywhere.com/quotes"

words_file = None
user_agent = None

final_words= open("words_list.txt", "w+", encoding='utf-8')
'''
s = socket.socket()
s.settimeout(5)   # 5 seconds
try:
    s.connect(('123.123.123.123', 12345))         # "random" IP address and port
except socket.error, exc:
    print "Caught exception socket.error : %s" % exc
'''

class OneSocket:
    global user_agent
    def __init__(self):
        ### AF_INET---> refers to the address family ipv4
        ### SOCK_STREAM ---> means connection oriented TCP protocol
        ### This is client
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, url):
        global user_agent
        url = urlparse(url)
        host = url.hostname
        path = url.path
        addr = socket.getaddrinfo(host, 80)[0][-1]
        self.sock.connect(addr)
        return (host, path)

    def get_response(self, url, filename):  ## one page response
        tmp=self.connect(url)
        if(user_agent):
            sent = self.sock.sendall(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\nUser-agent: %s\r\n\r\n' % (tmp[1], tmp[0], user_agent), 'utf8'))
            if sent == 0:
                raise RuntimeError("socket connection broken")
        ############################## Get Response  ####################################
        response=[]
        while True:
            data = self.sock.recv(4096)
            if data:
                response.append(data)
            else:
                break
        self.sock.close()

        response = b''.join(response)
        all_content = response.decode("utf8", "ignore")

        header = all_content.split('\r\n\r\n')[0]
        with open("header.txt", "w") as f:
            f.write(header)
            f.close()

        content = all_content.split('\r\n\r\n')[1]
        content = content.encode()
        with open(filename, 'wb') as f:
            f.write(content)
            f.close()

    ## 'POST' request && its response
    def post_reponse(self, url, login_data):
        # headers = { 'User-Agent': user_agent }
        # with requests.Session() as s:
        #     r = s.post(url, data = login_data, headers = headers, verify = False)
        #     with(open('f1.html', 'wb+')) as f:
        #         print('\nNew URL', r.url)
        #         for i in r.history:
        #             print(i.status_code, i.url)

'''
##############################################################
   Create 'wordsList'
###############################################################
'''
def capitalization_permutations(s):
    """Generates the different ways of capitalizing the letters in
    the string s."""

    # >>> list(capitalization_permutations('abc'))
    # ['ABC', 'aBC', 'AbC', 'abC', 'ABc', 'aBc', 'Abc', 'abc']
    # >>> list(capitalization_permutations(''))
    # ['']
    # >>> list(capitalization_permutations('X*Y'))
    # ['X*Y', 'x*Y', 'X*y', 'x*y']
    if s == '':
        yield ''
        return
    for rest in capitalization_permutations(s[1:]):
        yield s[0].upper() + rest
        if s[0].upper() != s[0].lower():
            yield s[0].lower() + rest

def lower_upper_permutation(words_list):
    global final_words

    for line in words_list:
        temp = list(capitalization_permutations(line))
        for item in temp:
            final_words.write("%s\n" % item)

# Function to reverse a string
def reverse(string):
    string = string[::-1]
    return string

# reverse
def reverse_chars(words_list):
    global final_words

    for line in words_list:
        final_words.write("%s\n" %reverse(line))


# leet-speak with the following case-insensitive conversions
def leet_speak(words_list):
    global final_words

    for line in words_list:
        line = line.replace('a', '4').replace('A', '4')
        line = line.replace('e', '3').replace('E', '3')
        line = line.replace('l', '1').replace('L', '1')
        line = line.replace('t', '7').replace('T', '7')
        line = line.replace('o', '0').replace('O', '0')
        final_words.write("%s\n" %line)


def create_dict(words_file):  ## words_file = base_words
    words_list =[]
    base_words = open("base_words.txt", 'w', encoding='utf-8')
    with open(words_file, mode="r", encoding='utf-8') as f:
        for line in f:
            temp = line.lower()
            temp= re.sub(r'\W+', '', temp)
            if temp not in words_list:
                base_words.write("%s\n" %temp)
                words_list.append(temp)
        f.close()
    base_words.close()

    if words_list != []:
        print(words_list)
        final_words = open("words_list.txt", 'w+', encoding='utf-8')
        lower_upper_permutation(words_list)
        reverse_chars(words_list)
        leet_speak(words_list)

    final_words.close()

##############################################
#  Cawler  Class  and basic function
###############################################

class Crawler:
    def __init__(self):
        self.words = []  ### Empty words list
        self.choice = 'depth' ##Depth-first(depth) / Breadth-first(breadth)
        self.maxD = 1 ##  max depth of pages to crawl
        self.maxTotal = 0 ## max total number of pages
        self.sock = None 

        parser = argparse.ArgumentParser()
        parser.add_argument('-u', '--user', nargs='?', type=str, metavar='user_agent', help='must be provide a custom user-agent for use', required=True)
        #parser.add_argument('url', type=str, help="website's url", required=True)
        parser.add_argument('-c', '--choice', nargs='?', type=str, choices=['depth','breadth'], default='breadth', help="Depth-first/Breadth-first choice of crawling", required=False)
        parser.add_argument('-d', '--depth', nargs='?', type=int, metavar='num', default=0, help="Maximum depth of pages to crawl", required=False)
        parser.add_argument('-p','--page', nargs='?', type=int, metavar='num', default=0, help='Maximum total number of crawled pages', required= False)
        sys.args = parser.parse_args()
    ############################################## Help #########################
    def help(self):
        parser.print_help()

    ############################################## Http--Get #########################
    def http_get(self, url, filename):
        global user_agent
        if user_agent:
            self.sock=OneSocket()
            self.sock.get_response(url, filename)

    ############################################## Http--Post #########################
    def http_post(self, url, data):
        if user_agent:
            sock=OneSocket()
            self.sock.post_reponse(url, data)


    ############################################## Links List #########################
    def dfs(self, links_list):
        print("here")



##############################################################################################
def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


#finding and putting all the words found on the website into the list words[] 
def find_words(soup,words):
    texts = soup.find_all(text=True)
    visible_texts = list(filter(tag_visible, texts)) 
    for n in range(len(visible_texts)):
        tmp=visible_texts[n].split()
        for i in range(len(tmp)):
            words.append(tmp[i])
    return words

#finding and putting all the links found on the website into the list links_depth[] at a specific level
def find_links(soup,links_depth,depth,logins,crawler):
    allLinks = soup.findAll('a',href=True)
    temp_list = []
    for n in allLinks:
        #check domain
        if (urlparse(n['href']).hostname)==None:
            thehttp=urljoin(starting_page,n['href'])
        else:
            if (urlparse(n['href']).hostname) != (urlparse(starting_page).hostname):
                continue
            thehttp=n['href']
        
        #check if the link is already in the dict
        found=0
        for n in range(len(links_depth)):
            if thehttp in links_depth[n]:
                found=1
        if thehttp in temp_list:
            found=1
        if found==0:
            if login_page(thehttp,crawler)==True:
                logins.append(thehttp)        
            temp_list.append(thehttp)

    if depth in links_depth:
        links_depth[depth].extend(temp_list)
    else:
        links_depth[depth]=temp_list

#finding and putting all the links found on the website into the list sd_links_depth[] at a specific level
def find_sdlinks(soup,sd_links_depth,depth,logins,crawler):
    allLinks = soup.findAll('a',href=True)
    temp_list = []
    for n in allLinks:
        #check domain
        if (urlparse(n['href']).hostname)==None:
            thehttp=urljoin(starting_page,n['href'])
        else:
            if (urlparse(n['href']).hostname) != (urlparse(starting_page).hostname):
                continue
            thehttp=n['href']
        
        #check if the link is already in the dict
        found=0
        for n in range(len(sd_links_depth)):
            if thehttp in sd_links_depth[n]:
                found=1
        if thehttp in temp_list:
            found=1
        if found==0:
            if login_page(thehttp,crawler)==True:
                logins.append(thehttp)        
            temp_list.append(thehttp)

    if depth in sd_links_depth:
        sd_links_depth[depth].extend(temp_list)
    else:
        sd_links_depth[depth]=temp_list        
 
#check if it is a login page
def login_page(html,crawler):
    crawler.http_get(html , 'check.html')
    website = open("check.html", encoding='utf8')
    soup2 = BeautifulSoup(website, "html.parser")

    allforms = soup2.findAll('form')
    for form in allforms:
        if form.get('name')==None:
            continue
        s=form.get('name').encode().decode()
        if bool(re.search('log[\s_]*in',s ,re.IGNORECASE))==True:
            return True
        if bool(re.search('sign[\s_]*in', s,re.IGNORECASE))==True:
            return True
    return False   

#change subdomain
def replace_subdomain(url,subdomain):
    
    old_host=urlparse(url).hostname.split('.')
    old_host[0]=subdomain
    new_host=('.').join(old_host)

    o = list(urlsplit(url))
    o[1] = new_host
    new_url = urlunsplit(o)

    return new_url


#writing to output files
def output_files(words,links_depth,sd_links_depth,logins):
    new_words =('\n'.join(words)).encode('utf-8','ignore')
    w = open("words.txt", "wb")
    w.write(new_words)

    l = open("links.txt", "wb")
    for n in range(len(links_depth)):
        new_links =('\n'.join(links_depth[n])).encode('utf-8','ignore')
        l.write(new_links)
    for y in range(len(sd_links_depth)):
        new_links =('\n'.join(sd_links_depth[y])).encode('utf-8','ignore')
        l.write(new_links)    

    new_logins =('\n'.join(logins)).encode('utf-8','ignore')
    log = open("logins.txt", "wb")
    log.write(new_logins)   

    w.close()
    l.close()
    log.close()

########################################### Main function#######################

def main():
    global user_agent
    global final_words
    global starting_page

    crawler = Crawler()
    own_config = dict()
    own_config['user_agent']= sys.args.user  # one user_agent
    own_config['choice'] = sys.args.choice  # breadth or depth
    own_config['depth']= sys.args.depth  #  depth of pages to crawling
    own_config['page'] = sys.args.page  # number of pages to crawled pages
    user_agent = own_config['user_agent']

    #crawler.http_post("https://3.16.240.57/wp-login.php","usersdds","EN9fQcC3jnsS")
     
    crawler.http_get(starting_page, 'home.html')

    #check deadend of the very first page
    header = open("header.txt", encoding='utf8')
    firstline=header.readline().rstrip()
    code = firstline.split(" ")[1]
    if code in error_codes:
        print("No available website can be crawled")
        exit(0)  

    ########################### Get words_list.txt && links.txt######################
    words=[]
    logins=[]

    web = open("home.html", encoding='utf8')
    soup = BeautifulSoup(web, "html.parser")
    links_depth[0]= [starting_page] ### start node of the tree

    if login_page(starting_page,crawler)==True:
        logins.append(starting_page)
    find_words(soup,words)
    find_links(soup,links_depth,1,logins,crawler) 

    # depth=1 || page=1
    if own_config['depth']==1 or own_config['page']==1:
        output_files(words,links_depth,logins)
        exit(0) 

    #Depth First Search
    if own_config['choice'] == 'depth':
        print("HI")
        
    # Breadth First Search
    else:
        page_opened=1
        current_depth=1

        while(True):
            if own_config['depth']!=0 and current_depth==own_config['depth']:
                break  
            if current_depth in links_depth:
                for each_link in links_depth[current_depth]:
                    crawler.http_get(each_link, 'home.html')

                    #check deadend
                    header = open("header.txt", encoding='utf8')
                    firstline=header.readline().rstrip()
                    error=0
                    for codes in error_codes: 
                        error_message="HTTP/1.1 "+codes
                        if firstline==error_message:
                            error=1
                    if error==1:
                        continue        

                    page_opened+=1
                    web = open("home.html", encoding='utf8')
                    soup = BeautifulSoup(web, "html.parser")
                    
                    find_words(soup,words)
                    find_links(soup,links_depth,current_depth+1,logins,crawler) 

                    if page_opened==own_config['page']:
                        break
                if page_opened==own_config['page']:
                    break 
                current_depth+=1      
            else:
                break 

   # We should crawl more pages!
   # Using Subdomains
    if(own_config['page']==0 or page_opened<own_config['page']):
        subdomains=[]
        sd = open("subdomains.txt", encoding='utf8')
        host=urlparse(starting_page).hostname.split('.')
        for line in sd:
            if host[0]==line.rstrip():
                continue
            subdomains.append(line.rstrip()) 
        sd.close()

    #Doing BFS
    index=0
    #own_config['page']==0 or page_opened<own_config['page'] or index<len(subdomains)
    while(index<3):
        
        crawler.http_get(replace_subdomain(starting_page,subdomains[index]), 'sd.html')
        print("Tried "+replace_subdomain(starting_page,subdomains[index]))

        #check deadend of the very first page
        header = open("header.txt", encoding='utf8')
        firstline=header.readline().rstrip()
        code = firstline.split(" ")[1]
        if code in error_codes:
            index+=1
            print("No available website can be crawled")
            continue 

        page_opened+=1
        index+=1
        web = open("sd.html", encoding='utf8')
        soup = BeautifulSoup(web, "html.parser")

        #replace the old starting url 
        starting_page=replace_subdomain(starting_page,subdomains[index])
        #clean the tree
        sd_links_depth.clear()
        ### start node of a new tree
        sd_links_depth[0]= [starting_page] 

        #exactly the same as what we did above
        if login_page(starting_page,crawler)==True:
            logins.append(starting_page)
        find_words(soup,words)
        find_sdlinks(soup,sd_links_depth,1,logins,crawler) 

        #Depth First Search
        if own_config['choice'] == 'depth':
            print("HI")
        
        # Breadth First Search
        else:
            current_depth=1

            while(True):
                if own_config['depth']!=0 and current_depth==own_config['depth']:
                    break  
                if current_depth in sd_links_depth:
                    for each_link in sd_links_depth[current_depth]:
                        crawler.http_get(each_link, 'home.html')

                        #check deadend
                        header = open("header.txt", encoding='utf8')
                        firstline=header.readline().rstrip()
                        error=0
                        for codes in error_codes: 
                            error_message="HTTP/1.1 "+codes
                            if firstline==error_message:
                                error=1
                        if error==1:
                            continue        

                        page_opened+=1
                        web = open("home.html", encoding='utf8')
                        soup = BeautifulSoup(web, "html.parser")
                        
                        find_words(soup,words)
                        find_sdlinks(soup,sd_links_depth,current_depth+1,logins,crawler) 

                        if page_opened==own_config['page']:
                            break
                    if page_opened==own_config['page']:
                        break 
                    current_depth+=1      
                else:
                    break           

    output_files(words,links_depth,sd_links_depth,logins)
    crawler.http_get("http://3.16.240.57/wp-login.php", 'home_login.html')
    

    with open("home_login.html", encoding= 'utf8') as f:
        soup2 = BeautifulSoup(f,"html.parser")
        allForm = soup2.findAll('form')
        user= None
        pwd = None
        for ele in allForm:
            t = ele.find('input').get('id')
            pwd = ele.find('input', type="password").get('name')
            if "log" in t:
                user = ele.find('input').get('name')

        combine_file = open("results.txt", 'r')
        l = []
        with open("results.txt", mode="r") as file_1:
            for line in file_1:
                log_1, pwd_1 = line.split(',')
                login_data = dict()
                login_data = {
                    user:log_1,
                    pwd: pwd_1.strip(),
                }
                l.append(login_data)
            file_1.close()
    
        for login_data in l:
            crawler.http_post("http://3.16.240.57/wp-login.php", login_data)
                        


combine_file = open("results.txt", 'w')
combined_list = []

with open("words_1.txt", mode="r") as f:
    for line in f:
        combined_list.append(line.strip())
    f.close()
    for i in range(0, len(combined_list)):
        for j in range(0, len(combined_list)):
            log = combined_list[i]
            pwd = combined_list[j]
            obj = log + "," +pwd
            combine_file.write(obj)
            combine_file.write('\n')
combine_file.close()
# main()


s = OneSocket()
s.get_response("https://www.google.com", "test.html")
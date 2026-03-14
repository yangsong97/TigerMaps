import sys
from bs4 import BeautifulSoup as Soup

longs = []
lats = []
total = []

def parseLog(file):
    soup = Soup(file, "lxml")
    for message in soup.find_all('longitude'):
        long = message.text
        longs.append(long)
    for message in soup.find_all('latitude'):
        lat = message.text
        lats.append(lat)
    for i in range(len(longs)):
        total.append([longs[i], lats[i]])
    return total

if __name__ == '__main__':
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            xml = f.read()
        result = parseLog(xml)
        print(result)
    else:
        print("Usage: python printerscrape.py <xml_file>")

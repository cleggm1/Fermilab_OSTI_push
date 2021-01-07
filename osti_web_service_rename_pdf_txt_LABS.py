import os
import re
from osti_web_service_constants import DIRECTORY

os.chdir(DIRECTORY)
for file in os.listdir(DIRECTORY):
    if re.search(r'\.pdf', file):
        file2 = file.replace('.pdf', '.txt')
        os.remove(file)
        new_file = open(file2, 'w+')
        new_file.close()
        print file2






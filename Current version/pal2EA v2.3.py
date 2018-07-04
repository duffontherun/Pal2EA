#!/usr/bin/python3

#Pal2EA v2.0
import glob, os, sys, re
import lzss

#Main Code
macrofile = "Palette Definitions.txt" #name of definitions file
EAfile = "Palette Installer.event" #name of generated EA installer
setupfile = "Palette Setup.event" #
compext = ".lzpal" #file extenstion of compressed output
labelList = [] #ensure unique labels for each entry

#error detection
curline = -1 #line number first line of current entry in file
errorlog = ""
warnlog = ""
curerror = False #if current entry has an error
error = False 

def addWarning(wtype, text= ""):
	global warnlog
	if(curline >= 0):
		warnlog += "Line " + str(curline) + ': '
	warnlog += wtype + ' warning '
	if(text):
		warnlog += ' - ' + text 
	warnlog += '\n'

def addError(etype, text=""):
	global errorlog
	global curerror
	curerror = True
	if(curline >= 0):
		errorlog += "Line " + str(curline) + ': ' 
	errorlog += etype + " error"
	if(text):
		 errorlog += " - " + text
	errorlog += '\n'

def generate():
	global error #
	global curline #
	global curerror #
	global errorlog #
	
	infile = getPaletteFile(); #get input file

	(path, infile) = os.path.split(infile)
	os.chdir(path) #change current directory to that of the input file

	folds = ['./_palettes']
	
	for fold in folds: #make folders for comrpessed palettes
		if(not os.path.exists(fold)):
			try:
				os.mkdir(fold)
			except:
				print("this isn't working")
				return
	with open(infile, 'r') as file:
		data = file.read()

	output = ""
	setup = ""

	entries = removeComments(data)
	entries = entries.split('#')
	#entries = list(filter(None, entries))
	meta = []
	if(len(entries) == 0):
		print("the input file seems empty")
		return
	for e in range(1, len(entries)):#(e = 1; e < len(entries); e++)
		curerror = False 
		z = entries[e].find('\n')
		n = entries[e][:z]
		m = data.find(n) 
		curline = lineNumber(m, data) 
		m = getinfo(n)
		meta.append(m)
		
		entry = entries[e][z:]
		
		if(entry.strip()): #attempt to convert into bytes
			entry = palette_hex(entry, m[2], m[1][1])
		else: #do nothing if empty
			entry = bytearray()
			addWarning("Empty Entry")
		
		outfile = ''
		
		if (len(entry) and (not error and not curerror)): #skip this entry if it is empty
			setup += ('\n// ' + m[0] +'\n')
			outfile = (folds[0] + '/' + m[0] + compext)
			#generate palette file
			try:
				if(m[1][1]): #check if palette should be compressed
					lzss.compress(entry, open(outfile, 'wb'))
				else:
					with open(outfile, 'wb') as f:
						f.seek(0)
						f.write(entry)
				print(m[0])
			except:
				#print("palette file generation error")
				addError("Output", "could not make palette file")
			
		#print macros for setup file
		if(curerror):
			error = True
		elif(m[1][0] == 'gen' and m[1][2]): 
			#outfile = (folds[0] + '/' + m[0] + compext)
			for z in range(2, len(m[1])):
				setup += ('\t' + 'setGenericPalette(' + m[1][z] + ',' + m[0] + ')\n')
		elif(m[1][0] == 'char' and m[1][2]):
			#outfile = (folds[0] + '/' + m[0] + compext)
			for z in range(2, len(m[1])):
				setup += ('\t' + 'setPalette(' + m[1][z] + ',' + m[0] + ')\n')
			x = int(len(m[3]))
			for z in range (0,x,3):
				setup += ('\t' + 'setCBSP(' + m[1][2] + ',' + m[3][z] + ',' + m[3][z+1] + ',' + m[3][z+2] + ')\n')
		
		if(outfile and (not error)):
			outfile = '\t#incbin "' + outfile + '" \n'
		if(m[4] and (not error)):
			output += ('PUSH \n' + 'ORG ' + m[4] + '\n' + m[0]
						+ ':\n' + outfile + 'POP \n\n')
		else:
			output += m[0] + ':\n' + outfile + '\n'
	if(not error):
		setup = ("//Palette Setup \n" + "//Generated by Pal2EA v2.x\n\n" + '#include "' + macrofile + '"\n'
			 + '#include "' + EAfile + '"\n' + setup)
		output = "//Palette Installer \n" + "//Generated by Pal2EA v2.x\n\n" + output
		try:
			with open(EAfile, 'w') as ofile:
				ofile.write(output)
				
			with open(setupfile, 'w') as sfile:
				sfile.write(setup)
			z = glob.glob('./' + macrofile, recursive = False)
			if (not z): #create file if it doesn't exist
				z = paldef()
				print('Generating ' + macrofile)
				with open('./' + macrofile, 'w') as dfile:
					dfile.write(z)
		except:
			#file generation error
			error = True
			print("could not generate files")
	#print error/warning log here
	if(warnlog):
		print('')
		print(warnlog)
	if(error):
		print('')
		print(errorlog)
		print("error(s) detected; no files written")
	else:
		print("no errors detected")
	return
	
#Functions

def getPaletteFile():
	validfile = False

	if(len(sys.argv) > 1):
		file = sys.argv[1]
		file = file.replace('"','')
		file = file.replace("'","")
		validfile = os.path.isfile(file)
	while(not validfile):
		file = input("select a file for input: ")
		file = file.replace('"','')
		file = file.replace("'","")
		if(os.path.isfile(file)):
			validfile = True
		else:
			print("This is not a valid file path")
	return file

def getinfo(line): #get metadata from # line
		
	def getdetails(op, ed,start=0, moresigns=False):
		global error
		badsigns = ['.','@','!','=','<','>','?','^'] 
		if(moresigns):
			badsigns.extend(['(',')',',','+','-','/','*','&','%','&'])
		#symbols that can't be in labels['(',')',','+','-','/','*','&','%','&']
		x = line.find(op, start)
		v = []
		if(x >= 0):
			z = line.find(ed, x+1)
			if (z > x):
				c = line[x + len(op):z]
				#check for syntax errors
				for sign in badsigns:
					if(sign in c):
						if (moresigns):
							addError("Invalid Label", (op + c + ed))
							c = '-' # syntax error for labels
						else:
							addError("Syntax", ("in" + op + c + ed))
							c = ''
						break;
				b = c.split(',')	
				v.extend(b)
			else:
				return [''] #parens error
		else:
			return ['']
		return v
		
	m = []
	global labelList
	global error
	for z in range(0,6):
		m.append('')
	#get insertion info
	
	ptype = getdetails('char{','}')
	if(ptype[0]):
		ptype.insert(0, 'char')
	else:
		ptype = getdetails('gen{','}')
		if(ptype[0]):
			ptype.insert(0,'gen')
		#else:
		#	ptype[0] = ['other']
	x = line.find('[nc]')
	if (x >= 0):
		ptype.insert(1,False) #turn off compression and autofill 
	else:
		ptype.insert(1,True)	
	m[1] = ptype #palette type
	#empty labels vs error
	#find label
	ptype = getdetails('"','"',0,True)
	if(ptype[0] == '-'):
		ptype[0] = ''
		z = ''
	elif(not ptype[0]): #generate generic label if no label found
		if(m[1][0]):
			if(len(m[1][1]) < 7):
				z = m[1][0] + '_2' #+ m[1][1]
			else:
				z = m[1][0] + '_Label'
		else:
			z = 'Label'
	else:
		ptype[0] = ptype[0].strip()
		ptype[0] = ptype[0].replace(' ', '_')
		z = ptype[0]
	#ensure label is unique; 
	#it should not match any of the previous labels
	x = 2
	c = z
	while (c and c in labelList):
		c = z + str(x)
		x += 1
	if(z):
		if(z in labelList):
			addWarning("Duplicate label", z + " changed to " + c)
		labelList.append(c)
	m[0] = c #label
	
	#autofill stuff
	ptype = getdetails('auto{','}')
	if (len(ptype) < 3):
		if(m[1][0] == 'gen'):
			if(not ptype[0]):
				ptype = [0, 4, 32]
			elif(len(ptype) == 1):
				ptype.extend([4,32])
			elif(len(ptype) == 2):
				ptype.append(32)
			for x in range(0,3):
				ptype[x] = int(ptype[x])
				
		elif(m[1][0] == 'char'):
			if(not ptype[0]):
				ptype = [0, 5, 32]
			elif(len(ptype) == 1):
				ptype.extend([5,32])
			elif(len(ptype) == 2):
				ptype.append(32)
			for x in range(0,3):
				ptype[x] = int(ptype[x])
		else:
			ptype = ['','','']
	m[2] = ptype #autofill stuff
	
	x = line.find("set{")
	m[3]=[]
	while(x >= 0):
		ptype = getdetails("set{","}",x)
		if(not ptype[0]):
			#print("parsing error in 'set{}' for", m[0])
			break;
		if(len(ptype) == 2):
			ptype.append('0x0')
		elif(len(ptype) < 2):
			ptype = ['','','']
		if(ptype[0]):
			m[3].extend(ptype)
		z = line.find("}",x+1)
		x = line.find("set{",z)
	
	ptype = getdetails('at{', '}')
	m[4] = ptype[0]
	
	return m
	
def lineNumber(p, data):
	lines = data[:p]
	return lines.count('\n') + 1
	
def removeComments(twc):
	global error
	x = 0
	while (twc.find('//') >=0):
		x = twc.find('//')
		if (x >= 0):
			z = twc.find('\n',x)
			if(z >= 0):
				c = twc[x:z]
			else: #assumes comment is at end of file
				c = twc[x:]
			twc = twc.replace(c,"")

		#do multi-line comments later using find() and rfind()
	return twc

"""
def autofill(data, amount, dindex = 1, length = 32): #redo this
    #data is a string of the palette hex
    pal = re.sub('[\s]', '', data) #remove all whitespace characters
    palnum = int(len(data)/length)
    #implement selecting which part to autofill later
    if(palnum < amount):
        contents = bytearray()
        for i in range (0,palnum)
            c = data[(i*length):((i+1)*length)]
            contents += bytearray.fromhex(c)
        #autofill the rest
        if(dindex > palnum):
            print("autofill error: default palette does not exist")
            return bytearray() #return empty array, skip entry
        else:
            c = data[(dindex*length):((dindex+1)*length)]
            for i in range (palnum, amount):
                contents += bytearray.fromhex(c)
    return contents;
"""

def palette_hex(paldata, auto, comp):
	pals = re.sub(r'\n\s*\n', '\n', paldata) #remove empty lines
	pals = pals.strip()
	if(comp):
		pals = pals.split('\n')
		pals = list(filter(None, pals)) #remove empty lines
		dindex = auto[0]
		amount = auto[1]
		length = auto[2]
		if (dindex > amount):
			#print('\t',"Autofill Error: Default palette does not exist")
			addError("Autofill", " Default palette does not exist")
			error = True
			#return or sys.exit()
		if (len(pals) < amount):
			for x in range(len(pals), amount):
				pals.append('auto')
		for p in range(0, amount):
			a = pals[p].find('auto')
			if (a >= 0):		
				pals[p] = pals[dindex]
			pals[p] = re.sub('[\s+]', '', pals[p])
		contents = "".join(pals)
	else:
		contents = re.sub('[\s+]', '', pals) #remove all whitespace
	
	try:
		contents = bytearray.fromhex(contents)
	except:
		addError("Hex Conversion")
		contents = bytearray() #return empty bytearray
	
	return contents

def paldef():
	#generates the defintions file

	defile = ('// defintions file generated by pal2EA v2.0' + '\n')
	
	#ifdef guard
	defile += ("#ifndef PalMacros" + '\n\t' + "#define PalMacros" + '\n')

	#define palette table
	defile += ('\t' + "#ifndef PaletteTable" + '\n')
	defile += ('\t\t' + "#ifdef _FE6_" + '\n\t\t\t' + "#define PaletteTable 0x7FC004" + '\n\t\t' + "#endif" + '\n')
	defile += ('\t\t' + "#ifdef _FE7_" + '\n\t\t\t' + "#define PaletteTable 0xFD8004" + '\n\t\t' + "#endif" + '\n')
	defile += ('\t\t' + "#ifdef _FE8_" + '\n\t\t\t' + "#define PaletteTable 0xEF8004" + '\n\t\t' + "#endif" + '\n')
	defile += ('\t' + "#endif" + '\n\n')
	defile += ('\t' + "#ifndef BattleSpriteTable" + '\n')
	defile += ('\t\t' + "#ifdef _FE6_" + '\n\t\t\t' + "#define BattleSpriteTable 0x6A0008" + '\n\t\t' + "#endif" + '\n')
	defile += ('\t\t' + "#ifdef _FE7_" + '\n\t\t\t' + "#define BattleSpriteTable 0xE00008" + '\n\t\t' + "#endif" + '\n')
	defile += ('\t\t' + "#ifdef _FE8_" + '\n\t\t\t' + "#define BattleSpriteTable 0xC00008" + '\n\t\t' + "#endif" + '\n') 
	defile += ('\t' + "#endif" + '\n\n')
	defile += ('\t' + '#ifndef CharacterTable' + '\n')
	defile += ('\t\t' + "#ifdef _FE6_" + '\n\t\t\t' + '#define CharacterTable 0x6076A0' + '\n\t\t' + "#endif" + '\n')
	defile += ('\t\t' + "#ifdef _FE7_" + '\n\t\t\t' + '#define CharacterTable 0xBDCE18' + '\n\t\t' + "#endif" + '\n')
	defile += ('\t' + "#endif" + '\n\n')	
	defile += ('\t' + '#define setPalette(index, palette) "PUSH; ORG (PaletteTable + index * 0x10); POIN palette; POP"' + '\n')
	defile += ('\t' + '#define setGenericPalette(index, genpal) "PUSH; ORG ((BattleSpriteTable - 0x4) + (index * 0x20)); POIN genpal; POP"' + '\n')
	defile += ('\t' + '#ifdef _FE8_' + '\n')
	defile += ('\t\t' + '#define setCharClass(char_id, trainee, base1, base2, promo1, promo2, promo3, promo4) ' +
			 '"PUSH; ORG ($95E0A4 + (char_id -1) * 7); BYTE trainee base1 base2; BYTE promo1 promo2 promo3 promo4; POP"' + '\n')
	defile += ('\t\t' + '#define setCharPalette(char_id, trainee, base1, base2, promo1, promo2, promo3, promo4) ' +
			 '"PUSH; ORG ($95EEA4 + (char_id -1) * 7); BYTE trainee base1 base2; BYTE promo1 promo2 promo3 promo4; POP"' + '\n')
	defile += ('\t' + '#endif' + '\n\n')
	defile += ('\t' + '#ifdef _FE8_' + '\n\t\t' + '#define setCBSP(char_pal, char_id, palnum, class_id) ' + 
			 '"PUSH; ORG ($95E0A4 + (char_id -1) * 7 + palnum); BYTE class_id; ORG ($95EEA4 + (char_id -1) * 7 + palnum); BYTE char_pal; POP"' + '\n')
	defile += ('\t' "#endif" + '\n')
	defile += ('\t' + '#ifdef _FE7_' + '\n\t\t' + '#define setCBSP(char_pal, char_id, palnum, not_used) "PUSH; ' + 
			 'ORG (CharacterTable + (char_id * 52) + 35 + palnum); BYTE char_pal; POP"' + '\n')
	defile += ('\t' "#endif" + '\n')
	defile += ('\t' + '#ifdef _FE6_' + '\n\t\t' + '#define setCBSP(char_pal, char_id, palnum, not_used) "PUSH; ' + 
			 'ORG (CharacterTable + (char_id * 48) + 35 + palnum); BYTE char_pal; POP"' + '\n')
	defile += ('\t' "#endif" + '\n')
	
	#ifdef guard
	defile += ("#endif" +'\n')
	return defile

if __name__ == '__main__':
	#input('Press Enter')
	print('pal2EA')
	generate()
	input('Press Enter to continue')	#end of program

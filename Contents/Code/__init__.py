# coding=utf-8

import re,time,string
import datetime


SOURCE = "[FilmAffinity Agent 0.8.4] : "

#Configuration values
SLEEP_GOOGLE_REQUEST = 0.5
MAX_GOOGLE_PAGES = 2
MAX_TRANSLATES = 2
MAX_RECHECK = 3
POOR_RESULT = 90

#Pref keys
PREF_REVIEWS = "pref_show_reviews"
PREF_REVIEWS_SI = "si"
PREF_REVIEWS_NO = "no"

PREF_IMGS = "pref_imgs"
PREF_IMGS_FA_ELSE_MDB = "FilmAffinity sino TheMovieDB"
PREF_IMGS_FA = "FilmAffinity"
PREF_IMGS_MDB = "TheMovieDB"

POSTER_TYPES = {u"Poster / Imagen Principal España" : 0,u"Posters España" : 1,"Poster / Imagen Principal" : 2, "Posters" :3}
ART_TYPES = {u"Wallpapers España" : 0, "Wallpapers" : 1, u"Promo España" : 2, "Promo" : 3, u"default España" : 4 , "default" : 5}

BINGSEARCH_URL   = 'http://api.bing.net/json.aspx?AppId=F1BE9EEA086577A2F3F4818DECFD82AB324066AA&Version=2.2&Query=%s&Sources=web&Web.Count=8&JsonType=raw'
GOOGLESEARCH_URL = "http://ajax.googleapis.com/ajax/services/search/web?v=1.0&userip=%s&rsz=large&start=%d&oe=utf-8&ie=utf-8&q=%s"
TMDB_GETINFO_IMDB = 'http://api.themoviedb.org/2.1/Movie.imdbLookup/en/json/a3dc111e66105f6387e99393813ae4d5/%s'
#FilmAffinity URLs
FILMAFFINITY_DETAIL_URL="http://www.filmaffinity.com/es/film%s.html"
FILMAFFINITY_EN_DETAIL_URL="http://www.filmaffinity.com/en/film%s.html"
FILMAFFINITY_IMAGES_URL="http://www.filmaffinity.com/es/filmimages.php?movie_id=%s"

class DetailDataHandler():
	def __init__(self,scope=None):
	   self.value = None
	   self.scope = scope
				  
	def handle(self,data):
		if len(data.strip()) > 0:
			if self.value is not None:
				self.value = self.value + data
			else:
				self.value = data
		return True
				  
	def getValue(self):
		return self.value
				  
	def getScope(self):
		return self.scope

	#Atomic handler only stops when is out of scope
	def isAtomic(self):
		return False

class ReviewsHandler(DetailDataHandler):
	def __init__(self,scope=None):
		self.value = None
		self.scope = scope
		self.pt = re.compile(r" [ ]+")
   												  
	def handle(self,data):
		#Log(SOURCE+data)
		svalue = data.strip()
		svalue = svalue.replace("\r\n","")
		svalue = self.pt.sub(" ",svalue)
		
		idx = svalue.rfind("--")
		if idx != -1:
			final = "\n" + svalue[:idx+2] + "\n"
			if idx+2 < len(svalue):
				final = final + svalue[idx+2:]
			svalue = final
		if self.value is not None:
			self.value = self.value + svalue
		else:
			self.value = svalue
		return True

	def isAtomic(self):
		return True


class DetailAttrsHandler():
	def __init__(self,scope=None):
	   self.scope = scope

	def handleAttrs(self,attrs):
		return False
				  
	def getValue(self):
		return None
	
	def getScope(self):
		return self.scope
		
	def isAtomic(self):
		return False

class MainPosterHandler(DetailAttrsHandler):
	def __init__(self,scope=None):
		self.image = None
		self.scope = scope

	def handleAttrs(self,attrib):
		if "href" in attrib:
			self.image = attrib["href"]

		return False
				  
	def getValue(self):
		return self.image

class LowResPosterHandler(DetailAttrsHandler):
	def __init__(self,scope=None):
		self.image = None
		self.scope = scope

	def handleAttrs(self,attrib):
		if "src" in attrib:
			img = attrib["src"]
			if img.find("pics.filmaffinity.com")!=-1:
				self.image = img
		return False
				  
	def getValue(self):
		return self.image
   

class NamesHandler(DetailDataHandler):
	def __init__(self,scope=None):
		self.values = []
		self.scope = scope
				  
	def handle(self,data):
		svalue = data.strip()
		if len(svalue) > 1:#Discard separator characters
			if svalue.find(",")!=-1:
				self.values = self.values + mapvalues(trim,svalue.split(","))				
			else:
				self.values.append(svalue)
		return True
				  
	def getValue(self):
		return self.values

class StudiosHandler(DetailDataHandler):
	def __init__(self,scope=None):
		self.values = []
		self.scope = scope
   
												  
	def handle(self,data):
		svalue = data.strip()
		if len(svalue) > 0:
			idx = svalue.find(";")
			if idx != -1:
				svalue = svalue[idx+1:]
			self.values = mapvalues(trim,svalue.split("/"))
			return False
		return True
				  
	def getValue(self):
		return self.values

class ImageHandler(DetailDataHandler):
	def __init__(self,scope=None):
		self.images = []
		self.scope = scope
		self.p = re.compile(r"url_s: '((.)*?)', url_l: '((.)*?)'(.)*?type_id: '((.)*?)', country: '((.)*?)'")
				  
	def handle(self,data):
		m = self.p.search(data)
		while m is not None:
			img = m.group(1,3,6,8)
			self.images.append(img)
			m = self.p.search(data,m.end())
		return False
				  
	def getValue(self):
		return self.images

class DetailHTMLParser():
	def __init__(self,details,attrs=None,tags=None,):
		self.details=details
		self.attrs=attrs
		self.tags=tags
		self.currentDetail=None
		self.currentAtomic = False
		self.currentElement=None
				  
	def parse(self,urlr):
		root = HTML.ElementFromURL(urlr)
		for e in root.iter():
			#Log("[FilmAffinity Agent] : Processing tag=",e.tag," text=",e.text," tail=",e.tail)
			self.handle(e)

	def filter(self,function,values):
		result = []
		for v in values:
			if function(v):
				result.append(v)
		return result
   
   
	def startProcessing(self,element,scope,atomic):
		if scope != None:
			#Looking for scope
			parent = element.getparent()
			self.currentElement = None
			self.currentAtomic = False
			while parent is not None:
				if parent.tag.lower()==scope:
					self.currentElement = parent
					self.currentAtomic = atomic
					break
				parent = parent.getparent()
		else:
			self.currentElement = element
			self.currentAtomic = False
			
   
	def isProcessing(self):
		return self.currentElement != None
				  
	def stopProcessing(self):
		#Log("[FilmAffinity Agent] : **Stop")
		self.currentElement = None
		self.currentAtomic = False
				  
	def isInProcessingScope(self,element):
		if self.currentElement is not None:
			parent = element.getparent()
			while parent is not None:
				if parent == self.currentElement:
					#Log("[FilmAffinity Agent] : Is in scope")
					return True
				parent = parent.getparent()
		#Log("[FilmAffinity Agent] : Not in scope")
		return False
				  
   
	def handle(self,element):
		#Log("[FilmAffinity Agent] : Atomic: "+str(self.currentAtomic))
		if (self.attrs is not None) and (not self.currentAtomic):
			for a,va in element.attrib.items():
				if a in self.attrs:
					vd = self.attrs[a]
					if va in vd:
						#Log("[FilmAffinity Agent] : Attribute found: "+a+"="+va)
						self.currentDetail = vd[va]
						self.stopProcessing()
		if (self.tags is not None) and (not self.currentAtomic):
			tag = element.tag
			if tag in self.tags:
				#Log("[FilmAffinity Agent] : Tag Found: " + tag)
				self.currentDetail = self.tags[tag]
				self.stopProcessing()
		text = element.text
		if (text!=None) and (text in self.details) and (not self.currentAtomic):
			#Log("[FilmAffinity Agent] : Detail found: "+text)
			self.currentDetail = text
			self.stopProcessing()
		elif self.currentDetail:
			handler = self.details[self.currentDetail]
			if handler is not None:
				if not self.isProcessing() or self.isInProcessingScope(element):
					if isinstance(handler,DetailAttrsHandler):
						#Log("[FilmAffinity Agent] : handle attributes: ",element.attrib)
						if not handler.handleAttrs(element.attrib):
							self.currentDetail = None						  
							self.stopProcessing()
						else:
							self.startProcessing(element,handler.getScope(),handler.isAtomic())
					elif isinstance(handler,DetailDataHandler):
						#Log("[FilmAffinity Agent] : handle text: ",text)
						if text==None:
							#The element text is empty, trying tail
							text = element.tail
							#Log(SOURCE+"handle tail: "+str(text))
						if text!=None:
							if not handler.handle(text):
								self.currentDetail = None						  
								self.stopProcessing()
							else:
								self.startProcessing(element,handler.getScope(),handler.isAtomic())
				else:
					self.currentDetail = None						  
					self.stopProcessing()


def Start():
	HTTP.CacheTime = CACHE_1DAY
 
  
class FilmAffinityAgent(Agent.Movies):
  name = 'FilmAffinity'
  languages = ['es']
  primary_provider = True
  accepts_from = ['com.plexapp.agents.localmedia']


  def recheckWithENResults(self,umedia_name,media,results,lang,englishids):
  	if len(results) > 0 and results[0].score<POOR_RESULT:
  		Log(SOURCE+"The best result got a poor score result, rechecking with EN results")
  		checks = 0
	  	response = {"responseData":{"cursor":{"pages":[],"currentPageIndex":-1},"results":[]}}
	  	responses = response["responseData"]["results"]
	  	for result in results:
	  		if (result.lang == "es") and (result.id not in englishids):
	  			Log(SOURCE+str(result.id)+" is spanish result, trying english version")
	  			enurl = FILMAFFINITY_EN_DETAIL_URL % result.id
	  			title = getTitleFromUrl(enurl)
	  			if title is not None:
		  			r = {"unescapedUrl":enurl,"titleNoFormatting":title}
		  			responses.append(r)
	  			checks += 1
	  			if checks == MAX_RECHECK:
	  				break
	  	score = 99
	  	self.checkGoogleResponse(response,umedia_name,media,results,score,lang,englishids)

  def recalcWithLongestSub(self,umedia_name,media,results,lang):
  	if len(results) > 0 and results[0].score<POOR_RESULT:
  		Log(SOURCE+"Still with poor score results, recalculating scores with longest substring")
	  	for result in results:
			uname = result.name.decode('utf-8')
			mratio = matchRatioLongest(umedia_name,uname)
			Log(SOURCE+"Match Longest "+uname+" ratio="+str(mratio))
			gain = mratio*25
	  		result.score = min(int(result.score + gain),99)


  def checkGoogleResponse(self,response,umedia_name,media,results,score,lang,englishids):
	if response is None:
		return (0,score)
	
	responses = response["responseData"]["results"]
	nr = len(results)
	if len(responses)>0:
		for result in responses:
			url = result["unescapedUrl"]
			title = unescapeHTML(result["titleNoFormatting"])
			if self.check(umedia_name,media.year,results,score,lang,englishids,url,title):
				score = score - 1
		if nr == len(results):
			Log(SOURCE+"Google. In this page there are no new results, stop the search process")
			#In this page there are no new results, stop the search process
			return (0,score)
		cursor = response["responseData"]["cursor"]
	
		pages = cursor["pages"]
		currentIdx = cursor["currentPageIndex"]+1
		if currentIdx >= len(pages):
			Log(SOURCE+"Google. Cursor has no more pages: "+str(cursor))
			#No more results
			return (0,score)
		return (int(pages[currentIdx]["start"]),score)
	else:
		return (0,score)

  def checkBingResponse(self,response,umedia_name,media,results,score,lang,englishids):
	if "Web" in response["SearchResponse"]:
		web = response["SearchResponse"]["Web"]
		if web["Total"]>0:
			responses = web["Results"]
			for result in responses:
				url = result["Url"]
				title = unescapeHTML(result["Title"])
				if self.check(umedia_name,media.year,results,score,lang,englishids,url,title):
					score = score - 1
	else:
		Log(SOURCE+"BING error:"+str(response));
	return (0,score)


  def check(self,umedia_name,media_year,results,score,lang,englishids,url,title):
	#Log("[FilmAffinity Agent] : "+title+" founded! Is a FilmAffinity result?")
	name, year = parseTitle(title)
	if name is not None:
		#The plugin support media names in english and spanish
		p = re.compile(r'http://www\.filmaffinity\.com/(es|en)(/ud)?/film([0-9]*)\.html')
		m = p.match(url)
		if m is not None:
			id = m.group(3)
			scorePenalty = 0
			#Match penalization
			uname =  name.decode('utf-8')
			mratio = matchRatioLeven(umedia_name,uname)
			Log(SOURCE+"Match Levien "+uname+" ratio="+str(mratio))
			dd = uname.find(":")
			if dd >0:
				upname = uname[0:dd]
				#Maybe the title has a subtitle, in this case titles could be too long and the previous ratio is not good
				mratio = max(mratio,matchRatioLongest(umedia_name,upname))
				Log(SOURCE+"Match Longest "+upname+" ratio="+str(mratio))
				
			scorePenalty += (1-mratio)*25
			if year is not None:
				if mratio == 1.0:
					if (media_year is not None) and (int(media_year) == int(year)):
						#Perfect gain score
						scorePenalty = -25
					
				#Year penalization
				# Check to see if the item's release year is in the future, if so penalize.
				if year > datetime.datetime.now().year:
					scorePenalty += 25
				# Check to see if the hinted year is different from FA's year, if so penalize.
				elif media_year and int(media_year) != int(year): 
					yearDiff = abs(int(media_year)-(int(year)))
					if yearDiff == 1:
						scorePenalty += 5
					elif yearDiff == 2:
						scorePenalty += 10
					else:
						scorePenalty += 15
			#TV penalization (I hate TV)
			if uname.find(u"(TV)") != -1:
				scorePenalty += 15
				
			Log(SOURCE+name+" penalty="+str(scorePenalty))
			rLang = m.group(1)
			results.Append(MetadataSearchResult(id = id, name  = name, year = year, lang  = rLang, score = min(int(score - scorePenalty),99)))
			if rLang == "en":
				englishids[id] = True
			return True
	return False
  
  def search(self, results, media, lang):
	if media.year is not None:
		searchYear = ' (' + str(media.year) + ')'
	else:
		searchYear = ''

	#Normalize the media.name (acutes seem to be wrong, é is e')
	umedia_name = normalizeU(media.name.decode('utf-8'))
	
	Log(SOURCE+"Searching "+umedia_name+searchYear)
	
	score = 99
	q = String.Quote(umedia_name.encode('utf-8') + searchYear, usePlus=True) + "+site:filmaffinity.com"
	currentIdx = 0
	finalURL = None
	englishids={}
	for i in range(MAX_GOOGLE_PAGES):
		response = google(currentIdx,q)
		currentIdx,score = self.checkGoogleResponse(response,umedia_name,media,results,score,lang,englishids)
		if currentIdx == 0:
			break

	try:
		q = String.Quote(umedia_name.encode('utf-8') + searchYear, usePlus=True) + "+site:filmaffinity.com"
		finalURL = BINGSEARCH_URL % q
		response = JSON.ObjectFromURL(finalURL)
		self.checkBingResponse(response,umedia_name,media,results,score,lang,englishids)

		results.Sort('score', descending=True)
	except Exception, e:
		Log(SOURCE+"Got an error when proccessing BING results: "+str(e))
	
	#Last chance, recheck spanish results (only with poor scores).
	self.recheckWithENResults(umedia_name,media,results,lang,englishids)

	results.Sort('score', descending=True)
	
	self.recalcWithLongestSub(umedia_name,media,results,lang)

	results.Sort('score', descending=True)

	#Translate english results (if we can and only MAX_TRANSLATES)
	translates = 0
	remove = False
	toWhack = []
	for result in results:
		if result.lang == "en":
			if not remove and translate(result,lang):
				translates += 1
				if translates == MAX_TRANSLATES:
					remove = True
			else:
				toWhack.append(result)
	for dupe in toWhack:
		results.Remove(dupe)
    
	# Finally, de-dupe the results.
	toWhack = []
	resultMap = {}
	for result in results:
		if not resultMap.has_key(result.id):
			resultMap[result.id] = True
		else:
			toWhack.append(result)
        
	for dupe in toWhack:
		results.Remove(dupe)
		
      
  def update(self, metadata, media, lang):
	mid = metadata.id
	reviews = (Prefs[PREF_REVIEWS]==PREF_REVIEWS_SI)

#	try:
	attrsMD = {"style" : {"color:#990000; font-size:22px; font-weight: bold;" : u"VALORACIÓN"},"class" : {"lightbox" : "POSTER"}}
	detailsMD = {"TITULO" : DetailDataHandler(),u"TÍTULO ORIGINAL" : DetailDataHandler("tr"),u"AÑO" : DetailDataHandler(),u"DURACIÓN" : DetailDataHandler(),u"PAÍS" : None,"DIRECTOR" : NamesHandler("tr"),u"GUIÓN" : NamesHandler("tr"),u"MÚSICA" : NamesHandler("tr"),u"FOTOGRAFÍA" : NamesHandler("tr"),"REPARTO" : NamesHandler("tr"),"PRODUCTORA" : StudiosHandler("tr"),u"GÉNERO" : NamesHandler("tr"),"SINOPSIS" : DetailDataHandler("tr"),u"VALORACIÓN" : DetailDataHandler(),"POSTER" : MainPosterHandler(),"LOWPOSTER" : LowResPosterHandler()}
	
	if reviews:
		detailsMD[u"CRÍTICAS"] = ReviewsHandler("tr")
		
	tagsMD = {"title" : "TITULO","img" : "LOWPOSTER"} 

	detailsImg = {"IMAGENES" : ImageHandler()}
	tagsImg = {"script" : "IMAGENES"} 

	@parallelize
	def htmlParsers():
		@task
		def filmDetailParser():
			finalURLMD = FILMAFFINITY_DETAIL_URL % mid
			parserMD = DetailHTMLParser(details=detailsMD,attrs=attrsMD,tags=tagsMD)
			parserMD.parse(finalURLMD)

		@task
		def filmImgsParser():
			finalURLImg = FILMAFFINITY_IMAGES_URL % mid 
			parserImg = DetailHTMLParser(details=detailsImg,tags=tagsImg)
			parserImg.parse(finalURLImg)
			
#	for d,h in detailsMD.items():
#		Log(SOURCE+d)
#		if h:
#			if d=="TITULO":
#				Log(cleanFATitle(h.getValue()))
#			else:
#				Log(h.getValue())


#	for d,h in detailsImg.items():
#		Log("[FilmAffinity Agent] : "+d)
#		if h:
#			Log(h.getValue())
	#title
	metadata.title = cleanFATitle(detailsMD["TITULO"].getValue())
	#year
	metadata.year = int(detailsMD[u"AÑO"].getValue())
	#genre
	metadata.genres.clear()
	for genre in detailsMD[u"GÉNERO"].getValue():
		metadata.genres.add(genre)
	#director
	metadata.directors.clear()
	for director in detailsMD["DIRECTOR"].getValue():
		metadata.directors.add(director)
	#writers
	metadata.writers.clear()
	for writer in detailsMD[u"GUIÓN"].getValue():
		metadata.writers.add(writer)
	#studio
	if len(detailsMD["PRODUCTORA"].getValue())>0:
		metadata.studio = detailsMD["PRODUCTORA"].getValue()[0]
	#Original Title
	metadata.original_title = detailsMD[u"TÍTULO ORIGINAL"].getValue()
	#Summary
	metadata.summary = detailsMD["SINOPSIS"].getValue()
	if reviews:
		reviewText = detailsMD[u"CRÍTICAS"].getValue()
		if reviewText is not None:
			metadata.summary = metadata.summary + reviewText
	#rating
	metadata.rating = float(string.replace(detailsMD[u"VALORACIÓN"].getValue(),",","."))
	#roles
	metadata.roles.clear()
	for person in detailsMD["REPARTO"].getValue():
		role = metadata.roles.new()
		role.actor = person

	#Posters, photos, ...
	himg = detailsMD["POSTER"].getValue()
	limg = detailsMD["LOWPOSTER"].getValue()
	imgs = detailsImg["IMAGENES"].getValue()
	p_order = 1
	f_orden = 1

	posters = []
	arts = []
	for i in range(len(POSTER_TYPES)):
		posters.append([])
	for i in range(len(ART_TYPES)):
		arts.append([])
	
	if himg is not None:
		imgs.insert(0,[limg,himg,"Poster / Imagen Principal",""])
	else:
		Log(SOURCE+"No main poster in FilmAffinity")
		
	if len(imgs) == 0:
		Log(SOURCE+"No images in FilmAffinity")

	hasPosters = False
	hasArt = False
	
	if (Prefs[PREF_IMGS]==PREF_IMGS_FA_ELSE_MDB) or (Prefs[PREF_IMGS]==PREF_IMGS_FA):
		for img in imgs:
			imgtype = img[2]
			imgcountry = img[3]
			imgtypecountry = None
			if imgtype not in POSTER_TYPES and imgtype not in ART_TYPES:
				imgtype = "default"
				
			if imgcountry is not None:
				imgtypecountry = imgtype+" "+imgcountry
	
			if (imgtypecountry is not None) and (imgtypecountry in POSTER_TYPES):
				hasPosters = True
				group = POSTER_TYPES[imgtypecountry]
				posters[group].append(img)
			elif (imgtypecountry is not None) and (imgtypecountry in ART_TYPES):
				group = ART_TYPES[imgtypecountry]
				arts[group].append(img)
			elif imgtype in POSTER_TYPES:
				hasPosters = True
				group = POSTER_TYPES[imgtype]
				posters[group].append(img)
			elif imgtype in ART_TYPES:
				group = ART_TYPES[imgtype]
				arts[group].append(img)
		hasArt = (len(arts[ART_TYPES[u"Wallpapers España"]]) + len(arts[ART_TYPES["Wallpapers"]])) > 0

	# Try ThemovieDB if FilmAffinity has no images
	if (Prefs[PREF_IMGS]==PREF_IMGS_FA_ELSE_MDB) or (Prefs[PREF_IMGS]==PREF_IMGS_MDB):
		try:
			getImagesFromTheMovieDB(metadata,hasPosters,hasArt,posters,arts)
		except Exception, e:
			Log(SOURCE+"Can't fetch images from TheMovieDB: "+str(e))
		
	
	#Insert posters in metadata
	i = 1
	valid_names = list()
	for group in posters:
		for img in group:
			imgsurl = img[0]
			imglurl = img[1]
			addPoster(metadata,imgsurl,imglurl,i,valid_names)
			i += 1
	if i==1:
		Log(SOURCE+"Ups!! I can't find a poster. Using low res poster from FilmAffinity")
		addPoster(metadata,limg,limg,1,valid_names)

	metadata.posters.validate_keys(valid_names)
	

	#Insert art in metadata
	i = 1
	valid_names = list()
	for group in arts:
		for img in group:
			imgsurl = img[0]
			imglurl = img[1]
			addArt(metadata,imgsurl,imglurl,i,valid_names)
			i += 1

	metadata.art.validate_keys(valid_names)

# I've got better information if I don't catch the exception
#	except Exception, e:
#		Log("[FilmAffinity Agent] : Exception "+str(e))
#		Log("[FilmAffinity Agent] : Error when updating with "+finalURL)

def isIn(urll,group):
	for img in group:
		if img[1]==urll:
			return True
	return False


def getImagesFromTheMovieDB(metadata,hasposter,hasart,posters,arts):
	proxy = Proxy.Preview
	if not hasposter or not hasart:
		imdbid = origTitleToImdb(metadata)
		if imdbid is not None:
			finalURL = TMDB_GETINFO_IMDB % imdbid
			tmdb_dict = JSON.ObjectFromURL(finalURL)[0]
			#Log(tmdb_dict)
			if not hasposter:
				Log(SOURCE+"FilmAffinity hasn't got posters, trying themoviedb")
				if 'posters' in tmdb_dict:
					thmdbposters = posters[POSTER_TYPES["Poster / Imagen Principal"]]
					for p in tmdb_dict['posters']:
						if p['image']['size'] == 'original':
							if not isIn(p['image']['url'],thmdbposters):
								p_id = p['image']['id']
								for t in tmdb_dict['posters']:
									if t['image']['id'] == p_id and t['image']['size'] == 'mid':
										thumb = t['image']['url']
										break
								try: 
									img = [thumb,p['image']['url'],"Poster / Imagen Principal",""]
									thmdbposters.append(img)
								except: pass
				else:
					Log(SOURCE+"themoviedb hasn't got posters")

			if not hasart:
				Log(SOURCE+"FilmAffinity hasn't got art, trying themoviedb")
				if 'backdrops' in tmdb_dict:
					thmdbart = arts[ART_TYPES["Wallpapers"]]
					for b in tmdb_dict['backdrops']:
						if b['image']['size'] == 'original':
							if not isIn(b['image']['url'],thmdbart):
								b_id = b['image']['id']
								for t in tmdb_dict['backdrops']:
									if t['image']['id'] == b_id and t['image']['size'] == 'poster':
										thumb = t['image']['url']
										break
								try: 
									img = [thumb,b['image']['url'],"Wallpapers",""]
									thmdbart.append(img)
								except: pass
				else:
					Log(SOURCE+"themoviedb hasn't got art")
		else:
			Log(SOURCE+"can't find IMDB ID")

def origTitleToImdb(metadata):
	origtitles = splitTitle(metadata.original_title)
	years = [metadata.year,metadata.year-1,metadata.year+1]
	for year in years:
		for origtitle in origtitles:
			origtitle = origtitle.strip()
			Log(SOURCE+"Searching IMDB ID for "+origtitle+" ("+str(year)+")")
			
			q = String.Quote('"' + origtitle.encode("utf-8") + ' (' + str(year) + ')"', usePlus=True) + "+site:imdb.com"
			
			currentIdx = 0
		
			for i in range(MAX_GOOGLE_PAGES):
				response = google(currentIdx,q)
				if response is None:
					return None
				results = response["responseData"]["results"]
				if len(results)>0:
					for result in response["responseData"]["results"]:
						m = re.match(r'http://www\.imdb\.com/title/tt([0-9]+)/',result["url"])
						if m is not None:
							imdbid = m.group(1)
							imdbtitle = result["titleNoFormatting"]
							Log(SOURCE+"IMDB result, title="+imdbtitle+" id="+imdbid)
							return imdbid
			
					cursor = response["responseData"]["cursor"]
				
					pages = cursor["pages"]
					currentIdx = cursor["currentPageIndex"]+1
					if currentIdx >= len(pages):
						#No more results
						break
					currentIdx = int(pages[currentIdx]["start"])
				else:
					break
	
	return None
	
def matchRatioLeven(uph1,uph2):
	uph1 = String.StripDiacritics(uph1).lower()
	uph2 = String.StripDiacritics(uph2).lower()
	m = max(len(uph1),len(uph2))
#	p = re.compile(r'\W+',flags=re.UNICODE)
#	words1 = p.split(uph1)
#	words2 = p.split(uph2)
#	s = difflib.SequenceMatcher(None,words1,words2)
#	return s.ratio()
	levenratio = 1-(float(Util.LevenshteinDistance(uph1,uph2))/float(m))
	return levenratio

def matchRatioLongest(uph1,uph2):
	uph1 = String.StripDiacritics(uph1).lower()
	uph2 = String.StripDiacritics(uph2).lower()
	longestCommonSubstring = len(Util.LongestCommonSubstring(uph1, uph2))
	longestratio = float(longestCommonSubstring) / len(uph1)
	return longestratio


MAPACUTE={u"a":u"á",u"e":u"é",u"i":u"í",u"o":u"ó",u"u":u"ú",u"A":u"Á",u"E":u"É",u"I":u"Í",u"O":u"Ó",u"U":u"Ú"}
MAPTILDE={"n":u"ñ","N":u"Ñ"}
 
def normalizeU(u):
	acuteChar=u"\u0301"
	tildeChar=u"\u0303"
	result = ""
	ignoreNext = False
	for i in reversed(range(len(u))):
		if not ignoreNext:
			if u[i] == acuteChar:
				if i>0 and u[i-1] in MAPACUTE:
					result = MAPACUTE[u[i-1]] + result
					ignoreNext = True
			elif u[i] == tildeChar:
				if i>0 and u[i-1] in MAPTILDE:
					result = MAPTILDE[u[i-1]] + result
					ignoreNext = True
			else:
				result = u[i] + result
		else:
			ignoreNext = False
	return result

def cleanFATitle(title):
	p = re.compile(r' \([0-9][0-9][0-9][0-9]\) \- FilmAffinity')
	return p.sub('', title)

def splitTitle(title):
	result = []
	p = re.compile(r'\(.*?\)')
	result.append(p.sub('', title))
	ts = p.findall(title)
	if ts is not None:
		for t in ts:
			result.append(t[1:-1])
	return result

def parseTitle(title):
	# Parse out title, year, and extra.
	titleRx = r'((.)*) \(([0-9][0-9][0-9][0-9])'
	m = re.match(titleRx, title)
	if m is not None:
		name = m.group(1)
		year = int(m.group(3))
		return (name, year)
		
	return (title, None)


def addPoster(metadata,surl,lurl,order,valid_names):
	try:
#		Log(surl + ": "+str(order))
		metadata.posters[lurl] = Proxy.Preview(HTTP.Request(surl, cacheTime=CACHE_1MONTH), sort_order = order)
		valid_names.append(lurl)
	except Exception, e:
		Log(SOURCE+"Exception "+str(e))
		Log(SOURCE+"Error when fetching poster image "+surl)

def addArt(metadata,surl,lurl,order,valid_names):
	try:
#		Log(surl + ": "+str(order))
		metadata.art[lurl] = Proxy.Preview(HTTP.Request(surl, cacheTime=CACHE_1MONTH), sort_order = order)
		valid_names.append(lurl)
	except Exception, e:
		Log(SOURCE+"Exception "+str(e))
		Log(SOURCE+"Error when fetching art "+surl)
		
def unescapeHTML(uvalue):
	html = u"<b>" + uvalue + u"</b>"
	un = HTML.ElementFromString(html)
	return un.text
#	def unescape(m):
#		escapeseq = m.group(0)
#		return unichr(int(escapeseq[2:-1]))
#	return re.sub(r'&#[0-9]+?;',unescape,uvalue)

def getTitleFromUrl(url):
	try:
		root = HTML.ElementFromURL(url)
		title = root.findtext(".//title")
		return title
	except Exception, e:
		Log(SOURCE+"Exception "+str(e))
		Log(SOURCE+"Can't extract title from "+url)
	return None


def translate(result,lang):
	title = getTitleFromUrl(FILMAFFINITY_DETAIL_URL % result.id)
	if title is not None:
		name, year = parseTitle(title)		
		if name is not None:
			result.name = name
			result.lang = lang
			return True
	return False
	
def trim(s): return s.strip()

def mapvalues(function,values):
	result = []
	for v in values:
		result.append(function(v))
	return result

def getPublicIP():
	try:
		ip = HTTP.Request('http://plexapp.com/ip.php').content.strip()
		return ip
	except Exception, e:
		Log(SOURCE+"Can't get public IP: "+str(e))
		return ""

def google(currentIdx,q):
	finalURL = GOOGLESEARCH_URL % (getPublicIP(),currentIdx,q)
	response = JSON.ObjectFromURL(finalURL,sleep=SLEEP_GOOGLE_REQUEST)
	if response["responseStatus"] != 200:
		Log(SOURCE+"Error in Google search: "+response["responseDetails"])
		return None
	return response
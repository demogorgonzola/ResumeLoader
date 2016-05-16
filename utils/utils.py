import copy

class JSONFormat:
	def __init__(self,format):
		self.__format = format

	def __constructUndefined(self,format):
		undefined = {}
		format_items = format.items() if isinstance(format,dict) else enumerate(format)
		for key,val in format_items:
			if isinstance(val,list) or isinstance(val,dict):
				inner_undefined = __constructUndefined(val)
				for entry in inner_undefined:
					if entry not in undefined:
						undefined[entry] = []
					undefined[entry].extend(inner_undefined[entry])
			elif isinstance(val,Undefined):
				if val not in undefined:
					undefined[val] = []
				undefined[val].append((format,key))
		return undefined

	def spawnInstance(self,variables):
		return self.__recursiveDictCopy(self.__format,variables)

	def __recursiveDictCopy(self,dictionary,variables):
		ret_dict = {} if isinstance(dictionary,dict) else [None] * len(dictionary)

		dict_items = dictionary.items() if isinstance(dictionary,dict) else enumerate(dictionary)
		for key,val in dict_items:
			if isinstance(val,Undefined):
				if val.var_name in variables:
					val = variables[val.var_name]
				else:
					print('ERROR: JSONFormat: Undefined Variable.')
					raise
			elif isinstance(val,dict) or isinstance(val,list):
				val = self.__recursiveDictCopy(val,variables)
			ret_dict[key] = val

		return ret_dict


class Undefined:
	def __init__(self,var_name=None):
		self.var_name = var_name
	def __eq__(self,another):
		return self.var_name == another.var_name
	def __hash__(self):
		return hash(self.var_name)


class HashableDict(dict):
	def __hash__(self):
		return hash(frozenset(self))#hash(tuple(sorted(self.items())))



def IterJSON(json):
	if not isinstance(json,dict):
		print 'ERROR: IterJSON: Not a dictionary.'
		raise
	def __recurseJSON(json):
		jsonitems = json.items if isinstance(json,dict) else enumerate(json)
		for key,val in jsonitems:
			if isinstance(val,dict) or isinstance(val,list):
				recurseJSON(val)
			else:
				yield (json,key,val)
	for step in __recurseJSON(json):
		yield step
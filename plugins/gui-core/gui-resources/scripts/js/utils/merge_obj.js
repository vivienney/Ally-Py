define(function(){	function mapper(obj1,obj2, options){		if ((options!==undefined) && ( options.keys!==undefined)) {			for (var key in options.keys) { 				var val = options.keys[key];				if(isNaN(key)) {					obj1[key] = obj2[val];					}else {					obj1[val] = obj2[val];					}			}				}		for (var key in obj2) { 			obj1[key] = obj2[key];			}				}	return mapper;});
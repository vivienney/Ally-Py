define(function(){    return {        encode: function(s) {            return encodeURIComponent(s);        },        decode: function(s) {            return decodeURIComponent(s);        }    }});
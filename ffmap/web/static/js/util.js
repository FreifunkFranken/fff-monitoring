
function int2mac(input) {
	return ("000000000000" + parseInt(input).toString(16)).substr(-12) // make HEX and add leading zeros
			.match( /.{1,2}/g )		// ["4a", "89", "26", "c4", "45", "78"]
			.join( ':' )			// "78:45:c4:26:89:4a"
}

function shortmac2mac(input) {
	return input.match( /.{1,2}/g )		// ["4a", "89", "26", "c4", "45", "78"]
			.join( ':' )			// "78:45:c4:26:89:4a"
}

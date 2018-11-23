var map = L.map('map');

var tilesosmorg = new L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
	attribution: '<a href="https://www.openstreetmap.org/copyright">&copy; Openstreetmap Contributors</a>',
	maxNativeZoom: 19,
	maxZoom: 22
});
map.addLayer(tilesosmorg);
var tilesosmde = new L.TileLayer('https://{s}.osm.rrze.fau.de/osmde/{z}/{x}/{y}.png', {
	attribution: '<a href="https://www.openstreetmap.org/copyright">&copy; Openstreetmap Contributors</a>',
	maxNativeZoom: 19,
	maxZoom: 22
});
var tilestfod = new L.TileLayer('https://{s}.tile.thunderforest.com/outdoors/{z}/{x}/{y}.png', {
	attribution: 'Maps &copy; <a href="http://www.thunderforest.com">Thunderforest</a>, Data &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
	maxNativeZoom: 22,
	maxZoom: 22
});

L.control.scale({imperial: false}).addTo(map);

var overlay_config = {
	maxNativeZoom: 22,
	maxZoom: 22,
	attribution: "",
	maximumAge: 1000*3600*24*10
}

var routers = new L.TileLayer(tileurls.routers + '/{z}/{x}/{y}.png', overlay_config);
var routers_v2 = new L.TileLayer(tileurls.routers_v2 + '/{z}/{x}/{y}.png', overlay_config);
var routers_local = new L.TileLayer(tileurls.routers_local + '/{z}/{x}/{y}.png', overlay_config);
var hoods = new L.TileLayer(tileurls.hoods + '/{z}/{x}/{y}.png', overlay_config);
var hoods_v2 = new L.TileLayer(tileurls.hoods_v2 + '/{z}/{x}/{y}.png', overlay_config);
var popuplayer = new L.TileLayer('');
layersControl = new L.Control.Layers({
	"openstreetmap.org": tilesosmorg,
	"openstreetmap.de": tilesosmde,
	"Thunderforest Outdoors": tilestfod
}, {
	"Routers V1": routers,
	"Routers V2": routers_v2,
	"Local Routers": routers_local,
	"Hoods V1": hoods,
	"Hoods V2": hoods_v2,
	"Position-Popup": popuplayer
});
map.addControl(layersControl);

var router_pointer_radius = 7.5; // actually 7 but let's add some rounding tolerance

if (window.matchMedia("(min--moz-device-pixel-ratio: 1.5),(-o-min-device-pixel-ratio: 3/2),(-webkit-min-device-pixel-ratio: 1.5),(min-device-pixel-ratio: 1.5),(min-resolution: 1.5dppx)").matches) {
	// Retina 2k Display: Make it easier to hit the pointer
	router_pointer_radius *= 2;
}

var popup;
var popupopen = false;

function update_permalink() {
	if (typeof mapurl != 'undefined') {
		var pos = map.getCenter();
		var zoom = map.getZoom();
		window.history.replaceState({}, document.title,
			mapurl + '?mapcenter=' + pos.lat.toFixed(5) + ',' + pos.lng.toFixed(5) + ',' + zoom
			+ '&layers=' + (map.hasLayer(routers)|0) + ',' + (map.hasLayer(routers_v2)|0) + ',' + (map.hasLayer(routers_local)|0) + ','
			+ (map.hasLayer(hoods)|0) + ',' + (map.hasLayer(hoods_v2)|0) + ',' + (map.hasLayer(popuplayer)|0) );
	}
}

function initialLayers() {
	routers.addTo(map);
	routers_v2.addTo(map);
	routers_local.addTo(map);
}

map.on('moveend', update_permalink);
map.on('zoomend', update_permalink);
map.on('overlayadd', update_permalink);
map.on('overlayremove', update_permalink);

map.on('click', function(pos) {
	// height = width of world in px
	var size_of_world_in_px = map.options.crs.scale(map.getZoom());
	
	layeropt = ""
	if (map.hasLayer(routers)) {
		console.debug("Looking for router in V1 ...");
		layeropt += "&v1=on"
	}
	if (map.hasLayer(routers_v2)) {
		console.debug("Looking for router in V2 ...");
		layeropt += "&v2=on"
	}
	if (map.hasLayer(routers_local)) {
		console.debug("Looking for router in local hoods ...");
		layeropt += "&local=on"
	}

	var px_per_deg_lng = size_of_world_in_px / 360;
	var px_per_deg_lat = size_of_world_in_px / 180;

	// normalize longitude (user can shift map west/east and leave the [-180..180] range
	var lng = mod(pos.latlng.lng, 360);
	var lat = pos.latlng.lat;
	if (lng > 180) { lng -= 360; }

	ajax_get_request(url_get_nearest_router + "?lng=" + lng + "&lat=" + lat + layeropt, function(router) {
		if (router) {
			// decide if router is close enough
			var lng_delta = Math.abs(lng - router.lng)
			var lat_delta = Math.abs(lat - router.lat)

			// convert degree distances into px distances on the map
			var x_delta_px = lng_delta * px_per_deg_lng;
			var y_delta_px = lat_delta * px_per_deg_lat;

			// use pythagoras to calculate distance
			var px_distance = Math.sqrt(x_delta_px*x_delta_px + y_delta_px*y_delta_px);

			console.debug("Distance to closest router ("+router.hostname+"): " + px_distance+"px");
		}

		// check if mouse click was on the router icon
		if (router && px_distance <= router_pointer_radius) {
			popupopen = true;
			console.log("Click on '"+router.hostname+"' detected.");
			console.log(router);
			var popup_html = "";
			var has_neighbours = 'neighbours' in router && router.neighbours.length > 0;

			// avoid empty tables
			if (has_neighbours) {
				has_neighbours = false;
				for (var i = 0; i < router.neighbours.length; i++) {
					neighbour = router.neighbours[i];
					if ('id' in neighbour) {
						has_neighbours = true;
					}
				}
			}

			if (has_neighbours) {
				console.log("Has "+router.neighbours.length+" neighbours.");
				popup_html += "<div class=\"popup-headline with-neighbours\">";
			}
			else {
				console.log("Has no neighbours.");
				popup_html += "<div class=\"popup-headline\">";
			}
			popup_html += '<b>Router <a href="' + url_router_info + router.id +'">'+router.hostname+'</a></b>';
			popup_html += "</div>"
			if (has_neighbours) {
				popup_html += '<table class="neighbours" style="width: 100%;">';
				popup_html += "<tr>";
				popup_html += "<th>Link</th>";
				popup_html += "<th>Quality</th>";
				popup_html += "<th>Interface</th>";
				popup_html += "</tr>";
				for (var i = 0; i < router.neighbours.length; i++) {
					neighbour = router.neighbours[i];
					// skip unknown neighbours
					if ('id' in neighbour) {
						popup_html += "<tr style=\"background-color: "+neighbour.color+";\">";
						popup_html += '<td><a href="'+url_router_info+neighbour.id+'" title="'+escapeHTML(neighbour.mac)+'" style="color:#000000">'+escapeHTML(neighbour.hostname)+'</a></td>'; // MACTODO
						popup_html += "<td>"+neighbour.quality+"</td>";
						popup_html += "<td>"+escapeHTML(neighbour.netif)+"</td>";
						popup_html += "</tr>";
					}
				}
				popup_html += "</table>";
			}
			popup = L.popup({offset: new L.Point(1, 1), maxWidth: 500})
				.setLatLng([router.lat, router.lng])
				.setContent(popup_html)
				.openOn(map);
		} else if(popupopen) {
			popupopen = false;
		} else if(map.hasLayer(popuplayer)) {
			popupopen = true;
			console.log("Click on lat: "+lat+", lng: "+lng+" detected.");
			var popup_html = "<div class=\"popup-headline\">";
			
			popup_html += '<b>Coordinates</b>';
			popup_html += '<p class="popup-latlng" style="margin:0">Latitude: '+lat.toFixed(8)+'</p>';
			popup_html += '<p class="popup-latlng" style="margin:0">Longitude: '+lng.toFixed(8)+'</p>';
			popup_html += "</div>"
			popup = L.popup({offset: new L.Point(1, 1), maxWidth: 500})
				.setLatLng([lat, lng])
				.setContent(popup_html)
				.openOn(map);
		}
	});
});

function ajax_get_request(url, callback_fkt) {
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
		if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
			var response_data = JSON.parse(xmlhttp.responseText);
			callback_fkt(response_data);
		}
	}
	xmlhttp.open("GET", url, true);
	xmlhttp.send();
}

function mod(n, m) {
	// use own modulo function (see http://stackoverflow.com/q/4467539)
	return ((n % m) + m) % m;
}

var entityMap = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	'"': '&quot;',
	"'": '&#39;',
	"/": '&#x2F;'
};

function escapeHTML(string) {
	return String(string).replace(/[&<>"'\/]/g, function (s) {
		return entityMap[s];
	});
}

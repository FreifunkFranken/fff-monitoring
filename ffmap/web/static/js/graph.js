var points_per_px = 0.3;
var controls_container = "<div style='right:60px;top:13px;position:absolute;display:none;' id='controls'></div>";
var reset_button = "<div class='btn btn-default btn-xs'>Reset</div>";

function labelFormatter(label, series) {
	var append_dots = (label.length > 18);
	label = label.substr(0, 17);
	if (append_dots) {
		label += "&hellip;";
	}
	return "<div style='font-size:8pt; text-align:center; padding:2px; color:white;'>" + label + "<br/>" + Math.round(series.percent) + "%</div>";
}

function legendFormatter(label, series) {
	var append_dots = (label.length > 28);
	label = label.substr(0, 27);
	if (append_dots) {
		label += "&hellip;";
	}
	return label;
}


function setup_plot_zoom(plot, pdata, num_data_points) {
	plot.getPlaceholder().bind("plotselected", function (event, ranges) {
		$.each(plot.getXAxes(), function(_, axis) {
			var zoom_correction_factor = (1000*300*num_data_points)/(ranges.xaxis.to - ranges.xaxis.from);
			plot.getOptions().series.downsample.threshold =
				Math.floor(plot.getPlaceholder().width()
				* points_per_px
				* zoom_correction_factor);
			axis.options.min = ranges.xaxis.from;
			axis.options.max = ranges.xaxis.to;
		});
		plot.setData(pdata);
		plot.setupGrid();
		plot.draw();
		plot.clearSelection();
		plot.getPlaceholder().children("#controls")
			.css("top", (plot.getPlotOffset().top+5) + "px")
			.css("left", (plot.getPlotOffset().left+5) + "px")
			.css("display", "block");
	});
	var plot_controls = $(controls_container).appendTo(plot.getPlaceholder());
	$(reset_button)
		.appendTo(plot_controls)
		.click(function (event) {
			event.preventDefault();
			$.each(plot.getXAxes(), function(_, axis) {
				axis.options.min = null;
				axis.options.max = null;
			});
			plot.getOptions().series.downsample.threshold = Math.floor(plot.getPlaceholder().width() * points_per_px);
			plot.setData(pdata);
			plot.setupGrid();
			plot.draw();
			plot.getPlaceholder().children("#controls")
				.css("top", (plot.getPlotOffset().top+5) + "px")
				.css("left", (plot.getPlotOffset().left+5) + "px")
				.css("display", "none");
		});
	plot.getPlaceholder().children("#controls")
		.css("top", (plot.getPlotOffset().top+5) + "px")
		.css("left", (plot.getPlotOffset().left+5) + "px");
}

// Per router statistics

function network_graph(netif) {
	var netstat = $("#netstat");
	var tx = [], rx = [];
	var len, i;
	for (len=netif_stats.length, i=0; i<len; i++) {
		if (netif_stats[i].netif != netif) { continue; }
		try {
			var tx_value = netif_stats[i].tx;
			var rx_value = netif_stats[i].rx;
			var date_value = netif_stats[i].time.$date;
			if(tx_value != null && rx_value != null) {
				tx.push([date_value, tx_value * 8]);
				rx.push([date_value, rx_value * 8]);
			}
		}
		catch(TypeError) {
			// pass
		}
	}
	var pdata = [
		{"label": "tx", "data": tx, "color": "#CB4B4B"},
		{"label": "rx", "data": rx, "color": "#8CACC6"}
	]
	var plot = $.plot(netstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0, mode: "bitRate"},
		legend: {noColumns: 2, hideable: true},
		series: {downsample: {threshold: Math.floor(netstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function neighbour_graph(neighbours) {
	var meshstat = $("#meshstat");
	var pdata = [];
	for (j=0; j<neighbours.length; j++) {
		var label = neighbours[j].name;

		// add network interface when there are multiple links to same node
		var k;
		for(k=0; k<neighbours.length; k++) {
			if(label == neighbours[k].name && k != j) {
				label += "@" + neighbours[j].netif;
			}
		}

		var mac = neighbours[j].mac;
		var data = [];
		var len, i;
		for (len=neigh_stats.length, i=0; i<len; i++) {
			if (neigh_stats[i].mac != mac) { continue; }
			try {
				var quality = neigh_stats[i].quality;
				var date_value = neigh_stats[i].time.$date;
				if(quality == null) {
					quality = 0;
				}
				data.push([date_value, Math.abs(quality)]);
			}
			catch(TypeError) {
				// pass
			}
		}
		pdata.push({"label": label, "data": data});
	}
	var plot = $.plot(meshstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0, autoscaleMargin: 0.5},
		legend: {noColumns: 2, hideable: true},
		series: {downsample: {threshold: Math.floor(meshstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function gw_graph(gws) {
	var gwstat = $("#gwstat");
	var pdata = [];
	for (j=0; j<gws.length; j++) {
		var label = gws[j].name;

		// add network interface when there are multiple links to same node
		var k;
		for(k=0; k<gws.length; k++) {
			if(label == gws[k].name && k != j) {
				label += "@" + gws[j].netif;
			}
		}

		var mac = gws[j].mac;
		var data = [];
		var len, i;
		for (len=gw_stats.length, i=0; i<len; i++) {
			if (gw_stats[i].mac != mac) { continue; }
			try {
				var quality = gw_stats[i].quality;
				var date_value = gw_stats[i].time.$date;
				if(quality == null) {
					quality = 0;
				}
				data.push([date_value, quality]);
			}
			catch(TypeError) {
				// pass
			}
		}
		pdata.push({"label": label, "data": data});
	}
	var plot = $.plot(gwstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0, max: 350},
		legend: {noColumns: 2, hideable: true},
		series: {downsample: {threshold: Math.floor(gwstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function memory_graph() {
	var memstat = $("#memstat");
	var free = [], caching = [], buffering = [];
	var len, i;
	for (len=router_stats.length, i=0; i<len; i++) {
		try {
			var free_value = router_stats[i].sys_memfree*1024;
			var caching_value = router_stats[i].sys_memcache*1024;
			var buffering_value = router_stats[i].sys_membuff*1024;
			var date_value = router_stats[i].time.$date;
			if(free_value != null && caching_value != null && buffering_value != null) {
				free.push([date_value, free_value]);
				caching.push([date_value, caching_value]);
				buffering.push([date_value, buffering_value]);
			}
		}
		catch(TypeError) {
			// pass
		}
	}
	var pdata = [
		{"label": "free", "data": free, "color": "#4DA74A"},
		{"label": "caching", "data": caching, "color": "#EDC240"},
		{"label": "buffering", "data": buffering, "color": "#8CACC6"}
	];
	var plot = $.plot(memstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0, mode: "byte", autoscaleMargin: 0.1},
		legend: {noColumns: 3, hideable: true},
		series: {downsample: {threshold: Math.floor(memstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function process_graph() {
	var procstat = $("#procstat");
	var runnable = [], total = [];
		var len, i;
		for (len=router_stats.length, i=0; i<len; i++) {
			try {
				var runnable_value = router_stats[i].sys_procrun;
				var total_value = router_stats[i].sys_proctot;
				var date_value = router_stats[i].time.$date;
				if(runnable_value != null && total_value != null) {
					runnable.push([date_value, runnable_value]);
					total.push([date_value, total_value]);
				}
			}
			catch(TypeError) {
				// pass
			}
		}
	var pdata = [
		{"label": "runnable", "data": runnable, "color": "#CB4B4B"},
		{"label": "total", "data": total, "color": "#EDC240"},
	];
	var plot = $.plot(procstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0, autoscaleMargin: 0.1},
		legend: {noColumns: 2, hideable: true},
		series: {downsample: {threshold: Math.floor(procstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function client_graph() {
	var clientstat = $("#clientstat");
	var clients = [], clients_eth = [], clients_w2 = [], clients_w5 = [];
	var len, i;
	for (len=router_stats.length, i=0; i<len; i++) {
		try {
			var client_value = router_stats[i].clients;
			var client_eth = router_stats[i].clients_eth;
			var client_w2 = router_stats[i].clients_w2;
			var client_w5 = router_stats[i].clients_w5;
			var date_value = router_stats[i].time.$date;
			if(client_value != null) {
				clients.push([date_value, client_value]);
			}
			if(client_eth != null) {
				clients_eth.push([date_value, client_eth]);
			}
			if(client_w2 != null) {
				clients_w2.push([date_value, client_w2]);
			}
			if(client_w5 != null) {
				clients_w5.push([date_value, client_w5]);
			}
		}
		catch(TypeError) {
			// pass
		}
	}
	var pdata = [];
	if (clients_w2.length > 0) {
		pdata.push(
			{"label": "2.4 GHz", "data": clients_w2, "color": "#CB4B4B"}
		);
	}
	if (clients_w5.length > 0) {
		pdata.push(
			{"label": "5 GHz", "data": clients_w5, "color": "#EDC240"}
		);
	}
	if (clients_eth.length > 0) {
		pdata.push(
			{"label": "Ethernet", "data": clients_eth, "color": "#4DA74A"}
		);
	}
	pdata.push(
		{"label": "Total", "data": clients, "color": "#8CACC6"}
	);
	
	var plot = $.plot(clientstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0},
		legend: {noColumns: 4, hideable: true},
		series: {downsample: {threshold: Math.floor(clientstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function loadavg_graph() {
	var loadstat = $("#loadstat");
	var loadavg = [];
	var len, i;
	for (len=router_stats.length, i=0; i<len; i++) {
		try {
			var load_value = router_stats[i].loadavg;
			var date_value = router_stats[i].time.$date;
			if(load_value != null) {
				loadavg.push([date_value, load_value]);
			}
		}
		catch(TypeError) {
			// pass
		}
	}
	var pdata = [
		{"label": "loadavg", "data": loadavg, "color": "#FF2626", lines: {fill: true}}
	];
	var plot = $.plot(loadstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0},
		legend: {hideable: true},
		series: {downsample: {threshold: Math.floor(loadstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function airtime_graph() {
	var airstat = $("#airstat");
	var airtime2 = [];
	var airtime5 = [];
	var len, i;
	for (len=router_stats.length, i=0; i<len; i++) {
		try {
			var air2_value = router_stats[i].airtime_w2;
			var air5_value = router_stats[i].airtime_w5;
			var date_value = router_stats[i].time.$date;
			if(air2_value != null) {
				airtime2.push([date_value, air2_value * 100]);
			}
			if(air5_value != null) {
				airtime5.push([date_value, air5_value * 100]);
			}
		}
		catch(TypeError) {
			// pass
		}
	}
	var pdata = [
		{"label": "Airtime 2.4 GHz / %", "data": airtime2, "color": "#CB4B4B"}
	];
	if (airtime5.length > 0) {
		pdata.push(
			{"label": "Airtime 5 GHz / %", "data": airtime5, "color": "#EDC240"}
		);
	}
	var plot = $.plot(airstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0, max: 100},
		legend: {noColumns: 2, hideable: true},
		series: {downsample: {threshold: Math.floor(airstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}


// Global statistics

function global_client_graph() {
	var clientstat = $("#globclientstat");
	var clients = [];
	var len, i;
	for (len=global_stats.length, i=0; i<len; i++) {
		try {
			var client_value = global_stats[i].clients;
			var date_value = global_stats[i].time.$date;
			if(client_value != null) {
				clients.push([date_value, client_value]);
			}
		}
		catch(TypeError) {
			// pass
		}
	}
	var pdata = [
		{"label": "clients", "data": clients, "color": "#8CACC6", lines: {fill: true}}
	];
	var plot = $.plot(clientstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0, autoscaleMargin: 0.1},
		legend: {hideable: true},
		//points: {show: true}
		series: {downsample: {threshold: Math.floor(clientstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function global_router_graph() {
	var memstat = $("#globrouterstat");
	var offline = [], online = [], unknown = [], orphaned = [], total = [];
	var len, i;
	for (len=global_stats.length, i=0; i<len; i++) {
		try {
			var offline_value = global_stats[i].offline;
			var online_value = global_stats[i].online;
			var unknown_value = global_stats[i].unknown;
			var orphaned_value = global_stats[i].orphaned;
			var date_value = global_stats[i].time.$date;
			if (offline_value == null) offline_value = 0;
			if (online_value == null) online_value = 0;
			if (unknown_value == null) unknown_value = 0;
			if (orphaned_value == null) orphaned_value = 0;
			offline.push([date_value, offline_value]);
			online.push([date_value, online_value]);
			unknown.push([date_value, unknown_value]);
			orphaned.push([date_value, orphaned_value]);
			total.push([date_value, offline_value + online_value + unknown_value + orphaned_value]);
		}
		catch(TypeError) {
			// pass
		}
	}
	var pdata = [
		{"label": "total", "data": total, "color": "#006DD9"},
		{"label": "online", "data": online, "color": "#4DA74A"},
		{"label": "offline", "data": offline, "color": "#CB4B4B"},
		{"label": "unknown", "data": unknown, "color": "#EDC240"},
		{"label": "orphaned", "data": orphaned, "color": "#666666"}
	];
	var plot = $.plot(memstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0, autoscaleMargin: 0.15},
		legend: {noColumns: 5, hideable: true},
		series: {downsample: {threshold: Math.floor(memstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function global_router_firmwares_graph() {
	var placeholder = $("#globrouterfwstat");
	var pdata = [];
	for (var fwname in router_firmwares) {
		pdata.push({
			"label": fwname,
			"data": [router_firmwares[fwname]]
		});
	}
	var plot = $.plot(placeholder, pdata, {
		legend: {noColumns: 1, show: true, "labelFormatter": legendFormatter},
		grid: {hoverable: true, clickable: true},
		tooltip: {show: true, content: "<b>%s</b>: %p.1%", shifts: {x: 15, y: 5}, defaultTheme: true},
		series: {pie: {
			show: true, radius: 99/100, label: {show: true, formatter: labelFormatter, radius: 0.5, threshold: 0.10},
			combine: {threshold: 0.005}
		}}
	});
	placeholder.bind("plotclick", function(event, pos, obj) {
		if (obj && obj.series.label != "Other") {
			window.location.href = routers_page_url + encodeURI("?q=firmware:^" + obj.series.label + "$ " + hoodstr);
		}
	});
}

function global_router_models_graph() {
	var placeholder = $("#globroutermodelsstat");
	var pdata = [];
	for (var mdname in router_models) {
		pdata.push({
			"label": mdname,
			"data": [router_models[mdname]]
		});
	}
	var plot = $.plot(placeholder, pdata, {
		legend: {noColumns: 1, show: true, "labelFormatter": legendFormatter},
		grid: {hoverable: true, clickable: true},
		tooltip: {show: true, content: "<b>%s</b>: %p.1%", shifts: {x: 15, y: 5}, defaultTheme: true},
		series: {pie: {
			show: true, radius: 99/100, label: {show: true, formatter: labelFormatter, radius: 0.5, threshold: 0.2},
			combine: {threshold: 0.019}
		}}
	});
	placeholder.bind("plotclick", function(event, pos, obj) {
		if (obj && obj.series.label != "Other") {
			window.location.href = routers_page_url + encodeURI("?q=hardware:^" + obj.series.label.replace(/ /g, '_') + "$ " + hoodstr);
		}
	});
}

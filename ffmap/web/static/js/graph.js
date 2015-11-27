var points_per_px = 0.3;
var controls_container = "<div style='right:60px;top:13px;position:absolute;display:none;' id='controls'></div>";
var reset_button = "<div class='btn btn-default btn-xs'>Reset</div>";
timezoneJS.timezone.zoneFileBasePath = '/static/tz';


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
	for (len=router_stats.length, i=0; i<len; i++) {
		try {
			var tx_value = router_stats[i].netifs[netif].tx;
			var rx_value = router_stats[i].netifs[netif].rx;
			var date_value = router_stats[i].time.$date;
			if(tx_value != null && rx_value != null) {
				tx.push([date_value, tx_value]);
				rx.push([date_value, rx_value]);
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
		yaxis: {min: 0, mode: "byteRate"},
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
				label += "@" + neighbours[j].net_if;
			}
		}

		var mac = neighbours[j].mac;
		var data = [];
		var len, i;
		for (len=router_stats.length, i=0; i<len; i++) {
			try {
				var quality = router_stats[i].neighbours[mac];
				var date_value = router_stats[i].time.$date;
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
	var plot = $.plot(meshstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0, max: 400},
		legend: {noColumns: 2, hideable: true},
		series: {downsample: {threshold: Math.floor(meshstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function memory_graph() {
	var memstat = $("#memstat");
	var free = [], caching = [], buffering = [];
	var len, i;
	for (len=router_stats.length, i=0; i<len; i++) {
		try {
			var free_value = router_stats[i].memory.free*1024;
			var caching_value = router_stats[i].memory.caching*1024;
			var buffering_value = router_stats[i].memory.buffering*1024;
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
		yaxis: {min: 0, mode: "byte"},
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
				var runnable_value = router_stats[i].processes.runnable;
				var total_value = router_stats[i].processes.total;
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
		yaxis: {min: 0, max: 50},
		legend: {noColumns: 2, hideable: true},
		series: {downsample: {threshold: Math.floor(procstat.width() * points_per_px)}}
	});
	setup_plot_zoom(plot, pdata, len);
}

function client_graph() {
	var clientstat = $("#clientstat");
	var clients = [];
	var len, i;
	for (len=router_stats.length, i=0; i<len; i++) {
		try {
			var client_value = router_stats[i].clients;
			var date_value = router_stats[i].time.$date;
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
		yaxis: {min: 0},
		legend: {hideable: true},
		series: {downsample: {threshold: Math.floor(clientstat.width() * points_per_px)}}
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
			var client_value = global_stats[i].total_clients;
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
	var offline = [], online = [], unknown = [];
	var len, i;
	for (len=global_stats.length, i=0; i<len; i++) {
		try {
			var offline_value = global_stats[i].router_status.offline;
			var online_value = global_stats[i].router_status.online;
			var unknown_value = global_stats[i].router_status.unknown;
			var date_value = global_stats[i].time.$date;
			if (offline_value == null) offline_value = 0;
			if (online_value == null) online_value = 0;
			if (unknown_value == null) unknown_value = 0;
			offline.push([date_value, offline_value]);
			online.push([date_value, online_value]);
			unknown.push([date_value, unknown_value]);
		}
		catch(TypeError) {
			// pass
		}
	}
	var pdata = [
		{"label": "online", "data": online, "color": "#4DA74A"},
		{"label": "offline", "data": offline, "color": "#CB4B4B"},
		{"label": "unknown", "data": unknown, "color": "#EDC240"}
	];
	var plot = $.plot(memstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0, autoscaleMargin: 0.1},
		legend: {noColumns: 3, hideable: true},
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
		tooltip: {show: true, content: "<b>%s</b>: %p.0%", shifts: {x: 15, y: 5}, defaultTheme: true},
		series: {pie: {show: true, radius: 99/100, label: {show: true, formatter: labelFormatter, radius: 0.5, threshold: 0.10}}}
	});
	placeholder.bind("plotclick", function(event, pos, obj) {
		if (obj) {
			window.location.href = routers_page_url + "?q=software.firmware:" + obj.series.label;
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
		tooltip: {show: true, content: "<b>%s</b>: %p.0%", shifts: {x: 15, y: 5}, defaultTheme: true},
		series: {pie: {show: true, radius: 99/100, label: {show: true, formatter: labelFormatter, radius: 0.5, threshold: 0.2}}}
	});
	placeholder.bind("plotclick", function(event, pos, obj) {
		if (obj) {
			window.location.href = routers_page_url + "?q=hardware.name:" + obj.series.label.replace(/ /g, '_');
		}
	});
}

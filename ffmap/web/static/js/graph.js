var points_per_px = 0.3;

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
		legend: {noColumns: 2},
		series: {downsample: {threshold: Math.floor(netstat.width() * points_per_px)}}
	});
	netstat.bind("plotselected", function (event, ranges) {
		$.each(plot.getXAxes(), function(_, axis) {
			var zoom_correction_factor = (1000*300*len)/(ranges.xaxis.to - ranges.xaxis.from);
			plot.getOptions().series.downsample.threshold = Math.floor(netstat.width() * points_per_px * zoom_correction_factor);
			axis.options.min = ranges.xaxis.from;
			axis.options.max = ranges.xaxis.to;
		});
		plot.setData(pdata);
		plot.setupGrid();
		plot.draw();
		plot.clearSelection();
		netstat.children("#controls")
			.css("top", (plot.getPlotOffset().top+5) + "px")
			.css("left", (plot.getPlotOffset().left+5) + "px")
			.css("display", "block");
	});
	var netstat_controls = $("<div style='right:60px;top:13px;position:absolute;display:none;' id='controls'></div>").appendTo(netstat);
	$("<div class='btn btn-default btn-xs'>Reset</div>")
		.appendTo(netstat_controls)
		.click(function (event) {
			event.preventDefault();
			console.log("button");
			$.each(plot.getXAxes(), function(_, axis) {
				axis.options.min = null;
				axis.options.max = null;
			});
			plot.getOptions().series.downsample.threshold = Math.floor(netstat.width() * points_per_px);
			plot.setData(pdata);
			plot.setupGrid();
			plot.draw();
			netstat.children("#controls")
				.css("top", (plot.getPlotOffset().top+5) + "px")
				.css("left", (plot.getPlotOffset().left+5) + "px")
				.css("display", "none");
		});
	netstat.children("#controls")
		.css("top", (plot.getPlotOffset().top+5) + "px")
		.css("left", (plot.getPlotOffset().left+5) + "px");
}

function neighbour_graph(neighbours) {
	var meshstat = $("#meshstat");
	var pdata = [];
	for (j=0; j<neighbours.length; j++) {
		var label = neighbours[j].name;
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
		legend: {noColumns: 2},
		series: {downsample: {threshold: Math.floor(meshstat.width() * points_per_px)}}
	});
	meshstat.bind("plotselected", function (event, ranges) {
		$.each(plot.getXAxes(), function(_, axis) {
			var zoom_correction_factor = (1000*300*len)/(ranges.xaxis.to - ranges.xaxis.from);
			plot.getOptions().series.downsample.threshold = Math.floor(meshstat.width() * points_per_px * zoom_correction_factor);
			axis.options.min = ranges.xaxis.from;
			axis.options.max = ranges.xaxis.to;
		});
		plot.setData(pdata);
		plot.setupGrid();
		plot.draw();
		plot.clearSelection();
		meshstat.children("#controls")
			.css("top", (plot.getPlotOffset().top+5) + "px")
			.css("left", (plot.getPlotOffset().left+5) + "px")
			.css("display", "block");
	});
	var meshstat_controls = $("<div style='right:60px;top:13px;position:absolute;display:none;' id='controls'></div>").appendTo(meshstat);
	$("<div class='btn btn-default btn-xs'>Reset</div>")
		.appendTo(meshstat_controls)
		.click(function (event) {
			event.preventDefault();
			console.log("button");
			$.each(plot.getXAxes(), function(_, axis) {
				axis.options.min = null;
				axis.options.max = null;
			});
			plot.getOptions().series.downsample.threshold = Math.floor(meshstat.width() * points_per_px);
			plot.setData(pdata);
			plot.setupGrid();
			plot.draw();
			meshstat.children("#controls")
				.css("top", (plot.getPlotOffset().top+5) + "px")
				.css("left", (plot.getPlotOffset().left+5) + "px")
				.css("display", "none");
		});
	meshstat.children("#controls")
		.css("top", (plot.getPlotOffset().top+5) + "px")
		.css("left", (plot.getPlotOffset().left+5) + "px");
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
		legend: {noColumns: 3},
		series: {downsample: {threshold: Math.floor(memstat.width() * points_per_px)}}
	});
	memstat.bind("plotselected", function (event, ranges) {
		$.each(plot.getXAxes(), function(_, axis) {
			var zoom_correction_factor = (1000*300*len)/(ranges.xaxis.to - ranges.xaxis.from);
			plot.getOptions().series.downsample.threshold = Math.floor(memstat.width() * points_per_px * zoom_correction_factor);
			axis.options.min = ranges.xaxis.from;
			axis.options.max = ranges.xaxis.to;
		});
		plot.setData(pdata);
		plot.setupGrid();
		plot.draw();
		plot.clearSelection();
		memstat.children("#controls")
			.css("top", (plot.getPlotOffset().top+5) + "px")
			.css("left", (plot.getPlotOffset().left+5) + "px")
			.css("display", "block");
	});
	var memstat_controls = $("<div style='right:60px;top:13px;position:absolute;display:none;' id='controls'></div>").appendTo(memstat);
	$("<div class='btn btn-default btn-xs'>Reset</div>")
		.appendTo(memstat_controls)
		.click(function (event) {
			event.preventDefault();
			console.log("button");
			$.each(plot.getXAxes(), function(_, axis) {
				axis.options.min = null;
				axis.options.max = null;
			});
			plot.getOptions().series.downsample.threshold = Math.floor(memstat.width() * points_per_px);
			plot.setData(pdata);
			plot.setupGrid();
			plot.draw();
			memstat.children("#controls")
				.css("top", (plot.getPlotOffset().top+5) + "px")
				.css("left", (plot.getPlotOffset().left+5) + "px")
				.css("display", "none");
		});
	memstat.children("#controls")
		.css("top", (plot.getPlotOffset().top+5) + "px")
		.css("left", (plot.getPlotOffset().left+5) + "px");
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
		legend: {noColumns: 2},
		series: {downsample: {threshold: Math.floor(procstat.width() * points_per_px)}}
	});
	procstat.bind("plotselected", function (event, ranges) {
		$.each(plot.getXAxes(), function(_, axis) {
			var zoom_correction_factor = (1000*300*len)/(ranges.xaxis.to - ranges.xaxis.from);
			plot.getOptions().series.downsample.threshold = Math.floor(procstat.width() * points_per_px * zoom_correction_factor);
			axis.options.min = ranges.xaxis.from;
			axis.options.max = ranges.xaxis.to;
		});
		plot.setData(pdata);
		plot.setupGrid();
		plot.draw();
		plot.clearSelection();
		procstat.children("#controls")
			.css("top", (plot.getPlotOffset().top+5) + "px")
			.css("left", (plot.getPlotOffset().left+5) + "px")
			.css("display", "block");
	});
	var procstat_controls = $("<div style='right:60px;top:13px;position:absolute;display:none;' id='controls'></div>").appendTo(procstat);
	$("<div class='btn btn-default btn-xs'>Reset</div>")
		.appendTo(procstat_controls)
		.click(function (event) {
			event.preventDefault();
			console.log("button");
			$.each(plot.getXAxes(), function(_, axis) {
				axis.options.min = null;
				axis.options.max = null;
			});
			plot.getOptions().series.downsample.threshold = Math.floor(procstat.width() * points_per_px);
			plot.setData(pdata);
			plot.setupGrid();
			plot.draw();
			procstat.children("#controls")
				.css("top", (plot.getPlotOffset().top+5) + "px")
				.css("left", (plot.getPlotOffset().left+5) + "px")
				.css("display", "none");
		});
	procstat.children("#controls")
		.css("top", (plot.getPlotOffset().top+5) + "px")
		.css("left", (plot.getPlotOffset().left+5) + "px");
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
	console.log(pdata);
	var plot = $.plot(clientstat, pdata, {
		xaxis: {mode: "time", timezone: "browser"},
		selection: {mode: "x"},
		yaxis: {min: 0},
		series: {downsample: {threshold: Math.floor(clientstat.width() * points_per_px)}}
	});
	clientstat.bind("plotselected", function (event, ranges) {
		$.each(plot.getXAxes(), function(_, axis) {
			var zoom_correction_factor = (1000*300*len)/(ranges.xaxis.to - ranges.xaxis.from);
			plot.getOptions().series.downsample.threshold = Math.floor(clientstat.width() * points_per_px * zoom_correction_factor);
			axis.options.min = ranges.xaxis.from;
			axis.options.max = ranges.xaxis.to;
		});
		plot.setData(pdata);
		plot.setupGrid();
		plot.draw();
		plot.clearSelection();
		clientstat.children("#controls")
			.css("top", (plot.getPlotOffset().top+5) + "px")
			.css("left", (plot.getPlotOffset().left+5) + "px")
			.css("display", "block");
	});
	var clientstat_controls = $("<div style='right:60px;top:13px;position:absolute;display:none;' id='controls'></div>").appendTo(clientstat);
	$("<div class='btn btn-default btn-xs'>Reset</div>")
		.appendTo(clientstat_controls)
		.click(function (event) {
			event.preventDefault();
			console.log("button");
			$.each(plot.getXAxes(), function(_, axis) {
				axis.options.min = null;
				axis.options.max = null;
			});
			plot.getOptions().series.downsample.threshold = Math.floor(clientstat.width() * points_per_px);
			plot.setData(pdata);
			plot.setupGrid();
			plot.draw();
			clientstat.children("#controls")
				.css("top", (plot.getPlotOffset().top+5) + "px")
				.css("left", (plot.getPlotOffset().left+5) + "px")
				.css("display", "none");
		});
	clientstat.children("#controls")
		.css("top", (plot.getPlotOffset().top+5) + "px")
		.css("left", (plot.getPlotOffset().left+5) + "px");
}

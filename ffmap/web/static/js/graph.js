function network_graph(netif) {
	var points_per_px = 0.3;
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
			.css("right", (plot.getPlotOffset().right+42) + "px")
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
				.css("right", (plot.getPlotOffset().right+42) + "px")
				.css("display", "none");
		});
	netstat.children("#controls")
		.css("top", (plot.getPlotOffset().top+5) + "px")
		.css("right", (plot.getPlotOffset().right+42) + "px");
}

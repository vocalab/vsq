$(document).ready(function(){
    $("body").css({width: vsq_length / 10 + 200 + "px"});
    var dynChart = new Highcharts.Chart({
        chart: {
            renderTo: 'dynchart',
            defaultSeriesType: 'area',
            zoomType: 'x',
        },
        title: {
            text: "dynamics curve"
        },
        yAxis: {
            max: 128,
            min: 0
        },
        legend: {
            enabled :false,
        },
        plotOptions: {
            area: {
                fillColor: {
                    linearGradient: [0, 0, 0, 300],
                    stops: [
                        [0, Highcharts.getOptions().colors[0]],
                        [1, 'rgba(2,0,0,0)']
                    ]
                },
                lineWidth: 1,
                marker: {
                    enabled: false,
                    states: {
                        hover: {
                            enabled: true,
                            radius: 5
                        }
                    }
                },
                shadow: false,
                states: {
                    hover: {
                        lineWidth: 1
                    }
                }
            },
            series: {
                step: true
            }
        },
        series:[{
            data: []
        }]
    });
    var pitChart = new Highcharts.Chart({
        chart: {
            renderTo: 'pitchart',
            defaultSeriesType: 'area',
            zoomType: 'x',
        },
        colors: ['#AA4643'],
        title: {
            text: "pitch curve"
        },
        yAxis: {
            max: 30000,
            min: -30000
        },
        legend: {
            enabled :false,
        },
        plotOptions: {
            area: {
                fillColor: {
                    linearGradient: [0, 0, 0, 300],
                    stops: [
                        [0, Highcharts.getOptions().colors[1]],
                        [1, 'rgba(0,2,0,0)']
                    ]
                },
                lineWidth: 1,
                marker: {
                    enabled: false,
                    states: {
                        hover: {
                            enabled: true,
                            radius: 5
                        }
                    }
                },
                shadow: false,
                states: {
                    hover: {
                        lineWidth: 1
                    }
                }
            },
            series: {
                step: true
            }
        },
        series:[{
            data: []
        }]
    });



    var changeHighlight = function(obj){
        var index = $(obj).parent().find("input:checkbox").index(obj);
        if(index !== -1){
            var range = $(obj).parent().find("#range" + $(obj).val());
            if($(obj).attr("checked") === "checked"){
                range.addClass("choosen");
            } else {
                range.removeClass("choosen");
            }
        }
    }
    var selectRule = function(obj){
        if($(obj).attr("checked") === "checked"){
            $(".rule").css("display", "none");
            $("#rule" + $(obj).val()).css("display", "block");
        }
    }
    var changeGraph = function(){
        var options = {
            success: function(response){
                dataset = $.evalJSON(response);
                dynChart.series[0].setData(dataset.dyn);
                pitChart.series[0].setData(dataset.pit);
            },
        url: "/appliedvsq"
        };
        $("#rule-form").ajaxSubmit(options);
    };
    $("input:checkbox").change(function(){
        changeHighlight(this);
        changeGraph();
    });
    $("input:checkbox").each(function(){ changeHighlight(this)} );
    $("input:radio").change(function(){ selectRule(this) });
    $(".rule").css("display", "none");
    $("input:radio").each(function(){ selectRule(this)} );
    $(".chooseable").click(function(){
        var clickedCandidate = $("input:checkbox[value="+$(this).attr("id").slice(5)+"]")
        if(clickedCandidate.attr("checked") === "checked"){
            clickedCandidate.removeAttr("checked");
        } else {
            clickedCandidate.attr("checked", "checked");
        }
    clickedCandidate.change();
    });

    changeGraph();
    jQuery.getJSON("/appliedlyric", function(anote){
        init_time = anote[0].start_time;
        for (var i=0; i < anote.length; i++) {
            span = $("<span>").addClass("anote").css({left: (anote[i].start_time - init_time) / 10 + $(".highcharts-series > path").offset().left + "px", width: anote[i].length / 10 + "px"}).html(anote[i].lyric).click(function(time){
                return function(){
                    console.log(time);
                }
            }(anote[i].start_time));
            $("#float-lyric").append(span);
        };
    });
    $("#float-lyric").css({width: vsq_length / 10 + "px"});
});

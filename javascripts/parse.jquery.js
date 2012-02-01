$(document).ready(function(){
    var changeHighlight = function(obj){
        var index = $("input:checkbox").index(obj);
        if(index !== -1){
            var range = $("#range" + index);
            if($(obj).attr("checked") === "checked"){
                range.addClass("choosen");
            } else {
                range.removeClass("choosen");
            }
        }
    }
    $("input:checkbox").change(function(){ changeHighlight(this) });
    $("input:checkbox").each(function(){ changeHighlight(this)} );
});

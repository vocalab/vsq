$(document).ready(function(){
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
    $("input:checkbox").change(function(){ changeHighlight(this) });
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
});

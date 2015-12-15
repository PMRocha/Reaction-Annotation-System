$( document ).ready(function() {
	
	$("#addQuery").on("click",addQuery);
		
		
	$(document).on("click",".remove_field", function(e){ //user click on remove text
		console.log("#estou aqui");
        e.preventDefault(); 
        $(this).parent('div').remove();
    })
});

function firstTagChild(element) {

	return element.children().first();
}

function addQuery() {
	var original = firstTagChild($("#QueryList"));
	var final = original.clone();
	final.append('<a href="#" class="remove_field">Remove</a>')
	final.appendTo($("#AddedQuery"));
}

// Setup Export to Ads API
// Get Audience Export List
var audienceList = localStorage.getItem("audienceList");
if (audienceList != null) {
  var json_list = JSON.parse(audienceList);
  for (var i=0; i < json_list.length; i++) {
    var item = json_list[i]
  	if (item){
          tr = $('<tr/>');
          tr.append("<td>" + item["query"] + "</td>");
          tr.append("<td>" + item["location"] + "</td>");
          tr.append("<td><button type='button' data-name='" + item['query'] + "' data-id='" + item['location'] + "' id='adsExport' class='btn btn-sm btn-danger' data-toggle='modal' data-target='#adsModal'>Export Audience</button></td>")
          $(".table").append(tr);
  	}
  }
}

$("#adsExport").click(function(e) {
  var bucket_location = $(this).data("id");
  var bucket_name = $(this).data("name");
  // Set bucket to local storage and then send the user a modal
  localStorage.setItem("selected_bucket_id", bucket_location);
  localStorage.setItem("selected_bucket_name", bucket_name);

  listAccounts();
});

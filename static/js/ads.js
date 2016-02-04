// Setup
function setup(){
  getAccounts();
  // Only show the accounts list.
  $(".ads-accounts").show();
  $(".ads-campaigns").hide();
  $(".ads-lineitems").hide();
  $(".ads-targeting").hide();
}

// get the accountList
function getAccounts(){
  $.getJSON("../../ads/api/accounts",
  function (json) {
    localStorage.setItem("adsAccounts", JSON.stringify(json["accounts"]));
  });
}

// Now setup
setup();

// List out the accounts from the Ads API
function listAccounts(){
  var accountList = JSON.parse(localStorage.getItem("adsAccounts"))
  $(accountList).each(function( index ) {
    $(".dropdown-ads-accounts").append("<li><a href='#' id='ads-api-account' data-id='" + accountList[index].id + "'>" + accountList[index].name + "</a></li>");
  });

  console.log("listing accounts")
  // onclick Item
  $("#ads-api-account").click(function(e) {
    e.preventDefault();
    var accountId = $(this).data("id");
    getCampaigns(accountId)
    // remove Ads Tools
    //$(".ads-accounts").hide();
    //$(".ads-api-account").remove();
    // Setup Campaigns
    //$(".ads-campaigns").show();
    //getCampaigns();

    // if audiences
    if (page == "AUDIENCE"){
      // Upload to TA
      var name = escape(localStorage.getItem("selected_bucket_name"));
      //newTA(accountId, name)

    }
      //getCampaigns(accountId)
      // remove Ads Tools
      $(".ads-accounts").hide();
      $(".ads-api-account").remove();
      // Setup Campaigns
      $(".ads-campaigns").show();
  });
}

// Create a new placeholder for a "new" TA
function newTA(account_id, name){
  console.log("newTA called");
  $.getJSON("../../ads/api/audiences/new?account_id=" + account_id + "&name=" + name,
  function (json) {
    console.log("received json");
    // setId to localStorage
    localStorage.setItem("selected_ta_list_id", json['id'])
    // Send new HTTP request to upload location of targetable data
    var ta_id = json["id"];
    mapBucket(account_id, ta_id, escape(localStorage.getItem("selected_bucket_id")))
  });

}

// Map the bucket to the placeholder
function mapBucket(account_id, identifier, input_file_path){
  console.log("mapBucket called");
  var encodedData = window.btoa(input_file_path)
  $.getJSON("../../ads/api/audiences/change?account_id=" + account_id + "&id=" + identifier + "&input_file_path=" + encodedData,
  function (json) {
    //console.log(json);

    if (json["error"]) {
      console.log("http request failed for mapping the bucket to the input_file_path");
      return false;
    }

  });
}

// get the campaignList
function getCampaigns(account_id){
  $.getJSON("../ads/api/campaigns?account_id=" + account_id,
  function (json) {
    $(json["campaigns"]).each(function( index ) {
      var campaign = json["campaigns"][index]
      $(".dropdown-ads-campaigns").append("<li><a href='#' class='ads-api-campaign' data-id='" + campaign['id'] + "'>" + escape(campaign['name']) + "</a></li>");
    });



    // onclick Item
    $(".ads-api-campaign").click(function(e) {
      e.preventDefault();
      var campaign_id = $(this).data("id");
      getLineItems(account_id, campaign_id);
      // Remove Campaign
      $(".ads-campaigns").hide();
      $(".ads-api-campaign").remove();
      // Setup Campaigns
      $(".ads-lineitems").show();
    });


  });
}

// get the lineItems
function getLineItems(account_id, campaign_id){
  $.getJSON("../ads/api/line_items?account_id=" + account_id + "&campaign_id=" + campaign_id,
  function (json) {

    $(json["line_items"]).each(function( index ) {
      var lineItem = json["line_items"][index];
      $(".dropdown-ads-lineitems").append("<li><a href='#' class='ads-api-lineitem' data-id='" + lineItem.id + "'>" + lineItem.name + "-" + lineItem.id + "</a></li>");
    });
    // LineItem
    $(".ads-api-lineitem").click(function(e) {
      localStorage.setItem("line_item", $(this).data("id"))
      $(".ads-lineitems").hide();
      $(".ads-api-lineitem").remove();
      $(".ads-targeting").show();
      getTargetingCriteria(account_id, campaign_id, $(this).data("id"));

      if (page == "AUDIENCE") {
        setTATargeting(account_id, campaign_id, $(this).data("id"));
      } else {
        getTargetingCriteria(account_id, campaign_id, $(this).data("id"));
      }

    });
  });
}


// set TargetingCriteria
function setTATargeting(account_id, campaign_id, line_item_id){
  // for each value send http request to create a targeting criteria
  $.getJSON("../../ads/api/targeting/new?account_id=" + account_id + "&line_item_id=" + line_item_id + "&targeting_value=" +  localStorage.getItem("selected_ta_list_id") + "&targeting_type=TAILORED_AUDIENCE",
  function (json) {
    if (json['valid'] == true){
      //everything is great
      console.log("no error");
      console.log(json);
      //$('#adsModal').hide();
      //location.reload();

    } else {
      // make things happen
      console.log("error");
      console.log(error);
      $(".error").show();
      $(".error-details").text(json);
    }
  });
}

// Get the targeting criteria to a dropdown to target
function getTargetingCriteria(account_id, campaign_id, line_item_id){
  $(".ads-add-targeting").click(function(e) {
    setTargetingCriteria(account_id, campaign_id, line_item_id);
  });

  var checkedVals = $('.term:checkbox:checked').map(function() {
    return this.value;
  }).get();


  $(checkedVals).each(function( index ) {
    console.log(checkedVals);
    $(".ads-targeting-list").append("<li>" + checkedVals[index] + "</li>");
  });

}

// set TargetingCriteria
function setTargetingCriteria(account_id, campaign_id, line_item_id){
  //
  var checkedVals = $('.term:checkbox:checked').map(function() {
    return this.value;
  }).get();

  // for each value send http request to create a targeting criteria
  $(checkedVals).each(function( index ) {
    var targeting_value = checkedVals[index];
    $.getJSON("../../ads/api/targeting/new?account_id=" + account_id + "&line_item_id=" + campaign_id + "&targeting_value=" + targeting_value,
    function (json) {
      if (json['valid'] == true) {
        // Ready
        console.log("ready");
      } else {
        // Not Valid
        console.log("not ready");
      }
    });
  });
}

// Ads-Modal on close
$('#adsModal').on('shown.bs.modal', function () {
  setup();
})

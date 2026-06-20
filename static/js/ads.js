// Setup
var targetingWriteInFlight = false;

function getCookie(name) {
  var cookies = document.cookie ? document.cookie.split(";") : [];
  for (var index = 0; index < cookies.length; index++) {
    var cookie = $.trim(cookies[index]);
    if (cookie.substring(0, name.length + 1) === name + "=") {
      return decodeURIComponent(cookie.substring(name.length + 1));
    }
  }
  return "";
}

function submitTargeting(payloads) {
  if (targetingWriteInFlight || payloads.length === 0) {
    return;
  }

  targetingWriteInFlight = true;
  $(".ads-add-targeting").prop("disabled", true);

  function finish() {
    targetingWriteInFlight = false;
    $(".ads-add-targeting").prop("disabled", false);
  }

  function submitAt(index) {
    if (index >= payloads.length) {
      finish();
      return;
    }
    $.ajax({
      url: "../../ads/api/targeting/new",
      type: "POST",
      dataType: "json",
      data: payloads[index],
      headers: {"X-CSRFToken": getCookie("csrftoken")}
    }).done(function(json) {
      if (json.valid === true) {
        submitAt(index + 1);
      } else {
        $(".error").show();
        $(".error-details").text("Targeting request was rejected.");
        finish();
      }
    }).fail(function() {
      $(".error").show();
      $(".error-details").text(
        "Targeting outcome is unknown. Inspect the Ads account before retrying."
      );
      finish();
    });
  }

  submitAt(0);
}

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
  submitTargeting([{
    account_id: account_id,
    line_item_id: line_item_id,
    targeting_value: localStorage.getItem("selected_ta_list_id"),
    targeting_type: "CUSTOM_AUDIENCE"
  }]);
}

// Get the targeting criteria to a dropdown to target
function getTargetingCriteria(account_id, campaign_id, line_item_id){
  $(".ads-add-targeting").off("click.targeting").on("click.targeting", function(e) {
    e.preventDefault();
    setTargetingCriteria(account_id, campaign_id, line_item_id);
  });

  var checkedVals = $('.term:checkbox:checked').map(function() {
    return this.value;
  }).get();


  $(checkedVals).each(function( index ) {
    $(".ads-targeting-list").append("<li>" + checkedVals[index] + "</li>");
  });

}

// set TargetingCriteria
function setTargetingCriteria(account_id, campaign_id, line_item_id){
  var checkedVals = $('.term:checkbox:checked').map(function() {
    return this.value;
  }).get();
  var payloads = $.map(checkedVals, function(targeting_value) {
    return {
      account_id: account_id,
      line_item_id: line_item_id,
      targeting_value: targeting_value,
      targeting_type: "PHRASE_KEYWORD"
    };
  });
  submitTargeting(payloads);
}

// Ads-Modal on close
$('#adsModal').on('shown.bs.modal', function () {
  setup();
})

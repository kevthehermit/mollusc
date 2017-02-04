/**
 * Part of Mollusc
 */


/*
Alert Bar:
Generates a dismissable alert bar at the top of tha page.
Params:
    alertType: str = success or warning or danger or info
    strong: str = text in BOLD
    message: str = remainder of message

 */

function alertBar(alertType, strong, message){
    var alert_bar = '<div id="alert-bar" class="alert alert-' + alertType + ' alert-dismissible fade in text-center" role="alert"> \
                           <button type="button" class="close" data-dismiss="alert" aria-label="Close">\
                           <span aria-hidden="true">&times;</span> \
                           </button>\
                           <strong>' + strong + '</strong> ' + message + '\
                           </div>';

    $('#alertTarget').after(alert_bar);

}

/*
Server side pagination of plugin rows.

 */

function datatablesAjax(dataset) {

    // Fill the First Page
    $.post('/ajaxhandler/'+dataset+'/')

        // Success
        .done(function(data) {
            // Get the HTML we want to use
            var html_data = data['data'];

            // Fill first 25 rows
            //$('#sessiontabletarget').html(html_data);

            // then handover to ajax
            $('#'+dataset+'table').DataTable({
                sDom: '<"top"flpr>rt<"bottom"ip><"clear">',
                oLanguage:{
                  sProcessing: '<div id="OuterBarG"><div id="FrontBarG" class="AnimationG"><div class="BarLineG"></div><div class="BarLineG"></div><div class="BarLineG"></div><div class="BarLineG"></div><div class="BarLineG"></div><div class="BarLineG"></div></div></div>'
                },
                processing: true,
                serverSide: true,
                ajax :{
                    url: '/ajaxhandler/'+dataset+'/',
                    type: 'POST',
                    data: function (d) {
                        d.session_id = dataset;
                        d.pagination = true;
                    },
                    dataSrc: function(json){
                       json.draw = json.data.draw;
                       json.recordsTotal = json.data.recordsTotal;
                       json.recordsFiltered = json.data.recordsFiltered;
                       json.columns = json.data.columns;

                       return json.data.data;
                    }
                },
                // Make new rows clickable
                createdRow: function (row, html_data, index) {
                    var session_id = html_data[0];
                    $(row).children('td').addClass('clickable');
                    $(row).children('td').attr('onclick', "document.location = '/session/"+ session_id +"/';");
                },
                pageLength:25,
                deferLoading: vresultCount
            });

            // End of Done
        })
        // Failed
        .error(function(xhr, status) {
                if (xhr.status == 500) {
                    alertBar('danger', 'Spaghetti-Os!', 'Server Generated an Error 500 Please check the console.');
                }
            }

        )
        // CleanUp
        .always(function(xhr, status) {
               // Nothing here yet
            }

        );
}

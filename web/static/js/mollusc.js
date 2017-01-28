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
New Ajax Handler
Single Function to handle Ajax calls

Params:
    command: str = name of command
    postFields: str(json) = json string of POST options
    spinner: Bool = Overlay a loading spinner or not.'
 */


function ajaxHandler(command, postFields, spinner) {

    // Convert postFields to json
    if (typeof postFields != 'string'){
        postOptions = postFields
    } else {
        var postOptions = JSON.parse(postFields);
    }

    // Sometimes we need to get values from form fields before the post.
    if (command == 'plugin_dir'){
        var postOptions = {'plugin_dir':$('#pluginDir').val()};
    }


    if (command == 'filtersessions'){
        postOptions['pluginname'] = $('#pluginname').val();
        postOptions['searchterm'] = $('#searchterm').val();

    }


    if (command == 'yara-string'){
        console.log('Yara Scanner');
        postOptions['yara-string'] = $('#yara-string').val();
        postOptions['yara-hex'] = $('#yara-hex').val();
        postOptions['yara-reverse'] = $('#yara-reverse').val();
        postOptions['yara-case'] = $('#yara-case').prop('checked');
        postOptions['yara-kernel'] = $('#yara-kernel').prop('checked');
        postOptions['yara-wide'] = $('#yara-wide').prop('checked');
        postOptions['yara-file'] = $('#yara-file').val();
        postOptions['yara-pid'] = $('#yara-pid').val();
    }

    if (command == 'memhex' || command == 'memhexdump'){
        postOptions['start_offset'] = $('#start_offset').val();
        postOptions['end_offset'] = $('#end_offset').val();
    }

    if (command == 'searchbar'){
        postOptions['search_type'] = $('#search_type').val();
        postOptions['search_text'] = $('#search_text').val();

    }

    if (command == 'addcomment'){
        postOptions['comment_text'] = document.getElementById('commentText').value;
    }

    // if selected show the loading image
    if (spinner == true){
        spinnerControl('open', 'Loading Data');
    }

    // Set Plugin Running
    if (command == 'runplugin'){
        var span_id = document.getElementById(postFields['plugin_name']+'_glyph');
        span_id.removeAttribute('class');
        span_id.className += 'glyphicon glyphicon-repeat';
        span_id.className += ' gly-spin';
    }


    // Try to add a session ID if one is present.
    var session_id = $('#sessionID').html();
    if(typeof session_id !== "undefined")
    {
      postOptions['session_id'] =session_id;
    }

    //Try to add active plugin ID
    if (postOptions['plugin_id'] == undefined)
    {
        if(typeof vActivePluginID !== "undefined")
        {
          postOptions['plugin_id'] = vActivePluginID;
        }
    }

    $.post("/ajaxhandler/" + command + "/", postOptions)

        // Success
        .done(function(data) {
            // POLL PLUGINS
            if (command == "pollplugins"){
                $('#pluginTable').html(data);

            // Filter Sessions
            } else if (command == "filtersessions"){
            for (var i = 0; i < data.length; i++) {
                session_id = data[i];
                console.log(session_id);
                $('tr').each(function(){
                    var tr = $(this);
                    if (tr.find('td:eq(0)').text()==session_id
                    ) tr.addClass('success');
                });
        }

            // Run Plugin
            }else if (command == "dropplugin"){
                notifications('warning', true, postOptions['plugin_id'], 'Plugin Deleted');

            // Run Plugin
            } else if (command == 'runplugin') {
                if (data.substring(0,5) == 'Error'){
                     notifications('error', true, postOptions['plugin_id'], 'View '+ data+ ' Output');
                } else if (data.substring(0,5) == 'Hmmmm') {
                    notifications('error', true, postOptions['plugin_id'], 'View '+ data+ ' Output');
                }else {

                notifications('success', true, postOptions['plugin_id'], 'View '+ data+ ' Output');
                }


            // Add Plugin Dir
            }else if (command == 'plugin_dir') {
                //alertBar('success', 'Added!', 'You have successfully added the plugin dir ' + data)
                location.reload();

            }else if (command == 'filedetails') {

                $('#fileModalDiv').html(data);
                //jQuery.noConflict();
                //Hide Any Open Modal
                $('.modal').modal('hide');
                // Open New Modal
                $('#fileModal').modal('show');

            }else if (command == 'hivedetails') {
                $('#hiveModalDiv').html(data);
                spinnerControl('close', 'Loading Data');
                $('#hiveModal').modal('show');
                // Enable table sorting
                $('#hiveTable').DataTable();

            // If target_div exists in the postoptions we are just writing out.
            }else if (postOptions["extension"]) {
                console.log("in Here");
                // Get the HTML we want to use
                var html_data = data['data'];
                // add additional JS
                var new_js = data['javascript'];
                eval(new_js);
                console.log(postOptions["target_div"]);
                $('#'+postOptions["target_div"]).html(html_data);

            }else if (command == 'dottree' || command == "vaddot") {
                console.log('DotTree');

                // Prepare the div
                $('#resultsTarget').html('<svg width="100%" height="100"><g/></svg>');
                var svg = d3.select("svg");
                var inner = d3.select("svg g");
                var zoom = d3.behavior.zoom().on("zoom", function() {
                      inner.attr("transform", "translate(" + d3.event.translate + ")" +
                                                  "scale(" + d3.event.scale + ")");
                    });
                svg.call(zoom);


                var render = dagreD3.render();
                var g = graphlibDot.read(data);
                // Set margins, if not present
                if (!g.graph().hasOwnProperty("marginx") &&
                    !g.graph().hasOwnProperty("marginy")) {
                  g.graph().marginx = 20;
                  g.graph().marginy = 20;
                }

                g.graph().transition = function(selection) {
                      return selection.transition().duration(500);
                    };

                d3.select("svg g").call(render, g);

                svg.attr("height", g.graph().height);

                var xCenterOffset = (g.graph().width) / 2;
                var yCenterOffset = (g.graph().height) / 2;

                inner.attr("transform", "translate("+xCenterOffset+", "+ yCenterOffset +")");



                $("svg").click(function( event ) {

                    if (command == 'dottree') {
                        // Reset the CSS
                        $("svg").find('rect').css("fill", "white");
                        $("svg").find('path').css("stroke", "white");

                        // Get nodes and paths
                        var node_list = inner.selectAll("g.node")[0];
                        var path_list = inner.selectAll("g.edgePath")[0];

                        // Get Selected Node
                        var selectedNode = $(event.target).closest('.node').find('rect');
                        var selectedNodeID = selectedNode[0].__data__;

                        // Set selected node to blue
                        selectedNode.html("TEST");
                        selectedNode.css("fill", "blue");
                        // Find parents and children

                        for (i = 0; i < path_list.length; i++) {

                            var ppid = path_list[i].__data__.v;
                            var pid = path_list[i].__data__.w;
                            // Parent
                            if (pid == selectedNodeID) {
                                var ppid_int = parseInt(ppid.slice(4));
                                $(node_list[ppid_int - 1]).find('rect').css("fill", "red");
                                $(path_list[i]).find('path').css("stroke", "red")
                            }
                            // Children
                            if (ppid == selectedNodeID) {
                                var pid_int = parseInt(pid.slice(4));
                                $(node_list[pid_int - 1]).find('rect').css("fill", "yellow");
                                $(path_list[i]).find('path').css("stroke", "yellow")
                            }
                        }
                    }
            });

                //image = Viz(data, {format: "png-image-element"});
                //$(image).attr('id', 'proctree');
                //$(image).width('100%').height(500);
                //$('#resultsTarget').html(image);
                //$('#'+postOptions["target_div"]).append(image);

            }else if (command == "deleteobject" || command == "dropsession") {
                $('.modal').modal('hide');
                datatablesAjax(vActivePluginID)

            }else if (command == 'memhex') {
                $('#'+postOptions["target_div"]).html(data);

            }else if (command == 'memhexdump') {
                var empty = true;

            }else if (command == 'addcomment') {
                $('#comment-block').html(data);

            }else if (command == 'pluginresults' || command == 'searchbar') {
                // Close the spinner
                spinnerControl('close', 'Loading Data');
                // Load the data
                $('#resultsTarget').html(data);
                // Enable table sorting

                // Return JQuery
                $('#resultsTable').DataTable({pageLength:25,scrollX: true,drawCallback: resultscontextmenu ($, window)});
                resultscontextmenu ($, window);

            }else if (command == 'bookmark') {
                //

            }else if (command == 'procmem') {
                notifications('success', true, postOptions['plugin_id'], 'Check memdump plugin for your file.');

            }else if (command == 'filedump') {
                notifications('success', true, postOptions['plugin_id'], 'Check dumpfiles plugin for your file.');
            }else if (command == 'linux_find_file') {
                notifications('success', true, postOptions['plugin_id'], 'Check linux_find_file plugin for your file.');
            }else {
                if (postOptions['target_div']){
                    $('#'+postOptions["target_div"]).html(data);
                }else{
                    alertBar('danger', 'Spaghetti-Os!', 'Unable to find a valid command')
                }

            }

            // End of Done
        })
        // Failed
        .error(function(xhr, status) {
                if (xhr.status == 500) {
                    alertBar('danger', 'Spaghetti-Os!', 'Server Generated an Error 500 Please check the console. ' +
                        'Typically volitility couldnt handle a plugin correctly');
                }
            }

        )
        // CleanUp
        .always(function(xhr, status) {
               spinnerControl('close');
            }

        );
}




/*
Server side pagination of plugin rows.

 */

function datatablesAjax(session_id) {

    // Fill the First Page
    $.post("/ajaxhandler/sessions/")

        // Success
        .done(function(data) {
            // Get the HTML we want to use
            var html_data = data['data'];

            // Fill first 25 rows
            $('#sessiontabletarget').html(html_data);

            // then handover to ajax
            $('#sessiontable').DataTable({
                sDom: '<"top"flpr>rt<"bottom"ip><"clear">',
                oLanguage:{
                  sProcessing: '<div id="OuterBarG"><div id="FrontBarG" class="AnimationG"><div class="BarLineG"></div><div class="BarLineG"></div><div class="BarLineG"></div><div class="BarLineG"></div><div class="BarLineG"></div><div class="BarLineG"></div></div></div>'
                },
                processing: true,
                serverSide: true,
                ajax :{
                    url: '/ajaxhandler/sessions/',
                    type: 'POST',
                    data: function (d) {
                        d.session_id = session_id;
                        d.pagination = true;
                    },
                    dataSrc: function(json){
                       json.draw = json.data.draw;
                       json.recordsTotal = json.data.recordsTotal;
                       json.recordsFiltered = json.data.recordsFiltered;

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
                    alertBar('danger', 'Spaghetti-Os!', 'Server Generated an Error 500 Please check the console. ' +
                        'Typically volitility couldnt handle a plugin correctly');
                }
            }

        )
        // CleanUp
        .always(function(xhr, status) {
               spinnerControl('close');
            }

        );
}


// start FastAPI servr
//    uvicorn script:app --reload
var chart2;

// const serverUrl = 'http://192.168.68.113:8000';
//const serverUrl = '__SERVER_URL__';
const serverUrl = 'http://107.174.172.150';
const apiUrl = serverUrl + '/wind?day=';
const apiImage = serverUrl + '/get_image';

// get wind data for specific date use this format
//serverUrl + '/wind?day=YYYY-MM-DD';
function getData(date,historyOnly=false) {
    
    // add date to the url
    let dateStr = date.toISOString().substring(0,10);

    let url  = apiUrl
    if (dateStr)
        url += dateStr;

    console.log("getting " + url)
    // Make a GET request
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {

            test_json = JSON.parse(data);

            var dirfixed = test_json.dir.map(northCenter);

            chart2.data.datasets[0].data = dirfixed;
            chart2.data.datasets[1].data = test_json.avg;
            chart2.data.datasets[2].data = test_json.gust;
            chart2.data.datasets[3].data = test_json.lull;
            chart2.data.labels = test_json.time;
            chart2.update();


            //console.log(test_json.time);
            //console.log(test_json.avg);
            //console.log(test_json.gust);
            //console.log(test_json.lull);
            //console.log(dirfixed);
            console.log(data);

            if (!historyOnly){
                updateLatestsStats(test_json);
            }
            updateGraphTitle(date);

            if (historyOnly){
                renderButtons(date);
                if (test_json.time.length == 0){
                    showMessage("NO WIND DATA FOR THIS DATE");
                }else{
                    showMessage("");
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });

}

// Convert a 0-360 degree direction to a compass point and degrees from it
function directionString(direction,simple=true) {
    const dir_dict = {
        0: "N",
        1: "NE",
        2: "E",
        3: "SE",
        4: "S",
        5: "SW",
        6: "W",
        7: "NW"
    }
    var dir_num = Number(direction);
    var dir_index = Math.floor(((dir_num + 22) % 360) / 45);
    var rem = (dir_num - dir_index * 45);
    rem = (rem > 23) ? rem - 360 : rem;
    var simpleResult = dir_dict[dir_index];

    var res
    if (simple){
        res = simpleResult;
    } else {
        res = simpleResult + " " + "<small>" + (rem < 0 ? ' ' : '+') + rem + "&#176</small>"
    }
    return res;
}

// Hack to make degree data fit into windspeed data, North is center of chart
function northCenter(degrees) {
    return ((degrees + 180) % 360) / 9;
}

function timeString(time24) {
    if (time24 == 0)
        return "12am";
    else if (time24 == 12)
        return "12pm";
    else if (time24 < 12)
        return time24.toString() + "am";
    else
        return (time24 - 12).toString() + "pm"
}

//Parse out the latest wind stats and update the HTML
function updateLatestsStats(json_data){

    var latestDiv = document.getElementById("latest-stats");

    latestDiv.innerHTML =
       "<h2>" + json_data.avg[json_data.avg.length-1] + "(g" +json_data.gust[json_data.gust.length-1] + ")<small>mph</small>  "  +directionString(json_data.dir[json_data.dir.length-1]) + "</br><small>"  + json_data.time[json_data.time.length-1]  + "</small></h2><br>";
   
}

function updateGraphTitle(date){

    let title = document.getElementById("graph-title");

    title.innerHTML =
        '<h3> Wind Graph ' + date.toLocaleString('en-US',  {dateStyle: 'short'})+ '</h3>';
}

function renderButtons(date){
    
    showndate = date;
    let dayButtons = document.getElementById("day-buttons");
    
    dayButtons.innerHTML = '<input id="next-btn" value="NEXT" type="button" onclick="getData(addDays(showndate,1),true);"></input>  &nbsp;&nbsp <input id="prev-btn" value="BACK" type="button" onclick="getData(addDays(showndate,-1),true);"></input> ';
           
}

function addDays(date, days) {
    var result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
  }

function showMessage(userMsg){

    let msg = document.getElementById("msg");
    
    if (userMsg.length > 0)
        msg.innerHTML = '<p class="w3-panel w3-orange">'+ userMsg +'</p>';
    else
         msg.innerHTML = '';
           
}

 /* Toggle between showing and hiding the navigation menu links when the user clicks on the hamburger menu / bar icon */
 function menu() {
    let x = document.getElementById("myLinks");
        if (x.style.display === "block") {
            x.style.display = "none";
        } else {
            x.style.display = "block";
        }
 }


 function includeHTML() {
    var z, i, elmnt, file, xhttp;
    /* Loop through a collection of all HTML elements: */
    z = document.getElementsByTagName("*");
    for (i = 0; i < z.length; i++) {
      elmnt = z[i];
      /*search for elements with a certain atrribute:*/
      file = elmnt.getAttribute("w3-include-html");
      if (file) {
        /* Make an HTTP request using the attribute value as the file name: */
        xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function() {
          if (this.readyState == 4) {
            if (this.status == 200) {elmnt.innerHTML = this.responseText;}
            if (this.status == 404) {elmnt.innerHTML = "Page not found.";}
            /* Remove the attribute, and call this function once more: */
            elmnt.removeAttribute("w3-include-html");
            includeHTML();
          }
        }
        xhttp.open("GET", file, true);
        xhttp.send();
        /* Exit the function: */
        return;
      }
    }
  }


  // chart js config
  const arrows = {
    id:'arrows',
    beforeInit(chart, args, plugins){
        console.log("hello")
        const fitValue  = chart.legend.fit;
        chart.legend.fit =  function fit(){
            fitValue.bind(chart.legend)();
            return this.height +=40
        }
    }
}


const chartConfig =  {
    plugins: [arrows],
    type: "line",
    data: {
        datasets: [{
            label: "Direction (North at middle)",
            pointRadius: 1,
            pointBackgroundColor: "rgb(0,0,255)",
            borderColor: "blue",
            fill: false,
            borderWidth: 4,
            tension: 0.3
        }, {
            label: "Wind Speed",
            pointRadius: 1,
            pointBackgroundColor: "rgb(0,0,255)",
            borderColor: "green",
            borderWidth: 4,
            fill: false,
            yAxisID: 'speed',
            tension: 0.3
        }, {
            label: "Gusts",
            pointRadius: 1,
            pointBackgroundColor: "rgb(255,0,0)",
            borderColor: "red",
            fill: false,
            borderWidth: 1,
            yAxisID: 'speed',
            tension: 0.3
        }, {
            label: "Lulls",
            pointRadius: 1,
            pointBackgroundColor: "rgb(255,0,0)",
            borderColor: "black",
            fill: '-1',
            borderWidth: 1,
            yAxisID: 'speed',
            tension: 0.3
        },
        ]
    },
    options: {
        plugins: {
            legend: {   
                display: true,
                align: 'end'
            }   
        },
        scales: {
            
            speed:{
                position: 'right',
                min: 0, 
                max:40,
                ticks:{      
                    color: 'gray',
                    font:{
                        weight: 'bold',
                        size:20
                    }
                }
            },
            direction:{
                position: 'right',
                min: 0,
                max: 8,
                ticks: {
                    callback: function(value, index, ticks) {
                        var x = ["S", "SW", "W", "NW", "N", "NE", "E", "SE", "S"];
                        return x[value % x.length];
                    },
                    color: 'blue',
                    font:{
                        weight: 'bold',
                        size: 20
                    },
                }
            }
        }
    }
};

function setSlider() {
  var sliders = document.querySelectorAll("#slider");
  for (var i = 0; i < sliders.length; i++) {
    sliders[i].onchange = function(e) {
        e.target.previousElementSibling.innerHTML = e.target.value + ' min(s)'
     }
  }

}
setSlider()


var getJSON = function(url, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.responseType = 'text';
    xhr.onload = function() {
      var status = xhr.status;
      if (status === 200) {
        callback(null, xhr.response);
      } else {
        callback(status, xhr.response);
      }
    };
    xhr.send();
};

getJSON('/logs.json',
function(err, data) {
  if (err !== null) {
    alert('Something went wrong: ' + err);
  } else {
	  const obj = JSON.parse(data)
	  content = '<pre>'
	  for (var i = 0; i < obj.length; i++) {
		content += obj[i][1] + ' ' + obj[i][3] + '\n'
	  }
	  content += '</pre>'
	  document.getElementById('logs').innerHTML = content
  }
});

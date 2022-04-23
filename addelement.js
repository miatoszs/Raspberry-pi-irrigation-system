function add(obj) {
  // Create the new node to insert
  let newNode = obj.previousElementSibling.cloneNode(true)

  // Get a reference to the parent node
  let parentDiv = obj.parentElement

  parentDiv.insertBefore(newNode, obj)
  setSlider()
}

function remove(obj) {
  element = obj.previousElementSibling.previousElementSibling.previousElementSibling
  if(typeof(element) != 'undefined' && element != null){

    obj.previousElementSibling.previousElementSibling.remove()

  }

  setSlider()
}

const addItem = document.getElementById('addItem')
const form = document.getElementById('form')


if (addItem) {
  addItem.addEventListener('click', addItemHandler);

  //Add a new Button when enter is pressed
  addItem.addEventListener('keyup', function(event) {
    // Number 13 is the "Enter" key on the keyboard
    if (event.keyCode === 13) {
      // Trigger the button element with a click
      addItem.click();
    }
  });
}

// keep track of the elements created
let ct = 1;
function addItemHandler (e){
  e.preventDefault()

  const {formWrapper, buttonEl,inputEl} =createDomElements
  ct++;
  // Construct HTML to be Injected into the DOM
  const formGroup = formWrapper(ct)

  const inputElm = inputEl(ct)
  formGroup.appendChild(inputElm)
  formGroup.appendChild(buttonEl(ct))

  //Append the form group to the Form
  form.appendChild(formGroup);

  //Focus the newly created input
  inputElm.focus()
}

//Remove element from the DOM
function removeElement(e) {
  const button = e.target;
  const formGroup = button.parentElement;
  //Select the form container and remove its child that was clicked
  form.removeChild(formGroup);
}

const createDomElements = {
  formWrapper: (id) => {
    let formGroup = document.createElement('div');
    formGroup.setAttribute('class', 'form__group' );
    formGroup.setAttribute('id', `form__group--${id}`);
    return formGroup
  },
  inputEl: (id) => {
    //create textbox
    let input = document.createElement('input');
    input.type = "time";
    input.setAttribute("class", 'form__input');
    input.setAttribute('id', `form__input--${id}`);
    input.setAttribute('placeholder', `Enter Language`);
    return input
  },
  buttonEl: (id) => {
    let deleteBtn = document.createElement('button');
    deleteBtn.setAttribute('id', `btn--${id}`);
    deleteBtn.setAttribute('class', "btn btn--delete");
    deleteBtn.onclick = function(e) {
      removeElement(e)
    };
    deleteBtn.setAttribute("type", "button");
    deleteBtn.innerHTML = "Remove";
    return deleteBtn;
  }
}

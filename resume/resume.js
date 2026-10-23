"use strict";

const printButton = document.getElementById("print-button");
if (printButton) {
  printButton.addEventListener("click", () => window.print());
}

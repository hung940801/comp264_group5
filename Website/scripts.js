"use strict";

const serverUrl = "http://127.0.0.1:8000";

async function uploadFile() {
    // encode input file as base64 string for upload
    let file = document.getElementById("file").files[0];
    let converter = new Promise(function(resolve, reject) {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result
            .toString().replace(/^data:(.*,)?/, ''));
        reader.onerror = (error) => reject(error);
    });
    let encodedString = await converter;

    // clear file upload input field
    document.getElementById("file").value = "";

    // make server call to upload file
    // and return the server upload promise
    return fetch(serverUrl + "/files", {
        method: "POST",
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({filename: file.name, filebytes: encodedString})
    }).then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new HttpError(response);
        }
    })
}

function updateFile(file) {
    document.getElementById("view").style.display = "block";

    let fileElem = document.getElementById("file");
    fileElem.alt = file["fileId"];

    console.log(file);

    return file;
}

function translateFile(file) {
    // make server call to translate file
    // and return the server upload promise
    return fetch(serverUrl + "/files/translate-text", {
        method: "POST",
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({fromLang: "auto", toLang: "en", text: file["text"]})
    }).then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new HttpError(response);
        }
    })
}

function annotateFile(translations) {
    document.getElementById("view").style.display = "block";

    let translationText = "";
    let translationsElem = document.getElementById("translations");
    let originalsElem = document.getElementById("original");
    while (translationsElem.firstChild) {
        translationsElem.removeChild(translationsElem.firstChild);
    }
    while (originalsElem.firstChild) {
        originalsElem.removeChild(originalsElem.firstChild);
    }
    translationsElem.clear
    originalsElem.clear
    for (let i = 0; i < translations.length; i++) {
        let originalElem = document.createElement("h6");
        originalElem.appendChild(document.createTextNode(
            translations[i]["text"]
        ));
        originalsElem.appendChild(originalElem);
        
        let translationElem = document.createElement("h6");
        translationElem.appendChild(document.createTextNode(
            translations[i]["text"] + " -> " + translations[i]["translation"]["translatedText"]
        ));
        translationsElem.appendChild(translationElem);
        translationText = translationText + translations[i]["translation"]["translatedText"] + " ";
    }
    console.log("translationText: " + translationText);
    return translationText;
}

// add new function for call sound generate API
function generateSound(translations) {
    return fetch(serverUrl + "/files/translate-text-to-speech", {
        method: "POST",
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({translations: translations})
    }).then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new HttpError(response);
        }
    })
}

// add a new function for displaying the generated sound
function displaySound(sound) {
    let audio_file = sound["audio_file_path"]
    var sound      = document.createElement('audio');
    sound.id       = 'audio-player';
    sound.controls = 'controls';
    sound.src      = "./" + audio_file;
    sound.type     = 'audio/mpeg';
    document.getElementById('audio_track').innerHTML = "";
    document.getElementById('audio_track').appendChild(sound);
    sound = ""
}

function uploadAndTranslate() {
    uploadFile()
        // .then(file => updateFile(file))
        .then(file => translateFile(file))
        .then(translations => annotateFile(translations))
        .then(translations => generateSound(translations)) // add new function call
        .then(sound => displaySound(sound)) // add new function call
        .then(() => {
            document.getElementById('audio-player').play();
        })
        .catch(error => {
            alert("Error: " + error);
        })
}

class HttpError extends Error {
    constructor(response) {
        super(`${response.status} for ${response.url}`);
        this.name = "HttpError";
        this.response = response;
    }
}

"use strict";
(function () {
    const createInput = function (name, value) {
        const input = document.createElement("input");
        input.name = name;
        input.value = value;
        return input;
    };
    const addInput = function (form, name, value) {
        form.appendChild(createInput(name, value));
    };
    const createAndSubmitStoryForm = function (storyLink) {
        const form = document.createElement("form");
        form.method = "post";
        form.action = "/story";
        const storyId = storyLink.getAttribute("storyId");
        const storyName = storyLink.getAttribute("storyName");
        addInput(form, "story_id", storyId);
        addInput(form, "storyname", storyName);
        document.body.appendChild(form);
        form.submit();
    };
    const addOnClicks = function () {
        const storyLinks = document.getElementsByClassName("story-link");
        for (let i = 0; i < storyLinks.length; i++) {
            const storyLink = storyLinks.item(i);
            storyLink.onclick = function () {
                createAndSubmitStoryForm(storyLink);
            };
        }
    };
    addOnClicks();
})();

(function() {

    const createInput = function(name: string, value: string): HTMLElement {
        const input = document.createElement("input");
        input.name = name;
        input.value = value;
        return input;
    };

    const addInput = function(form: HTMLFormElement, name: string, value: string): void {
        form.appendChild(createInput(name, value));
    };

    const createAndSubmitStoryForm = function(storyLink: HTMLLinkElement) {
        const form: HTMLFormElement = document.createElement("form");
        form.method = "post";
        form.action = "/story";
        const storyId: string = <string> storyLink.getAttribute("storyId");
        const storyName: string = <string> storyLink.getAttribute("storyName");
        addInput(form, "story_id", storyId);
        addInput(form, "storyname", storyName);
        document.body.appendChild(form);
        form.submit();
    };

    type HTMLLinks = HTMLCollectionOf<HTMLLinkElement>;

    const addOnClicks = function() {
        const storyLinks: HTMLLinks =
            <HTMLLinks> document.getElementsByClassName("story-link");
        for (let i = 0; i < storyLinks.length; i++) {
            const storyLink: HTMLLinkElement = storyLinks.item(i);
            storyLink.onclick = function() {
                createAndSubmitStoryForm(storyLink);
            };
        }
    };

    addOnClicks();

})();
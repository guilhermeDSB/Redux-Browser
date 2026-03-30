console.log("[Redux Test Ext] Content script injetado!");

// Testar o isolamento e comunicação (Mocked)
if (window.chrome && chrome.runtime) {
    console.log("[Redux Test Ext] chrome.runtime ID é:", chrome.runtime.id);
    chrome.storage.local.set({"redux_test": true}).then(() => {
        console.log("[Redux Test Ext] Storage escrito via Chrome API shims!");
    });
}

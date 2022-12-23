import puppeteer from "puppeteer";
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const config = require("./config.json");

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    const MINPRICE =
        Math.round(config["MIN_PRICE"] * config["BEDROOMS"] * 4.4 * 100) / 100;
    const MAXPRICE =
        Math.round(config["MAX_PRICE"] * config["BEDROOMS"] * 4.4 * 100) / 100;
    await page.goto(
        `https://www.zoopla.co.uk/to-rent/flats/london/?beds_max=${config["BEDROOMS"]}&beds_min=${config["BEDROOMS"]}&price_frequency=per_month&price_max=${MAXPRICE}&price_min=${MINPRICE}&property_sub_type=flats&q=London&search_source=refine&pn=1`
    );

    // Wait for suggest overlay to appear and click "show all results".
    const resultsSelector = "[data-testid='regular-listings']";
    await page.waitForSelector(resultsSelector);

    // Extract the results from the page.
    const links = await page.evaluate((resultsSelector) => {
        const regularListings = document.querySelector(resultsSelector);
        const featuredListings = document.querySelector(
            "[data-testid='featured-listings']"
        );
        return [...regularListings.querySelectorAll("a")]
            .concat([...featuredListings.querySelectorAll("a")])
            .map((d) => d.href)
            .filter((d) =>
                /https:\/\/www\.zoopla\.co\.uk\/to-rent\/details\/[0-9]+/.test(
                    d
                )
            );
    }, resultsSelector);

    // Print all the files.
    console.log(JSON.stringify(links));

    await browser.close();
})();

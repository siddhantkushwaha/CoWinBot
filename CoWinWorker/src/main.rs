use chrono;

use std::collections::HashMap;
use std::env;
use std::thread;
use std::time::Duration;

use reqwest::header::USER_AGENT;

fn get_pincode(server_url: &str) -> Result<i32, reqwest::Error> {
    let client = reqwest::blocking::Client::new();
    let url = format!("{}/get", server_url);
    let response: HashMap<String, i32> = client.get(url).send()?.json()?;

    let pincode = match response.get("pincode") {
        Some(i) => *i,
        None => -1,
    };
    return Ok(pincode);
}

fn get_info_for_pincode(pincode: i32) -> Result<String, reqwest::Error> {
    let formatted_date = chrono::offset::Local::now().format("%d-%m-%Y");

    let client = reqwest::blocking::Client::new();
    let url = format!("https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin?pincode={}&date={}", pincode, formatted_date);
    let user_agent_header = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36";
    let response: String = client
        .get(url)
        .header(USER_AGENT, user_agent_header)
        .send()?
        .text()?;

    return Ok(response);
}

fn index_pincode(server_url: &str, pincode: i32, data: String) -> Result<i32, reqwest::Error> {
    let client = reqwest::blocking::Client::new();
    let url = format!("{}/index", server_url);

    let params = [("pincode", pincode.to_string()), ("meta", data)];
    let response: HashMap<String, i32> = client.post(url).form(&params).send()?.json()?;

    let error_code = match response.get("error") {
        Some(i) => *i,
        None => -1,
    };
    return Ok(error_code);
}

fn main() {
    println!(
        "
    ----------------------------------------------------
        Worker node for CoWinBot. Thanks for helping!

                   t.me/vaccinecowinbot
    ----------------------------------------------------\n\n"
    );

    let args: Vec<String> = env::args().collect();

    let prioritise_pincode;
    if args.len() > 1 {
        prioritise_pincode = match args[1].parse::<i32>() {
            Ok(i) => i,
            Err(_err) => -1,
        };
    } else {
        prioritise_pincode = -1;
    }

    if prioritise_pincode > 0 {
        println!(
            "Pincode [{}] will be priortised by this node.\n",
            prioritise_pincode
        );
    }

    let server_url = "http://sid.centralindia.cloudapp.azure.com:5000";

    let mut i = 0;
    loop {
        println!("\n--------------- new iteration --------------");

        let pincode;
        if i == 0 && prioritise_pincode > 0 {
            pincode = prioritise_pincode;
        } else {
            pincode = match get_pincode(server_url) {
                Ok(i) => i,
                Err(_err) => {
                    println!("Failed to fetch pincode from server.");
                    continue;
                }
            };
        }

        println!("Got pincode [{}].", pincode);

        let pincode_info = match get_info_for_pincode(pincode) {
            Ok(info) => info,
            Err(_err) => {
                println!("Couldn't get info for pincode [{}].", pincode);
                continue;
            }
        };

        println!("Fetched data for pincode [{}].", pincode);

        let index_error_code = match index_pincode(server_url, pincode, pincode_info) {
            Ok(i) => i,
            Err(_err) => {
                println!("Failed to index pincode [{}] to server.", pincode);
                continue;
            }
        };

        println!(
            "Indexed data for pincode [{}], return code [{}].",
            pincode, index_error_code
        );

        i += 1;
        i %= 5;

        thread::sleep(Duration::from_secs(10))
    }
}

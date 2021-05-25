use chrono;

use std::collections::HashMap;
use std::thread;
use std::time::Duration;

use reqwest::header::USER_AGENT;

use magic_crypt::MagicCryptTrait;

fn encrypt_aes256(text: &String, key: &String, iv: &String) -> String {
    let mc = magic_crypt::new_magic_crypt!(key, 256, iv);
    let base64 = mc.encrypt_str_to_base64(text);
    return base64;
}

fn decrypt_aes256(text: &String, key: &String, iv: &String) -> String {
    let mc = magic_crypt::new_magic_crypt!(key, 256, iv);
    let plain_text: String = match mc.decrypt_base64_to_string(text) {
        Ok(i) => i,
        Err(_err) => String::from(""),
    };
    return plain_text;
}

fn get_external_ip() -> Result<String, reqwest::Error> {
    let client = reqwest::blocking::Client::new();
    let url = "https://ifconfig.me/ip";
    let ip = client.get(url).send()?.text()?;
    return Ok(ip);
}

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

fn get_int_input() -> i32 {
    let mut input_text = String::new();
    std::io::stdin()
        .read_line(&mut input_text)
        .expect("Failed to read user input.");

    let input_int = match input_text.trim().parse::<i32>() {
        Ok(i) => i,
        Err(_err) => -1,
    };

    return input_int;
}

fn main() {
    println!("\n\n----------------Worker node for t.me/vaccinecowinbot----------------\n\n");

    println!("Do you want this process to prioritise a pincode? Enter valid pincode, then press enter. To skip, press Enter.");
    let prioritise_pincode = get_int_input();
    let mut option = -1;

    if prioritise_pincode > 0 {
        println!("How often do you want to check? \n\n1. Every 10 seconds. \n2. Every 20 seconds. \n3. Every 30 seconds. \n4. Every 40 seconds. \n5. Every 50 seconds. \n6. Every minute. \n\nChoose from options 1 to 6.");
        option = get_int_input();
        if option < 1 || option > 6 {
            println!("Invalid option was chosen.");
            return;
        }
    }

    if prioritise_pincode > 0 {
        println!(
            "Pincode [{}] will be checked by this node every [{}] seconds.\n",
            prioritise_pincode,
            option * 10
        );
    }

    let mut ip = String::from("");
    let server_url = "";

    let mut i = 0;
    loop {
        if i > 0 {
            thread::sleep(Duration::from_secs(10));
        }

        println!("\n--------------- new iteration --------------");
        
        let pincode;
        if prioritise_pincode > 0 && (i % option) == 0 {
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

        if pincode <= 0 {
            println!("Failed to fetch pincode from server.");
            continue;
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

        // avoid updating so frequently, do it every 5 minutes, each loop takes about 10 seconds
        if i % 30 == 0 {
            ip = match get_external_ip() {
                Ok(res) => res,
                Err(_err) => {
                    println!("Failed to fetch client metadata.");
                    continue;
                }
            };
        }

        let key = format!("{}_{}", pincode, ip);
        let iv = format!("{}_{}", pincode, ip);
        let raw_data = format!("{}_{}", pincode, pincode_info);

        let encrypted_pincode_info = encrypt_aes256(&raw_data, &key, &iv);

        let index_error_code = match index_pincode(server_url, pincode, encrypted_pincode_info) {
            Ok(i) => i,
            Err(_err) => {
                println!("Failed to index pincode [{}] to server.", pincode);
                continue;
            }
        };

        let message = if index_error_code == 0 {
            "Data saved."
        } else if index_error_code == 2 {
            "Some other node had recently submitted data for this pincode."
        } else if index_error_code == 3 {
            "This is not a valid pincode."
        } else if index_error_code == 4 {
            "No user requested for this pincode."
        } else if index_error_code == 5 {
            "Data not from trusted source."
        } else {
            "Failed to save information."
        };

        println!("Pincode [{}], message [{}].", pincode, message);
        i += 1;
    }
}

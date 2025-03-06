from flask import Flask, render_template, request, jsonify
import json
import datetime
import os

app = Flask(__name__)

METAL_RATES_FILE = "metal_rates.json"

# ✅ Fetch the latest gold, silver & exchange rates from JSON
def get_live_metal_rates():
    today = datetime.date.today().strftime("%Y-%m-%d")
    if os.path.exists(METAL_RATES_FILE):
        with open(METAL_RATES_FILE, "r") as file:
            try:
                data = json.load(file)
                if data.get("date") == today:
                    return data.get("gold_24k_rate"), data.get("silver_rate"), data.get("exchange_rate", 90)
            except json.JSONDecodeError:
                os.remove(METAL_RATES_FILE)  # Delete corrupted data
    return None, None, 90  # Default exchange rate if not set

@app.route('/')
def index():
    return render_template('index.html')

# ✅ Set gold/silver rates and exchange rate
@app.route('/set_rates', methods=['POST'])
def set_rates():
    try:
        data = request.get_json()
        with open(METAL_RATES_FILE, "w") as file:
            json.dump({
                "date": datetime.date.today().strftime("%Y-%m-%d"),
                "gold_24k_rate": float(data.get('gold_rate', 0)),
                "silver_rate": float(data.get('silver_rate', 0)),
                "exchange_rate": float(data.get('exchange_rate', 90))  # ✅ INR to USD exchange rate
            }, file)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ✅ Fetch the latest rates for UI
@app.route('/get_rates', methods=['GET'])
def get_rates():
    gold_rate, silver_rate, exchange_rate = get_live_metal_rates()
    if gold_rate is not None and silver_rate is not None:
        return jsonify({'gold_rate': gold_rate, 'silver_rate': silver_rate, 'exchange_rate': exchange_rate})
    return jsonify({'error': 'Rates not set for today'}), 400

# ✅ Calculate the price of jewelry based on user input
@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        product_weight = float(data.get('product_weight', 0))
        total_carat = float(data.get('total_carat', 0))  
        stone_weight = total_carat * 0.2  # Convert carats to grams
        metal_weight = product_weight - stone_weight  # ✅ Correct metal weight calculation

        # ✅ Fetch daily rates
        gold_rate, silver_rate, exchange_rate = get_live_metal_rates()
        if gold_rate is None or silver_rate is None:
            return jsonify({'error': 'Set gold/silver rates first!'}), 400

        # ✅ Define all metal types
        metal_types = {
            '10k_gold': {'purity': 0.417, 'rate': gold_rate, 'making_charge': 1200},
            '14k_gold': {'purity': 0.583, 'rate': gold_rate, 'making_charge': 1200},
            '18k_gold': {'purity': 0.750, 'rate': gold_rate, 'making_charge': 1200},
            '925_silver': {'purity': 0.925, 'rate': silver_rate, 'making_charge': 800}
        }

        results = {}

        # ✅ Calculate values for each metal type
        for metal, details in metal_types.items():
            pure_metal_used = round(metal_weight * details['purity'], 3)
            pure_metal_value = round(pure_metal_used * details['rate'], 2)
            making_charge = round(product_weight * details['making_charge'], 2)

            # ✅ Calculate stone costs
            stone_costs = {stype: round(total_carat * float(data.get(f"{stype}_price", 0)), 2) for stype in ['natural', 'moissanite', 'lab_grown']}

            # ✅ Final Total Costs in INR & USD
            total_costs_inr = {stype: pure_metal_value + making_charge + cost for stype, cost in stone_costs.items()}
            total_costs_usd = {stype: round(total_costs_inr[stype] / exchange_rate, 2) for stype in total_costs_inr}

            # ✅ Store results
            results[metal] = {
                'total_costs_inr': total_costs_inr,
                'total_costs_usd': total_costs_usd
            }

        return jsonify({'exchange_rate': exchange_rate, 'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
